'use client';

import { useCallback, useEffect, useState } from 'react';
import FilterBar from '@/components/FilterBar';
import JobDetail from '@/components/JobDetail';
import JobList from '@/components/JobList';
import Map from '@/components/Map';
import SearchBar from '@/components/SearchBar';
import { JobSource } from '@/lib/api';
import {
  formatNumber,
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

export default function Home() {
  const [jobs, setJobs] = useState<JobSource[]>([]);
  const [selectedJob, setSelectedJob] = useState<JobSource | null>(null);
  const [filters, setFilters] = useState<Filters>({});
  const [mapCenter, setMapCenter] = useState<[number, number]>([-101.5, 54.2]);
  const [mapZoom, setMapZoom] = useState(3);
  const [mobileView, setMobileView] = useState<MobileView>('list');
  const [locale, setLocale] = useState<Locale>('ko');

  useEffect(() => {
    const savedLocale = window.localStorage.getItem('jobmap-locale');
    if (isLocale(savedLocale)) setLocale(savedLocale);
  }, []);

  useEffect(() => {
    document.documentElement.lang = LOCALE_TAGS[locale];
    document.title = t(locale, 'metaTitle');
  }, [locale]);

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
  }, []);

  return (
    <main className="job-app">
      <header className="app-bar">
        <div className="wordmark" aria-label={t(locale, 'home')}>
          <span className="wordmark__mark" aria-hidden="true">JM</span>
          <span className="wordmark__text">JobMap</span>
        </div>
        <div className="app-bar__actions">
          <div className="app-bar__status" aria-live="polite">
            <span className="status-dot" aria-hidden="true" />
            {t(locale, 'allCanada')} · {formatNumber(jobs.length, locale)}{t(locale, 'postings')}
          </div>
          <label className="language-select">
            <span className="sr-only">{t(locale, 'language')}</span>
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
            <SearchBar onLocationSelect={handleLocationSelect} locale={locale} />
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
