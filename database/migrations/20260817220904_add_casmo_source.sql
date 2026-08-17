-- Register the anonymous public-listing-only Casmo community job source.
INSERT INTO crawler_sources (source_key, display_name, adapter_key, enabled)
VALUES ('casmo', '캐스모', 'casmo', TRUE)
ON CONFLICT (source_key) DO UPDATE SET
  display_name = EXCLUDED.display_name,
  adapter_key = EXCLUDED.adapter_key,
  updated_at = NOW();
