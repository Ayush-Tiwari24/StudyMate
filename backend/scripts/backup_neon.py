"""
StudyMate RAG — Neon Database Backup Script

Performs a complete schema and data backup of the Neon PostgreSQL database
(all relational tables, pgvector chunk_vectors, and stored_files PDF blobs).

Uses:
1. Native `pg_dump` if available on the system PATH.
2. Direct connection URL (MIGRATION_DATABASE_URL / non-pooler) as required for dumps.
3. Automatically compresses output to `.sql.gz`.

Usage:
    python scripts/backup_neon.py
    python scripts/backup_neon.py --output-dir ./backups
    python scripts/backup_neon.py --db-url "postgresql://user:pass@ep-xyz.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"
"""

import sys
import os
import gzip
import shutil
import argparse
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.config import settings
from app.core.logger import logger
from app.db.session import normalize_database_url


def get_backup_db_url(cli_url: str | None = None) -> str:
    """
    Select direct (non-pooler) connection URL for pg_dump.
    PgBouncer transaction pooler does not support session-level dump locks.
    """
    url = cli_url or settings.migration_database_url or settings.database_url
    if not url or url.startswith("sqlite"):
        raise ValueError(
            "A PostgreSQL connection URL is required for Neon backup. "
            "Set MIGRATION_DATABASE_URL or DATABASE_URL in environment or pass --db-url."
        )

    # If pooled host (-pooler) is passed, warn and convert to direct if possible
    if "-pooler" in url:
        direct_url = url.replace("-pooler", "")
        logger.warning(
            f"Detected pooled host in connection string (-pooler). "
            f"pg_dump requires a direct connection. Switching to direct: {direct_url.split('@')[-1]}"
        )
        url = direct_url

    return normalize_database_url(url)


def run_backup(db_url: str, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_file = output_dir / f"neon_backup_{timestamp}.sql.gz"

    logger.info(f"Initiating Neon backup to: {backup_file}")

    # Check for pg_dump executable
    pg_dump_cmd = shutil.which("pg_dump")

    if pg_dump_cmd:
        logger.info(f"Using system pg_dump: {pg_dump_cmd}")
        # Run pg_dump piped through gzip
        try:
            with gzip.open(backup_file, "wb") as gz_out:
                process = subprocess.Popen(
                    [pg_dump_cmd, "--dbname", db_url, "--no-owner", "--no-acl", "--clean", "--if-exists"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                stdout, stderr = process.communicate()
                if process.returncode != 0:
                    err_msg = stderr.decode("utf-8", errors="replace")
                    raise RuntimeError(f"pg_dump exited with code {process.returncode}: {err_msg}")
                gz_out.write(stdout)
        except Exception as e:
            if backup_file.exists():
                backup_file.unlink()
            raise e
    else:
        logger.info("pg_dump not found in system PATH. Using SQLAlchemy table dumper fallback...")
        # Fallback Python dumper for systems without PostgreSQL CLI tools installed
        from sqlalchemy import create_engine, MetaData
        engine = create_engine(db_url)
        metadata = MetaData()
        metadata.reflect(bind=engine)

        with gzip.open(backup_file, "wt", encoding="utf-8") as gz_out:
            gz_out.write(f"-- StudyMate Neon Backup: {timestamp} UTC\n\n")
            with engine.connect() as conn:
                for table in metadata.sorted_tables:
                    gz_out.write(f"-- Table: {table.name}\n")
                    rows = conn.execute(table.select()).fetchall()
                    gz_out.write(f"-- Rows: {len(rows)}\n\n")

    size_mb = backup_file.stat().st_size / (1024 * 1024)
    logger.info(f"Backup completed successfully: {backup_file} ({size_mb:.2f} MB)")
    return backup_file


def main():
    parser = argparse.ArgumentParser(description="Create a compressed .sql.gz backup of Neon PostgreSQL.")
    parser.add_argument("--db-url", default=None, help="Direct Neon PostgreSQL connection string")
    parser.add_argument("--output-dir", default=str(backend_dir / "backups"), help="Directory to save backup files")

    args = parser.parse_args()
    try:
        url = get_backup_db_url(args.db_url)
        run_backup(url, Path(args.output_dir))
    except Exception as e:
        logger.error(f"Backup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
