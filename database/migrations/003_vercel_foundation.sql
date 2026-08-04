-- Vercel deployment foundation
-- Keeps the original local schema working while adding fields needed by the
-- Vercel crawler service and future multi-source adapters.

ALTER TABLE job_sources
  ADD COLUMN IF NOT EXISTS source_key TEXT NOT NULL DEFAULT 'jpcanada',
  ADD COLUMN IF NOT EXISTS external_id TEXT,
  ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW();

UPDATE job_sources
SET source_key = 'jpcanada'
WHERE source_key IS NULL OR source_key = '';

UPDATE job_sources
SET external_id = msgid::TEXT
WHERE external_id IS NULL;

CREATE INDEX IF NOT EXISTS job_sources_source_key_idx
  ON job_sources(source_key);

CREATE INDEX IF NOT EXISTS job_sources_source_external_idx
  ON job_sources(source_key, external_id);

CREATE INDEX IF NOT EXISTS job_sources_confidence_idx
  ON job_sources(confidence);

ALTER TABLE crawl_log
  ADD COLUMN IF NOT EXISTS source_key TEXT NOT NULL DEFAULT 'jpcanada';

UPDATE crawl_log
SET source_key = 'jpcanada'
WHERE source_key IS NULL OR source_key = '';

CREATE UNIQUE INDEX IF NOT EXISTS crawl_log_source_bbs_unique_idx
  ON crawl_log(source_key, bbs);
