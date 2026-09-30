"""
StudyMate RAG — RAG Chain

The full query pipeline:
1. Load chat history
2. Rewrite follow-up questions into standalone questions
3. Retrieve relevant chunks
4. (Optional) Rerank
5. Build prompt with context
6. Stream LLM response
7. Yield token and source events

This is an async generator used by the chat SSE endpoint.
"""

from typing import AsyncGenerator

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logger import logger
from app.models.message import Message
from app.services.retrieval.retriever import retrieve_chunks
from app.services.retrieval.reranker import rerank_chunks
from app.services.generation.prompts import build_answer_prompt, build_rewrite_prompt
from app.services.generation.llm import get_llm, get_llm_for_rewrite


NOT_FOUND_MESSAGE = "I couldn't find this in the provided documents."


async def rag_query(
    question: str,
    chat_id: int,
    user_id: int,
    document_ids: list[int],
    top_k: int | None = None,
    db: Session = None,
) -> AsyncGenerator[dict, None]:
    """
    Execute the full RAG pipeline and yield SSE events.

    Yields:
        {"type": "token", "text": "..."}   — streamed answer tokens
        {"type": "sources", "sources": [...]} — citation metadata
    """
    top_k = top_k or settings.top_k

    # ── Step 1: Load chat history ──────────────────────────────
    history = []
    if db:
        recent_msgs = (
            db.query(Message)
            .filter(Message.chat_id == chat_id)
            .order_by(Message.created_at.desc())
            .limit(settings.history_window * 2)  # user + assistant pairs
            .all()
        )
        recent_msgs.reverse()  # Chronological order
        history = [{"role": m.role, "content": m.content} for m in recent_msgs]

    # ── Step 2: Rewrite follow-up questions ────────────────────
    standalone_question = question
    if history and len(history) >= 2:
        try:
            rewrite_llm = get_llm_for_rewrite()
            rewrite_prompt = build_rewrite_prompt(history, question)
            response = rewrite_llm.invoke(rewrite_prompt)
            standalone_question = response.content.strip()
            logger.info(f"Rewritten question: {standalone_question}")
        except Exception as e:
            logger.warning(f"Question rewrite failed, using original: {e}")
            standalone_question = question

    # ── Step 3: Retrieve relevant chunks ───────────────────────
    chunks = retrieve_chunks(
        question=standalone_question,
        user_id=user_id,
        document_ids=document_ids,
        top_k=settings.fetch_k,  # Fetch more for reranking
    )

    # ── Step 4: Handle "not found" case ────────────────────────
    if not chunks:
        yield {"type": "token", "text": NOT_FOUND_MESSAGE}
        yield {"type": "sources", "sources": []}
        return

    # ── Step 5: Rerank (optional) ──────────────────────────────
    if settings.rerank_enabled:
        chunks = rerank_chunks(standalone_question, chunks, top_n=top_k)
    else:
        chunks = chunks[:top_k]

    # ── Step 6: Build prompt ───────────────────────────────────
    prompt = build_answer_prompt(chunks, standalone_question)

    # ── Step 7: Stream LLM response ───────────────────────────
    llm = get_llm(streaming=True)

    try:
        async for chunk in llm.astream(prompt):
            token_text = chunk.content
            if token_text:
                yield {"type": "token", "text": token_text}
    except Exception as e:
        logger.error(f"LLM streaming error: {e}")
        yield {"type": "token", "text": f"\n\n[Error: {str(e)}]"}

    # ── Step 8: Yield sources ──────────────────────────────────
    sources = []
    for i, chunk in enumerate(chunks):
        meta = chunk["metadata"]
        sources.append({
            "id": i + 1,
            "file": meta.get("filename", "unknown"),
            "document_id": meta.get("document_id"),
            "page": meta.get("page"),
            "score": chunk.get("score"),
            "snippet": chunk["content"][:200],
        })

    yield {"type": "sources", "sources": sources}
