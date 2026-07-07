"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-06 00:00:00
"""

from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geography
from sqlalchemy.dialects.postgresql import UUID


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.create_table(
        "geozones",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("center", Geography(geometry_type="POINT", srid=4326), nullable=False),
        sa.Column("radius_m", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_geozones_user_id", "geozones", ["user_id"])
    op.create_index("ix_geozones_is_active", "geozones", ["is_active"])
    op.create_index("ix_geozones_center", "geozones", ["center"], postgresql_using="gist")

    op.create_table(
        "latest_device_locations",
        sa.Column("user_id", sa.String(), primary_key=True, nullable=False),
        sa.Column("device_id", sa.String(), primary_key=True, nullable=False),
        sa.Column("location", Geography(geometry_type="POINT", srid=4326), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("reported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("latest_device_locations")
    op.drop_index("ix_geozones_center", table_name="geozones")
    op.drop_index("ix_geozones_is_active", table_name="geozones")
    op.drop_index("ix_geozones_user_id", table_name="geozones")
    op.drop_table("geozones")
