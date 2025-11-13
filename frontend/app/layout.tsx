import type { Metadata } from 'next'
import './globals.css'

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
    <html lang="ko">
      <body>{children}</body>
    </html>
  )
}


