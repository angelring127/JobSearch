export const SOURCE_COUNTRIES = ['kr', 'jp', 'cn'] as const;

export type SourceCountry = (typeof SOURCE_COUNTRIES)[number];

export const SOURCE_KEYS_BY_COUNTRY: Record<SourceCountry, readonly string[]> = {
  kr: ['ourvancouver', 'casmo', 'vanchosun'],
  jp: ['jpcanada', 'jinzaicanada'],
  cn: ['sinojobs'],
};

export function isSourceCountry(value: string | null): value is SourceCountry {
  return value !== null && SOURCE_COUNTRIES.includes(value as SourceCountry);
}
