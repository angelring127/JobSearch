-- PostgreSQL grants schema usage to PUBLIC by default. Remove that inherited
-- path so Supabase Data API roles cannot call PostGIS-owned public functions.

REVOKE ALL ON SCHEMA public FROM PUBLIC, anon, authenticated;
