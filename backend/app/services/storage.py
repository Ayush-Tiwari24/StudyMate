"""
StudyMate RAG — File Storage Interface

Provides an abstraction for storing and retrieving uploaded document files.
Supports:
- LocalStorage (default, files stored on local disk under UPLOAD_DIR)
- S3Storage (AWS S3, Cloudflare R2, Supabase Storage, or any S3-compatible service)
"""

import io
import shutil
from abc import ABC, abstractmethod
from functools import lru_cache
from pathlib import Path
from typing import Optional

from sqlalchemy import text

from app.core.config import settings
from app.core.logger import logger
from app.db.session import SessionLocal, engine
from app.models.stored_file import StoredFile
from app.utils.file_utils import safe_filename, ensure_dir


class BaseStorage(ABC):
    """Abstract file storage interface."""

    @abstractmethod
    def save(self, user_id: int, filename: str, content: bytes) -> str:
        """
        Save file content and return a relative storage key.

        Args:
            user_id: The ID of the owner.
            filename: The original file name.
            content: Raw byte contents.

        Returns:
            A storage key string (e.g. '1/notes.pdf').
        """
        pass

    @abstractmethod
    def open(self, key: str) -> bytes:
        """Read and return the complete file bytes for the given storage key."""
        pass

    @abstractmethod
    def open_stream(self, key: str):
        """Return a readable binary stream for the given storage key."""
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete the file matching the storage key."""
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check whether the file exists in storage."""
        pass

    @abstractmethod
    def delete_user_files(self, user_id: int) -> None:
        """Delete all files belonging to a user."""
        pass


class LocalStorage(BaseStorage):
    """Local filesystem storage backend."""

    def __init__(self, root_dir: Optional[Path] = None):
        self.root = root_dir or settings.upload_path
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str) -> Path:
        """Resolve a storage key or fallback absolute/relative path to a Path object."""
        p = Path(key)
        if p.is_absolute():
            return p
        return (self.root / key).resolve()

    def save(self, user_id: int, filename: str, content: bytes) -> str:
        clean_name = safe_filename(filename)
        user_folder = ensure_dir(self.root / str(user_id))
        dest = user_folder / clean_name

        with open(dest, "wb") as f:
            f.write(content)

        # Return relative key: e.g. "1/sample.pdf"
        key = f"{user_id}/{clean_name}"
        logger.info(f"LocalStorage saved: {key}")
        return key

    def open(self, key: str) -> bytes:
        path = self._resolve(key)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {key}")
        with open(path, "rb") as f:
            return f.read()

    def open_stream(self, key: str):
        path = self._resolve(key)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {key}")
        return open(path, "rb")

    def delete(self, key: str) -> None:
        path = self._resolve(key)
        if path.exists():
            path.unlink()
            logger.info(f"LocalStorage deleted: {key}")

    def exists(self, key: str) -> bool:
        return self._resolve(key).exists()

    def delete_user_files(self, user_id: int) -> None:
        user_dir = self.root / str(user_id)
        if user_dir.exists():
            shutil.rmtree(user_dir, ignore_errors=True)
            logger.info(f"LocalStorage deleted user directory: {user_dir}")


class S3Storage(BaseStorage):
    """S3-compatible object storage backend (AWS S3, Supabase Storage, Cloudflare R2)."""

    def __init__(self):
        import boto3
        from botocore.config import Config

        session = boto3.session.Session()
        client_kwargs = {
            "service_name": "s3",
            "region_name": settings.s3_region or "ap-south-1",
            "aws_access_key_id": settings.s3_access_key,
            "aws_secret_access_key": settings.s3_secret_key,
            "config": Config(
                signature_version="s3v4",
                s3={"addressing_style": "path"},
            ),
        }
        if settings.s3_endpoint_url:
            client_kwargs["endpoint_url"] = settings.s3_endpoint_url

        self.s3 = session.client(**client_kwargs)
        self.bucket = settings.s3_bucket
        logger.info(f"Initialized S3Storage with bucket: {self.bucket} (region: {client_kwargs['region_name']})")

    def save(self, user_id: int, filename: str, content: bytes) -> str:
        clean_name = safe_filename(filename)
        key = f"{user_id}/{clean_name}"
        self.s3.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=content,
            ContentType="application/pdf",
        )
        logger.info(f"S3Storage uploaded: s3://{self.bucket}/{key}")
        return key

    def open(self, key: str) -> bytes:
        response = self.s3.get_object(Bucket=self.bucket, Key=key)
        return response["Body"].read()

    def open_stream(self, key: str):
        response = self.s3.get_object(Bucket=self.bucket, Key=key)
        return response["Body"]

    def delete(self, key: str) -> None:
        self.s3.delete_object(Bucket=self.bucket, Key=key)
        logger.info(f"S3Storage deleted: s3://{self.bucket}/{key}")

    def exists(self, key: str) -> bool:
        try:
            self.s3.head_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:
            return False

    def delete_user_files(self, user_id: int) -> None:
        prefix = f"{user_id}/"
        try:
            paginator = self.s3.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
                objects = page.get("Contents", [])
                if objects:
                    delete_keys = [{"Key": obj["Key"]} for obj in objects]
                    self.s3.delete_objects(
                        Bucket=self.bucket,
                        Delete={"Objects": delete_keys},
                    )
            logger.info(f"S3Storage deleted all objects with prefix: {prefix}")
        except Exception as e:
            logger.warning(f"S3Storage error deleting prefix {prefix}: {e}")


