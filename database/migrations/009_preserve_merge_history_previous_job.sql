-- Preserve the removed representative ID as immutable audit data.
-- Reconciliation deletes the empty representative row after moving its raw
-- sources, so an ON DELETE SET NULL foreign key erases this audit reference.

ALTER TABLE job_merge_history
  DROP CONSTRAINT IF EXISTS job_merge_history_previous_job_id_fkey;
