from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.region import Region
from app.schemas.region import RegionResponse, RegionListResponse
from app.api.auth import verify_api_key

router = APIRouter(prefix="/internal/regions", tags=["regions"], dependencies=[Depends(verify_api_key)])


@router.get("", response_model=RegionListResponse)
async def list_regions(db: Session = Depends(get_db)):
    try:
        regions: List[Region] = db.query(Region).order_by(Region.id).all()
        data = [
            RegionResponse(
                id=region.id,
                city=region.city,
                bbs=region.bbs,
                listing_url=region.listing_url
            )
            for region in regions
        ]
        return RegionListResponse(success=True, data=data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load regions: {exc}"
        )
