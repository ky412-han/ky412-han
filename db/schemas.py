from pydantic import BaseModel
from typing import Optional, List

class FestivalSchema(BaseModel):
    id: int
    title: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    location: str
    image_url: str
    detail_link: str

    class Config:
        from_attributes = True

class PaginatedResponse(BaseModel):
    total_count: int
    page: int
    limit: int
    total_pages: int  # 추가
    data: List[FestivalSchema]

# 각 TourSpot의 상세 정보를 정의
class TourSpotDetail(BaseModel):
    id: int
    name: str
    address: str
    image_url: str
    description: str
    latitude: float = None
    longitude: float = None

# DayTrip의 데이터를 포함하는 스키마 정의
class TourSpotDayTrip(BaseModel):
    id: int
    location: str
    duration: str
    day: int
    description: str
    spots: List[TourSpotDetail]

class TourList(BaseModel):
    id: int
    location: str
    name : str
    address: str
    image_url: str
    description: str