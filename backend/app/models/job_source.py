from sqlalchemy import Column, Integer, BigInteger, String, Float, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.sql import func
from geoalchemy2 import Geography
from app.database import Base

class JobSource(Base):
    __tablename__ = "job_sources"
    
    id = Column(BigInteger, primary_key=True, index=True)
    msgid = Column(BigInteger, nullable=False)
    source_url = Column(Text, unique=True, nullable=False, index=True)
    region_hint = Column(String)
    title = Column(Text)
    wage_min = Column(Integer)
    wage_max = Column(Integer)
    lat = Column(Float)
    lng = Column(Float)
    geom = Column(Geography(geometry_type="Point", srid=4326), index=True)
    category = Column(String)
    confidence = Column(Float, default=0.8)
    posted_at = Column(TIMESTAMP)
    created_at = Column(TIMESTAMP, server_default=func.now())

