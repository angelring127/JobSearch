-- Operations/admin foundation for source status and crawl history.

CREATE TABLE IF NOT EXISTS crawler_sources (
  source_key TEXT PRIMARY KEY,
  display_name TEXT NOT NULL,
  adapter_key TEXT NOT NULL,
  enabled BOOLEAN NOT NULL DEFAULT TRUE,
  last_status TEXT,
  last_run_at TIMESTAMPTZ,
  last_success_at TIMESTAMPTZ,
  last_error TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO crawler_sources (source_key, display_name, adapter_key, enabled)
VALUES ('jpcanada', 'JPCanada', 'jpcanada', TRUE)
ON CONFLICT (source_key)
DO UPDATE SET
  display_name = EXCLUDED.display_name,
  adapter_key = EXCLUDED.adapter_key,
  updated_at = NOW();

CREATE TABLE IF NOT EXISTS crawl_runs (
  id BIGSERIAL PRIMARY KEY,
  source_key TEXT NOT NULL REFERENCES crawler_sources(source_key),
  trigger_type TEXT NOT NULL CHECK (trigger_type IN ('cron', 'manual')),
  status TEXT NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'ok', 'partial', 'failed', 'skipped')),
  started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  finished_at TIMESTAMPTZ,
  duration_ms INTEGER,
  regions INTEGER NOT NULL DEFAULT 0,
  processed INTEGER NOT NULL DEFAULT 0,
  created INTEGER NOT NULL DEFAULT 0,
  updated INTEGER NOT NULL DEFAULT 0,
  skipped INTEGER NOT NULL DEFAULT 0,
  failed INTEGER NOT NULL DEFAULT 0,
  error_message TEXT,
  summary JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS crawl_runs_source_started_idx ON crawl_runs(source_key, started_at DESC);
CREATE INDEX IF NOT EXISTS crawl_runs_status_idx ON crawl_runs(status);

CREATE TABLE IF NOT EXISTS crawl_failures (
  id BIGSERIAL PRIMARY KEY,
  run_id BIGINT NOT NULL REFERENCES crawl_runs(id) ON DELETE CASCADE,
  source_key TEXT NOT NULL REFERENCES crawler_sources(source_key),
  bbs INTEGER,
  city TEXT,
  msgid BIGINT,
  source_url TEXT,
  error_message TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS crawl_failures_run_idx ON crawl_failures(run_id);
CREATE INDEX IF NOT EXISTS crawl_failures_source_created_idx ON crawl_failures(source_key, created_at DESC);
