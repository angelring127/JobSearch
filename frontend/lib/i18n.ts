import type { JobSource } from '@/lib/api';

export const LOCALES = ['ko', 'en', 'ja', 'zh'] as const;

export type Locale = (typeof LOCALES)[number];

export const LANGUAGE_OPTIONS: ReadonlyArray<{ value: Locale; label: string; compactLabel: string }> = [
  { value: 'ko', label: '한국어', compactLabel: 'KO' },
  { value: 'en', label: 'English', compactLabel: 'EN' },
  { value: 'ja', label: '日本語', compactLabel: 'JA' },
  { value: 'zh', label: '简体中文', compactLabel: '中文' },
];

export const LOCALE_TAGS: Record<Locale, string> = {
  ko: 'ko-KR',
  en: 'en-CA',
  ja: 'ja-JP',
  zh: 'zh-CN',
};

const ko = {
  metaTitle: 'JobMap | 캐나다 일자리 지도',
  language: '언어',
  home: 'JobMap 홈',
  allCanada: '캐나다 전역',
  postings: '개 공고',
  discoveryPanel: '일자리 검색 및 목록',
  mapPanel: '일자리 지도',
  heroEyebrow: '캐나다 일자리 탐색',
  heroTitle: '지도에서 가까운 일자리를 찾으세요.',
  heroDescription: '지역을 검색하거나 지도를 움직이면 현재 화면의 공고를 바로 보여드립니다.',
  viewMode: '보기 방식',
  list: '목록',
  map: '지도',
  cityQuick: '주요 도시 바로가기',
  chooseCity: '도시를 선택하세요',
  jobsUnit: '개',
  cityCountError: '일자리 수를 불러오지 못했습니다.',
  cityHint: '도시는 중심 50km 반경, 캐나다 전체는 전국 기준입니다.',
  locationSearch: '지역 검색',
  locationPlaceholder: '도시 또는 지역 (예: Vancouver, BC)',
  searching: '검색 중',
  search: '검색',
  noLocation: '캐나다 내에서 일치하는 지역을 찾지 못했습니다.',
  locationLoadError: '지역을 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.',
  locationResults: '지역 검색 결과',
  filters: '상세 필터',
  filterHint: '직종 · 시급 · 반경',
  filterDescription: '조건을 조정해 결과를 좁혀보세요.',
  reset: '초기화',
  category: '직종',
  hourlyWage: '시급 (CAD)',
  minimumWage: '최소 시급',
  maximumWage: '최대 시급',
  minimum: '최소',
  maximum: '최대',
  radius: '반경 (km)',
  radiusExample: '예: 5',
  allCategories: '전체 직종',
  restaurant: '레스토랑 / 카페',
  retail: '소매점',
  hospitality: '호텔 / 관광',
  warehouse: '창고 / 물류',
  construction: '건설',
  cleaning: '청소',
  other: '기타',
  emptyTitle: '이 지역에는 표시할 공고가 없습니다.',
  emptyBody: '다른 지역을 검색하거나 지도를 이동해 보세요.',
  jobs: '개의 일자리',
  currentMap: '현재 지도 기준',
  jobResults: '검색된 일자리',
  untitled: '제목 없음',
  reviewNeeded: '검토 필요',
  wageUpTo: '최대',
  wageUnlisted: '시급 미표시',
  perHour: '/시간',
  posted: '게시',
  firstSeen: '확인',
  dateUnavailable: '게시일 정보 없음',
  detailsEyebrow: '일자리 상세',
  closeDetails: '상세 정보 닫기',
  confidence: '신뢰도',
  confidenceVeryHigh: '매우 높음',
  confidenceHigh: '높음',
  confidenceMedium: '보통',
  confidenceLow: '낮음',
  region: '지역',
  regionUnavailable: '지역 정보 없음',
  distance: '거리',
  postedDate: '게시일',
  sourceSite: '출처',
  sourceLink: '원문 공고 보기',
  showMyLocation: '내 위치',
  locating: '위치 확인 중',
  myLocationMarker: '내 현재 위치',
  locationPermissionDenied: '위치 권한이 거부되었습니다. 브라우저 설정에서 권한을 허용해 주세요.',
  locationUnavailable: '현재 위치를 확인하지 못했습니다. 잠시 후 다시 시도해 주세요.',
  jobsAtLocation: '이 위치의 일자리',
  job: '일자리',
  mapLoadError: '지도를 로드하는 중 오류가 발생했습니다.',
  mapInitError: '지도를 초기화하는 중 문제가 발생했습니다. 브라우저가 WebGL을 지원하는지 확인해 주세요.',
  mapLoading: '지도 범위 검색 중',
} as const;

