CREATE TABLE IF NOT EXISTS failure_events (
    id TEXT PRIMARY KEY,
    fingerprint_id TEXT NOT NULL,
    domain TEXT NOT NULL,
    nature TEXT NOT NULL,
    recoverability TEXT NOT NULL,
    severity TEXT NOT NULL,
    context_hash TEXT NOT NULL,
    timestamp TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_failure_fingerprint
ON failure_events (fingerprint_id);

CREATE TABLE IF NOT EXISTS lineage_nodes (
    lineage_id TEXT PRIMARY KEY,
    parent_lineage_id TEXT,
    execution_id TEXT NOT NULL,
    failure_fingerprint_id TEXT NOT NULL,
    directive_delta TEXT NOT NULL,
    timestamp TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_lineage_parent
ON lineage_nodes (parent_lineage_id);

CREATE TABLE IF NOT EXISTS directive_snapshots (
    directive_id TEXT PRIMARY KEY,
    execution_id TEXT NOT NULL,
    lineage_id TEXT NOT NULL,

    allowed_mutations TEXT NOT NULL,
    forbidden_mutations TEXT NOT NULL,

    attention_boosts TEXT NOT NULL,
    attention_penalties TEXT NOT NULL,

    derived_from_fingerprints TEXT NOT NULL,
    timestamp TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_directive_execution
ON directive_snapshots (execution_id);

CREATE INDEX IF NOT EXISTS idx_directive_lineage
ON directive_snapshots (lineage_id);
