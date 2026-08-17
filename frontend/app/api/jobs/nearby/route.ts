import { NextResponse } from 'next/server';
import { query } from '@/lib/server/db';
import { isSourceCountry, SOURCE_KEYS_BY_COUNTRY } from '@/lib/source-countries';

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
  source_key: string;
  source_name: string;
  confidence: number;
  category: string | null;
  region_hint: string | null;
  posted_at: string | null;
  posted_at_is_estimated: boolean;
  distance_km: number;
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

  const lat = numberParam(searchParams, 'lat');
  const lng = numberParam(searchParams, 'lng');
  const radius = numberParam(searchParams, 'radius');
  const wageMin = intParam(searchParams, 'wageMin');
  const wageMax = intParam(searchParams, 'wageMax');
  const limit = intParam(searchParams, 'limit', 100);
  const category = searchParams.get('category');
  const rawSourceCountry = searchParams.get('sourceCountry');
  const sourceCountry = rawSourceCountry || null;

  if (
    lat === null || lng === null || radius === null ||
    !Number.isFinite(lat) || !Number.isFinite(lng) || !Number.isFinite(radius) ||
    lat < -90 || lat > 90 || lng < -180 || lng > 180 ||
    radius < 0.1 || radius > 50
  ) {
    return NextResponse.json(
      {
        success: false,
        error: {
          code: 'INVALID_RADIUS_QUERY',
          message: 'Invalid nearby search parameters',
        },
      },
      { status: 400 }
    );
  }

  if (
    (wageMin !== null && wageMin !== undefined && (!Number.isFinite(wageMin) || wageMin < 0)) ||
    (wageMax !== null && wageMax !== undefined && (!Number.isFinite(wageMax) || wageMax < 0)) ||
    limit === null || !Number.isFinite(limit) || limit < 1 || limit > 500 ||
    (sourceCountry !== null && !isSourceCountry(sourceCountry))
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

  const radiusMeters = radius * 1000;
  const filters: string[] = ['j.confidence >= 0.6', 'j.hidden = FALSE'];
  const values: unknown[] = [lng, lat, radiusMeters];

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

  let sourceKeysIndex: number | null = null;
  if (sourceCountry && isSourceCountry(sourceCountry)) {
    values.push([...SOURCE_KEYS_BY_COUNTRY[sourceCountry]]);
    sourceKeysIndex = values.length;
    filters.push(
      `EXISTS (
        SELECT 1
        FROM job_sources country_source
        WHERE country_source.job_id = j.id
          AND country_source.source_key = ANY($${sourceKeysIndex}::text[])
      )`
    );
  }

  const selectedSourceFilter = sourceKeysIndex
    ? `AND source.source_key = ANY($${sourceKeysIndex}::text[])`
    : '';

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
          COALESCE(js.source_key, '') AS source_key,
          COALESCE(js.source_name, js.source_key, '') AS source_name,
          j.confidence,
          j.category,
          j.region_hint,
          TO_CHAR(js.posted_at, 'YYYY-MM-DD') AS posted_at,
          FALSE AS posted_at_is_estimated,
          ST_DistanceSphere(j.geom::geometry, ST_MakePoint($1, $2)::geometry) / 1000.0 AS distance_km
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
            ${selectedSourceFilter}
          ORDER BY (source.id = j.primary_source_id) DESC, source.created_at DESC
          LIMIT 1
        ) js ON TRUE
        WHERE ST_DWithin(j.geom::geography, ST_MakePoint($1, $2)::geography, $3)
          AND ${filters.join(' AND ')}
        ORDER BY distance_km ASC
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
        center: { lat, lng },
        radius_km: radius,
      },
      error: null,
    });
  } catch (error) {
    console.error('Failed to load nearby jobs', error);
    return NextResponse.json(
      {
        success: false,
        error: {
          code: 'DATABASE_ERROR',
          message: 'Failed to load nearby jobs',
        },
      },
      { status: 500 }
    );
  }
}
