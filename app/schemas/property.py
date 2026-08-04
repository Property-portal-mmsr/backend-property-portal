from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class OwnerInfo(BaseModel):
    name: str = "Rajesh Kumar"
    phone: str = "+91 9876543210"


class CaretakerInfo(BaseModel):
    name: str = "Arun Kumar"
    phone: str = "+91 9123456789"


class PropertyCreate(BaseModel):
    propertyId: Optional[str] = "PRP1001"
    name: str
    propertyType: str = "PG"
    category: str = "Co-Living"
    location: str = "Whitefield"
    address: str = "Whitefield, Bangalore"
    status: str = "Available"
    images: List[str] = []
    owner: Optional[OwnerInfo] = None
    caretaker: Optional[CaretakerInfo] = None
    availableUnits: int = 12
    totalUnits: int = 30
    amenities: List[str] = []
    pgOptions: List[Dict[str, Any]] = []
    rentalOptions: List[Dict[str, Any]] = []
    preferredFor: str = "Anyone"
    listedDate: str = "15 May 2026"
    youtubeLink: Optional[str] = ""


class PropertyUpdate(BaseModel):
    propertyId: Optional[str] = None
    name: Optional[str] = None
    propertyType: Optional[str] = None
    category: Optional[str] = None
    location: Optional[str] = None
    address: Optional[str] = None
    status: Optional[str] = None
    images: Optional[List[str]] = None
    owner: Optional[OwnerInfo] = None
    caretaker: Optional[CaretakerInfo] = None
    availableUnits: Optional[int] = None
    totalUnits: Optional[int] = None
    amenities: Optional[List[str]] = None
    pgOptions: Optional[List[Dict[str, Any]]] = None
    rentalOptions: Optional[List[Dict[str, Any]]] = None
    preferredFor: Optional[str] = None
    listedDate: Optional[str] = None
    youtubeLink: Optional[str] = None


class PropertyResponse(BaseModel):
    id: int
    propertyId: str
    name: str
    propertyType: str
    category: str
    location: str
    address: str
    status: str
    images: List[str]
    owner: OwnerInfo
    caretaker: CaretakerInfo
    availableUnits: int
    totalUnits: int
    amenities: List[str]
    pgOptions: List[Dict[str, Any]]
    rentalOptions: List[Dict[str, Any]]
    preferredFor: str
    listedDate: str
    youtubeLink: Optional[str] = ""

    @classmethod
    def from_db(cls, prop) -> "PropertyResponse":
        return cls(
            id=prop.id,
            propertyId=prop.property_id or f"PRP{prop.id + 1000}",
            name=prop.property_name or "",
            propertyType=prop.property_type or "PG",
            category=prop.category or "Co-Living",
            location=prop.location or "Whitefield",
            address=prop.address or "Whitefield, Bangalore",
            status=prop.status or "Available",
            images=prop.images if isinstance(prop.images, list) else [],
            owner=OwnerInfo(
                name=prop.owner_name or "Rajesh Kumar",
                phone=prop.owner_phone or "+91 9876543210",
            ),
            caretaker=CaretakerInfo(
                name=prop.caretaker_name or "Arun Kumar",
                phone=prop.caretaker_phone or "+91 9123456789",
            ),
            availableUnits=prop.available_units or 0,
            totalUnits=prop.total_units or 0,
            amenities=prop.amenities if isinstance(prop.amenities, list) else [],
            pgOptions=prop.pg_options if isinstance(prop.pg_options, list) else [],
            rentalOptions=(
                prop.rental_options if isinstance(prop.rental_options, list) else []
            ),
            preferredFor=prop.preferred_for or "Anyone",
            listedDate=prop.listed_date or "15 May 2026",
            youtubeLink=prop.youtube_link or "",
        )
