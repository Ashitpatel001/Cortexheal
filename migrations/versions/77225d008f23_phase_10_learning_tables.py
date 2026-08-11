"""phase 10 learning tables

Revision ID: 77225d008f23
Revises: d14064fb3063
Create Date: 2026-08-09 10:44:06.804920

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '77225d008f23'
down_revision: Union[str, Sequence[str], None] = 'd14064fb3063'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'pattern_records',
        sa.Column('pattern_id', sa.String(length=36), nullable=False),
        sa.Column('framework', sa.String(length=50), nullable=True),
        sa.Column('agent_id', sa.String(length=255), nullable=True),
        sa.Column('failure_type', sa.String(length=50), nullable=True),
        sa.Column('fingerprint', sa.String(length=64), nullable=True),
        sa.Column('fingerprint_version', sa.String(length=20), nullable=True),
        sa.Column('occurrences', sa.Integer(), server_default='0', nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_promotion_candidate', sa.Boolean(), server_default='false', nullable=True),
        sa.PrimaryKeyConstraint('pattern_id'),
        sa.UniqueConstraint('fingerprint')
    )
    
    op.create_table(
        'recovery_outcomes',
        sa.Column('outcome_id', sa.String(length=36), nullable=False),
        sa.Column('run_id', sa.String(length=36), nullable=True),
        sa.Column('incident_id', sa.String(length=36), nullable=True),
        sa.Column('pattern_id', sa.String(length=36), nullable=True),
        sa.Column('action_type', sa.String(length=50), nullable=True),
        sa.Column('ai_recommendation', sa.String(length=50), nullable=True),
        sa.Column('human_decision', sa.String(length=50), nullable=True),
        sa.Column('approval_actor', sa.String(length=100), nullable=True),
        sa.Column('execution_result', sa.String(length=50), nullable=True),
        sa.Column('verification_result', sa.String(length=50), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['pattern_id'], ['pattern_records.pattern_id'], ),
        sa.PrimaryKeyConstraint('outcome_id')
    )
    
    op.create_index('idx_patterns_fingerprint', 'pattern_records', ['fingerprint'], unique=False)
    op.create_index('idx_outcomes_pattern', 'recovery_outcomes', ['pattern_id'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_outcomes_pattern', table_name='recovery_outcomes')
    op.drop_index('idx_patterns_fingerprint', table_name='pattern_records')
    op.drop_table('recovery_outcomes')
    op.drop_table('pattern_records')
