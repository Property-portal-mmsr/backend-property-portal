from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.property import Property
from app.schemas.property import PropertyCreate, PropertyUpdate, PropertyResponse
from app.repositories.property_repository import PropertyRepository


class PropertyService:
    @staticmethod
    def get_all_properties(db: Session) -> List[PropertyResponse]:
        props = PropertyRepository.get_all(db)
        return [PropertyResponse.from_db(p) for p in props]

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
