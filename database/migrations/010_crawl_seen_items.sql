-- Track bounded recent-window crawl outcomes independently from the numeric
-- high-water mark so a source can repair older page gaps without retrying
-- intentionally rejected posts on every run.

CREATE TABLE IF NOT EXISTS crawl_seen_items (
  source_key TEXT NOT NULL REFERENCES crawler_sources(source_key) ON DELETE CASCADE,
  bbs INTEGER NOT NULL,
  external_id TEXT NOT NULL,
  outcome TEXT NOT NULL CHECK (outcome IN ('stored', 'skipped')),
  first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (source_key, bbs, external_id)
);

CREATE INDEX IF NOT EXISTS crawl_seen_items_updated_at_idx
  ON crawl_seen_items (updated_at);
