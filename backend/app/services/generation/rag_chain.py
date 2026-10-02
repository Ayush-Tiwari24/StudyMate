"""
StudyMate RAG — RAG Chain

The full query pipeline:
1. Load chat history
2. Rewrite follow-up questions into standalone questions
3. Retrieve relevant chunks
4. (Optional) Rerank
5. Build prompt with context
6. Stream LLM response (filtering reasoning tokens)
7. Yield token and source events (only cited sources)

This is an async generator used by the chat SSE endpoint.
"""

import re
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


class ReasoningFilter:
    """
    Filters out reasoning tokens (such as <think>...</think>, <thought>...</thought>)
    and any reasoning_content from LLM streams, ensuring only final answer text is forwarded.
    """
    def __init__(self):
        self.in_think = False
        self.buffer = ""

    def process_chunk(self, chunk) -> str:
        # Ignore reasoning metadata if present
        if hasattr(chunk, "additional_kwargs") and "reasoning_content" in chunk.additional_kwargs:
            pass

        content = chunk.content if hasattr(chunk, "content") else str(chunk)
        if not isinstance(content, str) or not content:
            return ""

        self.buffer += content
        output = []

        while self.buffer:
            if not self.in_think:
                lower_buf = self.buffer.lower()
                open_think = lower_buf.find("<think>")
                open_thought = lower_buf.find("<thought>")
                candidates = [pos for pos in (open_think, open_thought) if pos != -1]
                if not candidates:
                    # Check for partial opening tags at the end of buffer
                    potential_partial = False
                    for tag in ("<think>", "<thought>"):
                        for i in range(1, len(tag)):
                            if lower_buf.endswith(tag[:i]):
                                potential_partial = True
                                break
                        if potential_partial:
                            break

                    if potential_partial:
                        max_partial = 0
                        for tag in ("<think>", "<thought>"):
                            for i in range(1, len(tag)):
                                if lower_buf.endswith(tag[:i]) and i > max_partial:
                                    max_partial = i
                        safe_emit = self.buffer[:-max_partial]
                        self.buffer = self.buffer[-max_partial:]
                        output.append(safe_emit)
                    else:
                        output.append(self.buffer)
                        self.buffer = ""
                    break
                else:
                    earliest_pos = min(candidates)
                    tag_len = 7 if earliest_pos == open_think else 9
                    output.append(self.buffer[:earliest_pos])
                    self.buffer = self.buffer[earliest_pos + tag_len:]
                    self.in_think = True
            else:
                lower_buf = self.buffer.lower()
                close_think = lower_buf.find("</think>")
                close_thought = lower_buf.find("</thought>")
                candidates = [pos for pos in (close_think, close_thought) if pos != -1]
                if not candidates:
                    max_partial = 0
                    for tag in ("</think>", "</thought>"):
                        for i in range(1, len(tag)):
                            if lower_buf.endswith(tag[:i]) and i > max_partial:
                                max_partial = i
                    if max_partial > 0:
                        self.buffer = self.buffer[-max_partial:]
                    else:
                        self.buffer = ""
                    break
                else:
                    earliest_pos = min(candidates)
                    tag_len = 8 if earliest_pos == close_think else 10
                    self.buffer = self.buffer[earliest_pos + tag_len:]
                    self.in_think = False

        return "".join(output)

    def flush(self) -> str:
        if not self.in_think and self.buffer:
            res = self.buffer
            self.buffer = ""
            return res
        self.buffer = ""
        return ""


def clean_rewritten_query(raw_text: str) -> str:
    """
    Clean the output from a question rewrite model.
    Strips reasoning blocks (<think>...</think>), preamble labels,
    and returns a short plain question.
    """
    if not raw_text:
        return ""

    # Strip reasoning tags
    text = re.sub(r'<think>.*?</think>', '', raw_text, flags=re.DOTALL)
    text = re.sub(r'<thought>.*?</thought>', '', text, flags=re.DOTALL)

    lines = [line.strip() for line in text.split("\n") if line.strip()]
    if not lines:
        return ""

    clean_lines = []
    for line in lines:
        l = re.sub(
            r'^(optimized\s+search\s+query|search\s+query|standalone\s+query|rewritten\s+question|query):\s*',
            '',
            line,
            flags=re.IGNORECASE
        ).strip().strip('"').strip("'")
        if l and not l.lower().startswith(("here is", "i will", "based on", "the user", "to find", "retrieving")):
            clean_lines.append(l)

    result = clean_lines[-1] if clean_lines else lines[0]
    result = result.strip().strip('"').strip("'")
    return result


