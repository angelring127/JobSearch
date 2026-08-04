function getCrawlerServiceBaseUrl() {
  if (process.env.CRAWLER_SERVICE_URL) {
    return process.env.CRAWLER_SERVICE_URL.replace(/\/$/, '');
  }

  if (process.env.VERCEL_URL) {
    return `https://${process.env.VERCEL_URL}/crawler`;
  }

  return 'http://localhost:8001';
}

export async function runCrawlerSource(sourceKey: string) {
  const response = await fetch(`${getCrawlerServiceBaseUrl()}/admin/run`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${process.env.CRON_SECRET || 'dev-cron-secret'}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ source_key: sourceKey }),
    cache: 'no-store',
  });

  if (!response.ok) {
    throw new Error(`Crawler service returned ${response.status}`);
  }

  return response.json();
}
