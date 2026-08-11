'use client';

import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import FilterBar from '@/components/FilterBar';
import JobDetail from '@/components/JobDetail';
import JobList from '@/components/JobList';
import Map from '@/components/Map';
import SearchBar from '@/components/SearchBar';
import { getCityJobCounts, JobSource, type CityJobCounts } from '@/lib/api';
import { CITY_PRESETS } from '@/lib/city-presets';
import {
  formatNumber,
  getCompactCityLabel,
  isLocale,
  LANGUAGE_OPTIONS,
  LOCALE_TAGS,
  t,
  type Locale,
} from '@/lib/i18n';

type Filters = {
  wageMin?: number;
  wageMax?: number;
  category?: string;
  radius?: number;
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

function LanguageFlag({ locale }: { locale: Locale }) {
  if (locale === 'ko') {
    return (
      <svg viewBox="0 0 36 36" aria-hidden="true">
        <rect width="36" height="36" fill="#fff" />
        <circle cx="18" cy="18" r="7" fill="#1657a8" />
        <path d="M11 18a7 7 0 0 1 14 0 3.5 3.5 0 0 0-7 0 3.5 3.5 0 0 1-7 0Z" fill="#d9363e" stroke="none" />
        <path d="m8.2 10.2 4.4-2.6M9.3 12.2l4.4-2.6M22.3 26.4l4.4-2.6M23.4 28.4l4.4-2.6M23.4 7.6l4.4 2.6M22.3 9.6l4.4 2.6M9.3 23.8l4.4 2.6M8.2 25.8l4.4 2.6" stroke="#111827" strokeWidth="1.2" />
      </svg>
    );
  }

  if (locale === 'en') {
    return (
      <svg viewBox="0 0 36 36" aria-hidden="true">
        <rect width="36" height="36" fill="#fff" />
        <path d="M0 0h9v36H0zM27 0h9v36h-9z" fill="#d52b1e" stroke="none" />
        <path d="m18 5.5 2 4 3.8-1.4-1.1 4.1 3.6 1.1-3 3.2 1.2 2.1-5.1-.7.5 7.1h-3.8l.5-7.1-5.1.7 1.2-2.1-3-3.2 3.6-1.1-1.1-4.1 3.8 1.4Z" fill="#d52b1e" stroke="none" />
      </svg>
    );
  }

  if (locale === 'ja') {
    return (
      <svg viewBox="0 0 36 36" aria-hidden="true">
        <rect width="36" height="36" fill="#fff" />
        <circle cx="18" cy="18" r="8.5" fill="#bc002d" stroke="none" />
      </svg>
    );
  }

  return (
    <svg viewBox="0 0 36 36" aria-hidden="true">
      <rect width="36" height="36" fill="#de2910" />
      <path d="m18 6 1.8 3.7 4.1.6-3 2.9.7 4.1-3.6-1.9-3.6 1.9.7-4.1-3-2.9 4.1-.6Z" fill="#ffde00" stroke="none" />
    </svg>
  );
}

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

    getCityJobCounts(controller.signal)
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
  }, []);

  const handleJobsUpdate = useCallback((newJobs: JobSource[]) => {
    setJobs(newJobs);
  }, []);

  const handleFilterChange = useCallback((newFilters: Filters) => {
    setFilters(newFilters);
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

  const activeLanguage = LANGUAGE_OPTIONS.find((option) => option.value === locale) ?? LANGUAGE_OPTIONS[0];

  return (
    <main className="job-app">
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
          <label className="language-select" title={`${t(locale, 'language')}: ${activeLanguage.label}`}>
            <span className="sr-only">{t(locale, 'language')}</span>
            <span className="language-select__flag" aria-hidden="true">
              <LanguageFlag locale={locale} />
            </span>
            <span className="language-select__chevron" aria-hidden="true">
              <svg viewBox="0 0 12 12">
                <path d="m3.5 4.75 2.5 2.5 2.5-2.5" />
              </svg>
            </span>
            <select
              value={locale}
              onChange={(event) => handleLocaleChange(event.target.value as Locale)}
              aria-label={t(locale, 'language')}
            >
              {LANGUAGE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </label>
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
            />
          </div>

          <FilterBar filters={filters} onFilterChange={handleFilterChange} locale={locale} />

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
