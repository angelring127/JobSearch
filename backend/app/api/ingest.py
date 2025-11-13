from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from geoalchemy2 import functions
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from datetime import datetime
from app.database import get_db
from app.models import JobSource
from app.schemas.job import IngestRequest, IngestResponse, ApiResponse
from app.api.auth import verify_api_key
from app.services.geocoding import geocode_location

router = APIRouter(prefix="/internal", tags=["internal"])

@router.post("/ingest", response_model=ApiResponse, dependencies=[Depends(verify_api_key)])
async def ingest_job(
    request: IngestRequest,
    db: Session = Depends(get_db)
):
    """크롤러가 신규 데이터 삽입 요청"""
    try:
        # URL 중복 검사
        existing_job = db.query(JobSource).filter(
            JobSource.source_url == request.source_url
        ).first()
        
        # 지오코딩
        lat, lng, confidence = await geocode_location(
            request.location_text or "",
            request.region_hint
        )
        
        if lat is None or lng is None:
            return ApiResponse(
                success=False,
                error={
                    "code": "GEOCODING_FAILED",
                    "message": "Failed to geocode location",
                    "details": {
                        "location_text": request.location_text
                    }
                }
            )
        
        # PostGIS geometry 생성
        point = Point(lng, lat)
        geom = from_shape(point, srid=4326)
        
        if existing_job:
            # 업데이트
            existing_job.msgid = request.msgid
            existing_job.title = request.title
            existing_job.wage_min = request.wage_min
            existing_job.wage_max = request.wage_max
            existing_job.lat = lat
            existing_job.lng = lng
            existing_job.geom = geom
            existing_job.category = request.category
            existing_job.confidence = confidence
            existing_job.posted_at = request.posted_at
            existing_job.region_hint = request.region_hint
            
            db.commit()
            db.refresh(existing_job)
            
            return ApiResponse(
                success=True,
                data=IngestResponse(
                    id=existing_job.id,
                    msgid=existing_job.msgid,
                    source_url=existing_job.source_url,
                    lat=lat,
                    lng=lng,
                    confidence=confidence,
                    created=False
                ).model_dump()
            )
        else:
            # 신규 생성
            new_job = JobSource(
                msgid=request.msgid,
                source_url=request.source_url,
                region_hint=request.region_hint,
                title=request.title,
                wage_min=request.wage_min,
                wage_max=request.wage_max,
                lat=lat,
                lng=lng,
                geom=geom,
                category=request.category,
                confidence=confidence,
                posted_at=request.posted_at
            )
            
            db.add(new_job)
            db.commit()
            db.refresh(new_job)
            
            return ApiResponse(
                success=True,
                data=IngestResponse(
                    id=new_job.id,
                    msgid=new_job.msgid,
                    source_url=new_job.source_url,
                    lat=lat,
                    lng=lng,
                    confidence=confidence,
                    created=True
                ).model_dump()
            )
            
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


