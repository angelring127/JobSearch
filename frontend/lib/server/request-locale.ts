import 'server-only';

import { cookies, headers } from 'next/headers';
import { getLocaleFromAcceptLanguage, isLocale, type Locale } from '@/lib/i18n';

const LOCALE_COOKIE = 'jobmap-locale';

export async function getRequestLocale(): Promise<Locale> {
  const cookieStore = await cookies();
  const savedLocale = cookieStore.get(LOCALE_COOKIE)?.value ?? null;

  if (isLocale(savedLocale)) return savedLocale;

  const headerStore = await headers();
  return getLocaleFromAcceptLanguage(headerStore.get('accept-language'));
}
