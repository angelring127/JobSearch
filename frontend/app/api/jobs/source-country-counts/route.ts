import { NextResponse } from 'next/server';
import { query } from '@/lib/server/db';
import {
  SOURCE_COUNTRIES,
  SOURCE_KEYS_BY_COUNTRY,
  type SourceCountry,
} from '@/lib/source-countries';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

type CountRow = {
  value: SourceCountry | 'all';
  count: number;
};

export async function GET() {
  const values: unknown[] = [];
  const countryRows = SOURCE_COUNTRIES.map((country) => {
    const start = values.length + 1;
    values.push(country, [...SOURCE_KEYS_BY_COUNTRY[country]]);
    return `($${start}::text, $${start + 1}::text[])`;
  });

  try {
    const result = await query<CountRow>(
      `
        WITH eligible_jobs AS (
          SELECT id
          FROM jobs
          WHERE confidence >= 0.6
            AND hidden = FALSE
            AND geom IS NOT NULL
        ),
        source_countries(value, source_keys) AS (
          VALUES ${countryRows.join(', ')}
        )
        SELECT 'all'::text AS value, COUNT(*)::INTEGER AS count
        FROM eligible_jobs
        UNION ALL
        SELECT
          country.value,
          COUNT(eligible.id)::INTEGER AS count
        FROM source_countries country
        LEFT JOIN eligible_jobs eligible
          ON EXISTS (
            SELECT 1
            FROM job_sources source
            WHERE source.job_id = eligible.id
              AND source.source_key = ANY(country.source_keys)
          )
        GROUP BY country.value
      `,
      values
    );

    const counts: Record<SourceCountry | 'all', number> = {
      all: 0,
      kr: 0,
      jp: 0,
      cn: 0,
    };
    for (const row of result.rows) counts[row.value] = row.count;

    return NextResponse.json(
      {
        success: true,
        data: counts,
        error: null,
      },
      {
        headers: {
          'Cache-Control': 'no-store',
        },
      }
    );
  } catch (error) {
    console.error('Failed to load source-country job counts', error);
    return NextResponse.json(
      {
        success: false,
        error: {
          code: 'DATABASE_ERROR',
          message: 'Failed to load source-country job counts',
        },
      },
      { status: 500 }
    );
  }
}
