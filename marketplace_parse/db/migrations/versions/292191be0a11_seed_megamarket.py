"""seed megamarket

Revision ID: 292191be0a11
Revises: 05ac22aebc28
Create Date: 2026-04-30 00:06:13.936369

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "292191be0a11"
down_revision: Union[str, Sequence[str], None] = "05ac22aebc28"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


MARKETPLACES = [
    {"slug": "megamarket", "display_name": "МегаМаркет"},
]


def upgrade() -> None:
    marketplaces = sa.table(
        "marketplaces",
        sa.column("slug", sa.String),
        sa.column("display_name", sa.String),
    )
    op.bulk_insert(marketplaces, MARKETPLACES)


def downgrade() -> None:
    slugs = [m["slug"] for m in MARKETPLACES]
    op.execute(
        sa.text("DELETE FROM marketplaces WHERE slug IN :slugs").bindparams(
            sa.bindparam("slugs", expanding=True, value=slugs)
        )
    )
