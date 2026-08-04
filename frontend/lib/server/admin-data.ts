import { QueryResultRow } from 'pg';
import { query } from './db';

export interface AdminSourceRow extends QueryResultRow {
  source_key: string;
  display_name: string;
  adapter_key: string;
  enabled: boolean;
  last_status: string | null;
  last_run_at: Date | null;
  last_success_at: Date | null;
  last_error: string | null;
  last_run_id: string | null;
  last_trigger_type: string | null;
  last_started_at: Date | null;
  last_finished_at: Date | null;
  last_processed: number | null;
  last_failed: number | null;
}

export interface CrawlRunRow extends QueryResultRow {
  id: string;
  source_key: string;
  display_name: string;
  trigger_type: string;
  status: string;
  started_at: Date;
  finished_at: Date | null;
  duration_ms: number | null;
  processed: number;
  created: number;
  updated: number;
  skipped: number;
  failed: number;
  error_message: string | null;
}

export interface CrawlFailureRow extends QueryResultRow {
  id: string;
  run_id: string;
  source_key: string;
  display_name: string;
  bbs: number | null;
  city: string | null;
  msgid: string | null;
  source_url: string | null;
  error_message: string;
  created_at: Date;
}

export interface DuplicateCandidateRow extends QueryResultRow {
  id: string;
  source_job_id: string;
  candidate_job_id: string;
  score: string;
  reason: Record<string, unknown>;
  created_at: Date;
  source_title: string | null;
  source_region: string | null;
  source_wage_min: number | null;
  source_wage_max: number | null;
  candidate_title: string | null;
  candidate_region: string | null;
  candidate_wage_min: number | null;
  candidate_wage_max: number | null;
}

export interface MergeHistoryRow extends QueryResultRow {
  id: string;
  job_id: string;
  source_job_id: string;
  action: string;
  previous_job_id: string | null;
  reason: Record<string, unknown>;
  created_at: Date;
  source_title: string | null;
  job_title: string | null;
}

export interface AuditLogRow extends QueryResultRow {
  id: string;
  actor: string;
  action: string;
  target_type: string;
  target_id: string;
  metadata: Record<string, unknown>;
  created_at: Date;
}

export async function getAdminDashboardData() {
  const [sources, recentRuns, recentFailures, duplicateCandidates, mergeHistory, auditLog] = await Promise.all([
    query<AdminSourceRow>(
      `
      SELECT
        s.source_key,
        s.display_name,
        s.adapter_key,
        s.enabled,
        s.last_status,
        s.last_run_at,
        s.last_success_at,
        s.last_error,
        r.id::TEXT AS last_run_id,
        r.trigger_type AS last_trigger_type,
        r.started_at AS last_started_at,
        r.finished_at AS last_finished_at,
        r.processed AS last_processed,
        r.failed AS last_failed
      FROM crawler_sources s
      LEFT JOIN LATERAL (
        SELECT id, trigger_type, started_at, finished_at, processed, failed
        FROM crawl_runs
        WHERE source_key = s.source_key
        ORDER BY started_at DESC
        LIMIT 1
      ) r ON TRUE
      ORDER BY s.display_name ASC
      `
    ),
    query<CrawlRunRow>(
      `
      SELECT
        r.id::TEXT,
        r.source_key,
        s.display_name,
        r.trigger_type,
        r.status,
        r.started_at,
        r.finished_at,
        r.duration_ms,
        r.processed,
        r.created,
        r.updated,
        r.skipped,
        r.failed,
        r.error_message
      FROM crawl_runs r
      JOIN crawler_sources s ON s.source_key = r.source_key
      ORDER BY r.started_at DESC
      LIMIT 20
      `
    ),
    query<CrawlFailureRow>(
      `
      SELECT
        f.id::TEXT,
        f.run_id::TEXT,
        f.source_key,
        s.display_name,
        f.bbs,
        f.city,
        f.msgid::TEXT,
        f.source_url,
        f.error_message,
        f.created_at
      FROM crawl_failures f
      JOIN crawler_sources s ON s.source_key = f.source_key
      ORDER BY f.created_at DESC
      LIMIT 20
      `
    ),
    query<DuplicateCandidateRow>(
      `
      SELECT
        dc.id::TEXT,
        dc.source_job_id::TEXT,
        dc.candidate_job_id::TEXT,
        dc.score::TEXT,
        dc.reason,
        dc.created_at,
        js.title AS source_title,
        js.region_hint AS source_region,
        js.wage_min AS source_wage_min,
        js.wage_max AS source_wage_max,
        j.title AS candidate_title,
        j.region_hint AS candidate_region,
        j.wage_min AS candidate_wage_min,
        j.wage_max AS candidate_wage_max
      FROM duplicate_candidates dc
      JOIN job_sources js ON js.id = dc.source_job_id
      JOIN jobs j ON j.id = dc.candidate_job_id
      WHERE dc.status = 'pending'
      ORDER BY dc.score DESC, dc.created_at DESC
      LIMIT 20
      `
    ),
    query<MergeHistoryRow>(
      `
      SELECT
        h.id::TEXT,
        h.job_id::TEXT,
        h.source_job_id::TEXT,
        h.action,
        h.previous_job_id::TEXT,
        h.reason,
        h.created_at,
        js.title AS source_title,
        j.title AS job_title
      FROM job_merge_history h
      JOIN job_sources js ON js.id = h.source_job_id
      JOIN jobs j ON j.id = h.job_id
      ORDER BY h.created_at DESC
      LIMIT 20
      `
    ),
    query<AuditLogRow>(
      `
      SELECT
        id::TEXT,
        actor,
        action,
        target_type,
        target_id,
        metadata,
        created_at
      FROM admin_audit_log
      ORDER BY created_at DESC
      LIMIT 20
      `
    ),
  ]);

  return {
    sources: sources.rows,
    recentRuns: recentRuns.rows,
    recentFailures: recentFailures.rows,
    duplicateCandidates: duplicateCandidates.rows,
    mergeHistory: mergeHistory.rows,
    auditLog: auditLog.rows,
  };
}
