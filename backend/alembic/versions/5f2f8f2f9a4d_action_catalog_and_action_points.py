"""action_catalog_and_action_points

Revision ID: 5f2f8f2f9a4d
Revises: 88dd71e25e25
Create Date: 2026-03-12 21:05:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "5f2f8f2f9a4d"
down_revision = "88dd71e25e25"
branch_labels = None
depends_on = None


actionattribute = sa.Enum(
    "STRENGTH",
    "DEXTERITY",
    "CONSTITUTION",
    "INTELLIGENCE",
    "WISDOM",
    "CHARISMA",
    "DIPLOMACY",
    "SURVIVAL",
    "STEALTH",
    "MELEE",
    name="actionattribute",
    native_enum=False,
)
actionresolutionmode = sa.Enum(
    "DETERMINISTIC",
    "LLM_EFFECTS",
    name="actionresolutionmode",
    native_enum=False,
)


def upgrade() -> None:
    with op.batch_alter_table("entity_stats") as batch_op:
        batch_op.add_column(sa.Column("action_points", sa.Integer(), nullable=False, server_default="100"))
        batch_op.add_column(sa.Column("max_action_points", sa.Integer(), nullable=False, server_default="100"))

    op.create_table(
        "scenario_actions",
        sa.Column("id", sa.String(length=160), nullable=False),
        sa.Column("scenario_id", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("aliases", sa.JSON(), nullable=False),
        sa.Column("relevant_attribute", actionattribute, nullable=False),
        sa.Column("difficulty", sa.Integer(), nullable=False),
        sa.Column("action_point_cost", sa.Integer(), nullable=False),
        sa.Column("resolution_mode", actionresolutionmode, nullable=False),
        sa.Column("handler_key", sa.String(length=120), nullable=True),
        sa.Column("created_by_llm", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["scenario_id"], ["scenarios.id"], name=op.f("fk_scenario_actions_scenario_id_scenarios")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_scenario_actions")),
    )
    op.create_index(op.f("ix_scenario_actions_scenario_id"), "scenario_actions", ["scenario_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_scenario_actions_scenario_id"), table_name="scenario_actions")
    op.drop_table("scenario_actions")

    with op.batch_alter_table("entity_stats") as batch_op:
        batch_op.drop_column("max_action_points")
        batch_op.drop_column("action_points")
