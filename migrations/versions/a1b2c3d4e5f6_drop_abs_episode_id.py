"""drop abs_episode_id from episodes

Revision ID: a1b2c3d4e5f6
Revises: d915e1afd957
Create Date: 2026-04-24 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "d915e1afd957"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("episodes") as batch_op:
        batch_op.drop_column("abs_episode_id")


def downgrade() -> None:
    with op.batch_alter_table("episodes") as batch_op:
        batch_op.add_column(sa.Column("abs_episode_id", sa.String(length=200), nullable=True))
