# Migrating from Supabase to Neon (Serverless Postgres)

This guide walks through migrating existing StudyMate AI production data from Supabase (PostgreSQL + S3 Storage) to **Neon Serverless Postgres** as the single unified data store.

---

## Architecture Summary

| Component | Supabase Setup | Neon Unified Setup |
|---|---|---|
| **Relational Data** | Supabase Postgres (`users`, `chats`, `messages`, etc.) | Neon Postgres (`users`, `chats`, `messages`, etc.) |
| **Vectors** | Supabase pgvector (`chunk_vectors`) | Neon pgvector (`chunk_vectors` + HNSW index) |
| **PDF Files** | Supabase Storage (`s3://studymate-docs/...`) | Neon Postgres `stored_files` table (`bytea`) |
| **Connection Pooling** | Supabase pooler (port 6543) | Neon pooler (`-pooler` in hostname, transaction mode) |

---

## Pre-requisites

1. A Neon account with a new project created in **Singapore (`ap-southeast-1`)**.
2. Connection strings from your Neon dashboard:
   - **Pooled connection string** (contains `-pooler`): For `DATABASE_URL` (used by FastAPI backend).
   - **Direct connection string** (without `-pooler`, port 5432): For `MIGRATION_DATABASE_URL` (used by Alembic and `pg_dump`).
3. Local Python virtual environment active.

---

## Step 1: Run Alembic Migrations on Neon

Always use the **direct** connection string for migrations, because PgBouncer transaction mode prohibits certain schema-altering operations and advisory locks:

```bash
cd backend
export DATABASE_URL="postgresql://user:pass@ep-xyz.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"
export MIGRATION_DATABASE_URL="postgresql://user:pass@ep-xyz.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"

# Apply all migrations (0001_initial_schema, 0002_pgvector, 0003_stored_files)
alembic upgrade head
```

---

## Step 2: Export Data from Supabase

Use Supabase's direct connection string (port 5432) to dump relational tables:

```bash
pg_dump "postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres" \
  --no-owner \
  --no-privileges \
  --data-only \
  --exclude-table=spatial_ref_sys \
  --file=supabase_data_export.sql
```

---

## Step 3: Export PDFs from Supabase Storage to Neon

If you had PDFs stored in Supabase Storage S3 bucket, you can transfer them into the `stored_files` table:

```python
import os
import boto3
import hashlib
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.stored_file import StoredFile

# 1. Connect to S3
s3 = boto3.client(
    "s3",
    endpoint_url=os.getenv("S3_ENDPOINT_URL"),
    aws_access_key_id=os.getenv("S3_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("S3_SECRET_KEY"),
    region_name=os.getenv("S3_REGION", "ap-south-1"),
)
bucket = os.getenv("S3_BUCKET")

# 2. Connect to Neon
neon_engine = create_engine(os.getenv("MIGRATION_DATABASE_URL"))
Session = sessionmaker(bind=neon_engine)
db = Session()

# 3. Stream each file into Neon stored_files
paginator = s3.get_paginator("list_objects_v2")
for page in paginator.paginate(Bucket=bucket):
    for obj in page.get("Contents", []):
        key = obj["Key"]
        body = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
        sha256 = hashlib.sha256(body).hexdigest()
        user_id = int(key.split("/")[0]) if "/" in key else 1

        stored = StoredFile(
            key=key,
            user_id=user_id,
            content_type="application/pdf",
            size_bytes=len(body),
            sha256=sha256,
            data=body,
        )
        db.merge(stored)

db.commit()
print("All S3 files migrated to Neon stored_files!")
```

---

## Step 4: Import Relational Data into Neon

Load the relational tables:

```bash
psql "postgresql://user:pass@ep-xyz.ap-southeast-1.aws.neon.tech/neondb?sslmode=require" \
  -f supabase_data_export.sql
```

---

## Step 5: Align Auto-Increment Sequences

After inserting records with preserved primary keys, update sequence numbers so new inserts do not collide:

```sql
SELECT setval(pg_get_serial_sequence('users', 'id'), COALESCE(MAX(id), 1)) FROM users;
SELECT setval(pg_get_serial_sequence('refresh_tokens', 'id'), COALESCE(MAX(id), 1)) FROM refresh_tokens;
SELECT setval(pg_get_serial_sequence('chats', 'id'), COALESCE(MAX(id), 1)) FROM chats;
SELECT setval(pg_get_serial_sequence('documents', 'id'), COALESCE(MAX(id), 1)) FROM documents;
SELECT setval(pg_get_serial_sequence('chunks', 'id'), COALESCE(MAX(id), 1)) FROM chunks;
SELECT setval(pg_get_serial_sequence('messages', 'id'), COALESCE(MAX(id), 1)) FROM messages;
SELECT setval(pg_get_serial_sequence('sources', 'id'), COALESCE(MAX(id), 1)) FROM sources;
SELECT setval(pg_get_serial_sequence('feedback', 'id'), COALESCE(MAX(id), 1)) FROM feedback;
SELECT setval(pg_get_serial_sequence('stored_files', 'id'), COALESCE(MAX(id), 1)) FROM stored_files;
```

---

## Step 6: Verify and Reindex Vectors (if needed)

If vectors were not included in the export, or to verify vector index integrity:

```bash
cd backend
python scripts/reindex.py
python scripts/cleanup_orphans.py --dry-run
```
