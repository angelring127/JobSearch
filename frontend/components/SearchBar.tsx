'use client';

import { useCallback, useEffect, useId, useRef, useState } from 'react';
import { getCityJobCounts, type CityJobCounts } from '@/lib/api';
import { CITY_PRESETS } from '@/lib/city-presets';
import { formatNumber, getCityLabel, LOCALE_TAGS, t, type Locale } from '@/lib/i18n';

interface SearchBarProps {
  onLocationSelect: (center: [number, number], zoom?: number) => void;
  locale: Locale;
}

interface GeocodeResult {
  lat: string;
  lon: string;
  display_name: string;
}

export default function SearchBar({ onLocationSelect, locale }: SearchBarProps) {
  const inputId = useId();
  const listboxId = useId();
  const citySelectId = useId();
  const [selectedCity, setSelectedCity] = useState('');
  const [query, setQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [results, setResults] = useState<GeocodeResult[]>([]);
  const [showResults, setShowResults] = useState(false);
  const [searchError, setSearchError] = useState('');
  const [cityCounts, setCityCounts] = useState<CityJobCounts | null>(null);
  const [cityCountError, setCityCountError] = useState(false);
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    getCityJobCounts(controller.signal)
      .then((response) => {
        if (!response.success || !response.data) {
          throw new Error(response.error?.message ?? 'City count request failed');
        }

        setCityCounts(response.data);
      })
      .catch((error) => {
        if (error instanceof DOMException && error.name === 'AbortError') return;
        console.error('City count error:', error);
        setCityCountError(true);
      });

    return () => controller.abort();
  }, []);

  const searchLocations = useCallback(async (searchQuery: string, limit: number) => {
    const response = await fetch(
      `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(searchQuery)}&limit=${limit}&countrycodes=ca&accept-language=${encodeURIComponent(`${LOCALE_TAGS[locale]},en`)}`
    );

    if (!response.ok) {
      throw new Error('Location search failed');
    }

    return response.json() as Promise<GeocodeResult[]>;
  }, [locale]);

  const handleSearch = useCallback(async (searchQuery: string) => {
    if (!searchQuery.trim()) {
      setResults([]);
      setShowResults(false);
      setSearchError('');
      return;
    }

    setIsSearching(true);
    setSearchError('');
    try {
      const data = await searchLocations(searchQuery, 5);
      setResults(data);
      setShowResults(true);
    } catch (error) {
      console.error('Geocoding error:', error);
      setResults([]);
      setSearchError(t(locale, 'locationLoadError'));
    } finally {
      setIsSearching(false);
    }
  }, [locale, searchLocations]);

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

  const handleResultSelect = useCallback((result: GeocodeResult) => {
    onLocationSelect([parseFloat(result.lon), parseFloat(result.lat)], 15);
    setSelectedCity('');
    setQuery(result.display_name);
    setShowResults(false);
  }, [onLocationSelect]);

  const handleCitySelect = useCallback((value: string) => {
    const city = CITY_PRESETS.find((preset) => preset.value === value);
    if (!city) return;

    setSelectedCity(city.value);
    setShowResults(false);
    setSearchError('');
    onLocationSelect(city.center, city.zoom);
  }, [onLocationSelect]);

  const handleSearchClick = useCallback(async () => {
    if (!query.trim()) return;

    setIsSearching(true);
    setSearchError('');
    try {
      const data = await searchLocations(query, 1);
      if (data.length > 0) {
        handleResultSelect(data[0]);
      } else {
        setSearchError(t(locale, 'noLocation'));
      }
    } catch (error) {
      console.error('Geocoding error:', error);
      setSearchError(t(locale, 'locationLoadError'));
    } finally {
      setIsSearching(false);
    }
  }, [handleResultSelect, locale, query, searchLocations]);

  return (
    <div className="location-search">
      <div className="location-search__quick">
        <label className="field-label" htmlFor={citySelectId}>{t(locale, 'cityQuick')}</label>
        <select
          id={citySelectId}
          value={selectedCity}
          onChange={(event) => handleCitySelect(event.target.value)}
          aria-describedby={`${citySelectId}-hint`}
        >
          <option value="" disabled>{t(locale, 'chooseCity')}</option>
          {CITY_PRESETS.map((city) => (
            <option key={city.value} value={city.value}>
              {getCityLabel(city.value, locale, city.label)}
              {cityCounts ? ` (${formatNumber(cityCounts[city.value] ?? 0, locale)}${t(locale, 'jobsUnit')})` : ''}
            </option>
          ))}
        </select>
        <p className="field-hint" id={`${citySelectId}-hint`}>
          {cityCountError
            ? t(locale, 'cityCountError')
            : t(locale, 'cityHint')}
        </p>
      </div>

      <label className="field-label" htmlFor={inputId}>{t(locale, 'locationSearch')}</label>
      <div className="location-search__controls">
        <div className="location-search__input-wrap">
          <svg className="field-icon" aria-hidden="true" viewBox="0 0 24 24">
            <circle cx="11" cy="11" r="6" />
            <path d="m16 16 4 4" />
          </svg>
          <input
            id={inputId}
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter') {
                event.preventDefault();
                handleSearchClick();
              }
              if (event.key === 'Escape') {
                setShowResults(false);
              }
            }}
            onFocus={() => results.length > 0 && setShowResults(true)}
            placeholder={t(locale, 'locationPlaceholder')}
            role="combobox"
            aria-autocomplete="list"
            aria-controls={listboxId}
            aria-expanded={showResults && results.length > 0}
            aria-describedby={searchError ? `${inputId}-error` : undefined}
            aria-invalid={searchError ? 'true' : 'false'}
            autoComplete="off"
          />
        </div>
        <button
          type="button"
          onClick={handleSearchClick}
          disabled={isSearching || !query.trim()}
          className="primary-button search-button"
        >
          {isSearching && <span className="spinner" aria-hidden="true" />}
          <span>{isSearching ? t(locale, 'searching') : t(locale, 'search')}</span>
        </button>
      </div>

      <p className="field-error" id={`${inputId}-error`} aria-live="polite">{searchError}</p>

      {showResults && results.length > 0 && (
        <ul className="search-results" id={listboxId} role="listbox" aria-label={t(locale, 'locationResults')}>
          {results.map((result) => (
            <li key={`${result.lat}-${result.lon}`} role="presentation">
              <button
                type="button"
                role="option"
                aria-selected="false"
                onClick={() => handleResultSelect(result)}
              >
                {result.display_name}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
