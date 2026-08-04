'use server';

import { redirect } from 'next/navigation';
import { revalidatePath } from 'next/cache';
import type { PoolClient, QueryResultRow } from 'pg';
import { clearAdminSession, createAdminSession, requireAdmin, verifyAdminPassword } from '@/lib/server/admin-auth';
import { runCrawlerSource } from '@/lib/server/crawler-service';
import { getPool, query } from '@/lib/server/db';

interface DuplicateCandidateActionRow extends QueryResultRow {
  id: string;
  source_job_id: string;
  candidate_job_id: string;
  reason: Record<string, unknown>;
  current_job_id: string | null;
}

interface MergeRollbackActionRow extends QueryResultRow {
  id: string;
  job_id: string;
  source_job_id: string;
  title: string | null;
  region_hint: string | null;
  wage_min: number | null;
  wage_max: number | null;
  lat: number | null;
  lng: number | null;
  category: string | null;
  confidence: number;
}

interface InsertedJobRow extends QueryResultRow {
  id: string;
}

export async function loginAction(formData: FormData) {
  const password = String(formData.get('password') || '');
  if (!verifyAdminPassword(password)) {
    redirect('/admin/login?error=1');
  }

  await createAdminSession();
  redirect('/admin');
}

export async function logoutAction() {
  await clearAdminSession();
  redirect('/admin/login');
}

export async function toggleSourceAction(formData: FormData) {
  await requireAdmin();

  const sourceKey = String(formData.get('source_key') || '');
  const enabled = String(formData.get('enabled') || '') === 'true';
  if (!sourceKey) {
    throw new Error('source_key is required');
  }

  await query(
    `
    UPDATE crawler_sources
    SET enabled = $1,
        updated_at = NOW()
    WHERE source_key = $2
    `,
    [enabled, sourceKey]
  );

  revalidatePath('/admin');
}

export async function runSourceAction(formData: FormData) {
  await requireAdmin();

  const sourceKey = String(formData.get('source_key') || '');
  if (!sourceKey) {
    throw new Error('source_key is required');
  }

  const result = await runCrawlerSource(sourceKey);
  await logAudit('manual_crawl', 'crawler_source', sourceKey, result);
  revalidatePath('/admin');
}

export async function approveDuplicateAction(formData: FormData) {
  await requireAdmin();

  const candidateId = String(formData.get('candidate_id') || '');
  if (!candidateId) {
    throw new Error('candidate_id is required');
  }

  const client = await getPool().connect();
  try {
    await client.query('BEGIN');
    const candidate = await client.query<DuplicateCandidateActionRow>(
      `
      SELECT
        dc.id::TEXT,
        dc.source_job_id::TEXT,
        dc.candidate_job_id::TEXT,
        dc.reason,
        js.job_id::TEXT AS current_job_id
      FROM duplicate_candidates dc
      JOIN job_sources js ON js.id = dc.source_job_id
      WHERE dc.id = $1 AND dc.status = 'pending'
      FOR UPDATE
      `,
      [candidateId]
    );

    const row = candidate.rows[0];
    if (!row) {
      throw new Error('duplicate candidate not found');
    }

    await client.query('UPDATE job_sources SET job_id = $1 WHERE id = $2', [row.candidate_job_id, row.source_job_id]);
    await client.query(
      `
      INSERT INTO job_merge_history (job_id, source_job_id, action, previous_job_id, reason)
      VALUES ($1, $2, 'manual_merge', $3, $4::jsonb)
      `,
      [row.candidate_job_id, row.source_job_id, row.current_job_id, JSON.stringify(row.reason)]
    );
    await refreshSourceCount(client, row.candidate_job_id);
    if (row.current_job_id) {
      await refreshSourceCount(client, row.current_job_id);
    }
    await client.query(
      "UPDATE duplicate_candidates SET status = 'approved', reviewed_at = NOW(), reviewed_by = 'admin' WHERE id = $1",
      [candidateId]
    );
    await insertAudit(client, 'duplicate_approve', 'duplicate_candidate', candidateId, row);
    await client.query('COMMIT');
  } catch (error) {
    await client.query('ROLLBACK');
    throw error;
  } finally {
    client.release();
  }

  revalidatePath('/admin');
}

