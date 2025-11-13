'use client';

import { useState, useCallback, useEffect, useRef } from 'react';

interface SearchBarProps {
  onLocationSelect: (center: [number, number], zoom?: number) => void;
}

interface GeocodeResult {
  lat: string;
  lon: string;
  display_name: string;
}

export default function SearchBar({ onLocationSelect }: SearchBarProps) {
  const [query, setQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [results, setResults] = useState<GeocodeResult[]>([]);
  const [showResults, setShowResults] = useState(false);
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Nominatim APIを使用して位置検索
  const handleSearch = useCallback(async (searchQuery: string) => {
    if (!searchQuery.trim()) {
      setResults([]);
      setShowResults(false);
      return;
    }

    setIsSearching(true);
    try {
      // Nominatim API呼び出し（カナダ地域に絞り込み）
      const response = await fetch(
        `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(searchQuery)}&limit=5&countrycodes=ca&accept-language=en`
      );
      
      if (response.ok) {
        const data: GeocodeResult[] = await response.json();
        setResults(data);
        setShowResults(true);
      }
    } catch (error) {
      console.error('Geocoding error:', error);
      setResults([]);
    } finally {
      setIsSearching(false);
    }
  }, []);

  // デバウンス処理用のuseEffect
  useEffect(() => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    debounceTimerRef.current = setTimeout(() => {
      handleSearch(query);
    }, 500);

    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, [query, handleSearch]);

  // 検索入力ハンドラ
  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setQuery(e.target.value);
  }, []);

  // 検索結果選択ハンドラ
  const handleResultSelect = useCallback((result: GeocodeResult) => {
    const lat = parseFloat(result.lat);
    const lng = parseFloat(result.lon);
    onLocationSelect([lng, lat], 15); // ズームレベル15で表示（より拡大）
    setQuery(result.display_name);
    setShowResults(false);
  }, [onLocationSelect]);

  // 検索ボタンクリックハンドラ
  const handleSearchClick = useCallback(async () => {
    if (!query.trim()) return;
    
    setIsSearching(true);
    try {
      const response = await fetch(
        `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&limit=1&countrycodes=ca&accept-language=en`
      );
      
      if (response.ok) {
        const data: GeocodeResult[] = await response.json();
        if (data.length > 0) {
          const result = data[0];
          const lat = parseFloat(result.lat);
          const lng = parseFloat(result.lon);
          onLocationSelect([lng, lat], 15); // ズームレベル15で表示
          setQuery(result.display_name);
          setShowResults(false);
        }
      }
    } catch (error) {
      console.error('Geocoding error:', error);
    } finally {
      setIsSearching(false);
    }
  }, [query, onLocationSelect]);

  // Enterキーで検索
  const handleKeyPress = useCallback((e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleSearchClick();
    }
  }, [handleSearchClick]);

  return (
    <div className="relative">
      <div className="relative flex gap-2">
        <input
          type="text"
          value={query}
          onChange={handleInputChange}
          onKeyPress={handleKeyPress}
          onFocus={() => results.length > 0 && setShowResults(true)}
          placeholder="위치 검색 (예: Vancouver, BC)"
          className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          onClick={handleSearchClick}
          disabled={isSearching || !query.trim()}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
        >
          {isSearching ? (
            <>
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
              <span>검색 중...</span>
            </>
          ) : (
            <>
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <span>검색</span>
            </>
          )}
        </button>
      </div>
      
      {/* 検索結果ドロップダウン */}
      {showResults && results.length > 0 && (
        <div className="absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-60 overflow-y-auto">
          {results.map((result, index) => (
            <button
              key={index}
              onClick={() => handleResultSelect(result)}
              className="w-full text-left px-4 py-2 hover:bg-gray-100 transition-colors"
            >
              <div className="text-sm font-medium text-gray-900">
                {result.display_name}
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

