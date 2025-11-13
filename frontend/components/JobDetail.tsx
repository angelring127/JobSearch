'use client';

import { JobSource } from '@/lib/api';

interface JobDetailProps {
  job: JobSource;
  onClose: () => void;
}

export default function JobDetail({ job, onClose }: JobDetailProps) {
  // 時給表示フォーマット
  const formatWage = (): string => {
    if (job.wage_min && job.wage_max) {
      return `$${job.wage_min} - $${job.wage_max}/hr`;
    } else if (job.wage_min) {
      return `$${job.wage_min}+/hr`;
    } else if (job.wage_max) {
      return `Up to $${job.wage_max}/hr`;
    }
    return '시급 미표시';
  };

  // 日付表示フォーマット
  const formatDate = (dateString: string | null): string => {
    if (!dateString) return '날짜 정보 없음';
    const date = new Date(dateString);
    return date.toLocaleDateString('ko-KR', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  // 信頼度表示
  const getConfidenceLabel = (confidence: number): string => {
    if (confidence >= 0.9) return '매우 높음';
    if (confidence >= 0.7) return '높음';
    if (confidence >= 0.5) return '보통';
    return '낮음';
  };

  const getConfidenceColor = (confidence: number): string => {
    if (confidence >= 0.7) return 'text-green-600 bg-green-100';
    if (confidence >= 0.5) return 'text-yellow-600 bg-yellow-100';
    return 'text-red-600 bg-red-100';
  };

  return (
    <div className="fixed inset-x-0 bottom-0 bg-white border-t border-gray-200 shadow-lg z-50 max-h-[60vh] overflow-y-auto">
      <div className="max-w-4xl mx-auto p-6">
        {/* ヘッダー */}
        <div className="flex items-start justify-between mb-4">
          <div className="flex-1">
            <h2 className="text-xl font-bold text-gray-900 mb-2">
              {job.title || '제목 없음'}
            </h2>
            <div className="flex items-center gap-3 flex-wrap">
              <span className="text-lg font-semibold text-blue-600">
                {formatWage()}
              </span>
              {job.category && (
                <span className="text-sm text-gray-600 bg-gray-100 px-3 py-1 rounded">
                  {job.category}
                </span>
              )}
              <span className={`text-xs px-2 py-1 rounded ${getConfidenceColor(job.confidence)}`}>
                신뢰도: {getConfidenceLabel(job.confidence)}
              </span>
            </div>
          </div>
          <button
            onClick={onClose}
            className="ml-4 text-gray-400 hover:text-gray-600 transition-colors"
            aria-label="閉じる"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* 詳細情報 */}
        <div className="space-y-4">
          {/* 位置情報 */}
          <div>
            <h3 className="text-sm font-semibold text-gray-700 mb-2">위치 정보</h3>
            <div className="space-y-1 text-sm text-gray-600">
              {job.region_hint && (
                <div className="flex items-center gap-2">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                  <span>{job.region_hint}</span>
                </div>
              )}
              {job.lat && job.lng && (
                <div className="text-xs text-gray-500">
                  좌표: {job.lat.toFixed(6)}, {job.lng.toFixed(6)}
                </div>
              )}
              {typeof job.distance_km === 'number' && Number.isFinite(job.distance_km) && (
                <div className="text-xs text-gray-500">
                  거리: {job.distance_km.toFixed(1)}km
                </div>
              )}
            </div>
          </div>

          {/* 投稿情報 */}
          <div>
            <h3 className="text-sm font-semibold text-gray-700 mb-2">게시 정보</h3>
            <div className="text-sm text-gray-600 space-y-1">
              <div>게시일: {formatDate(job.posted_at)}</div>
              {job.msgid && (
                <div className="text-xs text-gray-500">메시지 ID: {job.msgid}</div>
              )}
            </div>
          </div>

          {/* JPCanadaリンク */}
          <div className="pt-4 border-t border-gray-200">
            <a
              href={job.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              <span>JPCanada에서 보기</span>
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
              </svg>
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}

