'use client';

import { useEffect, useId, useRef } from 'react';
import { JobSource } from '@/lib/api';
import { formatPostedDate, formatWage, getCategoryLabel, getJobTitle, getSourceName, t, type Locale } from '@/lib/i18n';

interface JobDetailProps {
  job: JobSource;
  onClose: () => void;
  locale: Locale;
}

export default function JobDetail({ job, onClose, locale }: JobDetailProps) {
  const titleId = useId();
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    closeButtonRef.current?.focus();
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [job.id, onClose]);

  const confidenceLabel = job.confidence >= 0.9
    ? t(locale, 'confidenceVeryHigh')
    : job.confidence >= 0.7
      ? t(locale, 'confidenceHigh')
      : job.confidence >= 0.5
        ? t(locale, 'confidenceMedium')
        : t(locale, 'confidenceLow');
  const confidenceLevel = job.confidence >= 0.7 ? 'high' : job.confidence >= 0.5 ? 'medium' : 'low';
  const sourceName = getSourceName(job);

  return (
    <aside className="job-detail" role="dialog" aria-modal="false" aria-labelledby={titleId}>
      <div className="job-detail__handle" aria-hidden="true" />
      <div className="job-detail__header">
        <div>
          <p className="eyebrow">{t(locale, 'detailsEyebrow')}</p>
          <h2 id={titleId}>{getJobTitle(job, locale)}</h2>
        </div>
        <button
          ref={closeButtonRef}
          type="button"
          className="icon-button"
          onClick={onClose}
          aria-label={t(locale, 'closeDetails')}
        >
          <svg aria-hidden="true" viewBox="0 0 24 24">
            <path d="M6 6l12 12M18 6 6 18" />
          </svg>
        </button>
      </div>

      <div className="job-detail__lead">
        <strong>{formatWage(job, locale)}</strong>
        {job.category && <span className="category-tag">{getCategoryLabel(job.category, locale)}</span>}
        <span className={`confidence-badge confidence-badge--${confidenceLevel}`}>
          {t(locale, 'confidence')} {confidenceLabel}
        </span>
      </div>

      <dl className="job-detail__facts">
        <div>
          <dt>{t(locale, 'region')}</dt>
          <dd>{job.region_hint || t(locale, 'regionUnavailable')}</dd>
        </div>
        {typeof job.distance_km === 'number' && Number.isFinite(job.distance_km) && (
          <div>
            <dt>{t(locale, 'distance')}</dt>
            <dd>{job.distance_km.toFixed(1)}km</dd>
          </div>
        )}
        <div>
          <dt>{t(locale, 'postedDate')}</dt>
          <dd>{formatPostedDate(job.posted_at, locale)}</dd>
        </div>
        {sourceName && (
          <div>
            <dt>{t(locale, 'sourceSite')}</dt>
            <dd>{sourceName}</dd>
          </div>
        )}
      </dl>

      <a className="primary-button job-detail__source" href={job.source_url} target="_blank" rel="noopener noreferrer">
        {t(locale, 'sourceLink')}
        <svg aria-hidden="true" viewBox="0 0 24 24">
          <path d="M14 5h5v5M19 5l-9 9M18 13v5a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5" />
        </svg>
      </a>
    </aside>
  );
}
