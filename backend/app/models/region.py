from sqlalchemy import Column, Integer, String, Text
from geoalchemy2 import Geography
from app.database import Base

class Region(Base):
    __tablename__ = "regions"
    
    id = Column(Integer, primary_key=True, index=True)
    city = Column(String, nullable=False)
    bbs = Column(Integer, nullable=False)
    listing_url = Column(Text, nullable=False)
    center = Column(Geography(geometry_type="Point", srid=4326), nullable=False)


