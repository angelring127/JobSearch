'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { Map as MapLibreMap, Marker } from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { getJobsByViewport, JobSource, ViewportParams } from '@/lib/api';

interface MapProps {
  initialCenter?: [number, number];
  initialZoom?: number;
  filters?: {
    wageMin?: number;
    wageMax?: number;
    category?: string;
    radius?: number;
  };
  selectedJob?: JobSource | null;
  onJobsUpdate?: (jobs: JobSource[]) => void;
  onJobSelect?: (job: JobSource) => void;
  onMapCenterChange?: (center: [number, number], zoom?: number) => void;
}

export default function Map({ 
  initialCenter = [-123.1207, 49.2827], 
  initialZoom = 12,
  filters,
  selectedJob,
  onJobsUpdate,
  onJobSelect,
  onMapCenterChange,
}: MapProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<MapLibreMap | null>(null);
  const markersRef = useRef<Marker[]>([]);
  const [jobs, setJobs] = useState<JobSource[]>([]);
  const [loading, setLoading] = useState(false);
  const [mapError, setMapError] = useState<string | null>(null);

  // マーカー更新関数
  const updateMarkers = useCallback((jobList: JobSource[], selected?: JobSource | null) => {
    if (!map.current || mapError) return;

    // 既存のマーカーを削除
    markersRef.current.forEach(marker => marker.remove());
    markersRef.current = [];
    
    jobList.forEach((job) => {
      if (job.lat && job.lng) {
        const el = document.createElement('div');
        el.className = 'job-marker';
        el.style.width = selected?.id === job.id ? '28px' : '20px';
        el.style.height = selected?.id === job.id ? '28px' : '20px';
        el.style.borderRadius = '50%';
        el.style.backgroundColor = selected?.id === job.id ? '#ef4444' : '#3b82f6';
        el.style.border = selected?.id === job.id ? '3px solid white' : '2px solid white';
        el.style.cursor = 'pointer';
        el.style.transition = 'all 0.2s ease';
        el.style.boxShadow = selected?.id === job.id ? '0 0 0 4px rgba(239, 68, 68, 0.3)' : 'none';

        const marker = new Marker(el)
          .setLngLat([job.lng, job.lat])
          .addTo(map.current!);

        el.addEventListener('click', () => {
          // マーカークリック時に選択状態を設定
          if (onJobSelect) {
            onJobSelect(job);
          }
        });

        markersRef.current.push(marker);
      }
    });
  }, [mapError, onJobSelect]);

  const loadJobsForViewport = useCallback(async () => {
    if (!map.current || mapError) return;

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
      };

      const response = await getJobsByViewport(params);
      if (response.success && response.data) {
        setJobs(response.data);
        updateMarkers(response.data, selectedJob);
        // 親コンポーネントにジョブリストを通知
        if (onJobsUpdate) {
          onJobsUpdate(response.data);
        }
      }
    } catch (error) {
      console.error('Failed to load jobs:', error);
    } finally {
      setLoading(false);
    }
  }, [mapError, updateMarkers, filters, selectedJob, onJobsUpdate]);

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
        center: initialCenter,
        zoom: initialZoom
      });

      map.current = mapInstance;

      // 지도 에러 핸들러
      mapInstance.on('error', (e) => {
        console.error('Map error:', e);
        setMapError('지도를 로드하는 중 오류가 발생했습니다.');
      });

      // 지도 로드 완료 후 이벤트 핸들러 등록
      mapInstance.on('load', () => {
        console.log('Map loaded successfully');
        // 지도 이동/줌 이벤트 핸들러 (디바운스)
        let debounceTimer: NodeJS.Timeout;
        const handleMapMove = () => {
          clearTimeout(debounceTimer);
          debounceTimer = setTimeout(() => {
            if (map.current) {
              loadJobsForViewport();
              // 地図中心変更を親に通知
              if (onMapCenterChange) {
                const center = map.current.getCenter();
                onMapCenterChange([center.lng, center.lat], map.current.getZoom());
              }
            }
          }, 400);
        };

        mapInstance!.on('moveend', handleMapMove);
        mapInstance!.on('zoomend', handleMapMove);

        // 초기 로드
        loadJobsForViewport();
      });
    } catch (error) {
      console.error('Failed to initialize map', error);
      setMapError('지도를 초기화하는 중 문제가 발생했습니다. 브라우저가 WebGL을 지원하는지 확인해 주세요.');
      return;
    }

    return () => {
      if (mapInstance) {
        mapInstance.remove();
      }
      map.current = null;
    };
  }, []); // 初期化は一度だけ

  // フィルタ変更時にジョブを再読み込み
  useEffect(() => {
    if (map.current && !mapError) {
      loadJobsForViewport();
    }
  }, [filters, loadJobsForViewport, mapError]);

  // 選択されたジョブが変更されたらマーカーを更新
  useEffect(() => {
    if (map.current && !mapError) {
      updateMarkers(jobs, selectedJob);
      // 選択されたジョブの位置に地図を移動
      if (selectedJob && selectedJob.lat && selectedJob.lng) {
        map.current.flyTo({
          center: [selectedJob.lng, selectedJob.lat],
          zoom: Math.max(map.current.getZoom(), 14),
          duration: 1000,
        });
      }
    }
  }, [selectedJob, jobs, updateMarkers, mapError]);

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
    <div className="relative w-full h-full">
      <div ref={mapContainer} className="w-full h-full bg-gray-100" />
      {mapError && (
        <div className="absolute inset-0 flex items-center justify-center px-6 text-center">
          <div className="rounded-lg bg-white/90 p-6 shadow">
            <p className="text-base text-gray-700">{mapError}</p>
          </div>
        </div>
      )}
      {loading && (
        <div className="absolute top-4 left-4 bg-white px-4 py-2 rounded shadow flex items-center gap-2">
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500"></div>
          <span className="text-sm">로딩 중...</span>
        </div>
      )}
    </div>
  );
}