type MessageKey = keyof typeof ko;

const en: Record<MessageKey, string> = {
  metaTitle: 'JobMap | Canada jobs on a map', language: 'Language', home: 'JobMap home',
  allCanada: 'Across Canada', postings: ' postings', discoveryPanel: 'Job search and results', mapPanel: 'Job map',
  heroEyebrow: 'Canada job discovery', heroTitle: 'Find jobs near you on the map.',
  heroDescription: 'Search a place or move the map to see jobs in the current view.', viewMode: 'View mode', list: 'List', map: 'Map',
  cityQuick: 'Jump to a major city', chooseCity: 'Choose a city', jobsUnit: '', cityCountError: 'Could not load job counts.',
  cityHint: 'Cities use a 50 km radius; Canada shows nationwide results.', locationSearch: 'Search by location',
  locationPlaceholder: 'City or area (for example, Vancouver, BC)', searching: 'Searching', search: 'Search',
  noLocation: 'No matching location was found in Canada.', locationLoadError: 'Could not load locations. Please try again shortly.',
  locationResults: 'Location search results', filters: 'More filters', filterHint: 'Role · pay · radius',
  filterDescription: 'Adjust the criteria to narrow the results.', reset: 'Reset', category: 'Role', hourlyWage: 'Hourly pay (CAD)',
  minimumWage: 'Minimum hourly pay', maximumWage: 'Maximum hourly pay', minimum: 'Minimum', maximum: 'Maximum',
  radius: 'Radius (km)', radiusExample: 'For example, 5', allCategories: 'All roles', restaurant: 'Restaurant / cafe',
  retail: 'Retail', hospitality: 'Hotel / tourism', warehouse: 'Warehouse / logistics', construction: 'Construction',
  cleaning: 'Cleaning', other: 'Other', emptyTitle: 'There are no jobs to show in this area.',
  emptyBody: 'Search another place or move the map.', jobs: ' jobs', currentMap: 'Current map view', jobResults: 'Job search results',
  untitled: 'Untitled job', reviewNeeded: 'Needs review', wageUpTo: 'Up to', wageUnlisted: 'Pay not listed', perHour: '/hr',
  posted: 'Posted', dateUnavailable: 'Posting date unavailable', detailsEyebrow: 'Job details', closeDetails: 'Close job details',
  firstSeen: 'First seen',
  confidence: 'Confidence', confidenceVeryHigh: 'Very high', confidenceHigh: 'High', confidenceMedium: 'Medium', confidenceLow: 'Low',
  region: 'Region', regionUnavailable: 'Region unavailable', distance: 'Distance', postedDate: 'Posted',
  sourceSite: 'Source', sourceLink: 'View original posting', showMyLocation: 'My location', locating: 'Locating',
  myLocationMarker: 'My current location', locationPermissionDenied: 'Location permission was denied. Allow it in your browser settings.',
  locationUnavailable: 'Your current location could not be found. Please try again shortly.',
  jobsAtLocation: 'Jobs at this location', job: 'Job',
  mapLoadError: 'An error occurred while loading the map.', mapInitError: 'The map could not start. Check whether your browser supports WebGL.',
  mapLoading: 'Searching this map area',
};

