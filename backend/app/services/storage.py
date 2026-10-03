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

    def delete(self, key: str) -> None:
        if not key:
            return
        path = self._resolve(key)
        if path.exists():
            path.unlink()
            logger.info(f"LocalStorage deleted: {key}")

    def exists(self, key: str) -> bool:
        if not key:
            return False
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

    def delete(self, key: str) -> None:
        if not key:
            return
        self.s3.delete_object(Bucket=self.bucket, Key=key)
        logger.info(f"S3Storage deleted: s3://{self.bucket}/{key}")

    def exists(self, key: str) -> bool:
        if not key:
            return False
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


class DatabaseStorage(BaseStorage):
    """
    Relational database blob storage backend (PostgreSQL bytea / SQLite BLOB).
    Stores PDF files in the stored_files table, allowing production deployments
    to keep zero files on local disk and avoid external S3/Supabase storage.
    """

    def save(self, user_id: int, filename: str, content: bytes) -> str:
        import hashlib
        import uuid
        random_hex = uuid.uuid4().hex
        key = f"{user_id}/{random_hex}.pdf"
        sha256 = hashlib.sha256(content).hexdigest()
        size = len(content)

        with SessionLocal() as db:
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

    def delete(self, key: str) -> None:
        if not key:
            return
        with SessionLocal() as db:
            deleted = db.query(StoredFile).filter(StoredFile.key == key).delete()
            db.commit()
            if deleted:
                logger.info(f"DatabaseStorage deleted: key={key}")

    def exists(self, key: str) -> bool:
        if not key:
            return False
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

