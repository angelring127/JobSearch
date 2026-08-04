-- Cover foreign-key columns used by joins and parent-row updates/deletes.

CREATE INDEX IF NOT EXISTS jobs_primary_source_id_idx
  ON public.jobs (primary_source_id);

CREATE INDEX IF NOT EXISTS duplicate_candidates_candidate_job_id_idx
  ON public.duplicate_candidates (candidate_job_id);
