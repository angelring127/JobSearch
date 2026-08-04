import { NextResponse } from 'next/server';
import { query } from '@/lib/server/db';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

type JobRow = {
  id: number;
  msgid: number;
  title: string | null;
  title_translations: Partial<Record<'ko' | 'en' | 'ja' | 'zh', string>>;
  wage_min: number | null;
  wage_max: number | null;
  lat: number | null;
  lng: number | null;
  source_url: string;
  source_name: string;
  confidence: number;
  category: string | null;
  region_hint: string | null;
  posted_at: string | null;
  posted_at_is_estimated: boolean;
};

function numberParam(params: URLSearchParams, key: string) {
  const value = params.get(key);
  if (value === null || value === '') return null;

  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : NaN;
}

function intParam(params: URLSearchParams, key: string, fallback?: number) {
  const value = numberParam(params, key);
  if (value === null) return fallback ?? null;
  if (!Number.isFinite(value)) return NaN;
  return Math.trunc(value);
}

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);

  const minLng = numberParam(searchParams, 'minLng');
  const minLat = numberParam(searchParams, 'minLat');
  const maxLng = numberParam(searchParams, 'maxLng');
  const maxLat = numberParam(searchParams, 'maxLat');
  const wageMin = intParam(searchParams, 'wageMin');
  const wageMax = intParam(searchParams, 'wageMax');
  const limit = intParam(searchParams, 'limit', 100);
  const category = searchParams.get('category');

  if (
    minLng === null || minLat === null || maxLng === null || maxLat === null ||
    !Number.isFinite(minLng) || !Number.isFinite(minLat) ||
    !Number.isFinite(maxLng) || !Number.isFinite(maxLat) ||
    minLng >= maxLng || minLat >= maxLat
  ) {
    return NextResponse.json(
      {
        success: false,
        error: {
          code: 'INVALID_BBOX',
          message: 'Invalid bounding box parameters',
        },
      },
      { status: 400 }
    );
  }

  if (
    (wageMin !== null && wageMin !== undefined && (!Number.isFinite(wageMin) || wageMin < 0)) ||
    (wageMax !== null && wageMax !== undefined && (!Number.isFinite(wageMax) || wageMax < 0)) ||
    limit === null || !Number.isFinite(limit) || limit < 1 || limit > 500
  ) {
    return NextResponse.json(
      {
        success: false,
        error: {
          code: 'INVALID_FILTER',
          message: 'Invalid filter parameters',
        },
      },
      { status: 400 }
    );
  }

  const filters: string[] = ['j.confidence >= 0.6', 'j.hidden = FALSE'];
  const values: unknown[] = [minLng, minLat, maxLng, maxLat];

  if (wageMin !== null && wageMin !== undefined) {
    values.push(wageMin);
    filters.push(`j.wage_min >= $${values.length}`);
  }

  if (wageMax !== null && wageMax !== undefined) {
    values.push(wageMax);
    filters.push(`j.wage_max <= $${values.length}`);
  }

  if (category) {
    values.push(category);
    filters.push(`j.category = $${values.length}`);
  }

  values.push(limit);

  try {
    const result = await query<JobRow>(
      `
        SELECT
          j.id::INTEGER AS id,
          COALESCE(js.msgid, 0)::INTEGER AS msgid,
          j.title,
          j.title_translations,
          j.wage_min,
          j.wage_max,
          COALESCE(ST_Y(j.geom::geometry), j.lat) AS lat,
          COALESCE(ST_X(j.geom::geometry), j.lng) AS lng,
          COALESCE(js.source_url, '') AS source_url,
          COALESCE(js.source_name, js.source_key, '') AS source_name,
          j.confidence,
          j.category,
          j.region_hint,
          TO_CHAR(js.posted_at, 'YYYY-MM-DD') AS posted_at,
          FALSE AS posted_at_is_estimated
        FROM jobs j
        LEFT JOIN LATERAL (
          SELECT
            source.msgid,
            source.source_url,
            source.source_key,
            crawler_source.display_name AS source_name,
            source.posted_at,
            source.created_at
          FROM job_sources source
          LEFT JOIN crawler_sources crawler_source USING (source_key)
          WHERE source.job_id = j.id
          ORDER BY (source.id = j.primary_source_id) DESC, source.created_at DESC
          LIMIT 1
        ) js ON TRUE
        WHERE j.geom && ST_MakeEnvelope($1, $2, $3, $4, 4326)
          AND ${filters.join(' AND ')}
        ORDER BY js.posted_at DESC NULLS LAST, j.updated_at DESC
        LIMIT $${values.length}
      `,
      values
    );

    return NextResponse.json({
      success: true,
      data: result.rows,
      meta: {
        count: result.rowCount,
        total: result.rowCount,
      },
      error: null,
    });
  } catch (error) {
    console.error('Failed to load viewport jobs', error);
    return NextResponse.json(
      {
        success: false,
        error: {
          code: 'DATABASE_ERROR',
          message: 'Failed to load jobs',
        },
      },
      { status: 500 }
    );
  }
}
