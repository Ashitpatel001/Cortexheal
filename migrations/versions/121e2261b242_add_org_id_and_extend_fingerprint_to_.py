
"""add org_id and extend fingerprint to pattern_records

Revision ID: 121e2261b242
Revises: 
Create Date: 2026-09-15 11:25:38.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "121e2261b242"
down_revision: Union[str, None] = "77225d008f23"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. Expand fingerprint column to hold full v1-SHA256 string
    op.alter_column("pattern_records", "fingerprint",
               existing_type=sa.VARCHAR(length=64),
               type_=sa.VARCHAR(length=128),
               existing_nullable=True)
               
    # 2. Add org_id for strict multi-tenant isolation
    op.add_column("pattern_records", sa.Column("org_id", sa.VARCHAR(length=36), server_default="default_org", nullable=False))
    
    # 3. Update unique constraint
    op.drop_constraint("pattern_records_fingerprint_key", "pattern_records", type_="unique")
    op.create_unique_constraint("uq_pattern_org_fingerprint", "pattern_records", ["org_id", "fingerprint"])

def downgrade() -> None:
    op.drop_constraint("uq_pattern_org_fingerprint", "pattern_records", type_="unique")
    op.create_unique_constraint("pattern_records_fingerprint_key", "pattern_records", ["fingerprint"])
    op.drop_column("pattern_records", "org_id")
    op.alter_column("pattern_records", "fingerprint",
               existing_type=sa.VARCHAR(length=128),
               type_=sa.VARCHAR(length=64),
               existing_nullable=True)

