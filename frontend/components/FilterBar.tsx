'use client';

import { useEffect, useState } from 'react';
import SearchBar from '@/components/SearchBar';
import type { CityJobCounts } from '@/lib/api';
import { getCategoryLabel, t, type Locale } from '@/lib/i18n';

interface FilterBarProps {
  filters: {
    wageMin?: number;
    wageMax?: number;
    category?: string;
    radius?: number;
  };
  onFilterChange: (filters: FilterBarProps['filters']) => void;
  onLocationSelect: (center: [number, number], zoom?: number) => void;
  selectedCity: string;
  cityCounts: CityJobCounts | null;
  cityCountError: boolean;
  onCityChange: (value: string) => void;
  locale: Locale;
}

const CATEGORIES = [
  '', 'restaurant', 'retail', 'hospitality', 'warehouse', 'construction', 'cleaning', 'other',
];

export default function FilterBar({
  filters,
  onFilterChange,
  onLocationSelect,
  selectedCity,
  cityCounts,
  cityCountError,
  onCityChange,
  locale,
}: FilterBarProps) {
  const [wageMin, setWageMin] = useState(filters.wageMin?.toString() || '');
  const [wageMax, setWageMax] = useState(filters.wageMax?.toString() || '');
  const [category, setCategory] = useState(filters.category || '');
  const [radius, setRadius] = useState(filters.radius?.toString() || '');

  useEffect(() => {
    onFilterChange({
      wageMin: wageMin ? parseInt(wageMin, 10) : undefined,
      wageMax: wageMax ? parseInt(wageMax, 10) : undefined,
      category: category || undefined,
      radius: radius ? parseFloat(radius) : undefined,
    });
  }, [wageMin, wageMax, category, radius, onFilterChange]);

  const activeFilterCount = [wageMin, wageMax, category, radius].filter(Boolean).length;

  const handleReset = () => {
    setWageMin('');
    setWageMax('');
    setCategory('');
    setRadius('');
  };

  return (
    <details className="filter-panel">
      <summary>
        <span>
          {t(locale, 'filters')}
          {activeFilterCount > 0 && <span className="filter-count">{activeFilterCount}</span>}
        </span>
        <span className="filter-summary__hint">{t(locale, 'filterHint')}</span>
      </summary>

      <div className="filter-panel__body">
        <div className="filter-panel__heading">
          <p>{t(locale, 'filterDescription')}</p>
          <button type="button" className="text-button" onClick={handleReset} disabled={activeFilterCount === 0}>
            {t(locale, 'reset')}
          </button>
        </div>

        <div className="filter-panel__location">
          <SearchBar
            onLocationSelect={onLocationSelect}
            selectedCity={selectedCity}
            cityCounts={cityCounts}
            cityCountError={cityCountError}
            onCityChange={onCityChange}
            locale={locale}
            showCityQuick={false}
          />
        </div>

        <div className="field-group">
          <label className="field-label" htmlFor="category-filter">{t(locale, 'category')}</label>
          <select id="category-filter" value={category} onChange={(event) => setCategory(event.target.value)}>
            {CATEGORIES.map((value) => (
              <option key={value} value={value}>
                {value ? getCategoryLabel(value, locale) : t(locale, 'allCategories')}
              </option>
            ))}
          </select>
        </div>

        <fieldset className="field-group">
          <legend className="field-label">{t(locale, 'hourlyWage')}</legend>
          <div className="range-fields">
            <label>
              <span className="sr-only">{t(locale, 'minimumWage')}</span>
              <input
                type="number"
                value={wageMin}
                onChange={(event) => setWageMin(event.target.value)}
                placeholder={t(locale, 'minimum')}
                min="0"
              />
            </label>
            <span aria-hidden="true">—</span>
            <label>
              <span className="sr-only">{t(locale, 'maximumWage')}</span>
              <input
                type="number"
                value={wageMax}
                onChange={(event) => setWageMax(event.target.value)}
                placeholder={t(locale, 'maximum')}
                min="0"
              />
            </label>
          </div>
        </fieldset>

        <div className="field-group">
          <label className="field-label" htmlFor="radius-filter">{t(locale, 'radius')}</label>
          <input
            id="radius-filter"
            type="number"
            value={radius}
            onChange={(event) => setRadius(event.target.value)}
            placeholder={t(locale, 'radiusExample')}
            min="0.1"
            max="50"
            step="0.1"
          />
        </div>
      </div>
    </details>
  );
}
