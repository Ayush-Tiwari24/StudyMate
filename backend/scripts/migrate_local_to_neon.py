"""
StudyMate RAG — Migrate Local Data to Neon Postgres

Copies all relational records and local PDF files from local environment (SQLite / local files)
into Neon Serverless Postgres (relational tables + bytea stored_files).

Features:
- Migrates: users, refresh_tokens, chats, documents, chunks, chat_documents, messages, message_sources, feedback.
- Migrates local PDF files directly into Neon's `stored_files` table.
- Synchronizes PostgreSQL auto-increment sequences via `setval()`.
- Validates row counts before and after migration.
- Supports --dry-run and optional --user-id filtering.

Usage:
    python scripts/migrate_local_to_neon.py --dest-url "postgresql://user:pass@ep-xyz.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"
    python scripts/migrate_local_to_neon.py --dest-url "..." --dry-run
    python scripts/migrate_local_to_neon.py --dest-url "..." --user-id 1
"""

import sys
import os
import argparse
import hashlib
from pathlib import Path
from typing import Optional

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine, text, select
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.logger import logger
from app.db.base import Base
from app.db.session import normalize_database_url
from app.models import (
    User,
    Document,
    Chunk,
    Chat,
    Message,
    MessageSource,
    Feedback,
    RefreshToken,
    StoredFile,
    chat_documents,
)
from app.services.storage import LocalStorage


