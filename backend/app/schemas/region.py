from pydantic import BaseModel
from typing import List


class RegionResponse(BaseModel):
    id: int
    city: str
    bbs: int
    listing_url: str


class RegionListResponse(BaseModel):
    success: bool
    data: List[RegionResponse]
