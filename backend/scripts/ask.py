"""
StudyMate RAG — CLI Ask Script

Usage:
    python -m scripts.ask --question "What is normalization?" --user-id 1 --doc-ids 1,2

Ask a question from the command line without the web UI.
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionLocal
from app.services.generation.rag_chain import rag_query


async def ask(question: str, user_id: int, doc_ids: list[int]):
    db = SessionLocal()
    try:
        print(f"\n❓ Question: {question}")
        print(f"📚 Searching documents: {doc_ids}")
        print(f"\n{'─' * 60}")
        print("🤖 Answer:\n")

        sources = []
        async for event in rag_query(
            question=question,
            chat_id=0,  # No chat context for CLI
            user_id=user_id,
            document_ids=doc_ids,
            db=db,
        ):
            if event["type"] == "token":
                print(event["text"], end="", flush=True)
            elif event["type"] == "sources":
                sources = event["sources"]

        print(f"\n\n{'─' * 60}")
        if sources:
            print("\n📖 Sources:")
            for s in sources:
                print(f"  [{s['id']}] {s['file']} — p.{s['page']} (score: {s.get('score', 'N/A')})")
                if s.get("snippet"):
                    print(f"      \"{s['snippet'][:100]}...\"")
        else:
            print("\n(No sources)")

    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Ask a question via CLI")
    parser.add_argument("--question", "-q", required=True, help="Your question")
    parser.add_argument("--user-id", type=int, default=1, help="User ID")
    parser.add_argument("--doc-ids", required=True, help="Comma-separated document IDs")
    args = parser.parse_args()

    doc_ids = [int(x.strip()) for x in args.doc_ids.split(",")]
    asyncio.run(ask(args.question, args.user_id, doc_ids))


if __name__ == "__main__":
    main()