const ja: Record<MessageKey, string> = {
  metaTitle: 'JobMap | カナダ求人マップ', language: '言語', home: 'JobMap ホーム', allCanada: 'カナダ全土', postings: '件の求人',
  discoveryPanel: '求人検索と一覧', mapPanel: '求人マップ', heroEyebrow: 'カナダの求人を探す', heroTitle: '地図で近くの求人を探しましょう。',
  heroDescription: '地域を検索するか地図を動かすと、表示範囲の求人がすぐに表示されます。', viewMode: '表示方法', list: '一覧', map: '地図',
  cityQuick: '主要都市へ移動', chooseCity: '都市を選択', jobsUnit: '件', cityCountError: '求人数を読み込めませんでした。',
  cityHint: '都市は中心から50km圏内、カナダ全土は全国の求人が対象です。', locationSearch: '地域を検索',
  locationPlaceholder: '都市または地域（例：Vancouver, BC）', searching: '検索中', search: '検索',
  noLocation: 'カナダ国内で一致する地域が見つかりませんでした。', locationLoadError: '地域を読み込めませんでした。しばらくしてから再度お試しください。',
  locationResults: '地域の検索結果', filters: '詳細フィルター', filterHint: '職種・時給・範囲',
  filterDescription: '条件を調整して結果を絞り込みます。', reset: 'リセット', category: '職種', hourlyWage: '時給（CAD）',
  minimumWage: '最低時給', maximumWage: '最高時給', minimum: '最低', maximum: '最高', radius: '範囲（km）', radiusExample: '例：5',
  allCategories: 'すべての職種', restaurant: 'レストラン / カフェ', retail: '小売', hospitality: 'ホテル / 観光',
  warehouse: '倉庫 / 物流', construction: '建設', cleaning: '清掃', other: 'その他',
  emptyTitle: 'この地域に表示できる求人はありません。', emptyBody: '別の地域を検索するか、地図を移動してください。',
  jobs: '件の求人', currentMap: '現在の地図範囲', jobResults: '求人検索結果', untitled: 'タイトルなし', reviewNeeded: '要確認',
  wageUpTo: '最大', wageUnlisted: '時給記載なし', perHour: '/時', posted: '掲載', dateUnavailable: '掲載日情報なし',
  firstSeen: '確認',
  detailsEyebrow: '求人詳細', closeDetails: '求人詳細を閉じる', confidence: '信頼度', confidenceVeryHigh: '非常に高い',
  confidenceHigh: '高い', confidenceMedium: '普通', confidenceLow: '低い', region: '地域', regionUnavailable: '地域情報なし',
  distance: '距離', postedDate: '掲載日', sourceSite: '掲載元', sourceLink: '元の求人を見る',
  showMyLocation: '現在地', locating: '位置を確認中', myLocationMarker: '現在地',
  locationPermissionDenied: '位置情報の使用が拒否されました。ブラウザの設定で許可してください。',
  locationUnavailable: '現在地を確認できませんでした。しばらくしてから再度お試しください。',
  jobsAtLocation: 'この場所の求人', job: '求人',
  mapLoadError: '地図の読み込み中にエラーが発生しました。', mapInitError: '地図を初期化できませんでした。ブラウザがWebGLに対応しているか確認してください。',
  mapLoading: '地図範囲を検索中',
};

