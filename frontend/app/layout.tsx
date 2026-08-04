import type { Metadata } from 'next'
import { Noto_Sans_KR, Space_Grotesk } from 'next/font/google'
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

export const metadata: Metadata = {
  title: 'JobMap',
  description: '캐나다 구인정보 지도 기반 탐색 서비스',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="ko" className={`${notoSansKr.variable} ${spaceGrotesk.variable}`}>
      <body>{children}</body>
    </html>
  )
}

