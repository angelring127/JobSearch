'use client';

import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import FilterBar from '@/components/FilterBar';
import JobDetail from '@/components/JobDetail';
import JobList from '@/components/JobList';
import LanguageSelector from '@/components/LanguageSelector';
import Map from '@/components/Map';
import SearchBar from '@/components/SearchBar';
import SourceCountrySelect from '@/components/SourceCountrySelect';
import { getCityJobCounts, JobSource, type CityJobCounts } from '@/lib/api';
import { CITY_PRESETS } from '@/lib/city-presets';
import {
  formatNumber,
  getCompactCityLabel,
  isLocale,
  LOCALE_TAGS,
  t,
  type Locale,
} from '@/lib/i18n';
import type { SourceCountry } from '@/lib/source-countries';

type Filters = {
  wageMin?: number;
  wageMax?: number;
  category?: string;
  radius?: number;
  sourceCountry?: SourceCountry;
};

type MobileView = 'list' | 'map';

const VANCOUVER_PRESET = CITY_PRESETS.find((city) => city.value === 'vancouver') ?? CITY_PRESETS[0];

function saveLocaleCookie(locale: Locale) {
  const secureAttribute = window.location.protocol === 'https:' ? '; Secure' : '';
  document.cookie = `jobmap-locale=${locale}; Path=/; Max-Age=31536000; SameSite=Lax${secureAttribute}`;
}

type JobMapAppProps = {
  initialLocale: Locale;
};

