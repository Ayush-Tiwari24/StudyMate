"""stored_files

Revision ID: 0003_stored_files
Revises: 0002_pgvector
Create Date: 2026-10-02 15:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0003_stored_files'
down_revision: Union[str, None] = '0002_pgvector'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── stored_files ─────────────────────────────────────────────
    op.create_table(
        'stored_files',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key', sa.Text(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('content_type', sa.Text(), server_default='application/pdf', nullable=False),
        sa.Column('size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('sha256', sa.String(length=64), nullable=True),
        sa.Column('data', sa.LargeBinary(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('stored_files', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_stored_files_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_stored_files_key'), ['key'], unique=True)
        batch_op.create_index(batch_op.f('ix_stored_files_user_id'), ['user_id'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('stored_files', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_stored_files_user_id'))
        batch_op.drop_index(batch_op.f('ix_stored_files_key'))
        batch_op.drop_index(batch_op.f('ix_stored_files_id'))
    op.drop_table('stored_files')
