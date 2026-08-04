from sqlalchemy import Column, ForeignKey, Integer, String, JSON
from app.models.base import Base


class Property(Base):
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(String(50), unique=True, index=True, nullable=True)
    property_name = Column(String(255), nullable=True)
    property_type = Column(String(100), default="PG")
    category = Column(String(100), default="Co-Living")
    location = Column(String(255), default="Whitefield")
    address = Column(String(500), default="Whitefield, Bangalore")
    status = Column(String(50), default="Available")
    images = Column(JSON, default=list)
    owner_id = Column(Integer, ForeignKey("owners.id"), nullable=True)
    owner_name = Column(String(100), default="Rajesh Kumar")
    owner_phone = Column(String(50), default="+91 9876543210")
    caretaker_name = Column(String(100), default="Arun Kumar")
    caretaker_phone = Column(String(50), default="+91 9123456789")
    available_units = Column(Integer, default=12)
    total_units = Column(Integer, default=30)
    amenities = Column(JSON, default=list)
    pg_options = Column(JSON, default=list)
    rental_options = Column(JSON, default=list)
    preferred_for = Column(String(100), default="Anyone")
    listed_date = Column(String(50), default="15 May 2026")
    youtube_link = Column(String(500), nullable=True, default="")

    