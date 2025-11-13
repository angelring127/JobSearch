from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime

class JobSourceResponse(BaseModel):
    id: int
    msgid: int
    title: Optional[str] = None
    wage_min: Optional[int] = None
    wage_max: Optional[int] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    source_url: str
    confidence: float
    category: Optional[str] = None
    region_hint: Optional[str] = None
    posted_at: Optional[datetime] = None
    distance_km: Optional[float] = None

    class Config:
        from_attributes = True

class ViewportQueryParams(BaseModel):
    minLng: float = Field(..., description="경계 박스 최소 경도")
    minLat: float = Field(..., description="경계 박스 최소 위도")
    maxLng: float = Field(..., description="경계 박스 최대 경도")
    maxLat: float = Field(..., description="경계 박스 최대 위도")
    zoom: Optional[int] = Field(None, description="현재 줌 레벨")
    wageMin: Optional[int] = Field(None, ge=0, description="최소 시급 필터")
    wageMax: Optional[int] = Field(None, ge=0, description="최대 시급 필터")
    category: Optional[str] = Field(None, description="직종 카테고리 필터")
    limit: Optional[int] = Field(100, ge=1, le=500, description="반환 개수 제한")

class NearbyQueryParams(BaseModel):
    lat: float = Field(..., ge=-90, le=90, description="중심 위도")
    lng: float = Field(..., ge=-180, le=180, description="중심 경도")
    radius: float = Field(..., ge=0.1, le=50, description="반경 (km 단위)")
    wageMin: Optional[int] = Field(None, ge=0, description="최소 시급 필터")
    wageMax: Optional[int] = Field(None, ge=0, description="최대 시급 필터")
    category: Optional[str] = Field(None, description="직종 카테고리 필터")
    limit: Optional[int] = Field(100, ge=1, le=500, description="반환 개수 제한")

class IngestRequest(BaseModel):
    source_url: str
    msgid: int
    region_hint: Optional[str] = None
    title: Optional[str] = None
    wage_min: Optional[int] = None
    wage_max: Optional[int] = None
    location_text: Optional[str] = None
    category: Optional[str] = None
    posted_at: Optional[datetime] = None

class IngestResponse(BaseModel):
    id: int
    msgid: int
    source_url: str
    lat: Optional[float] = None
    lng: Optional[float] = None
    confidence: float
    created: bool

class ApiResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    meta: Optional[dict] = None
    error: Optional[dict] = None


