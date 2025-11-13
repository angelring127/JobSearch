'use client';

import { useState, useEffect } from 'react';

interface FilterBarProps {
  filters: {
    wageMin?: number;
    wageMax?: number;
    category?: string;
    radius?: number;
  };
  onFilterChange: (filters: FilterBarProps['filters']) => void;
}

const CATEGORIES = [
  { value: '', label: '전체' },
  { value: 'restaurant', label: '레스토랑/카페' },
  { value: 'retail', label: '소매점' },
  { value: 'hospitality', label: '호텔/관광' },
  { value: 'warehouse', label: '창고/물류' },
  { value: 'construction', label: '건설' },
  { value: 'cleaning', label: '청소' },
  { value: 'other', label: '기타' },
];

export default function FilterBar({ filters, onFilterChange }: FilterBarProps) {
  const [wageMin, setWageMin] = useState<string>(filters.wageMin?.toString() || '');
  const [wageMax, setWageMax] = useState<string>(filters.wageMax?.toString() || '');
  const [category, setCategory] = useState<string>(filters.category || '');
  const [radius, setRadius] = useState<string>(filters.radius?.toString() || '');

  // フィルタ変更時に親コンポーネントに通知
  useEffect(() => {
    onFilterChange({
      wageMin: wageMin ? parseInt(wageMin) : undefined,
      wageMax: wageMax ? parseInt(wageMax) : undefined,
      category: category || undefined,
      radius: radius ? parseFloat(radius) : undefined,
    });
  }, [wageMin, wageMax, category, radius, onFilterChange]);

  // フィルタリセット
  const handleReset = () => {
    setWageMin('');
    setWageMax('');
    setCategory('');
    setRadius('');
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-700">필터</h3>
        <button
          onClick={handleReset}
          className="text-xs text-blue-600 hover:text-blue-800"
        >
          초기화
        </button>
      </div>

      {/* 時給フィルタ */}
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">
          시급 (CAD)
        </label>
        <div className="flex items-center gap-2">
          <input
            type="number"
            value={wageMin}
            onChange={(e) => setWageMin(e.target.value)}
            placeholder="최소"
            min="0"
            className="flex-1 px-3 py-1.5 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          <span className="text-gray-400">~</span>
          <input
            type="number"
            value={wageMax}
            onChange={(e) => setWageMax(e.target.value)}
            placeholder="최대"
            min="0"
            className="flex-1 px-3 py-1.5 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>
      </div>

      {/* 職種フィルタ */}
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">
          직종
        </label>
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          {CATEGORIES.map((cat) => (
            <option key={cat.value} value={cat.value}>
              {cat.label}
            </option>
          ))}
        </select>
      </div>

      {/* 距離フィルタ */}
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">
          반경 (km)
        </label>
        <input
          type="number"
          value={radius}
          onChange={(e) => setRadius(e.target.value)}
          placeholder="예: 5"
          min="0.1"
          max="50"
          step="0.1"
          className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>
    </div>
  );
}

