-- Preserve cents in hourly wages extracted from source titles and descriptions.

ALTER TABLE job_sources
  ALTER COLUMN wage_min TYPE NUMERIC(8,2) USING wage_min::NUMERIC(8,2),
  ALTER COLUMN wage_max TYPE NUMERIC(8,2) USING wage_max::NUMERIC(8,2);

ALTER TABLE jobs
  ALTER COLUMN wage_min TYPE NUMERIC(8,2) USING wage_min::NUMERIC(8,2),
  ALTER COLUMN wage_max TYPE NUMERIC(8,2) USING wage_max::NUMERIC(8,2);
