"""
JPCanada BBS 크롤러 모듈
"""
import re
import time
import logging
from datetime import datetime
from typing import Optional, Dict, List
from bs4 import BeautifulSoup
import httpx

from location_resolution import has_street_address

logger = logging.getLogger(__name__)

# リクエスト間隔（秒）
REQUEST_INTERVAL = 2.5

# User-Agent
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def parse_wage(text: str) -> tuple:
    """
    時給情報をパース
    例: "$18/hr", "$18-20/hr", "$18-$20/hour"
    """
    if not text:
        return None, None

    normalized = text.translate(str.maketrans({
        '０': '0', '１': '1', '２': '2', '３': '3', '４': '4',
        '５': '5', '６': '6', '７': '7', '８': '8', '９': '9',
        '＄': '$', '～': '~', 'ー': '-',
    })).replace(',', '')

    normalized = re.sub(r'\b20\d{2}[-/年]\s*\d{1,2}[-/月]\s*\d{1,2}\b', ' ', normalized)
    normalized = re.sub(r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b', ' ', normalized)

    candidate_patterns = [
        r'(?:\$|ca(?:d)?\s*\$?)\s*(\d{1,3}(?:\.\d{1,2})?)\s*(?:[-~〜–]\s*(?:\$|ca(?:d)?\s*\$?)?\s*(\d{1,3}(?:\.\d{1,2})?))?',
        r'(?:時給|hourly|wage|pay|給料|賃金|hour|hr|per\s+hour)\D{0,20}(\d{1,3}(?:\.\d{1,2})?)\s*(?:[-~〜–]\s*(\d{1,3}(?:\.\d{1,2})?))?',
        r'(\d{1,3}(?:\.\d{1,2})?)\s*(?:/h|/hr|/hour|ドル\s*/?\s*時|円\s*/?\s*時)',
    ]

    candidates = []
    for pattern in candidate_patterns:
        for match in re.finditer(pattern, normalized, re.IGNORECASE):
            low = _valid_hourly_wage(match.group(1))
            high = _valid_hourly_wage(match.group(2) if len(match.groups()) > 1 else None)
            if low is None:
                continue
            candidates.append((low, high or low))

    if not candidates:
        return None, None

    wage_min, wage_max = candidates[0]
    return wage_min, wage_max


def _valid_hourly_wage(value: Optional[str]) -> Optional[int]:
    if not value:
        return None

    parsed = float(value)
    if parsed < 10 or parsed > 100:
        return None
    return int(round(parsed))


def parse_category(title: str, description: str = "") -> Optional[str]:
    """
    職種カテゴリを推測
    """
    text = (title + " " + description).lower()
    
    if any(word in text for word in ['restaurant', 'cafe', 'kitchen', 'server', 'waiter', 'cook', 'chef', '레스토랑', '식당', '카페', '주방', '서버', '스시', '요리', '厨房', '餐厅', '咖啡', '服务员', '厨师', 'サーバー', 'レストラン', '調理']):
        return 'restaurant'
    elif any(word in text for word in ['retail', 'store', 'shop', 'sales', 'cashier', '판매', '매장', '캐시어', '소매', '零售', '商店', '销售', '收银员', '販売', 'レジ']):
        return 'retail'
    elif any(word in text for word in ['hotel', 'hospitality', 'front desk', 'reception', '호텔', '관광', '리셉션', '酒店', '旅游', '前台', 'ホテル', '観光', '受付']):
        return 'hospitality'
    elif any(word in text for word in ['warehouse', 'logistics', 'forklift', '창고', '물류', '배송', '배달', '仓库', '物流', '配送', '倉庫']):
        return 'warehouse'
    elif any(word in text for word in ['construction', 'laborer', 'carpenter', '건설', '목수', '공사', '建筑', '木工', '建設']):
        return 'construction'
    elif any(word in text for word in ['cleaning', 'cleaner', 'janitor', 'housekeeping', '청소', '클리너', '하우스키핑', '清洁', '清掃']):
        return 'cleaning'
    else:
        return 'other'


def parse_posted_date(text: str) -> Optional[datetime]:
    """
    投稿日をパース
    """
    if not text:
        return None
    
    # 日付パターンを試行
    patterns = [
        r'(\d{4})-(\d{2})-(\d{2})',  # YYYY-MM-DD
        r'(\d{2})/(\d{2})/(\d{4})',   # MM/DD/YYYY
        r'(\d{2})-(\d{2})-(\d{4})',   # MM-DD-YYYY
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            try:
                if pattern == patterns[0]:
                    year, month, day = match.groups()
                else:
                    month, day, year = match.groups()
                return datetime(int(year), int(month), int(day))
            except ValueError:
                continue
    
    return None


def extract_location_hints(text: str) -> Optional[str]:
    """
    位置情報のヒントを抽出（都市名のみ）
    """
    if not text:
        return None
    
    # カナダの主要都市名を検索
    cities = [
        'Vancouver', 'Victoria', 'Toronto', 'Whistler', 'Burnaby', 
        'Richmond', 'Surrey', 'North Vancouver', 'West Vancouver',
        'Coquitlam', 'New Westminster', 'Langley', 'Delta',
        'Kelowna', 'Banff', 'Canmore', 'Calgary', 'Edmonton',
        'Vernon', 'Nelson', 'Revelstoke', 'Jasper', 'Halifax',
        'Montreal', 'Winnipeg', 'Yellowknife'
    ]
    
    text_lower = text.lower()
    for city in cities:
        if city.lower() in text_lower:
            return city
    
    return None


def extract_addresses(text: str) -> List[str]:
    """
    本文から実際の住所を複数抽出（複数店舗の場合に対応）
    パターン:
    - "勤務地" キーワードの後の住所
    - 英語の住所パターン (数字 + Street/St/Ave/Avenue等)
    - 店舗名 + 住所
    - 地域名 (例: "Yaletown Vancouver")
    """
    addresses = []
    if not text:
        return addresses
    
    # パターン1: 「勤務地」「勤務場所」「Address」などのキーワードの後の住所
    location_keywords = [
        r'勤務地[：:]\s*([^\n]+)',
        r'勤務場所[：:]\s*([^\n]+)',
        r'勤務先[：:]\s*([^\n]+)',
        r'所在地[：:]\s*([^\n]+)',
        r'住所[：:]\s*([^\n]+)',
        r'場所[：:]\s*([^\n]+)',
        r'【募集店舗】\s*([^\n]+)',  # 募集店舗セクション
        r'Address[：:]\s*([^\n]+)',  # 英語のAddressキーワード
        r'Address\s+([^\n]+)',  # "Address "の後の住所（コロンなし）
        r'Location[：:]\s*([^\n]+)',  # Locationキーワード
        r'Location\s+([^\n]+)',  # "Location "の後の住所
        r'Work\s+Location[：:]\s*([^\n]+)',  # Work Location
        r'Work\s+Address[：:]\s*([^\n]+)',  # Work Address
    ]
    
    for pattern in location_keywords:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            address = match.strip()
            # 改行や余分な文字を削除
            address = re.sub(r'\s+', ' ', address).strip()
            # URLやメールアドレスを除外
            if len(address) > 5 and '@' not in address and 'http' not in address.lower():
                addresses.append(address)
    
    # パターン2: 英語の住所パターン (例: "1884 Dayton st, Kelowna, BC" または "4518 Hastings St, Burnaby, V5C 2K4")
    # 数字 + ストリート名 + 都市名 + 郵便番号/州名
    address_patterns = [
        r'(\d+[A-Za-z]?\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Boulevard|Blvd|Way|Lane|Ln)[,\s]+[A-Za-z\s]+(?:,\s*)?(?:V\d[A-Z]\s?\d[A-Z]\d|BC|AB|ON|QC|MB|SK|NB|NS|PE|NL|YT|NT|NU)?)',
        r'(\d+[A-Za-z]?\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd)[,\s]+[A-Za-z\s]+)',
        r'([A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd)[,\s]+[A-Za-z\s]+(?:,\s*)?(?:V\d[A-Z]\s?\d[A-Z]\d|BC|AB|ON|QC|MB|SK|NB|NS|PE|NL|YT|NT|NU)?)',
    ]
    
    for pattern in address_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            address = match.strip()
            if len(address) > 10 and address not in addresses:  # 意味のある住所かチェック、重複排除
                addresses.append(address)
    
    # パターン3: 地域名 + 都市名 (例: "Yaletown Vancouver", "Surrey・Langleyエリア")
    area_patterns = [
        r'([A-Z][a-z]+(?:town|land|park|hill|valley|beach|bay)[,\s]+(?:Vancouver|Burnaby|Surrey|Richmond|Victoria|Toronto|Kelowna|Calgary|Edmonton))',
        r'([A-Z][a-z]+(?:・|/|\s+)[A-Z][a-z]+(?:エリア|area|Area))',
    ]
    
    for pattern in area_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            area = match.strip()
            if len(area) > 5 and area not in addresses:
                addresses.append(area)
    
    # パターン4: 店舗名 + 住所の組み合わせ
    # 例: "The Ramen Butcher Burnaby\n4518 Hastings St, Burnaby, V5C 2K4"
    store_address_pattern = r'([A-Za-z\s&]+(?:Restaurant|Cafe|Shop|Store|Bistro|Kitchen|Pizza|Sushi|Ramen|Market|Enterprises)[,\s\n]+)?(\d+[A-Za-z]?\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd)[,\s]+[A-Za-z\s]+(?:,\s*)?(?:V\d[A-Z]\s?\d[A-Z]\d)?)'
    matches = re.findall(store_address_pattern, text, re.IGNORECASE | re.MULTILINE)
    for store_part, address_part in matches:
        if address_part:
            combined = (store_part.strip() + " " + address_part.strip()).strip()
            if len(combined) > 10 and combined not in addresses:
                addresses.append(combined)
    
    # 重複を除去
    seen = set()
    unique_addresses = []
    for addr in addresses:
        addr_lower = addr.lower()
        if addr_lower not in seen:
            seen.add(addr_lower)
            unique_addresses.append(addr)
    
    return unique_addresses


def extract_address(text: str) -> Optional[str]:
    """
    本文から最初の住所を抽出（後方互換性のため）
    """
    addresses = extract_addresses(text)
    return addresses[0] if addresses else None


def extract_store_name(text: str, title: str = "") -> Optional[str]:
    """
    店舗名を抽出
    """
    # タイトルから店舗名を推測
    if title:
        # レストラン、カフェなどのキーワードを含む場合
        store_keywords = ['Restaurant', 'Cafe', 'Shop', 'Store', 'Bistro', 'Kitchen', 'Pizza', 'Sushi', 'Ramen']
        for keyword in store_keywords:
            if keyword.lower() in title.lower():
                # タイトル全体またはキーワード前後の部分を返す
                return title
    
    # 本文から店舗名を検索
    store_patterns = [
        r'店名[：:]\s*([^\n]+)',
        r'店舗名[：:]\s*([^\n]+)',
        r'([A-Za-z\s&]+(?:Restaurant|Cafe|Shop|Store|Bistro|Kitchen|Pizza|Sushi|Ramen))',
    ]
    
    for pattern in store_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            store_name = match.group(1).strip()
            if len(store_name) > 3:
                return store_name
    
    return None


def parse_job_post(html: str, url: str, msgid: int) -> Optional[Dict]:
    """
    JPCanada BBS投稿をパース
    実際のHTML構造に基づいてパース
    ページに複数の投稿が含まれる場合、指定されたmsgidの投稿のみを抽出
    """
    try:
        soup = BeautifulSoup(html, 'lxml')
        
        # 指定されたmsgidの投稿セクションを探す
        # パターン: "No.106874" のような形式を探す
        msgid_pattern = re.compile(rf'No\.{msgid}\b', re.IGNORECASE)
        
        title = None
        content = ""
        section_start = None
        
        # msgidを含むテキストノードを探す
        msgid_text_node = None
        for elem in soup.find_all(string=msgid_pattern):
            msgid_text_node = elem
            break
        
        if msgid_text_node:
            # msgidを含む要素の親を取得
            parent_elem = msgid_text_node.find_parent()
            
            if parent_elem:
                # 親要素から開始して、次のh2タグ（タイトル）を探す
                # HTML構造: "No.{msgid}" → h2 (タイトル) → 本文
                
                # 方法1: 親要素内でh2を探す
                h2 = parent_elem.find('h2')
                if h2:
                    title = h2.get_text(strip=True)
                    # セクション全体を取得
                    section_start = parent_elem
                else:
                    # 方法2: 親要素の次の要素でh2を探す
                    next_elem = parent_elem.find_next()
                    while next_elem:
                        h2 = next_elem.find('h2')
                        if h2:
                            title = h2.get_text(strip=True)
                            section_start = next_elem
                            break
                        # 次の投稿セクション（"No."で始まる）が来たら停止
                        text = next_elem.get_text(strip=True)
                        if re.match(rf'No\.(?!{msgid})\d+', text):
                            break
                        next_elem = next_elem.find_next_sibling()
                
                # タイトルが見つかった場合、本文を取得
                if title and section_start:
                    # section_startから次の投稿セクション（"No.{다른숫자}"）までを取得
                    content_parts = []
                    current = section_start
                    max_iterations = 100
                    iteration = 0
                    
                    while current and iteration < max_iterations:
                        iteration += 1
                        text = current.get_text(strip=True)
                        
                        # 次の投稿セクション（"No."で始まる、ただし現在のmsgidは除く）が来たら停止
                        if re.match(rf'No\.(?!{msgid})\d+', text):
                            break
                        
                        # タイトルとmsgidパターンを除外
                        if text and len(text) > 10:
                            if text != title and not re.match(rf'No\.{msgid}', text):
                                # 各要素のテキストを追加
                                for child in current.find_all(['p', 'div', 'td', 'span', 'li']):
                                    child_text = child.get_text(strip=True)
                                    if child_text and len(child_text) > 5:
                                        if child_text not in content_parts:
                                            content_parts.append(child_text)
                        
                        current = current.find_next_sibling()
                        if not current:
                            break
                    
                    content = ' '.join(content_parts)
                    
                    # まだ内容が少ない場合、セクション全体のテキストを取得
                    if len(content) < 50:
                        full_text = section_start.get_text()
                        # タイトルと"No.{msgid}"を除く
                        full_text = re.sub(rf'No\.{msgid}.*?\n', '', full_text, flags=re.IGNORECASE)
                        if title:
                            full_text = full_text.replace(title, '', 1)
                        # 次の投稿セクションまで
                        next_post_match = re.search(rf'No\.(?!{msgid})\d+', full_text)
                        if next_post_match:
                            full_text = full_text[:next_post_match.start()]
                        content = full_text.strip()
        
        # フォールバック: タイトルが見つからない場合
        if not title:
            # 通常のパターンで探す（最初のh2）
            h2_elem = soup.find('h2')
            if h2_elem:
                title_text = h2_elem.get_text(strip=True)
                # "No."で始まるタイトルは除外
                if title_text and len(title_text) > 5 and not title_text.startswith('No.'):
                    title = title_text
        
        # 本文がまだ取得できていない場合のフォールバック
        if not content or len(content) < 50:
            # msgidテキストノードから次の投稿セクションまでを取得
            if msgid_text_node:
                parent = msgid_text_node.find_parent()
                if parent:
                    content_parts = []
                    current = parent
                    for _ in range(50):  # 最大50要素まで探索
                        if current:
                            text = current.get_text(strip=True)
                            # 次の投稿セクション（"No."で始まる、ただし現在のmsgidは除く）が来たら停止
                            if re.match(rf'No\.(?!{msgid})\d+', text):
                                break
                            if text and len(text) > 10 and text != title and not re.match(rf'No\.{msgid}', text):
                                content_parts.append(text)
                            current = current.find_next_sibling()
                        else:
                            break
                    if content_parts:
                        content = ' '.join(content_parts)
            
            # それでも見つからない場合、通常のパターンで探す
            if not content or len(content) < 50:
                content_patterns = [
                    soup.find('div', class_=re.compile(r'content|post|message|body', re.I)),
                    soup.find('div', id=re.compile(r'content|post|message|body', re.I)),
                    soup.find('td', class_=re.compile(r'content|post|message', re.I)),
                    soup.find('article'),
                    soup.find('main'),
                ]
                for elem in content_patterns:
                    if elem:
                        content = elem.get_text()
                        if len(content) > 50:
                            break
            
            # 最後のフォールバック: body全体から取得
            if not content or len(content) < 50:
                body = soup.find('body')
                if body:
                    content = body.get_text()
        
        # 時給情報を抽出
        wage_min, wage_max = parse_wage((title or "") + " " + content)
        
        # カテゴリ推測
        category = parse_category(title or "", content)
        
        # 位置情報ヒント（都市名）
        region_hint = extract_location_hints(content)
        
        # 投稿者情報から地域ヒントを抽出（オプション）
        if not region_hint:
            author_pattern = re.search(r'([A-Za-z]+)/([A-Za-z\s,]+)', content)
            if author_pattern:
                location_part = author_pattern.group(2)
                region_hint = extract_location_hints(location_part)
        
        # 実際の住所を複数抽出（複数店舗対応）
        addresses = extract_addresses(content)
        
        # 店舗名を抽出
        store_name = extract_store_name(content, title or "")
        
        # location_textを構築（優先順位: 最初の住所 > 店舗名+都市名 > 都市名のみ）
        # 複数の住所がある場合は最初のものを使用（最も具体的な情報）
        location_text = None
        if addresses:
            # 最初の住所を使用
            address = addresses[0]
            location_text = address
            # 都市名が含まれていない場合、region_hintを追加
            if region_hint:
                # 住所に都市名が含まれているかチェック
                city_in_address = any(city.lower() in address.lower() for city in [
                    'Vancouver', 'Victoria', 'Toronto', 'Burnaby', 'Surrey', 'Richmond',
                    'Kelowna', 'Banff', 'Canmore', 'Calgary', 'Edmonton', 'Vernon',
                    'Nelson', 'Revelstoke', 'Jasper', 'Halifax', 'Montreal', 'Winnipeg'
                ])
                if not city_in_address and region_hint.lower() not in address.lower():
                    location_text = f"{address}, {region_hint}, BC"
            location_kind = "street_address" if has_street_address(address) else "neighborhood"
        elif store_name and region_hint:
            location_text = f"{store_name}, {region_hint}, BC"
            location_kind = "business_or_landmark"
        elif region_hint:
            location_text = f"{region_hint}, BC"
            location_kind = "city_only"
        else:
            location_kind = "none"
        
        # 複数住所がある場合はログに記録（将来の拡張用）
        if len(addresses) > 1:
            logger.info(f"Found {len(addresses)} addresses for msgid {msgid}: {addresses}")
        
        # 投稿日（HTMLから日付パターンを検索）
        posted_at = parse_posted_date(content)
        
        return {
            'msgid': msgid,
            'source_url': url,
            'title': title,
            'wage_min': wage_min,
            'wage_max': wage_max,
            'category': category,
            'region_hint': region_hint,
            'location_text': location_text,  # 実際の住所または店舗名+都市名
            'location_kind': location_kind,
            'posted_at': posted_at.isoformat() if posted_at else None,
        }
    except Exception as e:
        logger.error(f"Failed to parse job post {url}: {e}", exc_info=True)
        return None


def fetch_bbs_page(url: str, client: httpx.Client) -> Optional[str]:
    """
    BBSページを取得
    """
    try:
        response = client.get(url, timeout=30.0)
        response.raise_for_status()
        return response.text
    except Exception as e:
        logger.error(f"Failed to fetch {url}: {e}")
        return None


def extract_msgids_from_listing(html: str) -> List[int]:
    """
    リストページからmsgidを抽出
    JPCanadaの実際のHTML構造に基づく:
    - No.5895 のような形式
    - topics.php?msgid=5895 のようなリンク
    """
    msgids = []
    try:
        soup = BeautifulSoup(html, 'lxml')
        
        # パターン1: topics.php?msgid=XXXX のリンクを検索
        links = soup.find_all('a', href=re.compile(r'topics\.php\?msgid=(\d+)'))
        for link in links:
            match = re.search(r'topics\.php\?msgid=(\d+)', link.get('href', ''))
            if match:
                msgid = int(match.group(1))
                msgids.append(msgid)
        
        # パターン2: No.XXXX のようなテキストから抽出
        # HTML内の "No.5895" のようなパターンを検索
        text_content = soup.get_text()
        no_pattern_matches = re.findall(r'No\.(\d+)', text_content)
        for match in no_pattern_matches:
            try:
                msgid = int(match)
                msgids.append(msgid)
            except ValueError:
                continue
        
        # パターン3: listing.php?bbs=X&msgid=XXXX のようなURLパラメータ
        url_params = re.findall(r'msgid=(\d+)', html)
        for param in url_params:
            try:
                msgid = int(param)
                msgids.append(msgid)
            except ValueError:
                continue
        
        # 重複を除去してソート（降順）
        msgids = sorted(set(msgids), reverse=True)
        
        logger.debug(f"Extracted {len(msgids)} msgids from listing page")
        
    except Exception as e:
        logger.error(f"Failed to extract msgids: {e}")
    
    return msgids


def crawl_bbs_listing(listing_url: str, last_msgid: int, client: httpx.Client) -> List[int]:
    """
    BBSリストページをクロールしてmsgidリストを取得
    JPCanadaの実際のURL構造: https://bbs.jpcanada.com/listing.php?bbs={bbs_id}&msgid={msgid}
    msgidパラメータを使用してページネーション（オプション）
    """
    logger.info(f"Crawling BBS listing: {listing_url}")
    
    # 最初のページを取得
    html = fetch_bbs_page(listing_url, client)
    if not html:
        raise RuntimeError("Failed to fetch listing page: %s" % listing_url)
    
    msgids = extract_msgids_from_listing(html)
    
    # last_msgidより大きいもののみフィルタ
    new_msgids = [msgid for msgid in msgids if msgid > last_msgid]
    
    logger.info(f"Found {len(new_msgids)} new posts (total: {len(msgids)})")
    
    # ページネーション: より古いmsgidで追加ページを取得（オプション）
    # 現在の実装では最初のページのみ処理
    # 必要に応じて、最小msgidを使用して追加ページを取得可能
    
    return new_msgids


def crawl_job_post(msgid: int, base_url: str, bbs_id: int, client: httpx.Client) -> Optional[Dict]:
    """
    個別のジョブ投稿をクロール
    JPCanadaの実際のURL構造: https://bbs.jpcanada.com/topics.php?bbs={bbs_id}&msgid={msgid}
    """
    # base_urlからドメインを抽出（listing.phpが含まれる場合）
    if 'listing.php' in base_url:
        base_url = base_url.split('listing.php')[0].rstrip('/')
    
    # ドメインが完全なURLでない場合、デフォルトを使用
    if not base_url.startswith('http'):
        base_url = 'https://bbs.jpcanada.com'
    
    # 実際のJPCanada URL構造に基づく
    url = f"{base_url}/topics.php?bbs={bbs_id}&msgid={msgid}"
    
    logger.info(f"Crawling job post: {url}")
    
    html = fetch_bbs_page(url, client)
    if not html:
        return None
    
    job_data = parse_job_post(html, url, msgid)
    
    # リクエスト間隔を確保
    time.sleep(REQUEST_INTERVAL)
    
    return job_data
