"""
StudyMate RAG — Text Chunker

Splits cleaned page text into overlapping chunks with metadata.
Uses RecursiveCharacterTextSplitter logic: split on paragraph → sentence → word.
"""

from app.core.config import settings
from app.core.logger import logger


def chunk_pages(
    pages: list[dict],
    document_id: int,
    filename: str,
    user_id: int,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[dict]:
    """
    Split page texts into overlapping chunks with metadata.

    Args:
        pages: List of {"page": int, "text": str}
        document_id: DB document ID
        filename: Original filename
        user_id: Owner user ID
        chunk_size: Max characters per chunk (default from settings)
        chunk_overlap: Overlap between chunks (default from settings)

    Returns:
        List of chunk dicts with keys:
        - content: str
        - metadata: {user_id, document_id, filename, page, chunk_index}
    """
    chunk_size = chunk_size or settings.chunk_size
    chunk_overlap = chunk_overlap or settings.chunk_overlap

    # Separators: paragraph → sentence → word
    separators = ["\n\n", "\n", ". ", " ", ""]

    all_chunks = []
    global_chunk_index = 0

    for page_data in pages:
        page_num = page_data["page"]
        text = page_data["text"]

        if not text.strip():
            continue

        # Split this page's text into chunks
        page_chunks = _recursive_split(text, chunk_size, chunk_overlap, separators)

        for chunk_text in page_chunks:
            if not chunk_text.strip():
                continue

            all_chunks.append({
                "content": chunk_text.strip(),
                "metadata": {
                    "user_id": user_id,
                    "document_id": document_id,
                    "filename": filename,
                    "page": page_num,
                    "chunk_index": global_chunk_index,
                },
            })
            global_chunk_index += 1

    logger.info(
        f"Chunked document {filename}: {len(pages)} pages -> {len(all_chunks)} chunks "
        f"(size={chunk_size}, overlap={chunk_overlap})"
    )
    return all_chunks


def _recursive_split(
    text: str,
    chunk_size: int,
    chunk_overlap: int,
    separators: list[str],
) -> list[str]:
    """
    Recursively split text using the best available separator.
    Mirrors LangChain's RecursiveCharacterTextSplitter logic.
    """
    if len(text) <= chunk_size:
        return [text]

    # Find the best separator (first one that exists in text)
    separator = ""
    for sep in separators:
        if sep in text:
            separator = sep
            break

    # Split text by the chosen separator
    if separator:
        parts = text.split(separator)
    else:
        # Last resort: character-level split
        parts = list(text)

    # Merge parts into chunks respecting chunk_size
    chunks = []
    current_chunk = ""

    for part in parts:
        candidate = current_chunk + (separator if current_chunk else "") + part

        if len(candidate) <= chunk_size:
            current_chunk = candidate
        else:
            if current_chunk:
                chunks.append(current_chunk)

            # If a single part exceeds chunk_size, recursively split it
            if len(part) > chunk_size:
                remaining_seps = separators[separators.index(separator) + 1:] if separator in separators else separators[1:]
                sub_chunks = _recursive_split(part, chunk_size, chunk_overlap, remaining_seps or [""])
                chunks.extend(sub_chunks[:-1])
                current_chunk = sub_chunks[-1] if sub_chunks else ""
            else:
                current_chunk = part

    if current_chunk:
        chunks.append(current_chunk)

    # Apply overlap: prepend the end of the previous chunk to the next
    if chunk_overlap > 0 and len(chunks) > 1:
        overlapped = [chunks[0]]
        for i in range(1, len(chunks)):
            prev = chunks[i - 1]
            overlap_text = prev[-chunk_overlap:] if len(prev) > chunk_overlap else prev
            overlapped.append(overlap_text + separator + chunks[i])
        chunks = overlapped

    return chunks
