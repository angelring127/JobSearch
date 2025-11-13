from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.schemas.job import (
    ViewportQueryParams,
    NearbyQueryParams,
    JobSourceResponse,
    ApiResponse
)
from app.services.job_service import get_jobs_by_viewport, get_jobs_by_nearby

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

@router.get("/viewport", response_model=ApiResponse)
async def get_viewport_jobs(
    minLng: float = Query(..., description="경계 박스 최소 경도"),
    minLat: float = Query(..., description="경계 박스 최소 위도"),
    maxLng: float = Query(..., description="경계 박스 최대 경도"),
    maxLat: float = Query(..., description="경계 박스 최대 위도"),
    zoom: Optional[int] = Query(None, description="현재 줌 레벨"),
    wageMin: Optional[int] = Query(None, ge=0, description="최소 시급 필터"),
    wageMax: Optional[int] = Query(None, ge=0, description="최대 시급 필터"),
    category: Optional[str] = Query(None, description="직종 카테고리 필터"),
    limit: Optional[int] = Query(100, ge=1, le=500, description="반환 개수 제한"),
    db: Session = Depends(get_db)
):
    """뷰포트 내 일자리 조회"""
    try:
        # 파라미터 검증
        if minLng >= maxLng or minLat >= maxLat:
            raise HTTPException(
                status_code=400,
                detail="Invalid bounding box parameters"
            )
        
        jobs = get_jobs_by_viewport(
            db=db,
            min_lng=minLng,
            min_lat=minLat,
            max_lng=maxLng,
            max_lat=maxLat,
            wage_min=wageMin,
            wage_max=wageMax,
            category=category,
            limit=limit
        )
        
        return ApiResponse(
            success=True,
            data=[job.model_dump() for job in jobs],
            meta={
                "count": len(jobs),
                "total": len(jobs)
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@router.get("/nearby", response_model=ApiResponse)
async def get_nearby_jobs(
    lat: float = Query(..., ge=-90, le=90, description="중심 위도"),
    lng: float = Query(..., ge=-180, le=180, description="중심 경도"),
    radius: float = Query(..., ge=0.1, le=50, description="반경 (km 단위)"),
    wageMin: Optional[int] = Query(None, ge=0, description="최소 시급 필터"),
    wageMax: Optional[int] = Query(None, ge=0, description="최대 시급 필터"),
    category: Optional[str] = Query(None, description="직종 카테고리 필터"),
    limit: Optional[int] = Query(100, ge=1, le=500, description="반환 개수 제한"),
    db: Session = Depends(get_db)
):
    """반경 내 일자리 조회"""
    try:
        jobs = get_jobs_by_nearby(
            db=db,
            lat=lat,
            lng=lng,
            radius_km=radius,
            wage_min=wageMin,
            wage_max=wageMax,
            category=category,
            limit=limit
        )
        
        return ApiResponse(
            success=True,
            data=[job.model_dump() for job in jobs],
            meta={
                "count": len(jobs),
                "total": len(jobs),
                "center": {
                    "lat": lat,
                    "lng": lng
                },
                "radius_km": radius
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@router.get("/clusters", response_model=ApiResponse)
async def get_clusters(
    minLng: float = Query(..., description="경계 박스 최소 경도"),
    minLat: float = Query(..., description="경계 박스 최소 위도"),
    maxLng: float = Query(..., description="경계 박스 최대 경도"),
    maxLat: float = Query(..., description="경계 박스 최대 위도"),
    zoom: int = Query(..., ge=0, le=20, description="현재 줌 레벨"),
    wageMin: Optional[int] = Query(None, ge=0),
    wageMax: Optional[int] = Query(None, ge=0),
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """클러스터링 데이터 반환 (향후 구현)"""
    # TODO: PostGIS ST_ClusterWithin 구현
    return ApiResponse(
        success=True,
        data=[],
        meta={
            "zoom": zoom,
            "cluster_count": 0
        }
    )


