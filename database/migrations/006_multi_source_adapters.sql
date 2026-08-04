-- Register public job sources supported by the Python crawler adapters.

INSERT INTO crawler_sources (source_key, display_name, adapter_key, enabled)
VALUES
  ('ourvancouver', '우벤유', 'ourvancouver', TRUE),
  ('jinzaicanada', '인재 캐나다', 'jinzaicanada', TRUE),
  ('vanchosun', '밴조선', 'vanchosun', TRUE)
ON CONFLICT (source_key)
DO UPDATE SET
  display_name = EXCLUDED.display_name,
  adapter_key = EXCLUDED.adapter_key,
  updated_at = NOW();
