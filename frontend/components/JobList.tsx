'use client';

import { JobSource } from '@/lib/api';
import {
  formatNumber,
  formatPostedDate,
  formatWage,
  getCategoryLabel,
  getJobTitle,
  getSourceName,
  t,
  type Locale,
} from '@/lib/i18n';

interface JobListProps {
  jobs: JobSource[];
  selectedJob: JobSource | null;
  onJobSelect: (job: JobSource) => void;
  locale: Locale;
}

const formatDistance = (job: JobSource): string => {
  if (typeof job.distance_km === 'number' && Number.isFinite(job.distance_km)) {
    return `${job.distance_km.toFixed(1)}km`;
  }
  return '';
};

export default function JobList({ jobs, selectedJob, onJobSelect, locale }: JobListProps) {
  if (jobs.length === 0) {
    return (
      <div className="empty-state" role="status">
        <span className="empty-state__icon" aria-hidden="true">↗</span>
        <h2>{t(locale, 'emptyTitle')}</h2>
        <p>{t(locale, 'emptyBody')}</p>
      </div>
    );
  }

  return (
    <div className="job-list">
      <div className="job-list__header">
        <p aria-live="polite"><strong>{formatNumber(jobs.length, locale)}</strong>{t(locale, 'jobs')}</p>
        <span>{t(locale, 'currentMap')}</span>
      </div>
      <ul className="job-list__items" aria-label={t(locale, 'jobResults')}>
        {jobs.map((job) => {
          const isSelected = selectedJob?.id === job.id;
          const sourceName = getSourceName(job);
          return (
            <li key={job.id}>
              <button
                type="button"
                onClick={() => onJobSelect(job)}
                className="job-card"
                aria-pressed={isSelected}
              >
                <span className="job-card__topline">
                  <span className="job-card__title">{getJobTitle(job, locale)}</span>
                  {job.confidence < 0.7 && <span className="confidence-badge confidence-badge--review">{t(locale, 'reviewNeeded')}</span>}
                </span>

                <span className="job-card__wage">{formatWage(job, locale)}</span>

                <span className="job-card__meta">
                  {job.region_hint && <span>{job.region_hint}</span>}
                  {formatDistance(job) && <span>{formatDistance(job)}</span>}
                  {job.category && <span>{getCategoryLabel(job.category, locale)}</span>}
                  {sourceName && <span><strong>{t(locale, 'sourceSite')}</strong> {sourceName}</span>}
                </span>

                <span className="job-card__date">
                  <span>{t(locale, 'posted')}</span>
                  <span>{formatPostedDate(job.posted_at, locale)}</span>
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
