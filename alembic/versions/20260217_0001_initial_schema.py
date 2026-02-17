"""Initial security defense schema.

Revision ID: 20260217_0001
Revises:
Create Date: 2026-02-17 12:35:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260217_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False, server_default="analyst"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_is_active", "users", ["is_active"], unique=False)
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table(
        "attack_sequence_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("attack_family", sa.String(length=64), nullable=False),
        sa.Column("signature", sa.Text(), nullable=False),
        sa.Column("tokens", sa.JSON(), nullable=False),
        sa.Column("embedding_hint", sa.JSON(), nullable=False),
        sa.Column("predicted_mutation", sa.Text(), nullable=True),
        sa.Column("risk_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_attack_sequence_events_attack_family",
        "attack_sequence_events",
        ["attack_family"],
        unique=False,
    )
    op.create_index(
        "ix_attack_sequence_events_created_at",
        "attack_sequence_events",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_attack_sequence_events_risk_score",
        "attack_sequence_events",
        ["risk_score"],
        unique=False,
    )

    op.create_table(
        "model_artifacts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("model_name", sa.String(length=128), nullable=False),
        sa.Column("model_version", sa.String(length=32), nullable=False),
        sa.Column("model_type", sa.String(length=64), nullable=False),
        sa.Column("artifact_path", sa.String(length=512), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_model_artifacts_created_at", "model_artifacts", ["created_at"], unique=False)
    op.create_index("ix_model_artifacts_is_active", "model_artifacts", ["is_active"], unique=False)
    op.create_index("ix_model_artifacts_model_name", "model_artifacts", ["model_name"], unique=False)
    op.create_index("ix_model_artifacts_model_type", "model_artifacts", ["model_type"], unique=False)
    op.create_index("ix_model_artifacts_model_version", "model_artifacts", ["model_version"], unique=False)

    op.create_table(
        "login_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("source_ip", sa.String(length=64), nullable=False),
        sa.Column("user_agent", sa.String(length=512), nullable=False, server_default=""),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("latency_ms", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("risk_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("anomaly_flag", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("context", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_login_events_anomaly_flag", "login_events", ["anomaly_flag"], unique=False)
    op.create_index("ix_login_events_created_at", "login_events", ["created_at"], unique=False)
    op.create_index("ix_login_events_risk_score", "login_events", ["risk_score"], unique=False)
    op.create_index("ix_login_events_source_ip", "login_events", ["source_ip"], unique=False)
    op.create_index("ix_login_events_success", "login_events", ["success"], unique=False)
    op.create_index("ix_login_events_user_id", "login_events", ["user_id"], unique=False)
    op.create_index("ix_login_user_time", "login_events", ["user_id", "created_at"], unique=False)

    op.create_table(
        "network_flows",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("source_ip", sa.String(length=64), nullable=False),
        sa.Column("destination_ip", sa.String(length=64), nullable=False),
        sa.Column("protocol", sa.String(length=16), nullable=False),
        sa.Column("bytes_in", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("bytes_out", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("packets", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duration_ms", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("tcp_flags", sa.JSON(), nullable=False),
        sa.Column("anomaly_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("anomaly_flag", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("label", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_network_flows_anomaly_flag", "network_flows", ["anomaly_flag"], unique=False)
    op.create_index("ix_network_flows_anomaly_score", "network_flows", ["anomaly_score"], unique=False)
    op.create_index("ix_network_flows_created_at", "network_flows", ["created_at"], unique=False)
    op.create_index("ix_network_flows_destination_ip", "network_flows", ["destination_ip"], unique=False)
    op.create_index("ix_network_flows_protocol", "network_flows", ["protocol"], unique=False)
    op.create_index("ix_network_flows_source_ip", "network_flows", ["source_ip"], unique=False)
    op.create_index("ix_network_flows_user_id", "network_flows", ["user_id"], unique=False)
    op.create_index(
        "ix_flow_src_dst_time",
        "network_flows",
        ["source_ip", "destination_ip", "created_at"],
        unique=False,
    )

    op.create_table(
        "timeseries_points",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("metric_name", sa.String(length=64), nullable=False),
        sa.Column("metric_value", sa.Float(), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_timeseries_points_created_at", "timeseries_points", ["created_at"], unique=False)
    op.create_index("ix_timeseries_points_metric_name", "timeseries_points", ["metric_name"], unique=False)
    op.create_index("ix_timeseries_points_user_id", "timeseries_points", ["user_id"], unique=False)
    op.create_index("ix_timeseries_points_window_end", "timeseries_points", ["window_end"], unique=False)
    op.create_index("ix_timeseries_points_window_start", "timeseries_points", ["window_start"], unique=False)
    op.create_index(
        "ix_ts_metric_time",
        "timeseries_points",
        ["metric_name", "created_at"],
        unique=False,
    )

    op.create_table(
        "defense_actions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("event_id", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("reward", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("decision_context", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_defense_actions_action", "defense_actions", ["action"], unique=False)
    op.create_index("ix_defense_actions_created_at", "defense_actions", ["created_at"], unique=False)
    op.create_index("ix_defense_actions_event_id", "defense_actions", ["event_id"], unique=False)
    op.create_index("ix_defense_actions_event_type", "defense_actions", ["event_type"], unique=False)
    op.create_index("ix_defense_actions_user_id", "defense_actions", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_defense_actions_user_id", table_name="defense_actions")
    op.drop_index("ix_defense_actions_event_type", table_name="defense_actions")
    op.drop_index("ix_defense_actions_event_id", table_name="defense_actions")
    op.drop_index("ix_defense_actions_created_at", table_name="defense_actions")
    op.drop_index("ix_defense_actions_action", table_name="defense_actions")
    op.drop_table("defense_actions")

    op.drop_index("ix_ts_metric_time", table_name="timeseries_points")
    op.drop_index("ix_timeseries_points_window_start", table_name="timeseries_points")
    op.drop_index("ix_timeseries_points_window_end", table_name="timeseries_points")
    op.drop_index("ix_timeseries_points_user_id", table_name="timeseries_points")
    op.drop_index("ix_timeseries_points_metric_name", table_name="timeseries_points")
    op.drop_index("ix_timeseries_points_created_at", table_name="timeseries_points")
    op.drop_table("timeseries_points")

    op.drop_index("ix_flow_src_dst_time", table_name="network_flows")
    op.drop_index("ix_network_flows_user_id", table_name="network_flows")
    op.drop_index("ix_network_flows_source_ip", table_name="network_flows")
    op.drop_index("ix_network_flows_protocol", table_name="network_flows")
    op.drop_index("ix_network_flows_destination_ip", table_name="network_flows")
    op.drop_index("ix_network_flows_created_at", table_name="network_flows")
    op.drop_index("ix_network_flows_anomaly_score", table_name="network_flows")
    op.drop_index("ix_network_flows_anomaly_flag", table_name="network_flows")
    op.drop_table("network_flows")

    op.drop_index("ix_login_user_time", table_name="login_events")
    op.drop_index("ix_login_events_user_id", table_name="login_events")
    op.drop_index("ix_login_events_success", table_name="login_events")
    op.drop_index("ix_login_events_source_ip", table_name="login_events")
    op.drop_index("ix_login_events_risk_score", table_name="login_events")
    op.drop_index("ix_login_events_created_at", table_name="login_events")
    op.drop_index("ix_login_events_anomaly_flag", table_name="login_events")
    op.drop_table("login_events")

    op.drop_index("ix_model_artifacts_model_version", table_name="model_artifacts")
    op.drop_index("ix_model_artifacts_model_type", table_name="model_artifacts")
    op.drop_index("ix_model_artifacts_model_name", table_name="model_artifacts")
    op.drop_index("ix_model_artifacts_is_active", table_name="model_artifacts")
    op.drop_index("ix_model_artifacts_created_at", table_name="model_artifacts")
    op.drop_table("model_artifacts")

    op.drop_index("ix_attack_sequence_events_risk_score", table_name="attack_sequence_events")
    op.drop_index("ix_attack_sequence_events_created_at", table_name="attack_sequence_events")
    op.drop_index("ix_attack_sequence_events_attack_family", table_name="attack_sequence_events")
    op.drop_table("attack_sequence_events")

    op.drop_index("ix_users_username", table_name="users")
    op.drop_index("ix_users_is_active", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
