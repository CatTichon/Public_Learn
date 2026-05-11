"""add code task fields

Revision ID: 0002_add_code_task_fields
Revises: 0001_initial
Create Date: 2026-04-29
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_add_code_task_fields"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("task", sa.Column("starter_code", sa.Text(), nullable=True))
    op.add_column("task", sa.Column("test_cases", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("task", "test_cases")
    op.drop_column("task", "starter_code")