async def rag_query(
    question: str,
    chat_id: int,
    user_id: int,
    document_ids: list[int],
    top_k: int | None = None,
    db: Session = None,
    user_preferences: dict | None = None,
) -> AsyncGenerator[dict, None]:
    """
    Execute the full RAG pipeline and yield SSE events.

    Yields:
        {"type": "token", "text": "..."}   — streamed answer tokens
        {"type": "sources", "sources": [...]} — citation metadata
    """
    prefs = user_preferences or {}
    pref_top_k = prefs.get("top_k")
    pref_provider = prefs.get("llm_provider")
    pref_model = prefs.get("model_name")
    pref_temp = prefs.get("temperature")

    effective_top_k = top_k or pref_top_k or settings.top_k

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

    # ── Step 2: Rewrite follow-up questions / Expand broad queries ──
    doc_titles = []
    if db and document_ids:
        try:
            from app.models.document import Document
            docs = db.query(Document).filter(Document.id.in_(document_ids)).all()
            doc_titles = [d.filename.replace('.pdf', '').strip() for d in docs]
        except Exception as e:
            logger.warning(f"Could not load document titles: {e}")

    standalone_question = question
    is_broad_query = any(k in question.lower() for k in [
        "this material", "these notes", "this document", "these documents",
        "study quiz", "generate a quiz", "summarize", "summary", "overview",
        "core topics", "key concepts", "primary definitions"
    ])

    if (history and len(history) >= 2) or (is_broad_query and doc_titles):
        rewrite_prompt = build_rewrite_prompt(history, question, doc_titles=doc_titles)
        candidate = None
        try:
            rewrite_llm = get_llm_for_rewrite(provider=pref_provider, model_name=pref_model)
            response = rewrite_llm.invoke(rewrite_prompt)
            candidate = clean_rewritten_query(response.content)
        except Exception as e:
            logger.warning(f"Question rewrite failed on primary model: {e}")
            active_provider = pref_provider or settings.llm_provider
            if active_provider == "groq" and (pref_model != settings.groq_fallback_model):
                try:
                    logger.info(f"Retrying rewrite with fallback model {settings.groq_fallback_model}")
                    rewrite_llm = get_llm_for_rewrite(provider="groq", model_name=settings.groq_fallback_model)
                    response = rewrite_llm.invoke(rewrite_prompt)
                    candidate = clean_rewritten_query(response.content)
                except Exception as fb_err:
                    logger.warning(f"Fallback rewrite also failed: {fb_err}")

        if candidate and len(candidate) > 5:
            standalone_question = candidate
            logger.info(f"Optimized retrieval query: {standalone_question}")
        else:
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

    # Filter out promotional/advertisement cover pages if other chunks exist
    def is_promo(text: str) -> bool:
        t = text.lower().replace(" ", "").replace("\n", "")
        return any(sig in t for sig in ["gatewayclasses", "paidcourses", "recordedvideolecture", "linkindescription"])

    non_promo = [c for c in chunks if not is_promo(c["content"])]
    if non_promo:
        chunks = non_promo

    # ── Step 5: Rerank (optional) ──────────────────────────────
    if settings.rerank_enabled:
        chunks = rerank_chunks(standalone_question, chunks, top_n=effective_top_k)
    else:
        chunks = chunks[:effective_top_k]

    # ── Step 6: Build prompt ───────────────────────────────────
    prompt = build_answer_prompt(chunks, standalone_question)

    # ── Step 7: Stream LLM response ───────────────────────────
    llm = get_llm(
        streaming=True,
        provider=pref_provider,
        model_name=pref_model,
        temperature=pref_temp,
    )

    reasoning_filter = ReasoningFilter()
    full_answer_parts = []

    try:
        async for chunk in llm.astream(prompt):
            token_text = reasoning_filter.process_chunk(chunk)
            if token_text:
                full_answer_parts.append(token_text)
                yield {"type": "token", "text": token_text}
        tail = reasoning_filter.flush()
        if tail:
            full_answer_parts.append(tail)
            yield {"type": "token", "text": tail}
    except Exception as e:
        logger.error(f"LLM streaming error on primary model: {e}")
        active_provider = pref_provider or settings.llm_provider
        # If no tokens have been streamed yet, attempt fallback model
        if not full_answer_parts and active_provider == "groq" and (pref_model != settings.groq_fallback_model):
            try:
                logger.info(f"Attempting fallback to Groq model {settings.groq_fallback_model}")
                fb_llm = get_llm(
                    streaming=True,
                    provider="groq",
                    model_name=settings.groq_fallback_model,
                    temperature=pref_temp,
                )
                fb_filter = ReasoningFilter()
                async for chunk in fb_llm.astream(prompt):
                    token_text = fb_filter.process_chunk(chunk)
                    if token_text:
                        full_answer_parts.append(token_text)
                        yield {"type": "token", "text": token_text}
                tail = fb_filter.flush()
                if tail:
                    full_answer_parts.append(tail)
                    yield {"type": "token", "text": tail}
            except Exception as fb_err:
                logger.error(f"Fallback LLM error: {fb_err}")
                yield {"type": "token", "text": f"\n\n[Error: {str(fb_err)}]"}
        else:
            yield {"type": "token", "text": f"\n\n[Error: {str(e)}]"}

    # ── Step 8: Yield sources (matching citations in answer) ────
    full_answer_text = "".join(full_answer_parts)
    cited_ids = {int(m) for m in re.findall(r'\[(\d+)\]', full_answer_text)}

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

    # Filter to only return sources cited inline [1], [2], etc., if citations are present
    if cited_ids:
        cited_sources = [s for s in sources if s["id"] in cited_ids]
        if cited_sources:
            sources = cited_sources

    yield {"type": "sources", "sources": sources}
