"""seed_marketplaces

Revision ID: c9272131c8af
Revises: c712bae9b154
Create Date: 2026-04-25 01:03:32.253045

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c9272131c8af"
down_revision: Union[str, Sequence[str], None] = "c712bae9b154"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


MARKETPLACES = [
    {"slug": "yandex_market", "display_name": "Яндекс Маркет"},
    {"slug": "ozon", "display_name": "Ozon"},
    {"slug": "wildberries", "display_name": "Wildberries"},
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
