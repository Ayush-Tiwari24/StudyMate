"""make documents.file_path nullable

Revision ID: 0004_file_path_nullable
Revises: 0003_stored_files
Create Date: 2026-10-03 14:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0004_file_path_nullable'
down_revision: Union[str, None] = '0003_stored_files'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('documents', schema=None) as batch_op:
        batch_op.alter_column(
            'file_path',
            existing_type=sa.String(length=500),
            nullable=True,
        )


def downgrade() -> None:
    with op.batch_alter_table('documents', schema=None) as batch_op:
        batch_op.alter_column(
            'file_path',
            existing_type=sa.String(length=500),
            nullable=False,
        )
