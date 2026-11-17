"""Initial normalized workspace schema, search indexes and RLS."""

from pathlib import Path

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None
SCOPED = (
    "persons",
    "person_contacts",
    "person_connections",
    "tags",
    "person_tags",
    "organizations",
    "person_organizations",
    "relationships",
    "sources",
    "ai_suggestions",
    "audit_log",
)


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(Path(__file__).with_name("0001_schema.sql").read_text())
    for table in SCOPED:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY workspace_isolation ON {table} USING (workspace_id = nullif(current_setting('app.workspace_id', true), '')::uuid) WITH CHECK (workspace_id = nullif(current_setting('app.workspace_id', true), '')::uuid)"
        )
    op.execute("GRANT USAGE ON SCHEMA public TO crm_app")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO crm_app")
    op.execute("REVOKE UPDATE, DELETE ON audit_log FROM crm_app")
    op.execute("REVOKE ALL ON alembic_version FROM crm_app")
    op.execute("""CREATE FUNCTION protect_personal_members() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF EXISTS (SELECT 1 FROM workspaces WHERE id=NEW.workspace_id AND kind='personal' AND owner_id<>NEW.user_id) THEN
        RAISE EXCEPTION 'Personal workspace accepts only its owner';
      END IF;
      RETURN NEW;
    END $$""")
    op.execute(
        "CREATE TRIGGER personal_member_guard BEFORE INSERT OR UPDATE ON workspace_members FOR EACH ROW EXECUTE FUNCTION protect_personal_members()"
    )


def downgrade():
    op.execute("DROP TRIGGER personal_member_guard ON workspace_members")
    op.execute("DROP FUNCTION protect_personal_members()")
    op.execute(
        "DROP TABLE "
        + ", ".join(
            reversed(
                [
                    "login_attempts",
                    "users",
                    "sessions",
                    "workspaces",
                    "audit_log",
                    "invitations",
                    "organizations",
                    "persons",
                    "sources",
                    "tags",
                    "workspace_members",
                    "agent_tokens",
                    "ai_suggestions",
                    "person_connections",
                    "person_contacts",
                    "person_organizations",
                    "person_tags",
                    "relationships",
                ]
            )
        )
        + " CASCADE"
    )
