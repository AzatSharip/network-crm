CREATE TABLE login_attempts (
	key VARCHAR(64) NOT NULL, 
	count INTEGER NOT NULL, 
	window_start TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (key)
);

CREATE TABLE users (
	email VARCHAR(254) NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	password_hash TEXT NOT NULL, 
	active BOOLEAN NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (email)
);

CREATE TABLE sessions (
	token_hash VARCHAR(64) NOT NULL, 
	user_id UUID NOT NULL, 
	csrf_hash VARCHAR(64) NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (token_hash), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE INDEX ix_sessions_expires_at ON sessions (expires_at);

CREATE TABLE workspaces (
	name VARCHAR(120) NOT NULL, 
	kind VARCHAR(16) NOT NULL, 
	owner_id UUID NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CHECK (kind IN ('personal','family')), 
	FOREIGN KEY(owner_id) REFERENCES users (id)
);

CREATE UNIQUE INDEX one_personal_per_user ON workspaces (owner_id) WHERE kind='personal';

CREATE TABLE audit_log (
	actor_id UUID NOT NULL, 
	action VARCHAR(80) NOT NULL, 
	entity_id UUID, 
	detail JSONB NOT NULL, 
	workspace_id UUID NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(actor_id) REFERENCES users (id), 
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id)
);

CREATE INDEX ix_audit_log_workspace_id ON audit_log (workspace_id);

CREATE TABLE invitations (
	workspace_id UUID NOT NULL, 
	email VARCHAR(254) NOT NULL, 
	role VARCHAR(12) NOT NULL, 
	token_hash VARCHAR(64) NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	accepted_at TIMESTAMP WITH TIME ZONE, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CHECK (role IN ('editor','viewer','admin')), 
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id), 
	UNIQUE (token_hash)
);

CREATE TABLE organizations (
	name VARCHAR(200) NOT NULL, 
	workspace_id UUID NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (workspace_id, name), 
	UNIQUE (workspace_id, id), 
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id)
);

CREATE INDEX ix_organizations_workspace_id ON organizations (workspace_id);

CREATE TABLE persons (
	display_name VARCHAR(200) NOT NULL, 
	first_name VARCHAR(100) NOT NULL, 
	last_name VARCHAR(100) NOT NULL, 
	middle_name VARCHAR(100) NOT NULL, 
	aliases JSONB NOT NULL, 
	city VARCHAR(120) NOT NULL, 
	country VARCHAR(120) NOT NULL, 
	profession VARCHAR(200) NOT NULL, 
	competencies TEXT NOT NULL, 
	description TEXT NOT NULL, 
	notes TEXT NOT NULL, 
	version INTEGER NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_by UUID NOT NULL, 
	search_text TEXT NOT NULL, 
	search_vector TSVECTOR GENERATED ALWAYS AS (setweight(to_tsvector('russian', display_name), 'A') || setweight(to_tsvector('russian', search_text), 'B') || setweight(to_tsvector('simple', search_text), 'C')) STORED NOT NULL, 
	workspace_id UUID NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (workspace_id, id), 
	FOREIGN KEY(updated_by) REFERENCES users (id), 
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id)
);

CREATE INDEX ix_person_search_trgm ON persons USING gin (search_text gin_trgm_ops);

CREATE INDEX ix_person_search_vector ON persons USING gin (search_vector);

CREATE INDEX ix_persons_workspace_id ON persons (workspace_id);

CREATE TABLE sources (
	name VARCHAR(200) NOT NULL, 
	reference VARCHAR(1000) NOT NULL, 
	workspace_id UUID NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (workspace_id, id), 
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id)
);

CREATE INDEX ix_sources_workspace_id ON sources (workspace_id);

CREATE TABLE tags (
	name VARCHAR(80) NOT NULL, 
	workspace_id UUID NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (workspace_id, name), 
	UNIQUE (workspace_id, id), 
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id)
);

CREATE INDEX ix_tags_workspace_id ON tags (workspace_id);

CREATE TABLE workspace_members (
	workspace_id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	role VARCHAR(12) NOT NULL, 
	PRIMARY KEY (workspace_id, user_id), 
	CHECK (role IN ('admin','editor','viewer')), 
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE TABLE agent_tokens (
	user_id UUID NOT NULL, 
	token_hash VARCHAR(64) NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	revoked BOOLEAN NOT NULL, 
	workspace_id UUID NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(workspace_id, user_id) REFERENCES workspace_members (workspace_id, user_id) ON DELETE CASCADE, 
	UNIQUE (token_hash), 
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id)
);

CREATE INDEX ix_agent_tokens_workspace_id ON agent_tokens (workspace_id);

