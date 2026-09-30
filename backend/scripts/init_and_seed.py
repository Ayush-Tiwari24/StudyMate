"""
Seed database with default users and re-index existing raw PDF if needed.
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.core.security import hash_password
from app.models.user import User
from app.models.document import Document
from app.services.ingestion.pipeline import run_ingestion_pipeline


def init_db():
    print("Creating all tables on engine...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Seed user 1: amit@university.edu
        user1 = db.query(User).filter(User.email == "amit@university.edu").first()
        if not user1:
            user1 = User(
                id=1,
                name="Prof. Amit Sharma",
                email="amit@university.edu",
                password_hash=hash_password("password123"),
            )
            db.add(user1)
            print("Created user: amit@university.edu (password123)")

        # Seed user 2: student@example.com
        user2 = db.query(User).filter(User.email == "student@example.com").first()
        if not user2:
            user2 = User(
                name="Demo Student",
                email="student@example.com",
                password_hash=hash_password("student123"),
            )
            db.add(user2)
            print("Created user: student@example.com (student123)")

        db.commit()
        db.refresh(user1)

        # Check existing PDF in data/raw_pdfs/1/
        raw_pdf_dir = Path(__file__).resolve().parent.parent / "data" / "raw_pdfs" / "1"
        if raw_pdf_dir.exists():
            pdfs = list(raw_pdf_dir.glob("*.pdf"))
            if pdfs:
                target_pdf = pdfs[0]
                doc = db.query(Document).filter(Document.user_id == user1.id).first()
                if not doc:
                    file_bytes = target_pdf.read_bytes()
                    from app.utils.file_utils import compute_sha256
                    doc = Document(
                        user_id=user1.id,
                        filename="DAA  U-1  Combined Notes.pdf",
                        file_path=str(target_pdf.resolve()),
                        file_hash=compute_sha256(file_bytes),
                        size_bytes=len(file_bytes),
                        status="uploaded",
                    )
                    db.add(doc)
                    db.commit()
                    db.refresh(doc)
                    print(f"Created document record id={doc.id} for {target_pdf.name}")
                    print("Running ingestion pipeline...")
                    run_ingestion_pipeline(doc.id)
                    print("Ingestion pipeline completed!")
                else:
                    print(f"Document already registered: id={doc.id}, status={doc.status}")
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