const zh: Record<MessageKey, string> = {
  metaTitle: 'JobMap | 加拿大职位地图', language: '语言', home: 'JobMap 首页', allCanada: '加拿大境内', postings: '个职位',
  discoveryPanel: '职位搜索和列表', mapPanel: '职位地图', heroEyebrow: '探索加拿大职位', heroTitle: '在地图上寻找附近的职位。',
  heroDescription: '搜索地点或移动地图，即可查看当前区域内的职位。', viewMode: '查看方式', list: '列表', map: '地图',
  cityQuick: '快速前往主要城市', chooseCity: '选择城市', jobsUnit: '个', cityCountError: '无法加载职位数量。',
  cityHint: '城市按中心50公里范围显示；加拿大选项显示全国职位。', locationSearch: '搜索地点',
  locationPlaceholder: '城市或地区（例如 Vancouver, BC）', searching: '搜索中', search: '搜索',
  noLocation: '在加拿大境内未找到匹配地点。', locationLoadError: '无法加载地点，请稍后重试。', locationResults: '地点搜索结果',
  filters: '详细筛选', filterHint: '职位 · 时薪 · 范围', filterDescription: '调整条件以缩小结果范围。', reset: '重置',
  category: '职位类别', hourlyWage: '时薪（CAD）', minimumWage: '最低时薪', maximumWage: '最高时薪', minimum: '最低', maximum: '最高',
  radius: '范围（公里）', radiusExample: '例如 5', allCategories: '所有类别', restaurant: '餐厅 / 咖啡馆', retail: '零售',
  hospitality: '酒店 / 旅游', warehouse: '仓库 / 物流', construction: '建筑', cleaning: '清洁', other: '其他',
  emptyTitle: '此区域暂无可显示的职位。', emptyBody: '请搜索其他地点或移动地图。', jobs: '个职位', currentMap: '当前地图范围',
  jobResults: '职位搜索结果', untitled: '无标题职位', reviewNeeded: '需要审核', wageUpTo: '最高', wageUnlisted: '未注明时薪',
  perHour: '/小时', posted: '发布于', dateUnavailable: '暂无发布日期', detailsEyebrow: '职位详情', closeDetails: '关闭职位详情',
  firstSeen: '首次发现',
  confidence: '可信度', confidenceVeryHigh: '非常高', confidenceHigh: '高', confidenceMedium: '中等', confidenceLow: '低',
  region: '地区', regionUnavailable: '暂无地区信息', distance: '距离', postedDate: '发布日期',
  sourceSite: '来源网站', sourceLink: '查看原始职位', showMyLocation: '我的位置', locating: '正在定位', myLocationMarker: '我的当前位置',
  locationPermissionDenied: '位置权限已被拒绝，请在浏览器设置中允许访问。',
  locationUnavailable: '无法获取当前位置，请稍后重试。',
  jobsAtLocation: '此位置的职位', job: '职位', mapLoadError: '加载地图时发生错误。',
  mapInitError: '无法初始化地图，请确认浏览器支持 WebGL。', mapLoading: '正在搜索地图区域',
};

const MESSAGES: Record<Locale, Record<MessageKey, string>> = { ko, en, ja, zh };

const CITY_LABELS: Record<Locale, Record<string, string>> = {
  ko: { canada: '캐나다 전체', vancouver: '밴쿠버 · 브리티시컬럼비아', victoria: '빅토리아 · 브리티시컬럼비아', calgary: '캘거리 · 앨버타', edmonton: '에드먼턴 · 앨버타', winnipeg: '위니펙 · 매니토바', toronto: '토론토 · 온타리오', ottawa: '오타와 · 온타리오', montreal: '몬트리올 · 퀘벡', halifax: '핼리팩스 · 노바스코샤' },
  en: { canada: 'All of Canada', vancouver: 'Vancouver · British Columbia', victoria: 'Victoria · British Columbia', calgary: 'Calgary · Alberta', edmonton: 'Edmonton · Alberta', winnipeg: 'Winnipeg · Manitoba', toronto: 'Toronto · Ontario', ottawa: 'Ottawa · Ontario', montreal: 'Montreal · Quebec', halifax: 'Halifax · Nova Scotia' },
  ja: { canada: 'カナダ全土', vancouver: 'バンクーバー・ブリティッシュコロンビア', victoria: 'ビクトリア・ブリティッシュコロンビア', calgary: 'カルガリー・アルバータ', edmonton: 'エドモントン・アルバータ', winnipeg: 'ウィニペグ・マニトバ', toronto: 'トロント・オンタリオ', ottawa: 'オタワ・オンタリオ', montreal: 'モントリオール・ケベック', halifax: 'ハリファックス・ノバスコシア' },
  zh: { canada: '加拿大全境', vancouver: '温哥华 · 不列颠哥伦比亚省', victoria: '维多利亚 · 不列颠哥伦比亚省', calgary: '卡尔加里 · 艾伯塔省', edmonton: '埃德蒙顿 · 艾伯塔省', winnipeg: '温尼伯 · 曼尼托巴省', toronto: '多伦多 · 安大略省', ottawa: '渥太华 · 安大略省', montreal: '蒙特利尔 · 魁北克省', halifax: '哈利法克斯 · 新斯科舍省' },
};