CREATE TABLE ai_suggestions (
	operation VARCHAR(30) NOT NULL, 
	target_id UUID, 
	source_id UUID NOT NULL, 
	expected_version INTEGER, 
	before JSONB NOT NULL, 
	payload JSONB NOT NULL, 
	confidence INTEGER NOT NULL, 
	status VARCHAR(12) NOT NULL, 
	job_key VARCHAR(100) NOT NULL, 
	record_key VARCHAR(100) NOT NULL, 
	created_by UUID NOT NULL, 
	reviewed_by UUID, 
	reviewed_at TIMESTAMP WITH TIME ZONE, 
	workspace_id UUID NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(workspace_id, source_id) REFERENCES sources (workspace_id, id), 
	FOREIGN KEY(workspace_id, target_id) REFERENCES persons (workspace_id, id), 
	UNIQUE (workspace_id, job_key, record_key), 
	CHECK (status IN ('pending','approved','rejected','applied')), 
	CHECK (confidence BETWEEN 0 AND 100), 
	FOREIGN KEY(created_by) REFERENCES users (id), 
	FOREIGN KEY(reviewed_by) REFERENCES users (id), 
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id)
);

CREATE INDEX ix_ai_suggestions_workspace_id ON ai_suggestions (workspace_id);

CREATE TABLE person_connections (
	workspace_id UUID NOT NULL, 
	person_id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	knows BOOLEAN NOT NULL, 
	priority VARCHAR(1), 
	is_primary BOOLEAN NOT NULL, 
	PRIMARY KEY (workspace_id, person_id, user_id), 
	FOREIGN KEY(workspace_id, person_id) REFERENCES persons (workspace_id, id) ON DELETE CASCADE, 
	FOREIGN KEY(workspace_id, user_id) REFERENCES workspace_members (workspace_id, user_id) ON DELETE CASCADE, 
	CHECK (priority IS NULL OR priority IN ('A','B','C'))
);

CREATE UNIQUE INDEX one_primary_connection ON person_connections (person_id) WHERE is_primary;

CREATE TABLE person_contacts (
	person_id UUID NOT NULL, 
	platform VARCHAR(50) NOT NULL, 
	kind VARCHAR(20) NOT NULL, 
	value VARCHAR(1000) NOT NULL, 
	normalized_value VARCHAR(1000) NOT NULL, 
	label VARCHAR(100) NOT NULL, 
	is_primary BOOLEAN NOT NULL, 
	source VARCHAR(500) NOT NULL, 
	verification VARCHAR(16) NOT NULL, 
	workspace_id UUID NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(workspace_id, person_id) REFERENCES persons (workspace_id, id) ON DELETE CASCADE, 
	UNIQUE (person_id, platform, kind, normalized_value), 
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id)
);

CREATE INDEX ix_person_contacts_normalized_value ON person_contacts (normalized_value);

CREATE INDEX ix_person_contacts_workspace_id ON person_contacts (workspace_id);

CREATE TABLE person_organizations (
	workspace_id UUID NOT NULL, 
	person_id UUID NOT NULL, 
	organization_id UUID NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	PRIMARY KEY (workspace_id, person_id, organization_id), 
	FOREIGN KEY(workspace_id, person_id) REFERENCES persons (workspace_id, id) ON DELETE CASCADE, 
	FOREIGN KEY(workspace_id, organization_id) REFERENCES organizations (workspace_id, id)
);

CREATE TABLE person_tags (
	workspace_id UUID NOT NULL, 
	person_id UUID NOT NULL, 
	tag_id UUID NOT NULL, 
	PRIMARY KEY (workspace_id, person_id, tag_id), 
	FOREIGN KEY(workspace_id, person_id) REFERENCES persons (workspace_id, id) ON DELETE CASCADE, 
	FOREIGN KEY(workspace_id, tag_id) REFERENCES tags (workspace_id, id)
);

CREATE TABLE relationships (
	from_person_id UUID NOT NULL, 
	to_person_id UUID NOT NULL, 
	type VARCHAR(80) NOT NULL, 
	directed BOOLEAN NOT NULL, 
	comment TEXT NOT NULL, 
	source VARCHAR(500) NOT NULL, 
	created_by UUID NOT NULL, 
	workspace_id UUID NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(workspace_id, from_person_id) REFERENCES persons (workspace_id, id) ON DELETE CASCADE, 
	FOREIGN KEY(workspace_id, to_person_id) REFERENCES persons (workspace_id, id) ON DELETE CASCADE, 
	CHECK (from_person_id <> to_person_id), 
	UNIQUE (workspace_id, from_person_id, to_person_id, type, directed), 
	FOREIGN KEY(created_by) REFERENCES users (id), 
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id)
);

CREATE INDEX ix_relationships_workspace_id ON relationships (workspace_id);
