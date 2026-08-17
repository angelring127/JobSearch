import { NextResponse } from 'next/server';
import { CITY_PRESETS, type CityPreset } from '@/lib/city-presets';
import { query } from '@/lib/server/db';
import { isSourceCountry, SOURCE_KEYS_BY_COUNTRY } from '@/lib/source-countries';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

type CityCountRow = {
  value: string;
  count: number;
};

const metroPresets = CITY_PRESETS.filter(
  (preset): preset is CityPreset & { radiusKm: number } => preset.radiusKm !== null
);

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const rawSourceCountry = searchParams.get('sourceCountry');
  const sourceCountry = rawSourceCountry || null;
  if (sourceCountry !== null && !isSourceCountry(sourceCountry)) {
    return NextResponse.json(
      {
        success: false,
        error: {
          code: 'INVALID_FILTER',
          message: 'Invalid source country',
        },
      },
      { status: 400 }
    );
  }

  const values: unknown[] = [];
  const cityRows = metroPresets.map((preset) => {
    const start = values.length + 1;
    values.push(
      preset.value,
      preset.center[0],
      preset.center[1],
      preset.radiusKm * 1000
    );
    return `($${start}::text, $${start + 1}::double precision, $${start + 2}::double precision, $${start + 3}::double precision)`;
  });
  let sourceKeysIndex: number | null = null;
  if (sourceCountry && isSourceCountry(sourceCountry)) {
    values.push([...SOURCE_KEYS_BY_COUNTRY[sourceCountry]]);
    sourceKeysIndex = values.length;
  }
  const sourceFilter = sourceKeysIndex
    ? `AND EXISTS (
        SELECT 1
        FROM job_sources country_source
        WHERE country_source.job_id = j.id
          AND country_source.source_key = ANY($${sourceKeysIndex}::text[])
      )`
    : '';

  try {
    const result = await query<CityCountRow>(
      `
        WITH cities(value, lng, lat, radius_meters) AS (
          VALUES ${cityRows.join(', ')}
        ),
        city_counts AS (
          SELECT
            c.value,
            COUNT(j.id)::INTEGER AS count
          FROM cities c
          LEFT JOIN jobs j
            ON j.confidence >= 0.6
            AND j.hidden = FALSE
            AND j.geom IS NOT NULL
            ${sourceFilter}
            AND ST_DWithin(
              j.geom,
              ST_SetSRID(ST_MakePoint(c.lng, c.lat), 4326)::geography,
              c.radius_meters
            )
          GROUP BY c.value
        )
        SELECT 'canada'::text AS value, COUNT(*)::INTEGER AS count
        FROM jobs j
        WHERE j.confidence >= 0.6
          AND j.hidden = FALSE
          AND j.geom IS NOT NULL
          ${sourceFilter}
        UNION ALL
        SELECT value, count
        FROM city_counts
      `,
      values
    );

    const counts = Object.fromEntries(
      CITY_PRESETS.map((preset) => [preset.value, 0])
    ) as Record<string, number>;

    for (const row of result.rows) {
      counts[row.value] = row.count;
    }

    return NextResponse.json(
      {
        success: true,
        data: counts,
        meta: {
          radius_km: 50,
        },
        error: null,
      },
      {
        headers: {
          'Cache-Control': 'no-store',
        },
      }
    );
  } catch (error) {
    console.error('Failed to load city job counts', error);
    return NextResponse.json(
      {
        success: false,
        error: {
          code: 'DATABASE_ERROR',
          message: 'Failed to load city job counts',
        },
      },
      { status: 500 }
    );
  }
}
