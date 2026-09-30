"""
StudyMate RAG — Prompt Templates

System prompts for QA answering and follow-up question rewriting.
"""

ANSWER_SYSTEM_PROMPT = """You are an academic assistant. Answer the student's question using ONLY the numbered context below. Cite sources inline like [1], [2].

If the context does not contain the answer, reply exactly:
"I couldn't find this in the provided documents."

Be clear, structured, and use simple language. Use bullet points or steps where helpful.

Context:
{context}

Question: {question}

Answer:"""


REWRITE_PROMPT = """Given the chat history and the latest question, rewrite the latest question so it is fully standalone. Do not answer it.

History:
{history}

Latest question: {question}

Standalone question:"""


def build_answer_prompt(context_chunks: list[dict], question: str) -> str:
    """
    Build the answer prompt by inserting numbered context blocks.

    Args:
        context_chunks: List of chunk dicts with "content" and "metadata"
        question: The user's question

    Returns:
        The formatted prompt string.
    """
    context_lines = []
    for i, chunk in enumerate(context_chunks, 1):
        meta = chunk["metadata"]
        filename = meta.get("filename", "unknown")
        page = meta.get("page", "?")
        context_lines.append(f"[{i}] ({filename}, p.{page}): {chunk['content']}")

    context_str = "\n\n".join(context_lines)

    return ANSWER_SYSTEM_PROMPT.format(context=context_str, question=question)


def build_rewrite_prompt(history: list[dict], question: str) -> str:
    """
    Build the follow-up rewrite prompt.

    Args:
        history: List of message dicts with "role" and "content"
        question: The follow-up question to rewrite

    Returns:
        The formatted rewrite prompt.
    """
    history_lines = []
    for msg in history:
        role = "User" if msg["role"] == "user" else "Assistant"
        # Truncate long messages
        content = msg["content"][:300] + "..." if len(msg["content"]) > 300 else msg["content"]
        history_lines.append(f"{role}: {content}")

    history_str = "\n".join(history_lines) if history_lines else "(no prior messages)"

    return REWRITE_PROMPT.format(history=history_str, question=question)