export default function JobMapApp({ initialLocale }: JobMapAppProps) {
  const router = useRouter();
  const [jobs, setJobs] = useState<JobSource[]>([]);
  const [selectedJob, setSelectedJob] = useState<JobSource | null>(null);
  const [filters, setFilters] = useState<Filters>({});
  const [mapCenter, setMapCenter] = useState<[number, number]>(VANCOUVER_PRESET.center);
  const [mapZoom, setMapZoom] = useState(VANCOUVER_PRESET.zoom);
  const [mobileView, setMobileView] = useState<MobileView>('map');
  const [selectedCity, setSelectedCity] = useState(VANCOUVER_PRESET.value);
  const [cityCounts, setCityCounts] = useState<CityJobCounts | null>(null);
  const [cityCountError, setCityCountError] = useState(false);
  const [locale, setLocale] = useState<Locale>(initialLocale);

  useEffect(() => {
    const savedLocale = window.localStorage.getItem('jobmap-locale');
    if (isLocale(savedLocale)) {
      setLocale(savedLocale);
      saveLocaleCookie(savedLocale);

      if (savedLocale !== initialLocale) {
        router.refresh();
      }
    }
  }, [initialLocale, router]);

  useEffect(() => {
    document.documentElement.lang = LOCALE_TAGS[locale];
    document.title = t(locale, 'metaTitle');
  }, [locale]);

  useEffect(() => {
    const controller = new AbortController();

    getCityJobCounts(filters.sourceCountry, controller.signal)
      .then((response) => {
        if (!response.success || !response.data) {
          throw new Error(response.error?.message ?? 'City count request failed');
        }
        setCityCounts(response.data);
        setCityCountError(false);
      })
      .catch((error) => {
        if (error instanceof DOMException && error.name === 'AbortError') return;
        console.error('City count error:', error);
        setCityCountError(true);
      });

    return () => controller.abort();
  }, [filters.sourceCountry]);

  const handleJobsUpdate = useCallback((newJobs: JobSource[]) => {
    setJobs(newJobs);
  }, []);

  const handleFilterChange = useCallback((newFilters: Filters) => {
    setFilters((current) => ({
      ...newFilters,
      sourceCountry: current.sourceCountry,
    }));
  }, []);

  const handleSourceCountryChange = useCallback((sourceCountry?: SourceCountry) => {
    setFilters((current) => ({ ...current, sourceCountry }));
    setSelectedJob(null);
  }, []);

  const handleMapCenterChange = useCallback((center: [number, number], zoom?: number) => {
    setMapCenter(center);
    if (zoom !== undefined) {
      setMapZoom(zoom);
    }
  }, []);

  const handleLocationSelect = useCallback((center: [number, number], zoom?: number) => {
    handleMapCenterChange(center, zoom);
    setMobileView('map');
  }, [handleMapCenterChange]);

  const handleCityChange = useCallback((value: string) => {
    setSelectedCity(value);
    const city = CITY_PRESETS.find((preset) => preset.value === value);
    if (city) handleLocationSelect(city.center, city.zoom);
  }, [handleLocationSelect]);

  const handleJobSelect = useCallback((job: JobSource) => {
    setSelectedJob(job);
    setMobileView('map');
  }, []);

  const handleJobDetailClose = useCallback(() => {
    setSelectedJob(null);
  }, []);

  const handleLocaleChange = useCallback((nextLocale: Locale) => {
    setLocale(nextLocale);
    window.localStorage.setItem('jobmap-locale', nextLocale);
    saveLocaleCookie(nextLocale);
  }, []);

  return (
    <main className={`job-app job-app--${mobileView}`}>
      <header className="app-bar">
        <div className="wordmark" aria-label={t(locale, 'home')}>
          <span className="wordmark__mark" aria-hidden="true">JM</span>
          <span className="wordmark__text">JobMap</span>
        </div>
        <label className="header-region-select">
          <span className="sr-only">{t(locale, 'cityQuick')}</span>
          <select
            value={selectedCity}
            onChange={(event) => handleCityChange(event.target.value)}
            aria-label={t(locale, 'cityQuick')}
            aria-busy={cityCounts === null && !cityCountError}
          >
            <option value="" disabled>{t(locale, 'chooseCity')}</option>
            {CITY_PRESETS.map((city) => (
              <option key={city.value} value={city.value}>
                {getCompactCityLabel(city.value, locale, city.label)}
                {cityCounts ? ` (${formatNumber(cityCounts[city.value] ?? 0, locale)}${t(locale, 'jobsUnit')})` : ''}
              </option>
            ))}
          </select>
        </label>
        <div className="app-bar__actions">
          <div className="app-bar__status" aria-live="polite">
            <span className="status-dot" aria-hidden="true" />
            {t(locale, 'allCanada')} · {formatNumber(jobs.length, locale)}{t(locale, 'postings')}
          </div>
          <LanguageSelector
            locale={locale}
            label={t(locale, 'language')}
            onChange={handleLocaleChange}
          />
        </div>
      </header>

      <div className={`workspace workspace--${mobileView}`}>
        <aside className="discovery-panel" aria-label={t(locale, 'discoveryPanel')}>
          <div className="discovery-panel__intro">
            <p className="eyebrow">{t(locale, 'heroEyebrow')}</p>
            <h1>{t(locale, 'heroTitle')}</h1>
            <p>{t(locale, 'heroDescription')}</p>
          </div>

          <div className="search-section">
            <SearchBar
              onLocationSelect={handleLocationSelect}
              selectedCity={selectedCity}
              cityCounts={cityCounts}
              cityCountError={cityCountError}
              onCityChange={handleCityChange}
              locale={locale}
              showLocationSearch={false}
            />
            <SourceCountrySelect
              value={filters.sourceCountry}
              onChange={handleSourceCountryChange}
              locale={locale}
            />
          </div>

          <FilterBar
            filters={filters}
            onFilterChange={handleFilterChange}
            onLocationSelect={handleLocationSelect}
            selectedCity={selectedCity}
            cityCounts={cityCounts}
            cityCountError={cityCountError}
            onCityChange={handleCityChange}
            locale={locale}
          />

          <div className="job-list-region">
            <JobList
              jobs={jobs}
              selectedJob={selectedJob}
              onJobSelect={handleJobSelect}
              locale={locale}
            />
          </div>
        </aside>

        <section className="map-panel" aria-label={t(locale, 'mapPanel')}>
          <Map
            initialCenter={mapCenter}
            initialZoom={mapZoom}
            filters={filters}
            selectedJob={selectedJob}
            onJobsUpdate={handleJobsUpdate}
            onJobSelect={handleJobSelect}
            onMapCenterChange={handleMapCenterChange}
            isActive={mobileView === 'map'}
            locale={locale}
          />
        </section>
      </div>

      <nav className="mobile-view-switcher" aria-label={t(locale, 'viewMode')}>
        <button
          type="button"
          className="mobile-view-switcher__button"
          aria-pressed={mobileView === 'list'}
          onClick={() => setMobileView('list')}
        >
          {t(locale, 'list')}
        </button>
        <button
          type="button"
          className="mobile-view-switcher__button"
          aria-pressed={mobileView === 'map'}
          onClick={() => setMobileView('map')}
        >
          {t(locale, 'map')}
        </button>
      </nav>

      {selectedJob && (
        <JobDetail job={selectedJob} onClose={handleJobDetailClose} locale={locale} />
      )}
    </main>
  );
}
