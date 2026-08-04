-- JobMap uses server-side PostgreSQL connections only. Prevent Supabase Data
-- API roles from reading or mutating operational tables and PostGIS objects.

ALTER TABLE public.regions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.job_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.crawl_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.crawler_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.crawl_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.crawl_failures ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.duplicate_candidates ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.job_merge_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.admin_audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.crawl_seen_items ENABLE ROW LEVEL SECURITY;

-- The application does not use Supabase Data API access. Revoking schema
-- usage also protects PostGIS-owned tables and functions that the project
-- database owner cannot alter directly.
REVOKE ALL ON SCHEMA public
FROM anon, authenticated;

REVOKE ALL PRIVILEGES ON TABLE
  public.regions,
  public.job_sources,
  public.crawl_log,
  public.crawler_sources,
  public.crawl_runs,
  public.crawl_failures,
  public.jobs,
  public.duplicate_candidates,
  public.job_merge_history,
  public.admin_audit_log,
  public.crawl_seen_items
FROM anon, authenticated;

REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public
FROM anon, authenticated;

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
REVOKE ALL PRIVILEGES ON TABLES FROM anon, authenticated;

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
REVOKE ALL PRIVILEGES ON SEQUENCES FROM anon, authenticated;