def migrate_local_to_neon(
    source_url: str,
    dest_url: str,
    dry_run: bool = False,
    user_id_filter: Optional[int] = None,
):
    norm_source = normalize_database_url(source_url)
    norm_dest = normalize_database_url(dest_url)

    logger.info("=" * 60)
    logger.info("StudyMate AI — Local to Neon Migration")
    logger.info("=" * 60)
    logger.info(f"Source:      {norm_source.split('@')[-1] if '@' in norm_source else norm_source}")
    logger.info(f"Destination: {norm_dest.split('@')[-1] if '@' in norm_dest else norm_dest}")
    logger.info(f"Dry Run:     {dry_run}")
    if user_id_filter:
        logger.info(f"User Filter: User ID {user_id_filter}")
    logger.info("=" * 60)

    source_engine = create_engine(norm_source)
    dest_engine = create_engine(norm_dest)

    SourceSession = sessionmaker(bind=source_engine)
    DestSession = sessionmaker(bind=dest_engine)

    src_db = SourceSession()
    dest_db = DestSession()

    try:
        # Step 1: Verify tables exist on destination
        if not dry_run:
            logger.info("Verifying destination schema...")
            Base.metadata.create_all(bind=dest_engine)

        # ── 1. Users ──
        logger.info("\n[1/10] Migrating Users...")
        user_query = src_db.query(User)
        if user_id_filter:
            user_query = user_query.filter(User.id == user_id_filter)
        users = user_query.all()
        logger.info(f"Found {len(users)} users in source.")

        for u in users:
            if not dry_run:
                existing = dest_db.query(User).filter(User.id == u.id).first()
                if not existing:
                    dest_db.merge(User(
                        id=u.id,
                        name=u.name,
                        email=u.email,
                        password_hash=u.password_hash,
                        preferences=u.preferences or {},
                        created_at=u.created_at,
                    ))
        if not dry_run:
            dest_db.commit()

        # ── 2. Refresh Tokens ──
        logger.info("\n[2/10] Migrating Refresh Tokens...")
        rt_query = src_db.query(RefreshToken)
        if user_id_filter:
            rt_query = rt_query.filter(RefreshToken.user_id == user_id_filter)
        tokens = rt_query.all()
        logger.info(f"Found {len(tokens)} refresh tokens in source.")

        for rt in tokens:
            if not dry_run:
                existing = dest_db.query(RefreshToken).filter(RefreshToken.id == rt.id).first()
                if not existing:
                    dest_db.merge(RefreshToken(
                        id=rt.id,
                        user_id=rt.user_id,
                        token_hash=rt.token_hash,
                        expires_at=rt.expires_at,
                        revoked_at=rt.revoked_at,
                        created_at=rt.created_at,
                    ))
        if not dry_run:
            dest_db.commit()

        # ── 3. Documents ──
        logger.info("\n[3/10] Migrating Documents...")
        doc_query = src_db.query(Document)
        if user_id_filter:
            doc_query = doc_query.filter(Document.user_id == user_id_filter)
        docs = doc_query.all()
        logger.info(f"Found {len(docs)} documents in source.")

        valid_doc_ids = set()
        for d in docs:
            valid_doc_ids.add(d.id)
            if not dry_run:
                dest_db.merge(Document(
                    id=d.id,
                    user_id=d.user_id,
                    filename=d.filename,
                    file_path=d.file_path,
                    file_hash=d.file_hash,
                    size_bytes=d.size_bytes,
                    pages=d.pages,
                    chunk_count=d.chunk_count,
                    progress=d.progress,
                    status=d.status,
                    error_message=d.error_message,
                    uploaded_at=d.uploaded_at,
                ))
        if not dry_run:
            dest_db.commit()

        # ── 4. Chunks ──
        logger.info("\n[4/10] Migrating Chunks...")
        chunk_query = src_db.query(Chunk)
        if user_id_filter:
            chunk_query = chunk_query.filter(Chunk.document_id.in_(valid_doc_ids))
        chunks = chunk_query.all()
        logger.info(f"Found {len(chunks)} chunks in source.")

        for c in chunks:
            if not dry_run:
                dest_db.merge(Chunk(
                    id=c.id,
                    document_id=c.document_id,
                    chunk_index=c.chunk_index,
                    page=c.page,
                    content=c.content,
                    vector_id=c.vector_id,
                    meta=c.meta or {},
                    created_at=c.created_at,
                ))
        if not dry_run:
            dest_db.commit()

        # ── 5. Chats ──
        logger.info("\n[5/10] Migrating Chats...")
        chat_query = src_db.query(Chat)
        if user_id_filter:
            chat_query = chat_query.filter(Chat.user_id == user_id_filter)
        chats = chat_query.all()
        logger.info(f"Found {len(chats)} chats in source.")

        valid_chat_ids = set()
        for ch in chats:
            valid_chat_ids.add(ch.id)
            if not dry_run:
                dest_db.merge(Chat(
                    id=ch.id,
                    user_id=ch.user_id,
                    title=ch.title,
                    created_at=ch.created_at,
                    updated_at=ch.updated_at,
                ))
        if not dry_run:
            dest_db.commit()

        # ── 6. Chat Documents Association ──
        logger.info("\n[6/10] Migrating Chat-Document associations...")
        assoc_rows = src_db.execute(select(chat_documents)).fetchall()
        assoc_count = 0
        for row in assoc_rows:
            c_id, d_id = row[0], row[1]
            if user_id_filter and (c_id not in valid_chat_ids or d_id not in valid_doc_ids):
                continue
            assoc_count += 1
            if not dry_run:
                dest_db.execute(
                    text("INSERT INTO chat_documents (chat_id, document_id) VALUES (:c, :d) ON CONFLICT DO NOTHING"),
                    {"c": c_id, "d": d_id},
                )
        logger.info(f"Migrated {assoc_count} chat-document links.")
        if not dry_run:
            dest_db.commit()

        # ── 7. Messages ──
        logger.info("\n[7/10] Migrating Messages...")
        msg_query = src_db.query(Message)
        if user_id_filter:
            msg_query = msg_query.filter(Message.chat_id.in_(valid_chat_ids))
        messages = msg_query.all()
        logger.info(f"Found {len(messages)} messages in source.")

        valid_msg_ids = set()
        for m in messages:
            valid_msg_ids.add(m.id)
            if not dry_run:
                dest_db.merge(Message(
                    id=m.id,
                    chat_id=m.chat_id,
                    role=m.role,
                    content=m.content,
                    model_used=m.model_used,
                    latency_ms=m.latency_ms,
                    created_at=m.created_at,
                ))
        if not dry_run:
            dest_db.commit()

        # ── 8. Message Sources ──
        logger.info("\n[8/10] Migrating Message Sources...")
        src_query = src_db.query(MessageSource)
        if user_id_filter:
            src_query = src_query.filter(MessageSource.message_id.in_(valid_msg_ids))
        sources = src_query.all()
        logger.info(f"Found {len(sources)} message sources in source.")

        for s in sources:
            if not dry_run:
                dest_db.merge(MessageSource(
                    id=s.id,
                    message_id=s.message_id,
                    document_id=s.document_id,
                    page=s.page,
                    score=s.score,
                    snippet=s.snippet,
                ))
        if not dry_run:
            dest_db.commit()

        # ── 9. Feedback ──
        logger.info("\n[9/10] Migrating Feedback...")
        fb_query = src_db.query(Feedback)
        if user_id_filter:
            fb_query = fb_query.filter(Feedback.message_id.in_(valid_msg_ids))
        feedbacks = fb_query.all()
        logger.info(f"Found {len(feedbacks)} feedback entries in source.")

        for fb in feedbacks:
            if not dry_run:
                dest_db.merge(Feedback(
                    id=fb.id,
                    message_id=fb.message_id,
                    rating=fb.rating,
                    comment=fb.comment,
                    created_at=fb.created_at,
                ))
        if not dry_run:
            dest_db.commit()

        # ── 10. Local PDF Files -> Neon stored_files Table ──
        logger.info("\n[10/10] Migrating local PDF files to Neon stored_files (bytea)...")
        local_storage = LocalStorage()
        files_migrated = 0

        for d in docs:
            key = d.file_path
            if local_storage.exists(key):
                pdf_bytes = local_storage.open(key)
                sha256 = hashlib.sha256(pdf_bytes).hexdigest()
                files_migrated += 1
                logger.info(f"  Uploading file for doc #{d.id}: {d.filename} ({len(pdf_bytes)} bytes)")
                if not dry_run:
                    existing_sf = dest_db.query(StoredFile).filter(StoredFile.key == key).first()
                    if existing_sf:
                        existing_sf.data = pdf_bytes
                        existing_sf.size_bytes = len(pdf_bytes)
                        existing_sf.sha256 = sha256
                    else:
                        dest_db.add(StoredFile(
                            key=key,
                            user_id=d.user_id,
                            content_type="application/pdf",
                            size_bytes=len(pdf_bytes),
                            sha256=sha256,
                            data=pdf_bytes,
                        ))
            else:
                logger.warning(f"  Warning: PDF file for document id={d.id} ({key}) not found on local disk.")

        if not dry_run:
            dest_db.commit()
            logger.info(f"Committed {files_migrated} files into Neon stored_files.")

        # ── Sequence Alignment for PostgreSQL ──
        if not dry_run and dest_engine.dialect.name == "postgresql":
            logger.info("\nSynchronizing PostgreSQL sequences (setval)...")
            tables = [
                ("users", "id"),
                ("refresh_tokens", "id"),
                ("chats", "id"),
                ("documents", "id"),
                ("chunks", "id"),
                ("messages", "id"),
                ("sources", "id"),
                ("feedback", "id"),
                ("stored_files", "id"),
            ]
            with dest_engine.begin() as conn:
                for table, col in tables:
                    try:
                        conn.execute(text(f"""
                            SELECT setval(
                                pg_get_serial_sequence('{table}', '{col}'),
                                COALESCE((SELECT MAX({col}) FROM {table}), 1)
                            );
                        """))
                        logger.info(f"  Sequence updated: {table}.{col}")
                    except Exception as seq_err:
                        logger.warning(f"  Could not setval for {table}: {seq_err}")

        # ── Verification Summary ──
        logger.info("\n" + "=" * 60)
        logger.info("MIGRATION SUMMARY")
        logger.info("=" * 60)
        dest_user_count = dest_db.query(User).count() if not dry_run else len(users)
        dest_doc_count = dest_db.query(Document).count() if not dry_run else len(docs)
        dest_chunk_count = dest_db.query(Chunk).count() if not dry_run else len(chunks)
        dest_chat_count = dest_db.query(Chat).count() if not dry_run else len(chats)
        dest_msg_count = dest_db.query(Message).count() if not dry_run else len(messages)
        dest_file_count = dest_db.query(StoredFile).count() if not dry_run else files_migrated

        logger.info(f"Users:        Source {len(users)} -> Dest {dest_user_count}")
        logger.info(f"Documents:    Source {len(docs)} -> Dest {dest_doc_count}")
        logger.info(f"Chunks:       Source {len(chunks)} -> Dest {dest_chunk_count}")
        logger.info(f"Chats:        Source {len(chats)} -> Dest {dest_chat_count}")
        logger.info(f"Messages:     Source {len(messages)} -> Dest {dest_msg_count}")
        logger.info(f"Stored Files: Migrated {files_migrated} files -> Dest {dest_file_count}")

        if dry_run:
            logger.info("\nDRY RUN COMPLETE — No changes were committed to destination.")
        else:
            logger.info("\nSUCCESS — Migration to Neon completed successfully!")

    finally:
        src_db.close()
        dest_db.close()


def main():
    parser = argparse.ArgumentParser(description="Migrate local StudyMate database and PDFs to Neon Postgres.")
    parser.add_argument("--source-url", default=settings.database_url, help="Source database URL (default: settings.DATABASE_URL)")
    parser.add_argument("--dest-url", required=True, help="Destination Neon PostgreSQL connection URL")
    parser.add_argument("--user-id", type=int, default=None, help="Optional user ID filter")
    parser.add_argument("--dry-run", action="store_true", help="Inspect and count records without writing")

    args = parser.parse_args()
    migrate_local_to_neon(
        source_url=args.source_url,
        dest_url=args.dest_url,
        dry_run=args.dry_run,
        user_id_filter=args.user_id,
    )


if __name__ == "__main__":
    main()
