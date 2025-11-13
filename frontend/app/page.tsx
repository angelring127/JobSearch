'use client';

import { useState, useCallback } from 'react';
import Map from '@/components/Map';
import SearchBar from '@/components/SearchBar';
import FilterBar from '@/components/FilterBar';
import JobList from '@/components/JobList';
import JobDetail from '@/components/JobDetail';
import { JobSource } from '@/lib/api';

export default function Home() {
  const [jobs, setJobs] = useState<JobSource[]>([]);
  const [selectedJob, setSelectedJob] = useState<JobSource | null>(null);
  const [filters, setFilters] = useState({
    wageMin: undefined as number | undefined,
    wageMax: undefined as number | undefined,
    category: undefined as string | undefined,
    radius: undefined as number | undefined,
  });
  const [mapCenter, setMapCenter] = useState<[number, number]>([-123.1207, 49.2827]);
  const [mapZoom, setMapZoom] = useState(12);

  // ジョブリスト更新ハンドラ
  const handleJobsUpdate = useCallback((newJobs: JobSource[]) => {
    setJobs(newJobs);
  }, []);

  // フィルタ更新ハンドラ
  const handleFilterChange = useCallback((newFilters: typeof filters) => {
    setFilters(newFilters);
  }, []);

  // 地図中心移動ハンドラ
  const handleMapCenterChange = useCallback((center: [number, number], zoom?: number) => {
    setMapCenter(center);
    if (zoom !== undefined) {
      setMapZoom(zoom);
    }
  }, []);

  return (
    <main className="flex flex-col h-screen">
      <header className="bg-white shadow-sm p-4 flex-shrink-0">
        <h1 className="text-2xl font-bold">JobMap</h1>
        <p className="text-sm text-gray-600">캐나다 구인정보 지도 기반 탐색</p>
      </header>
      <div className="flex-1 flex min-h-0">
        {/* 左側パネル: 検索バー + フィルタ + リスト */}
        <div className="w-96 bg-white border-r border-gray-200 flex flex-col flex-shrink-0">
          <div className="p-4 border-b border-gray-200">
            <SearchBar onLocationSelect={handleMapCenterChange} />
          </div>
          <div className="p-4 border-b border-gray-200">
            <FilterBar filters={filters} onFilterChange={handleFilterChange} />
          </div>
          <div className="flex-1 overflow-hidden">
            <JobList 
              jobs={jobs} 
              selectedJob={selectedJob}
              onJobSelect={setSelectedJob}
            />
          </div>
        </div>
        
        {/* 右側: 地図エリア */}
        <div className="flex-1 relative min-h-0">
          <Map 
            initialCenter={mapCenter}
            initialZoom={mapZoom}
            filters={filters}
            selectedJob={selectedJob}
            onJobsUpdate={handleJobsUpdate}
            onJobSelect={setSelectedJob}
            onMapCenterChange={handleMapCenterChange}
          />
        </div>
      </div>
      
      {/* 詳細ポップアップ */}
      {selectedJob && (
        <JobDetail job={selectedJob} onClose={() => setSelectedJob(null)} />
      )}
    </main>
  );
}
