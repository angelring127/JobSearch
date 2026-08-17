'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { Map as MapLibreMap, Marker } from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { getJobsByViewport, JobSource, ViewportParams } from '@/lib/api';
import { getJobTitle, t, type Locale } from '@/lib/i18n';
import type { SourceCountry } from '@/lib/source-countries';

type LocationError = 'permission' | 'unavailable' | null;

interface MapProps {
  initialCenter?: [number, number];
  initialZoom?: number;
  filters?: {
    wageMin?: number;
    wageMax?: number;
    category?: string;
    radius?: number;
    sourceCountry?: SourceCountry;
  };
  selectedJob?: JobSource | null;
  onJobsUpdate?: (jobs: JobSource[]) => void;
  onJobSelect?: (job: JobSource) => void;
  onMapCenterChange?: (center: [number, number], zoom?: number) => void;
  isActive?: boolean;
  locale: Locale;
}

export default function Map({ 
  initialCenter = [-101.5, 54.2],
  initialZoom = 3,
  filters,
  selectedJob,
  onJobsUpdate,
  onJobSelect,
  onMapCenterChange,
  isActive = true,
  locale,
}: MapProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<MapLibreMap | null>(null);
  const mapLoadedRef = useRef(false);
  const mapErrorRef = useRef(false);
  const markersRef = useRef<Marker[]>([]);
  const userLocationMarkerRef = useRef<Marker | null>(null);
  const viewportRequestRef = useRef<AbortController | null>(null);
  const viewportRequestIdRef = useRef(0);
  const moveDebounceRef = useRef<NodeJS.Timeout | null>(null);
  const initialCenterRef = useRef(initialCenter);
  const initialZoomRef = useRef(initialZoom);
  const onMapCenterChangeRef = useRef(onMapCenterChange);
  const selectedJobRef = useRef(selectedJob);
  const [jobs, setJobs] = useState<JobSource[]>([]);
  const [loading, setLoading] = useState(true);
  const [mapError, setMapError] = useState<'load' | 'init' | null>(null);
  const [locationError, setLocationError] = useState<LocationError>(null);
  const [isLocating, setIsLocating] = useState(false);
  const [hasUserLocation, setHasUserLocation] = useState(false);

  const showMyLocation = useCallback(() => {
    if (!navigator.geolocation) {
      setLocationError('unavailable');
      return;
    }

    setIsLocating(true);
    setLocationError(null);
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        const currentMap = map.current;
        if (!currentMap) {
          setIsLocating(false);
          setLocationError('unavailable');
          return;
        }

        const position: [number, number] = [coords.longitude, coords.latitude];
        if (userLocationMarkerRef.current) {
          userLocationMarkerRef.current.setLngLat(position);
        } else {
          const markerElement = document.createElement('div');
          markerElement.className = 'user-location-marker';
          markerElement.setAttribute('role', 'img');
          markerElement.setAttribute('aria-label', t(locale, 'myLocationMarker'));
          markerElement.title = t(locale, 'myLocationMarker');
          userLocationMarkerRef.current = new Marker({ element: markerElement })
            .setLngLat(position)
            .addTo(currentMap);
        }

        const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        currentMap.flyTo({
          center: position,
          zoom: Math.max(currentMap.getZoom(), 13),
          duration: reduceMotion ? 0 : 800,
        });
        setHasUserLocation(true);
        setIsLocating(false);
      },
      (error) => {
        setIsLocating(false);
        setLocationError(error.code === error.PERMISSION_DENIED ? 'permission' : 'unavailable');
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 }
    );
  }, [locale]);

  const updateMarkers = useCallback((jobList: JobSource[], selected?: JobSource | null) => {
    if (!map.current || mapError) return;

    markersRef.current.forEach(marker => marker.remove());
    markersRef.current = [];

    const groupedJobs = new globalThis.Map<string, JobSource[]>();
    jobList.forEach((job) => {
      if (job.lat !== null && job.lat !== undefined && job.lng !== null && job.lng !== undefined) {
        const key = `${job.lng.toFixed(5)},${job.lat.toFixed(5)}`;
        groupedJobs.set(key, [...(groupedJobs.get(key) || []), job]);
      }
    });

    groupedJobs.forEach((group) => {
      const anchorJob = group[0];
      const selectedInGroup = selected ? group.some((job) => job.id === selected.id) : false;
      if (anchorJob.lat !== null && anchorJob.lat !== undefined && anchorJob.lng !== null && anchorJob.lng !== undefined) {
        const el = document.createElement('div');
        el.className = [
          'job-marker',
          group.length > 1 ? 'job-marker--cluster' : '',
          selectedInGroup ? 'job-marker--selected' : '',
        ].filter(Boolean).join(' ');
        el.title = group.length > 1
          ? `${t(locale, 'jobsAtLocation')} ${group.length}`
          : getJobTitle(anchorJob, locale);
        el.setAttribute('role', 'button');
        el.setAttribute('tabindex', '0');
        el.setAttribute('aria-label', el.title);
        if (group.length > 1) {
          el.textContent = String(group.length);
        }

        const marker = new Marker({ element: el })
          .setLngLat([anchorJob.lng, anchorJob.lat])
          .addTo(map.current!);

        const selectMarker = () => {
          if (onJobSelect) {
            onJobSelect(selectedInGroup && selected ? selected : anchorJob);
          }
        };
        el.addEventListener('click', selectMarker);
        el.addEventListener('keydown', (event) => {
          if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            selectMarker();
          }
        });

        markersRef.current.push(marker);
      }
    });
  }, [locale, mapError, onJobSelect]);

  const loadJobsForViewport = useCallback(async () => {
    if (!map.current || !mapLoadedRef.current || mapError) return;

    viewportRequestRef.current?.abort();
    const controller = new AbortController();
    const requestId = ++viewportRequestIdRef.current;
    viewportRequestRef.current = controller;
    setLoading(true);

    try {
      const bounds = map.current.getBounds();
      const params: ViewportParams = {
        minLng: bounds.getWest(),
        minLat: bounds.getSouth(),
        maxLng: bounds.getEast(),
        maxLat: bounds.getNorth(),
        zoom: Math.floor(map.current.getZoom()),
        wageMin: filters?.wageMin,
        wageMax: filters?.wageMax,
        category: filters?.category,
        sourceCountry: filters?.sourceCountry,
      };

      const response = await getJobsByViewport(params, controller.signal);
      if (requestId === viewportRequestIdRef.current && response.success && response.data) {
        setJobs(response.data);
        updateMarkers(response.data, selectedJobRef.current);
        // 親コンポーネントにジョブリストを通知
        if (onJobsUpdate) {
          onJobsUpdate(response.data);
        }
      }
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') return;
      console.error('Failed to load jobs:', error);
    } finally {
      if (requestId === viewportRequestIdRef.current) {
        viewportRequestRef.current = null;
        setLoading(false);
      }
    }
  }, [mapError, updateMarkers, filters, onJobsUpdate]);

  const loadJobsForViewportRef = useRef(loadJobsForViewport);

  useEffect(() => {
    loadJobsForViewportRef.current = loadJobsForViewport;
    onMapCenterChangeRef.current = onMapCenterChange;
  }, [loadJobsForViewport, onMapCenterChange]);

  useEffect(() => {
    selectedJobRef.current = selectedJob;
  }, [selectedJob]);

  // 地図初期化
  useEffect(() => {
    if (!mapContainer.current) return;

    let mapInstance: MapLibreMap | null = null;

    try {
      // MapLibre 초기화
      mapInstance = new MapLibreMap({
        container: mapContainer.current,
        style: {
          version: 8,
          sources: {
            'raster-tiles': {
              type: 'raster',
              tiles: [
                'https://tile.openstreetmap.org/{z}/{x}/{y}.png'
              ],
              tileSize: 256,
              attribution: '© OpenStreetMap contributors'
            }
          },
          layers: [
            {
              id: 'simple-tiles',
              type: 'raster',
              source: 'raster-tiles',
              minzoom: 0,
              maxzoom: 22
            }
          ]
        },
        center: initialCenterRef.current,
        zoom: initialZoomRef.current
      });

      map.current = mapInstance;

      // 지도 에러 핸들러
      mapInstance.on('error', (e) => {
        console.error('Map error:', e);
        mapErrorRef.current = true;
        viewportRequestIdRef.current += 1;
        viewportRequestRef.current?.abort();
        viewportRequestRef.current = null;
        setLoading(false);
        setMapError('load');
      });

      // 지도 로드 완료 후 이벤트 핸들러 등록
      mapInstance.on('load', () => {
        console.log('Map loaded successfully');
        mapLoadedRef.current = true;
        const handleMapMoveStart = () => {
          if (mapErrorRef.current) return;
          viewportRequestIdRef.current += 1;
          viewportRequestRef.current?.abort();
          viewportRequestRef.current = null;
          setLoading(true);
        };

        // 지도 이동 완료 후 현재 범위의 공고를 다시 불러온다.
        const handleMapMove = () => {
          if (mapErrorRef.current) {
            setLoading(false);
            return;
          }
          if (moveDebounceRef.current) clearTimeout(moveDebounceRef.current);
          moveDebounceRef.current = setTimeout(() => {
            if (map.current) {
              loadJobsForViewportRef.current();
              // 地図中心変更を親に通知
              if (onMapCenterChangeRef.current) {
                const center = map.current.getCenter();
                onMapCenterChangeRef.current([center.lng, center.lat], map.current.getZoom());
              }
            }
          }, 250);
        };

        mapInstance!.on('movestart', handleMapMoveStart);
        mapInstance!.on('moveend', handleMapMove);

        // 초기 로드
        loadJobsForViewportRef.current();
      });
    } catch (error) {
      console.error('Failed to initialize map', error);
      mapErrorRef.current = true;
      setLoading(false);
      setMapError('init');
      return;
    }

    return () => {
      mapErrorRef.current = true;
      viewportRequestIdRef.current += 1;
      viewportRequestRef.current?.abort();
      viewportRequestRef.current = null;
      if (moveDebounceRef.current) {
        clearTimeout(moveDebounceRef.current);
        moveDebounceRef.current = null;
      }
      userLocationMarkerRef.current?.remove();
      userLocationMarkerRef.current = null;
      if (mapInstance) {
        mapInstance.remove();
      }
      mapLoadedRef.current = false;
      map.current = null;
    };
  }, []); // 初期化は一度だけ

  useEffect(() => {
    const markerElement = userLocationMarkerRef.current?.getElement();
    if (!markerElement) return;
    markerElement.setAttribute('aria-label', t(locale, 'myLocationMarker'));
    markerElement.title = t(locale, 'myLocationMarker');
  }, [locale]);

  useEffect(() => {
    if (!isActive || !map.current) return;
    const resizeFrame = window.requestAnimationFrame(() => map.current?.resize());
    return () => window.cancelAnimationFrame(resizeFrame);
  }, [isActive]);

  // フィルタ変更時にジョブを再読み込み
  useEffect(() => {
    if (map.current && !mapError) {
      loadJobsForViewportRef.current();
    }
  }, [filters, mapError]);

  // ジョブまたは選択状態が変わったらマーカーだけ更新
  useEffect(() => {
    if (map.current && !mapError) {
      updateMarkers(jobs, selectedJob);
    }
  }, [selectedJob, jobs, updateMarkers, mapError]);

  const selectedJobId = selectedJob?.id ?? null;
  const selectedJobLat = selectedJob?.lat ?? null;
  const selectedJobLng = selectedJob?.lng ?? null;

  // 選択されたジョブ自体が変わった時だけ、その位置に地図を移動
  useEffect(() => {
    if (
      map.current
      && !mapError
      && selectedJobId !== null
      && selectedJobLat !== null
      && selectedJobLng !== null
    ) {
      map.current.flyTo({
        center: [selectedJobLng, selectedJobLat],
        zoom: Math.max(map.current.getZoom(), 14),
        duration: 1000,
      });
    }
  }, [selectedJobId, selectedJobLat, selectedJobLng, mapError]);

  // 地図中心変更（外部から）
  useEffect(() => {
    if (map.current && !mapError) {
      const currentCenter = map.current.getCenter();
      const newCenter = initialCenter;
      // 中心が大きく変わった場合のみ移動
      const distance = Math.sqrt(
        Math.pow(currentCenter.lng - newCenter[0], 2) + 
        Math.pow(currentCenter.lat - newCenter[1], 2)
      );
      if (distance > 0.01) {
        map.current.flyTo({
          center: newCenter,
          zoom: initialZoom,
          duration: 1000,
        });
      }
    }
  }, [initialCenter, initialZoom, mapError]);

  return (
    <div className="map-shell" aria-busy={loading}>
      <div ref={mapContainer} className="map-canvas" />
      <div className="map-location-control">
        <button
          type="button"
          className="map-location-button"
          onClick={showMyLocation}
          disabled={isLocating || Boolean(mapError)}
          aria-pressed={hasUserLocation}
        >
          {isLocating ? (
            <span className="spinner" aria-hidden="true" />
          ) : (
            <svg aria-hidden="true" viewBox="0 0 24 24">
              <circle cx="12" cy="12" r="3" />
              <path d="M12 2v3M12 19v3M2 12h3M19 12h3" />
            </svg>
          )}
          <span>{t(locale, isLocating ? 'locating' : 'showMyLocation')}</span>
        </button>
        {locationError && (
          <p className="map-location-error" role="alert">
            {t(locale, locationError === 'permission' ? 'locationPermissionDenied' : 'locationUnavailable')}
          </p>
        )}
      </div>
      {mapError && (
        <div className="map-message map-message--error" role="alert">
          <p>{t(locale, mapError === 'load' ? 'mapLoadError' : 'mapInitError')}</p>
        </div>
      )}
      {loading && (
        <div className="map-message map-message--loading" role="status" aria-live="polite">
          <span className="spinner spinner--accent" aria-hidden="true" />
          <span>{t(locale, 'mapLoading')}</span>
        </div>
      )}
    </div>
  );
}
