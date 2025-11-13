'use client';

import { JobSource } from '@/lib/api';

interface JobListProps {
  jobs: JobSource[];
  selectedJob: JobSource | null;
  onJobSelect: (job: JobSource) => void;
}

export default function JobList({ jobs, selectedJob, onJobSelect }: JobListProps) {
  // 時給表示フォーマット
  const formatWage = (job: JobSource): string => {
    if (job.wage_min && job.wage_max) {
      return `$${job.wage_min} - $${job.wage_max}/hr`;
    } else if (job.wage_min) {
      return `$${job.wage_min}+/hr`;
    } else if (job.wage_max) {
      return `Up to $${job.wage_max}/hr`;
    }
    return '시급 미표시';
  };

  // 距離表示フォーマット
  const formatDistance = (job: JobSource): string => {
    if (typeof job.distance_km === 'number' && Number.isFinite(job.distance_km)) {
      return `${job.distance_km.toFixed(1)}km`;
    }
    return '';
  };

  // 日付表示フォーマット
  const formatDate = (dateString: string | null): string => {
    if (!dateString) return '';
    const date = new Date(dateString);
    const now = new Date();
    const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) return '오늘';
    if (diffDays === 1) return '어제';
    if (diffDays < 7) return `${diffDays}일 전`;
    if (diffDays < 30) return `${Math.floor(diffDays / 7)}주 전`;
    return `${Math.floor(diffDays / 30)}개월 전`;
  };

  if (jobs.length === 0) {
    return (
      <div className="h-full flex items-center justify-center p-6">
        <div className="text-center text-gray-500">
          <p className="text-sm">표시할 일자리가 없습니다.</p>
          <p className="text-xs mt-2">지도를 이동하여 검색해보세요.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="p-4 border-b border-gray-200 bg-gray-50">
        <p className="text-sm font-medium text-gray-700">
          {jobs.length}개의 일자리 발견
        </p>
      </div>
      <div className="divide-y divide-gray-200">
        {jobs.map((job) => (
          <button
            key={job.id}
            onClick={() => onJobSelect(job)}
            className={`w-full text-left p-4 hover:bg-gray-50 transition-colors ${
              selectedJob?.id === job.id ? 'bg-blue-50 border-l-4 border-blue-500' : ''
            }`}
          >
            <div className="space-y-2">
              {/* タイトル */}
              <div className="flex items-start justify-between gap-2">
                <h3 className="text-sm font-semibold text-gray-900 line-clamp-2">
                  {job.title || '제목 없음'}
                </h3>
                {job.confidence < 0.7 && (
                  <span className="text-xs text-yellow-600 bg-yellow-100 px-2 py-0.5 rounded flex-shrink-0">
                    낮은 신뢰도
                  </span>
                )}
              </div>

              {/* 時給 */}
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-blue-600">
                  {formatWage(job)}
                </span>
                {job.category && (
                  <span className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded">
                    {job.category}
                  </span>
                )}
              </div>

              {/* 位置情報 */}
              <div className="flex items-center gap-3 text-xs text-gray-600">
                {job.region_hint && (
                  <span className="flex items-center gap-1">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                    </svg>
                    {job.region_hint}
                  </span>
                )}
                {job.distance_km !== undefined && (
                  <span>{formatDistance(job)}</span>
                )}
              </div>

              {/* 投稿日 */}
              {job.posted_at && (
                <div className="text-xs text-gray-400">
                  {formatDate(job.posted_at)}
                </div>
              )}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

