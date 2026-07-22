from sqlalchemy import Column, Integer, String

from app.models.base import Base


class Owner(Base):
    __tablename__ = "owners"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(20))
    email = Column(String(100))
    address = Column(String(255))