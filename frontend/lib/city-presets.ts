export interface CityPreset {
  value: string;
  label: string;
  center: [number, number];
  zoom: number;
  radiusKm: number | null;
}

export const CITY_PRESETS: CityPreset[] = [
  { value: 'canada', label: '캐나다 전체', center: [-101.5, 54.2], zoom: 3, radiusKm: null },
  { value: 'vancouver', label: '밴쿠버 · 브리티시컬럼비아', center: [-123.1207, 49.2827], zoom: 10, radiusKm: 50 },
  { value: 'victoria', label: '빅토리아 · 브리티시컬럼비아', center: [-123.3656, 48.4284], zoom: 11, radiusKm: 50 },
  { value: 'calgary', label: '캘거리 · 앨버타', center: [-114.0719, 51.0447], zoom: 10, radiusKm: 50 },
  { value: 'edmonton', label: '에드먼턴 · 앨버타', center: [-113.4938, 53.5461], zoom: 10, radiusKm: 50 },
  { value: 'winnipeg', label: '위니펙 · 매니토바', center: [-97.1384, 49.8951], zoom: 10, radiusKm: 50 },
  { value: 'toronto', label: '토론토 · 온타리오', center: [-79.3832, 43.6532], zoom: 10, radiusKm: 50 },
  { value: 'ottawa', label: '오타와 · 온타리오', center: [-75.6972, 45.4215], zoom: 10, radiusKm: 50 },
  { value: 'montreal', label: '몬트리올 · 퀘벡', center: [-73.5673, 45.5019], zoom: 10, radiusKm: 50 },
  { value: 'halifax', label: '핼리팩스 · 노바스코샤', center: [-63.5752, 44.6488], zoom: 10, radiusKm: 50 },
];
