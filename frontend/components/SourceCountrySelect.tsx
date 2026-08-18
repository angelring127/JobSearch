'use client';

import { useId } from 'react';
import type { SourceCountryJobCounts } from '@/lib/api';
import {
  formatNumber,
  getSourceCountryLabel,
  t,
  type Locale,
} from '@/lib/i18n';
import {
  SOURCE_COUNTRIES,
  type SourceCountry,
} from '@/lib/source-countries';

interface SourceCountrySelectProps {
  value?: SourceCountry;
  onChange: (value?: SourceCountry) => void;
  locale: Locale;
  counts: SourceCountryJobCounts | null;
  countError: boolean;
  compact?: boolean;
}

export default function SourceCountrySelect({
  value,
  onChange,
  locale,
  counts,
  countError,
  compact = false,
}: SourceCountrySelectProps) {
  const selectId = useId();
  const hintId = `${selectId}-hint`;
  const countSuffix = (country?: SourceCountry) => {
    if (!counts) return '';
    const count = counts[country ?? 'all'];
    return ` (${formatNumber(count, locale)}${t(locale, 'jobsUnit')})`;
  };

  return (
    <label className={`source-country-select${compact ? ' source-country-select--compact' : ''}`}>
      <span className={compact ? 'sr-only' : 'field-label'}>{t(locale, 'sourceCountry')}</span>
      <select
        id={selectId}
        value={value ?? ''}
        onChange={(event) => onChange((event.target.value || undefined) as SourceCountry | undefined)}
        aria-label={compact ? t(locale, 'sourceCountry') : undefined}
        aria-describedby={compact ? undefined : hintId}
        aria-busy={counts === null && !countError}
      >
        <option value="">
          {getSourceCountryLabel(undefined, locale)}{countSuffix()}
        </option>
        {SOURCE_COUNTRIES.map((country) => (
          <option key={country} value={country}>
            {getSourceCountryLabel(country, locale)}{countSuffix(country)}
          </option>
        ))}
      </select>
      {!compact && (
        <span className="field-hint" id={hintId}>
          {countError ? t(locale, 'sourceCountryCountError') : t(locale, 'sourceCountryHint')}
        </span>
      )}
    </label>
  );
}
