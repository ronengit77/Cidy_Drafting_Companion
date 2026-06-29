from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002_artifacts"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "artifacts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("schema_id", sa.String(length=128), nullable=False),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("content", postgresql.JSONB(), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_artifacts_owner_id", "artifacts", ["owner_id"])
    op.create_table(
        "artifact_versions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("artifact_id", sa.Uuid(), sa.ForeignKey("artifacts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("content", postgresql.JSONB(), nullable=False),
        sa.Column("author_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_artifact_versions_artifact_id", "artifact_versions", ["artifact_id"])
    op.create_table(
        "artifact_collaborators",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("artifact_id", sa.Uuid(), sa.ForeignKey("artifacts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("artifact_id", "user_id", name="uq_artifact_user"),
    )
    op.create_index("ix_artifact_collaborators_artifact_id", "artifact_collaborators", ["artifact_id"])
    op.create_index("ix_artifact_collaborators_user_id", "artifact_collaborators", ["user_id"])


def downgrade() -> None:
    op.drop_table("artifact_collaborators")
    op.drop_index("ix_artifact_versions_artifact_id", table_name="artifact_versions")
    op.drop_table("artifact_versions")
    op.drop_index("ix_artifacts_owner_id", table_name="artifacts")
    op.drop_table("artifacts")
