# Supabase Production Rollout SPEC

## Purpose

Prepare the empty `SearchingJob` Supabase PostgreSQL project for JobMap's
server-only database access without exposing operational data through the
Supabase Data API.

## Scope

- Apply the existing JobMap migrations in their documented order.
- Enable PostGIS and verify the required application tables and source seeds.
- Enable RLS on every JobMap-owned table in the exposed `public` schema.
- Remove `anon` and `authenticated` access to JobMap tables, sequences, and the
  `public` schema because the application uses PostgreSQL connections only.
- Keep Supabase-managed PostGIS objects unchanged while making them unreachable
  to Data API roles through schema privilege removal.
- Add indexes for the two foreign-key columns reported by the Supabase
  performance advisor.
- Record the production rollout and residual external configuration in the
  Vercel implementation board.

## Exclusions

- Do not add Supabase client SDK usage or browser-exposed database credentials.
- Do not add Data API policies for `anon` or `authenticated` roles.
- Do not move, drop, or recreate the Supabase-managed PostGIS extension.
- Do not copy local job rows or run production crawlers in this checkpoint.
- Do not store a database password or connection string in Git.

## Scenarios

1. A server-side Vercel function connects with `DATABASE_URL` and can query and
   mutate JobMap tables.
2. A caller using the Supabase publishable key cannot use the Data API to read,
   insert, update, delete, truncate, or call public PostGIS functions.
3. A fresh database can apply the committed migrations in order and end with
   the same protected schema.
4. Supabase-owned PostGIS objects remain installed and usable by the database
   owner even though the advisor cannot enable RLS on `spatial_ref_sys`.

## Completion Criteria

- Supabase records the ten existing migrations and all new rollout migrations.
- PostGIS is installed, five regions and four crawler sources exist, and job
  tables are initially empty.
- All eleven JobMap-owned public tables have RLS enabled.
- `anon` and `authenticated` have no public schema usage and no SELECT, INSERT,
  DELETE, or TRUNCATE privilege on `public.jobs`.
- The effective ability to call the reported PostGIS security-definer function
  is false for both Data API roles.
- The two foreign-key indexes exist and no unindexed-foreign-key advisor remains.
- No secret value is present in the Git diff.

## Edge Cases

- Enabling RLS on `spatial_ref_sys` fails because it is owned by Supabase; the
  migration must protect it through schema access removal instead.
- Revoking privileges from named Data API roles alone is insufficient when
  PostgreSQL's `PUBLIC` role still grants schema usage.
- Empty-database unused-index notices are expected until production queries run
  and must not cause required indexes to be removed.

## Test Method

- Inspect Supabase project, table, extension, and migration metadata.
- Execute privilege and RLS verification queries as the database owner.
- Run Supabase security and performance advisors after all DDL.
- Run `git diff --check` and inspect the checkpoint diff for credentials.
- Validate review inputs and dispatch a read-only independent review.
