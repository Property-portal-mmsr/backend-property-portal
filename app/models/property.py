from sqlalchemy import Column, ForeignKey, Integer, String, JSON, Boolean, Numeric, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
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

    property_images = relationship("PropertyImage", back_populates="property", cascade="all, delete-orphan", order_by="PropertyImage.sort_order")
    property_amenities = relationship("PropertyAmenity", back_populates="property", cascade="all, delete-orphan")
    property_pricing = relationship("PropertyPricing", back_populates="property", uselist=False, cascade="all, delete-orphan")


class PropertyImage(Base):
    __tablename__ = "property_images"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True)
    image_url = Column(String(500), nullable=False)
    is_primary = Column(Boolean, default=False, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    content_type = Column(String(80), default="image/jpeg", nullable=False)
    file_size = Column(Integer, nullable=True)

    property = relationship("Property", back_populates="property_images")


class PropertyAmenity(Base):
    __tablename__ = "property_amenities"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=False)
    amenity_name = Column(String(255), nullable=False)

    property = relationship("Property", back_populates="property_amenities")


class PropertyPricing(Base):
    __tablename__ = "property_pricing"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, unique=True)
    private_price = Column(Numeric(10, 2), nullable=True)
    single_price = Column(Numeric(10, 2), nullable=True)
    double_price = Column(Numeric(10, 2), nullable=True)
    triple_price = Column(Numeric(10, 2), nullable=True)
    starting_price = Column(Numeric(10, 2), nullable=True)

    property = relationship("Property", back_populates="property_pricing")