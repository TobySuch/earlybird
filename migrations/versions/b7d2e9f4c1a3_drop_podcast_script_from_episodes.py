"""drop podcast_script from episodes

Revision ID: b7d2e9f4c1a3
Revises: 5cf957bd71bb
Create Date: 2026-07-13 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7d2e9f4c1a3"
down_revision: Union[str, Sequence[str], None] = "5cf957bd71bb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("episodes") as batch_op:
        batch_op.drop_column("podcast_script")


def downgrade() -> None:
    with op.batch_alter_table("episodes") as batch_op:
        batch_op.add_column(sa.Column("podcast_script", sa.Text(), nullable=True))
