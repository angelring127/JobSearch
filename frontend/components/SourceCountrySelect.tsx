'use client';

import { useId } from 'react';
import {
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
  compact?: boolean;
}

export default function SourceCountrySelect({
  value,
  onChange,
  locale,
  compact = false,
}: SourceCountrySelectProps) {
  const selectId = useId();
  const hintId = `${selectId}-hint`;

  return (
    <label className={`source-country-select${compact ? ' source-country-select--compact' : ''}`}>
      <span className={compact ? 'sr-only' : 'field-label'}>{t(locale, 'sourceCountry')}</span>
      <select
        id={selectId}
        value={value ?? ''}
        onChange={(event) => onChange((event.target.value || undefined) as SourceCountry | undefined)}
        aria-label={compact ? t(locale, 'sourceCountry') : undefined}
        aria-describedby={compact ? undefined : hintId}
      >
        <option value="">{getSourceCountryLabel(undefined, locale)}</option>
        {SOURCE_COUNTRIES.map((country) => (
          <option key={country} value={country}>
            {getSourceCountryLabel(country, locale)}
          </option>
        ))}
      </select>
      {!compact && <span className="field-hint" id={hintId}>{t(locale, 'sourceCountryHint')}</span>}
    </label>
  );
}
