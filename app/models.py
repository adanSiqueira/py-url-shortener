from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Boolean, func
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime
from .database import Base

class URL(Base):
    __tablename__ = "urls"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(16), unique=True, nullable=False)
    original_url = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    custom = Column(Boolean, default=False)

    clicks = relationship("Click", back_populates="url", cascade="all, delete")


class Click(Base):
    __tablename__ = "clicks"

    id = Column(Integer, primary_key=True, index=True)
    url_id = Column(Integer, ForeignKey("urls.id", ondelete="CASCADE"))
    occurred_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    ip = Column(String(64), nullable=True)
    user_agent = Column(String(256), nullable=True)
    referer = Column(String(256), nullable=True)

    url = relationship("URL", back_populates="clicks")
