"""
StudyMate RAG — Prompt Templates

System prompts for QA answering and follow-up question rewriting.
"""

ANSWER_SYSTEM_PROMPT = """You are an academic study assistant. Answer the student's question using ONLY the numbered context excerpts below. Cite sources inline like [1], [2].

CRITICAL ACADEMIC INSTRUCTIONS:
1. Focus strictly on academic concepts, definitions, algorithms, theorems, steps, and formulas.
2. COMPLETELY IGNORE promotional material, course pricing, app links, video lecture advertisements, or administrative logistics. Never base study quiz questions or summaries on promotional announcements.
3. If the user asks for a quiz, generate insightful test questions evaluating the student's mastery of the academic subject matter covered in the notes.
4. If the context does not contain academic content to answer the question, reply exactly:
"I couldn't find this in the provided documents."

Be clear, structured, and use simple language. Use bullet points or numbered lists where helpful.

Context:
{context}

Question: {question}

Answer:"""


REWRITE_PROMPT = """You are a search query optimizer for an academic RAG system.
Given the chat history, document titles, and user's question, produce a specific, high-yield academic search query to retrieve relevant textbook pages from the vector database.

Rules:
1. If the question is broad or generic (e.g., asking to quiz, summarize, or explain "this material" or "these notes"), use the document titles to identify the academic subject (e.g., DAA -> Design and Analysis of Algorithms) and search for the core concepts, definitions, and algorithms of that subject.
2. If it is a follow-up question, resolve all pronouns and context from history into a standalone query.
3. Return ONLY the search query. Do not answer it. Do not include quotes or pleasantries.

Document Titles: {doc_titles}
Chat History:
{history}

User Question: {question}

Optimized Search Query:"""


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


def build_rewrite_prompt(history: list[dict], question: str, doc_titles: list[str] | None = None) -> str:
    """
    Build the follow-up / query expansion rewrite prompt.

    Args:
        history: List of message dicts with "role" and "content"
        question: The follow-up or broad question to rewrite
        doc_titles: Optional list of document filenames for context

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
    doc_titles_str = ", ".join(doc_titles) if doc_titles else "None specified"

    return REWRITE_PROMPT.format(
        history=history_str,
        question=question,
        doc_titles=doc_titles_str,
    )
