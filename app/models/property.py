from sqlalchemy import Column, ForeignKey, Integer, String

from app.models.base import Base


class Property(Base):
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True, index=True)
    property_name = Column(String(255), nullable=False)
    location = Column(String(255))
    property_type = Column(String(100))
    owner_id = Column(Integer, ForeignKey("owners.id"))
    