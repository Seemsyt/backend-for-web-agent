"""Create LangGraph checkpoints table

Revision ID: langgraph001
Revises: 76741f7e9b70
Create Date: 2026-03-26 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'langgraph001'
down_revision: Union[str, Sequence[str], None] = '76741f7e9b70'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create checkpoints table for LangGraph AsyncPostgresSaver"""
    op.create_table(
        'checkpoints',
        sa.Column('thread_id', sa.String(), nullable=False),
        sa.Column('checkpoint_ns', sa.String(), nullable=False),
        sa.Column('checkpoint_id', sa.String(), nullable=False),
        sa.Column('parent_checkpoint_id', sa.String(), nullable=True),
        sa.Column('type', sa.String(), nullable=True),
        sa.Column('checkpoint', sa.LargeBinary(), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('thread_id', 'checkpoint_ns', 'checkpoint_id'),
    )
    
    # Create index for faster queries
    op.create_index(
        'ix_checkpoints_thread_id',
        'checkpoints',
        ['thread_id']
    )
    
    # Create table for checkpoint writes
    op.create_table(
        'checkpoint_writes',
        sa.Column('thread_id', sa.String(), nullable=False),
        sa.Column('checkpoint_ns', sa.String(), nullable=False),
        sa.Column('checkpoint_id', sa.String(), nullable=False),
        sa.Column('channel', sa.String(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('value', sa.LargeBinary(), nullable=False),
        sa.PrimaryKeyConstraint('thread_id', 'checkpoint_ns', 'checkpoint_id', 'channel'),
        sa.ForeignKeyConstraint(
            ['thread_id', 'checkpoint_ns', 'checkpoint_id'],
            ['checkpoints.thread_id', 'checkpoints.checkpoint_ns', 'checkpoints.checkpoint_id'],
            ondelete='CASCADE'
        ),
    )


def downgrade() -> None:
    """Drop checkpoint tables"""
    op.drop_table('checkpoint_writes')
    op.drop_table('checkpoints')
