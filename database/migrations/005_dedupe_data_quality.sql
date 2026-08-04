-- Representative jobs, duplicate review, merge history, and admin audit log.

CREATE TABLE IF NOT EXISTS jobs (
  id BIGSERIAL PRIMARY KEY,
  primary_source_id BIGINT REFERENCES job_sources(id) ON DELETE SET NULL,
  title TEXT,
  region_hint TEXT,
  wage_min INTEGER,
  wage_max INTEGER,
  lat DOUBLE PRECISION,
  lng DOUBLE PRECISION,
  geom GEOGRAPHY(Point,4326),
  category TEXT,
  confidence FLOAT NOT NULL DEFAULT 0.8,
  source_count INTEGER NOT NULL DEFAULT 1,
  hidden BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS jobs_geom_idx ON jobs USING GIST(geom);
CREATE INDEX IF NOT EXISTS jobs_confidence_idx ON jobs(confidence);
CREATE INDEX IF NOT EXISTS jobs_category_idx ON jobs(category);
CREATE INDEX IF NOT EXISTS jobs_region_idx ON jobs(region_hint);

ALTER TABLE job_sources
  ADD COLUMN IF NOT EXISTS job_id BIGINT REFERENCES jobs(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS job_sources_job_id_idx ON job_sources(job_id);

WITH inserted AS (
  INSERT INTO jobs (
    primary_source_id, title, region_hint, wage_min, wage_max,
    lat, lng, geom, category, confidence, source_count
  )
  SELECT
    js.id, js.title, js.region_hint, js.wage_min, js.wage_max,
    js.lat, js.lng, js.geom, js.category, COALESCE(js.confidence, 0.8), 1
  FROM job_sources js
  WHERE js.job_id IS NULL
  RETURNING id, primary_source_id
)
UPDATE job_sources js
SET job_id = inserted.id
FROM inserted
WHERE js.id = inserted.primary_source_id;

CREATE TABLE IF NOT EXISTS duplicate_candidates (
  id BIGSERIAL PRIMARY KEY,
  source_job_id BIGINT NOT NULL REFERENCES job_sources(id) ON DELETE CASCADE,
  candidate_job_id BIGINT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  score NUMERIC(5,4) NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
  reason JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  reviewed_at TIMESTAMPTZ,
  reviewed_by TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS duplicate_candidates_source_candidate_idx
  ON duplicate_candidates(source_job_id, candidate_job_id);

CREATE INDEX IF NOT EXISTS duplicate_candidates_status_idx ON duplicate_candidates(status);

CREATE TABLE IF NOT EXISTS job_merge_history (
  id BIGSERIAL PRIMARY KEY,
  job_id BIGINT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  source_job_id BIGINT NOT NULL REFERENCES job_sources(id) ON DELETE CASCADE,
  action TEXT NOT NULL CHECK (action IN ('auto_merge', 'manual_merge', 'rollback')),
  previous_job_id BIGINT REFERENCES jobs(id) ON DELETE SET NULL,
  reason JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS job_merge_history_job_idx ON job_merge_history(job_id, created_at DESC);
CREATE INDEX IF NOT EXISTS job_merge_history_source_idx ON job_merge_history(source_job_id, created_at DESC);

CREATE TABLE IF NOT EXISTS admin_audit_log (
  id BIGSERIAL PRIMARY KEY,
  actor TEXT NOT NULL DEFAULT 'admin',
  action TEXT NOT NULL,
  target_type TEXT NOT NULL,
  target_id TEXT NOT NULL,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS admin_audit_log_created_idx ON admin_audit_log(created_at DESC);
CREATE INDEX IF NOT EXISTS admin_audit_log_action_idx ON admin_audit_log(action);
