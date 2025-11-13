import httpx
import os
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

async def geocode_location(location_text: str, region_hint: Optional[str] = None) -> Tuple[Optional[float], Optional[float], float]:
    """
    住所テキストを座標に変換
    
    Args:
        location_text: 住所テキスト（例: "1884 Dayton st, Kelowna, BC" または "Yaletown Vancouver"）
        region_hint: 地域ヒント（例: "Vancouver", "Kelowna"）
    
    Returns:
        (lat, lng, confidence) タプル
        confidence: 0.0 ~ 1.0
    """
    if not location_text or not location_text.strip():
        # location_textが空の場合、region_hintを使用
        if region_hint:
            return get_region_center(region_hint)
        return None, None, 0.3
    
    nominatim_url = os.getenv("NOMINATIM_URL", "https://nominatim.openstreetmap.org")
    
    try:
        async with httpx.AsyncClient() as client:
            # クエリを構築（カナダに限定）
            query = location_text.strip()
            # region_hintがある場合、クエリに追加して精度を向上
            if region_hint and region_hint.lower() not in query.lower():
                query = f"{query}, {region_hint}, Canada"
            else:
                # カナダの州名が含まれていない場合、追加
                if not any(province in query for province in ['BC', 'AB', 'ON', 'QC', 'MB', 'SK', 'NB', 'NS', 'PE', 'NL', 'YT', 'NT', 'NU', 'Canada']):
                    query = f"{query}, Canada"
            
            # Nominatim API呼び出し（1秒に1回制限）
            params = {
                "q": query,
                "format": "json",
                "limit": 1,
                "addressdetails": 1,
                "countrycodes": "ca",  # カナダに限定
                "accept-language": "en"
            }
            
            headers = {
                "User-Agent": "JobMap/1.0 (contact@jobmap.ca)"
            }
            
            response = await client.get(
                f"{nominatim_url}/search",
                params=params,
                headers=headers,
                timeout=10.0
            )
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    result = data[0]
                    lat = float(result["lat"])
                    lng = float(result["lon"])
                    
                    # 精度に基づいてconfidenceを設定
                    importance = result.get("importance", 0)
                    if importance > 0.7:
                        confidence = 0.9
                    elif importance > 0.5:
                        confidence = 0.8
                    elif importance > 0.3:
                        confidence = 0.7
                    else:
                        confidence = 0.6
                    
                    logger.info(f"Geocoded '{location_text}' -> ({lat}, {lng}) with confidence {confidence}")
                    return lat, lng, confidence
            
            logger.warning(f"Geocoding returned no results for '{location_text}'")
            
            # 失敗時はregion_hintベースの座標を使用
            if region_hint:
                lat, lng, conf = get_region_center(region_hint)
                logger.info(f"Using region_hint fallback for '{region_hint}' -> ({lat}, {lng})")
                return lat, lng, conf
            
            return None, None, 0.3
            
    except Exception as e:
        logger.error(f"Geocoding failed for '{location_text}': {e}")
        # 失敗時はregion_hintベースの座標を使用
        if region_hint:
            lat, lng, conf = get_region_center(region_hint)
            logger.info(f"Using region_hint fallback after error for '{region_hint}' -> ({lat}, {lng})")
            return lat, lng, conf
        return None, None, 0.3

def get_region_center(region_hint: str) -> Tuple[Optional[float], Optional[float], float]:
    """地域ヒントから中心座標を取得"""
    region_centers = {
        "Vancouver": (49.2827, -123.1207),
        "Victoria": (48.4284, -123.3656),
        "Toronto": (43.6532, -79.3832),
        "Whistler": (50.1163, -122.9574),
        "Burnaby": (49.2488, -122.9805),
        "Surrey": (49.1913, -122.8490),
        "Richmond": (49.1666, -123.1364),
        "Kelowna": (49.8880, -119.4960),
        "Banff": (51.1784, -115.5708),
        "Canmore": (51.0888, -115.3581),
        "Calgary": (51.0447, -114.0719),
        "Edmonton": (53.5461, -113.4938),
        "Vernon": (50.2670, -119.2724),
        "Nelson": (49.4995, -117.2855),
        "Revelstoke": (50.9971, -118.1953),
        "Jasper": (52.8737, -118.0814),
        "Halifax": (44.6488, -63.5752),
        "Montreal": (45.5017, -73.5673),
        "Winnipeg": (49.8951, -97.1384),
        "Yellowknife": (62.4540, -114.3718),
    }
    
    region_hint_lower = region_hint.lower()
    for city, (lat, lng) in region_centers.items():
        if city.lower() in region_hint_lower:
            return lat, lng, 0.5
    
    # デフォルトはVancouver
    logger.warning(f"Unknown region_hint '{region_hint}', using Vancouver as default")
    return 49.2827, -123.1207, 0.5


