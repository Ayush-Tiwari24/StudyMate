"""pgvector_chunk_vectors

Revision ID: 0002_pgvector
Revises: 0001_initial_schema
Create Date: 2026-10-02 14:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

from app.core.config import settings

# revision identifiers, used by Alembic.
revision: str = '0002_pgvector'
down_revision: Union[str, None] = '0001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        # SQLite or non-Postgres dialect: pgvector extension and tables skipped
        return

    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    dim = settings.embedding_dim or 384

    # ── chunk_vectors ─────────────────────────────────────────────
    op.create_table(
        'chunk_vectors',
        sa.Column('id', sa.Text(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('filename', sa.Text(), nullable=True),
        sa.Column('page', sa.Integer(), nullable=True),
        sa.Column('chunk_index', sa.Integer(), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('embedding', Vector(dim), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    # B-Tree index on (user_id, document_id) for scoped filtering
    op.create_index(
        'ix_chunk_vectors_user_doc',
        'chunk_vectors',
        ['user_id', 'document_id'],
        unique=False,
    )

    # HNSW vector index with cosine distance
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_chunk_vectors_embedding_hnsw "
        "ON chunk_vectors USING hnsw (embedding vector_cosine_ops);"
    )

    # ── vector_meta ───────────────────────────────────────────────
    vector_meta_table = op.create_table(
        'vector_meta',
        sa.Column('key', sa.Text(), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('key'),
    )

    # Seed initial metadata with active embedding model name
    op.bulk_insert(
        vector_meta_table,
        [
            {'key': 'embedding_model', 'value': settings.embedding_model},
            {'key': 'embedding_dim', 'value': str(dim)},
        ],
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.drop_table('vector_meta')
    op.drop_table('chunk_vectors')
    # Note: Keep 'vector' extension in Postgres as other extensions/tables might depend on it
