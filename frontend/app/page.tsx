import JobMapApp from '@/components/JobMapApp';
import { getRequestLocale } from '@/lib/server/request-locale';

export default async function Home() {
  const initialLocale = await getRequestLocale();

  return <JobMapApp initialLocale={initialLocale} />;
}
