from sqlalchemy import Column, Integer, BigInteger, DateTime, func
from src.db.database import Base

class BlockHeader(Base):
    __tablename__ = "block_headers"

    id = Column(Integer, primary_key=True, index=True)
    block_number = Column(BigInteger, unique=True, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())