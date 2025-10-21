from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Boolean, func
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class URL(Base):
    """
    SQLAlchemy model for 'urls' table:
    - Stores original URLs and their short codes
    - Tracks creation time and optional expiration
    - 'custom' indicates if the code was manually set
    - Defines relationship to Clicks
    """
    __tablename__ = "urls"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(16), unique=True, nullable=False)
    original_url = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    custom = Column(Boolean, default=False)

    clicks = relationship("Click", back_populates="url", cascade="all, delete")
    """ Relationship to Click table:
        - 'back_populates' allows bidirectional access
        - 'cascade="all, delete"' ensures clicks are removed if URL is deleted
    """


class Click(Base):
    """
    SQLAlchemy model for 'clicks' table:
    - Stores metadata of each URL access
    - Fields: url_id (FK), timestamp, IP, user_agent, referer
    - Relationship to URL for ORM convenience
    """
    __tablename__ = "clicks"

    id = Column(Integer, primary_key=True, index=True)
    url_id = Column(Integer, ForeignKey("urls.id", ondelete="CASCADE"))
    occurred_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    ip = Column(String(64), nullable=True)
    user_agent = Column(String(256), nullable=True)
    referer = Column(String(256), nullable=True)

    url = relationship("URL", back_populates="clicks")
    """ Relationship to URL table:
        - Allows ORM to access the parent URL object
        - 'back_populates' syncs relationship with URL.clicks
    """