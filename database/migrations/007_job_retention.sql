-- Support the scheduled two-week job retention cleanup.

CREATE INDEX IF NOT EXISTS job_sources_retention_idx
  ON job_sources ((COALESCE(posted_at, created_at)));
