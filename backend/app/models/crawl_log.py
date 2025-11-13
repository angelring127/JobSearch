from sqlalchemy import Column, Integer, BigInteger
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.sql import func
from app.database import Base

class CrawlLog(Base):
    __tablename__ = "crawl_log"
    
    id = Column(Integer, primary_key=True, index=True)
    bbs = Column(Integer, nullable=False, index=True)
    last_seen_msgid = Column(BigInteger)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())


