from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.property import Property
from app.schemas.property import PropertyCreate, PropertyUpdate, PropertyResponse, PaginatedPropertyResponse
from app.repositories.property_repository import PropertyRepository
import math

class PropertyService:
    @staticmethod
    def get_all_properties(
        db: Session,
        location: Optional[str] = None,
        propertyType: Optional[str] = None,
        category: Optional[str] = None,
        furnishing: Optional[str] = None,
        status: Optional[str] = None,
        units: Optional[str] = None,
        priceRange: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> PaginatedPropertyResponse:
        # Fetch paginated and filtered data from database
        props, total = PropertyRepository.get_all(
            db, 
            location=location, 
            propertyType=propertyType,
            category=category, 
            furnishing=furnishing,
            status=status,
            units=units,
            priceRange=priceRange,
            search=search,
            skip=skip,
            limit=limit
        )
        
        pages = math.ceil(total / limit) if limit > 0 else 1
        page = (skip // limit) + 1 if limit > 0 else 1
            
        return PaginatedPropertyResponse(
            items=[PropertyResponse.from_db(p) for p in props],
            total=total,
            page=page,
            size=limit,
            pages=pages
        )

    @staticmethod
    def get_property_by_id(db: Session, prop_id: int) -> Optional[PropertyResponse]:
        prop = PropertyRepository.get_by_id(db, prop_id)
        if not prop:
            return None
        return PropertyResponse.from_db(prop)

    @staticmethod
    def create_property(db: Session, prop_data: PropertyCreate) -> PropertyResponse:
        new_prop = PropertyRepository.create(db, prop_data)
        return PropertyResponse.from_db(new_prop)

    @staticmethod
    def update_property(db: Session, prop_id: int, update_data: PropertyUpdate) -> Optional[PropertyResponse]:
        prop = PropertyRepository.get_by_id(db, prop_id)
        if not prop:
            return None
        updated_prop = PropertyRepository.update(db, prop, update_data)
        return PropertyResponse.from_db(updated_prop)

    @staticmethod
    def delete_property(db: Session, prop_id: int) -> bool:
        prop = PropertyRepository.get_by_id(db, prop_id)
        if not prop:
            return False
        PropertyRepository.delete(db, prop)
        return True