export async function rejectDuplicateAction(formData: FormData) {
  await requireAdmin();

  const candidateId = String(formData.get('candidate_id') || '');
  if (!candidateId) {
    throw new Error('candidate_id is required');
  }

  await query(
    "UPDATE duplicate_candidates SET status = 'rejected', reviewed_at = NOW(), reviewed_by = 'admin' WHERE id = $1",
    [candidateId]
  );
  await logAudit('duplicate_reject', 'duplicate_candidate', candidateId, {});
  revalidatePath('/admin');
}

export async function rollbackMergeAction(formData: FormData) {
  await requireAdmin();

  const historyId = String(formData.get('history_id') || '');
  if (!historyId) {
    throw new Error('history_id is required');
  }

  const client = await getPool().connect();
  try {
    await client.query('BEGIN');
    const history = await client.query<MergeRollbackActionRow>(
      `
      SELECT
        h.id::TEXT,
        h.job_id::TEXT,
        h.source_job_id::TEXT,
        js.title,
        js.region_hint,
        js.wage_min,
        js.wage_max,
        js.lat,
        js.lng,
        js.category,
        js.confidence
      FROM job_merge_history h
      JOIN job_sources js ON js.id = h.source_job_id
      WHERE h.id = $1 AND h.action IN ('auto_merge', 'manual_merge')
      FOR UPDATE
      `,
      [historyId]
    );

    const row = history.rows[0];
    if (!row) {
      throw new Error('merge history not found');
    }

    const inserted = await client.query<InsertedJobRow>(
      `
      INSERT INTO jobs (
        primary_source_id, title, region_hint, wage_min, wage_max,
        lat, lng, geom, category, confidence, source_count
      )
      VALUES (
        $1, $2, $3, $4, $5,
        $6, $7,
        CASE
          WHEN $6::DOUBLE PRECISION IS NOT NULL AND $7::DOUBLE PRECISION IS NOT NULL
            THEN ST_SetSRID(ST_MakePoint($7::DOUBLE PRECISION, $6::DOUBLE PRECISION), 4326)::geography
          ELSE NULL
        END,
        $8, $9, 1
      )
      RETURNING id::TEXT
      `,
      [
        row.source_job_id,
        row.title,
        row.region_hint,
        row.wage_min,
        row.wage_max,
        row.lat,
        row.lng,
        row.category,
        row.confidence,
      ]
    );
    const newJobId = inserted.rows[0].id;
    await client.query('UPDATE job_sources SET job_id = $1 WHERE id = $2', [newJobId, row.source_job_id]);
    await refreshSourceCount(client, row.job_id);
    await client.query(
      `
      INSERT INTO job_merge_history (job_id, source_job_id, action, previous_job_id, reason)
      VALUES ($1, $2, 'rollback', $3, $4::jsonb)
      `,
      [newJobId, row.source_job_id, row.job_id, JSON.stringify({ rolled_back_history_id: historyId })]
    );
    await insertAudit(client, 'merge_rollback', 'job_merge_history', historyId, { new_job_id: newJobId });
    await client.query('COMMIT');
  } catch (error) {
    await client.query('ROLLBACK');
    throw error;
  } finally {
    client.release();
  }

  revalidatePath('/admin');
}

async function logAudit(action: string, targetType: string, targetId: string, metadata: unknown) {
  await query(
    `
    INSERT INTO admin_audit_log (actor, action, target_type, target_id, metadata)
    VALUES ('admin', $1, $2, $3, $4::jsonb)
    `,
    [action, targetType, targetId, JSON.stringify(metadata)]
  );
}

async function insertAudit(
  client: PoolClient,
  action: string,
  targetType: string,
  targetId: string,
  metadata: unknown
) {
  await client.query(
    `
    INSERT INTO admin_audit_log (actor, action, target_type, target_id, metadata)
    VALUES ('admin', $1, $2, $3, $4::jsonb)
    `,
    [action, targetType, targetId, JSON.stringify(metadata)]
  );
}

async function refreshSourceCount(
  client: PoolClient,
  jobId: string
) {
  await client.query(
    `
    UPDATE jobs
    SET source_count = (
      SELECT COUNT(*) FROM job_sources WHERE job_id = $1
    ),
    updated_at = NOW()
    WHERE id = $1
    `,
    [jobId]
  );
}