class DatabaseStream(io.RawIOBase):
    """
    Streaming reader for database-stored files (Postgres bytea / SQLite BLOB).
    Queries SQL slices in chunks using substring / substr to stream to HTTP clients
    without buffering the entire file into Python RAM twice.
    """

    def __init__(self, key: str, chunk_size: int = 64 * 1024):
        super().__init__()
        self.key = key
        self.chunk_size = chunk_size
        self._pos = 0  # 0-indexed byte position in stream
        self._total_size: Optional[int] = None
        self._is_postgres = (engine.dialect.name == "postgresql")

        with SessionLocal() as db:
            row = db.query(StoredFile.size_bytes).filter(StoredFile.key == key).first()
            if not row:
                raise FileNotFoundError(f"File not found in database storage: {key}")
            self._total_size = int(row[0])

    @property
    def total_size(self) -> int:
        return self._total_size or 0

    def readable(self) -> bool:
        return True

    def readinto(self, b) -> int:
        data = self.read(len(b))
        n = len(data)
        b[:n] = data
        return n

    def read(self, size: int = -1) -> bytes:
        if self._total_size is None or self._pos >= self._total_size:
            return b""

        if size is None or size < 0:
            bytes_to_read = self._total_size - self._pos
        else:
            bytes_to_read = min(size, self._total_size - self._pos)

        if bytes_to_read <= 0:
            return b""

        # SQL substring / substr is 1-based
        start_1based = self._pos + 1
        with SessionLocal() as db:
            if self._is_postgres:
                sql = text("SELECT substring(data from :start for :len) FROM stored_files WHERE key = :key")
            else:
                sql = text("SELECT substr(data, :start, :len) FROM stored_files WHERE key = :key")

            res = db.execute(sql, {"start": start_1based, "len": bytes_to_read, "key": self.key}).scalar()

        chunk = bytes(res) if res is not None else b""
        self._pos += len(chunk)
        return chunk

    def __iter__(self):
        while True:
            chunk = self.read(self.chunk_size)
            if not chunk:
                break
            yield chunk


class DatabaseStorage(BaseStorage):
    """
    Relational database blob storage backend (PostgreSQL bytea / SQLite BLOB).
    Stores PDF files in the stored_files table, allowing production deployments
    to keep zero files on local disk and avoid external S3/Supabase storage.
    """

    def save(self, user_id: int, filename: str, content: bytes) -> str:
        import hashlib
        clean_name = safe_filename(filename)
        key = f"{user_id}/{clean_name}"
        sha256 = hashlib.sha256(content).hexdigest()
        size = len(content)

        with SessionLocal() as db:
            existing = db.query(StoredFile).filter(StoredFile.key == key).first()
            if existing:
                existing.data = content
                existing.size_bytes = size
                existing.sha256 = sha256
                existing.content_type = "application/pdf"
            else:
                stored = StoredFile(
                    key=key,
                    user_id=user_id,
                    content_type="application/pdf",
                    size_bytes=size,
                    sha256=sha256,
                    data=content,
                )
                db.add(stored)
            db.commit()

        logger.info(f"DatabaseStorage saved: key={key} size={size} bytes")
        return key

    def open(self, key: str) -> bytes:
        with SessionLocal() as db:
            row = db.query(StoredFile.data).filter(StoredFile.key == key).first()
            if not row or row[0] is None:
                raise FileNotFoundError(f"File not found in database storage: {key}")
            return bytes(row[0])

    def open_stream(self, key: str):
        return DatabaseStream(key)

    def delete(self, key: str) -> None:
        with SessionLocal() as db:
            deleted = db.query(StoredFile).filter(StoredFile.key == key).delete()
            db.commit()
            if deleted:
                logger.info(f"DatabaseStorage deleted: key={key}")

    def exists(self, key: str) -> bool:
        with SessionLocal() as db:
            row = db.query(StoredFile.id).filter(StoredFile.key == key).first()
            return row is not None

    def delete_user_files(self, user_id: int) -> None:
        with SessionLocal() as db:
            count = db.query(StoredFile).filter(StoredFile.user_id == user_id).delete()
            db.commit()
            logger.info(f"DatabaseStorage deleted {count} files for user_id={user_id}")


@lru_cache(maxsize=1)
def get_storage() -> BaseStorage:
    """Return the configured storage backend singleton."""
    backend = settings.storage_backend.lower().strip()
    if backend == "db":
        return DatabaseStorage()
    elif backend == "s3":
        return S3Storage()
    return LocalStorage()

