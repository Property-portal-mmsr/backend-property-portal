from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class OwnerInfo(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None


class CaretakerInfo(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None


class PriceInfo(BaseModel):
    starting: Optional[float] = None
    single: Optional[float] = None
    double: Optional[float] = None
    triple: Optional[float] = None
    private: Optional[float] = None


class PropertyCreate(BaseModel):
    propertyId: Optional[str] = None
    name: str
    description: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    deposit: Optional[float] = None
    unitType: Optional[str] = None
    furnishing: Optional[str] = None
    otherSpecifications: Optional[Dict[str, Any]] = None
    propertyType: Optional[str] = None
    category: Optional[str] = None
    location: Optional[str] = None
    address: Optional[str] = None
    status: Optional[str] = None
    images: List[str] = []
    owner: Optional[OwnerInfo] = None
    caretaker: Optional[CaretakerInfo] = None
    availableUnits: Optional[int] = None
    totalUnits: Optional[int] = None
    amenities: List[str] = []
    pgOptions: List[Dict[str, Any]] = []
    rentalOptions: List[Dict[str, Any]] = []
    salesKit: Optional[Dict[str, Any]] = None
    preferredFor: Optional[str] = None
    listedDate: Optional[str] = None
    youtubeLink: Optional[str] = ""
    price: Optional[PriceInfo] = None


class PropertyUpdate(BaseModel):
    propertyId: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    deposit: Optional[float] = None
    unitType: Optional[str] = None
    furnishing: Optional[str] = None
    otherSpecifications: Optional[Dict[str, Any]] = None
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
    salesKit: Optional[Dict[str, Any]] = None
    preferredFor: Optional[str] = None
    listedDate: Optional[str] = None
    youtubeLink: Optional[str] = None
    price: Optional[PriceInfo] = None


class PropertyResponse(BaseModel):
    id: int
    propertyId: str
    name: str
    description: Optional[str]
    city: Optional[str]
    state: Optional[str]
    pincode: Optional[str]
    deposit: Optional[float]
    unitType: Optional[str]
    furnishing: Optional[str]
    otherSpecifications: Optional[Dict[str, Any]]
    propertyType: Optional[str]
    category: Optional[str]
    location: Optional[str]
    address: Optional[str]
    status: Optional[str]
    price: Optional[PriceInfo] = None
    images: List[str]
    owner: Optional[OwnerInfo]
    caretaker: Optional[CaretakerInfo]
    availableUnits: Optional[int]
    totalUnits: Optional[int]
    amenities: List[str]
    pgOptions: List[Dict[str, Any]]
    rentalOptions: List[Dict[str, Any]]
    salesKit: Optional[Dict[str, Any]]
    preferredFor: Optional[str]
    listedDate: Optional[str]
    youtubeLink: Optional[str] = ""
    lastUpdated: Optional[str] = None

    @classmethod
    def from_db(cls, prop) -> "PropertyResponse":
        return cls(
            id=prop.id,
            propertyId=prop.property_id or f"PRP{prop.id + 1000}",
            name=prop.property_name or "",
            description=prop.description,
            city=prop.city,
            state=prop.state,
            pincode=prop.pincode,
            deposit=float(prop.deposit) if prop.deposit is not None else None,
            unitType=prop.unit_type,
            furnishing=prop.furnishing,
            otherSpecifications=prop.other_specifications if isinstance(prop.other_specifications, dict) else {},
            propertyType=prop.property_type,
            category=prop.category,
            location=prop.location,
            address=prop.address,
            status=prop.status,
            price=PriceInfo(
                starting=float(prop.property_pricing.starting_price) if prop.property_pricing and prop.property_pricing.starting_price is not None else None,
                single=float(prop.property_pricing.single_price) if prop.property_pricing and prop.property_pricing.single_price is not None else None,
                double=float(prop.property_pricing.double_price) if prop.property_pricing and prop.property_pricing.double_price is not None else None,
                triple=float(prop.property_pricing.triple_price) if prop.property_pricing and prop.property_pricing.triple_price is not None else None,
                private=float(prop.property_pricing.private_price) if prop.property_pricing and prop.property_pricing.private_price is not None else None,
            ) if prop.property_pricing else None,
            images=[img.image_url for img in prop.property_images] if getattr(prop, 'property_images', None) else (prop.images if isinstance(prop.images, list) else []),
            owner=OwnerInfo(
                name=prop.owner_name,
                phone=prop.owner_phone,
            ),
            caretaker=CaretakerInfo(
                name=prop.caretaker_name,
                phone=prop.caretaker_phone,
            ),
            availableUnits=prop.available_units,
            totalUnits=prop.total_units,
            amenities=[am.amenity_name for am in prop.property_amenities] if getattr(prop, 'property_amenities', None) else (prop.amenities if isinstance(prop.amenities, list) else []),
            pgOptions=prop.pg_options if isinstance(prop.pg_options, list) else [],
            rentalOptions=prop.rental_options if isinstance(prop.rental_options, list) else [],
            salesKit=prop.sales_kit if isinstance(prop.sales_kit, dict) else {},
            preferredFor=prop.preferred_for,
            listedDate=prop.listed_date,
            youtubeLink=prop.youtube_link or "",
            lastUpdated=prop.updated_at.strftime("%d %b %Y") if getattr(prop, 'updated_at', None) else None,
        )

class PaginatedPropertyResponse(BaseModel):
    items: List[PropertyResponse]
    total: int
    page: int
    size: int
    pages: int