const COMPACT_CITY_LABELS: Record<Locale, Record<string, string>> = {
  ko: { canada: '캐나다 전체', vancouver: '밴쿠버', victoria: '빅토리아', calgary: '캘거리', edmonton: '에드먼턴', winnipeg: '위니펙', toronto: '토론토', ottawa: '오타와', montreal: '몬트리올', halifax: '핼리팩스' },
  en: { canada: 'All Canada', vancouver: 'Vancouver', victoria: 'Victoria', calgary: 'Calgary', edmonton: 'Edmonton', winnipeg: 'Winnipeg', toronto: 'Toronto', ottawa: 'Ottawa', montreal: 'Montreal', halifax: 'Halifax' },
  ja: { canada: 'カナダ全土', vancouver: 'バンクーバー', victoria: 'ビクトリア', calgary: 'カルガリー', edmonton: 'エドモントン', winnipeg: 'ウィニペグ', toronto: 'トロント', ottawa: 'オタワ', montreal: 'モントリオール', halifax: 'ハリファックス' },
  zh: { canada: '加拿大全境', vancouver: '温哥华', victoria: '维多利亚', calgary: '卡尔加里', edmonton: '埃德蒙顿', winnipeg: '温尼伯', toronto: '多伦多', ottawa: '渥太华', montreal: '蒙特利尔', halifax: '哈利法克斯' },
};

const SOURCE_LABELS: Record<Locale, Record<string, string>> = {
  ko: {
    jpcanada: 'JP 캐나다',
    ourvancouver: '우벤유',
    jinzaicanada: '인재 캐나다',
    vanchosun: '밴쿠버 조선일보',
  },
  en: {
    jpcanada: 'JP Canada',
    ourvancouver: 'Our Vancouver',
    jinzaicanada: 'Jinzai Canada',
    vanchosun: 'Vancouver Chosun',
  },
  ja: {
    jpcanada: 'JPカナダ',
    ourvancouver: 'アワー・バンクーバー',
    jinzaicanada: '人材カナダ',
    vanchosun: 'バンクーバー朝鮮日報',
  },
  zh: {
    jpcanada: 'JP加拿大',
    ourvancouver: '我们的温哥华',
    jinzaicanada: '加拿大人才网',
    vanchosun: '温哥华朝鲜日报',
  },
};

export function isLocale(value: string | null): value is Locale {
  return value !== null && LOCALES.includes(value as Locale);
}

export function t(locale: Locale, key: MessageKey): string {
  return MESSAGES[locale][key];
}

export function formatNumber(value: number, locale: Locale): string {
  return value.toLocaleString(LOCALE_TAGS[locale]);
}

export function formatPostedDate(value: string | null, locale: Locale): string {
  if (!value) return t(locale, 'dateUnavailable');
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return t(locale, 'dateUnavailable');
  return new Intl.DateTimeFormat(LOCALE_TAGS[locale], {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    timeZone: 'UTC',
  }).format(date);
}

export function formatWage(job: JobSource, locale: Locale): string {
  const min = job.wage_min === null ? null : formatNumber(job.wage_min, locale);
  const max = job.wage_max === null ? null : formatNumber(job.wage_max, locale);
  if (min && max) return `$${min}–$${max}${t(locale, 'perHour')}`;
  if (min) return `$${min}+${t(locale, 'perHour')}`;
  if (max) return `${t(locale, 'wageUpTo')} $${max}${t(locale, 'perHour')}`;
  return t(locale, 'wageUnlisted');
}

export function getJobTitle(job: JobSource, locale: Locale): string {
  return job.title_translations?.[locale]?.trim() || job.title?.trim() || t(locale, 'untitled');
}

export function getSourceName(job: JobSource, locale: Locale): string {
  const sourceKey = job.source_key?.trim().toLowerCase();
  if (sourceKey && SOURCE_LABELS[locale][sourceKey]) return SOURCE_LABELS[locale][sourceKey];

  const sourceName = job.source_name?.trim();
  if (sourceName) return sourceName;

  try {
    return new URL(job.source_url).hostname.replace(/^www\./, '');
  } catch {
    return '';
  }
}

export function getCategoryLabel(value: string | null | undefined, locale: Locale): string {
  if (!value) return '';
  const key = value as MessageKey;
  return Object.prototype.hasOwnProperty.call(MESSAGES[locale], key) ? t(locale, key) : value;
}

export function getCityLabel(value: string, locale: Locale, fallback: string): string {
  return CITY_LABELS[locale][value] || fallback;
}

export function getCompactCityLabel(value: string, locale: Locale, fallback: string): string {
  return COMPACT_CITY_LABELS[locale][value] || getCityLabel(value, locale, fallback);
}
