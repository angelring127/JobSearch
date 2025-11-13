from sqlalchemy.orm import Session
from sqlalchemy import func, text
from geoalchemy2 import functions
from geoalchemy2.shape import to_shape
from typing import List, Optional
from app.models import JobSource
from app.schemas.job import JobSourceResponse

def get_jobs_by_viewport(
    db: Session,
    min_lng: float,
    min_lat: float,
    max_lng: float,
    max_lat: float,
    wage_min: Optional[int] = None,
    wage_max: Optional[int] = None,
    category: Optional[str] = None,
    limit: int = 100
) -> List[JobSourceResponse]:
    """뷰포트 내 일자리 조회"""
    # PostGIS Envelope 쿼리 (raw SQL 사용)
    base_sql = """
        SELECT id, msgid, title, wage_min, wage_max, lat, lng, 
               source_url, confidence, category, region_hint, posted_at,
               ST_X(geom::geometry) AS lng_from_geom,
               ST_Y(geom::geometry) AS lat_from_geom
        FROM job_sources
        WHERE geom && ST_MakeEnvelope(:min_lng, :min_lat, :max_lng, :max_lat, 4326)
    """
    
    params = {
        "min_lng": min_lng,
        "min_lat": min_lat,
        "max_lng": max_lng,
        "max_lat": max_lat
    }
    
    # 필터 조건 추가
    conditions = []
    if wage_min is not None:
        conditions.append("wage_min >= :wage_min")
        params["wage_min"] = wage_min
    if wage_max is not None:
        conditions.append("wage_max <= :wage_max")
        params["wage_max"] = wage_max
    if category:
        conditions.append("category = :category")
        params["category"] = category
    
    if conditions:
        base_sql += " AND " + " AND ".join(conditions)
    
    base_sql += " ORDER BY posted_at DESC LIMIT :limit"
    params["limit"] = limit
    
    sql = text(base_sql)
    results = db.execute(sql, params).fetchall()
    
    # 응답 형식으로 변환
    jobs = []
    for row in results:
        lat = row.lat_from_geom if row.lat_from_geom else row.lat
        lng = row.lng_from_geom if row.lng_from_geom else row.lng
        
        jobs.append(JobSourceResponse(
            id=row.id,
            msgid=row.msgid,
            title=row.title,
            wage_min=row.wage_min,
            wage_max=row.wage_max,
            lat=lat,
            lng=lng,
            source_url=row.source_url,
            confidence=row.confidence,
            category=row.category,
            region_hint=row.region_hint,
            posted_at=row.posted_at
        ))
    
    return jobs

def get_jobs_by_nearby(
    db: Session,
    lat: float,
    lng: float,
    radius_km: float,
    wage_min: Optional[int] = None,
    wage_max: Optional[int] = None,
    category: Optional[str] = None,
    limit: int = 100
) -> List[JobSourceResponse]:
    """반경 내 일자리 조회"""
    radius_m = radius_km * 1000  # kmをmに変換
    
    # PostGIS DWithin 쿼리 (raw SQL 사용)
    base_sql = """
        SELECT id, msgid, title, wage_min, wage_max, lat, lng,
               source_url, confidence, category, region_hint, posted_at,
               ST_X(geom::geometry) AS lng_from_geom,
               ST_Y(geom::geometry) AS lat_from_geom,
               ST_DistanceSphere(geom::geometry, ST_MakePoint(:lng, :lat)::geometry) / 1000.0 AS distance_km
        FROM job_sources
        WHERE ST_DWithin(geom::geography, ST_MakePoint(:lng, :lat)::geography, :radius_m)
    """
    
    params = {
        "lng": lng,
        "lat": lat,
        "radius_m": radius_m
    }
    
    # 필터 조건 추가
    conditions = []
    if wage_min is not None:
        conditions.append("wage_min >= :wage_min")
        params["wage_min"] = wage_min
    if wage_max is not None:
        conditions.append("wage_max <= :wage_max")
        params["wage_max"] = wage_max
    if category:
        conditions.append("category = :category")
        params["category"] = category
    
    if conditions:
        base_sql += " AND " + " AND ".join(conditions)
    
    base_sql += " ORDER BY distance_km ASC LIMIT :limit"
    params["limit"] = limit
    
    sql = text(base_sql)
    results = db.execute(sql, params).fetchall()
    
    # 응답 형식으로 변환
    jobs = []
    for row in results:
        lat_val = row.lat_from_geom if row.lat_from_geom else row.lat
        lng_val = row.lng_from_geom if row.lng_from_geom else row.lng
        
        jobs.append(JobSourceResponse(
            id=row.id,
            msgid=row.msgid,
            title=row.title,
            wage_min=row.wage_min,
            wage_max=row.wage_max,
            lat=lat_val,
            lng=lng_val,
            source_url=row.source_url,
            confidence=row.confidence,
            category=row.category,
            region_hint=row.region_hint,
            posted_at=row.posted_at,
            distance_km=row.distance_km
        ))
    
    return jobs

