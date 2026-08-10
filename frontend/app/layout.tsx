import type { Metadata } from 'next'
import { Noto_Sans_KR, Space_Grotesk } from 'next/font/google'
import { LOCALE_TAGS, t } from '@/lib/i18n'
import { getRequestLocale } from '@/lib/server/request-locale'
import './globals.css'

const notoSansKr = Noto_Sans_KR({
  variable: '--font-noto-kr',
  weight: ['400', '500', '700'],
  display: 'swap',
  preload: false,
})

const spaceGrotesk = Space_Grotesk({
  variable: '--font-space-grotesk',
  subsets: ['latin'],
  display: 'swap',
})

export async function generateMetadata(): Promise<Metadata> {
  const locale = await getRequestLocale()

  return {
    title: t(locale, 'metaTitle'),
    description: t(locale, 'metaDescription'),
  }
}

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const locale = await getRequestLocale()

  return (
    <html lang={LOCALE_TAGS[locale]} className={`${notoSansKr.variable} ${spaceGrotesk.variable}`}>
      <body>{children}</body>
    </html>
  )
}
