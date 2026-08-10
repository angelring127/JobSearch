-- Register the rate-limited public Sinojobs RSS/JobPosting adapter.

INSERT INTO crawler_sources (source_key, display_name, adapter_key, enabled)
VALUES ('sinojobs', 'Sinojobs Canada', 'sinojobs', TRUE)
ON CONFLICT (source_key)
DO UPDATE SET
  display_name = EXCLUDED.display_name,
  adapter_key = EXCLUDED.adapter_key,
  updated_at = NOW();
