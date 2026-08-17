// API client for JobMap Next.js route handlers
import type { SourceCountry } from '@/lib/source-countries';

export interface JobSource {
  id: number;
  msgid: number;
  title: string | null;
  title_translations?: Partial<Record<'ko' | 'en' | 'ja' | 'zh', string>> | null;
  wage_min: number | null;
  wage_max: number | null;
  lat: number | null;
  lng: number | null;
  source_url: string;
  source_key?: string;
  source_name?: string;
  confidence: number;
  category: string | null;
  region_hint: string | null;
  posted_at: string | null;
  posted_at_is_estimated?: boolean;
  distance_km?: number;
}

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  meta?: {
    count?: number;
    total?: number;
    center?: { lat: number; lng: number };
    radius_km?: number;
  };
  error?: {
    code: string;
    message: string;
    details?: any;
  };
}

export interface ViewportParams {
  minLng: number;
  minLat: number;
  maxLng: number;
  maxLat: number;
  zoom?: number;
  wageMin?: number;
  wageMax?: number;
  category?: string;
  sourceCountry?: SourceCountry;
  limit?: number;
}

export interface NearbyParams {
  lat: number;
  lng: number;
  radius: number;
  wageMin?: number;
  wageMax?: number;
  category?: string;
  sourceCountry?: SourceCountry;
  limit?: number;
}

export type CityJobCounts = Record<string, number>;

export async function getCityJobCounts(
  sourceCountry?: SourceCountry,
  signal?: AbortSignal
): Promise<ApiResponse<CityJobCounts>> {
  const queryParams = new URLSearchParams();
  if (sourceCountry) queryParams.set('sourceCountry', sourceCountry);
  const query = queryParams.toString();
  const response = await fetch(`/api/jobs/city-counts${query ? `?${query}` : ''}`, { signal });

  if (!response.ok) {
    throw new Error(`API error: ${response.statusText}`);
  }

  return response.json();
}

export async function getJobsByViewport(
  params: ViewportParams,
  signal?: AbortSignal
): Promise<ApiResponse<JobSource[]>> {
  const queryParams = new URLSearchParams();
  queryParams.append('minLng', params.minLng.toString());
  queryParams.append('minLat', params.minLat.toString());
  queryParams.append('maxLng', params.maxLng.toString());
  queryParams.append('maxLat', params.maxLat.toString());
  
  if (params.zoom !== undefined) {
    queryParams.append('zoom', params.zoom.toString());
  }
  if (params.wageMin !== undefined) {
    queryParams.append('wageMin', params.wageMin.toString());
  }
  if (params.wageMax !== undefined) {
    queryParams.append('wageMax', params.wageMax.toString());
  }
  if (params.category) {
    queryParams.append('category', params.category);
  }
  if (params.sourceCountry) {
    queryParams.append('sourceCountry', params.sourceCountry);
  }
  if (params.limit !== undefined) {
    queryParams.append('limit', params.limit.toString());
  }

  const response = await fetch(`/api/jobs/viewport?${queryParams}`, { signal });
  
  if (!response.ok) {
    throw new Error(`API error: ${response.statusText}`);
  }
  
  return response.json();
}

export async function getJobsByNearby(
  params: NearbyParams
): Promise<ApiResponse<JobSource[]>> {
  const queryParams = new URLSearchParams();
  queryParams.append('lat', params.lat.toString());
  queryParams.append('lng', params.lng.toString());
  queryParams.append('radius', params.radius.toString());
  
  if (params.wageMin !== undefined) {
    queryParams.append('wageMin', params.wageMin.toString());
  }
  if (params.wageMax !== undefined) {
    queryParams.append('wageMax', params.wageMax.toString());
  }
  if (params.category) {
    queryParams.append('category', params.category);
  }
  if (params.sourceCountry) {
    queryParams.append('sourceCountry', params.sourceCountry);
  }
  if (params.limit !== undefined) {
    queryParams.append('limit', params.limit.toString());
  }

  const response = await fetch(`/api/jobs/nearby?${queryParams}`);
  
  if (!response.ok) {
    throw new Error(`API error: ${response.statusText}`);
  }
  
  return response.json();
}
