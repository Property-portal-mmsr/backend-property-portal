from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.property import Property
from app.schemas.property import PropertyCreate, PropertyUpdate


class PropertyRepository:
    @staticmethod
    def get_all(db: Session) -> List[Property]:
        return db.query(Property).all()

    @staticmethod
    def get_by_id(db: Session, property_id: int) -> Optional[Property]:
        return db.query(Property).filter(Property.id == property_id).first()

    @staticmethod
    def get_by_property_id(db: Session, property_id: str) -> Optional[Property]:
        return db.query(Property).filter(Property.property_id == property_id).first()

    @staticmethod
    def create(db: Session, prop_data: PropertyCreate) -> Property:
        owner_name = prop_data.owner.name if prop_data.owner else "Rajesh Kumar"
        owner_phone = prop_data.owner.phone if prop_data.owner else "+91 9876543210"
        caretaker_name = prop_data.caretaker.name if prop_data.caretaker else "Arun Kumar"
        caretaker_phone = prop_data.caretaker.phone if prop_data.caretaker else "+91 9123456789"

        new_prop = Property(
            property_id=prop_data.propertyId or "PRP1001",
            property_name=prop_data.name,
            property_type=prop_data.propertyType,
            category=prop_data.category,
            location=prop_data.location,
            address=prop_data.address,
            status=prop_data.status,
            images=prop_data.images,
            owner_name=owner_name,
            owner_phone=owner_phone,
            caretaker_name=caretaker_name,
            caretaker_phone=caretaker_phone,
            available_units=prop_data.availableUnits,
            total_units=prop_data.totalUnits,
            amenities=prop_data.amenities,
            pg_options=prop_data.pgOptions,
            rental_options=prop_data.rentalOptions,
            preferred_for=prop_data.preferredFor,
            listed_date=prop_data.listedDate,
            youtube_link=prop_data.youtubeLink or "",
        )
        db.add(new_prop)
        db.commit()
        db.refresh(new_prop)
        return new_prop

    @staticmethod
    def update(db: Session, db_prop: Property, update_data: PropertyUpdate) -> Property:
        update_dict = update_data.model_dump(exclude_unset=True)
        if "name" in update_dict and update_dict["name"] is not None:
            db_prop.property_name = update_dict["name"]
        if "propertyId" in update_dict and update_dict["propertyId"]:
            db_prop.property_id = update_dict["propertyId"]
        if "propertyType" in update_dict and update_dict["propertyType"] is not None:
            db_prop.property_type = update_dict["propertyType"]
        if "category" in update_dict and update_dict["category"] is not None:
            db_prop.category = update_dict["category"]
        if "location" in update_dict and update_dict["location"] is not None:
            db_prop.location = update_dict["location"]
        if "address" in update_dict and update_dict["address"] is not None:
            db_prop.address = update_dict["address"]
        if "status" in update_dict and update_dict["status"] is not None:
            db_prop.status = update_dict["status"]
        if "images" in update_dict and update_dict["images"] is not None:
            db_prop.images = update_dict["images"]
        if "availableUnits" in update_dict and update_dict["availableUnits"] is not None:
            db_prop.available_units = update_dict["availableUnits"]
        if "totalUnits" in update_dict and update_dict["totalUnits"] is not None:
            db_prop.total_units = update_dict["totalUnits"]
        if "amenities" in update_dict and update_dict["amenities"] is not None:
            db_prop.amenities = update_dict["amenities"]
        if "pgOptions" in update_dict and update_dict["pgOptions"] is not None:
            db_prop.pg_options = update_dict["pgOptions"]
        if "rentalOptions" in update_dict and update_dict["rentalOptions"] is not None:
            db_prop.rental_options = update_dict["rentalOptions"]
        if "preferredFor" in update_dict and update_dict["preferredFor"] is not None:
            db_prop.preferred_for = update_dict["preferredFor"]
        if "listedDate" in update_dict and update_dict["listedDate"] is not None:
            db_prop.listed_date = update_dict["listedDate"]
        if "youtubeLink" in update_dict and update_dict["youtubeLink"] is not None:
            db_prop.youtube_link = update_dict["youtubeLink"]
        if update_data.owner:
            db_prop.owner_name = update_data.owner.name
            db_prop.owner_phone = update_data.owner.phone
        if update_data.caretaker:
            db_prop.caretaker_name = update_data.caretaker.name
            db_prop.caretaker_phone = update_data.caretaker.phone

        db.commit()
        db.refresh(db_prop)
        return db_prop

    @staticmethod
    def delete(db: Session, db_prop: Property) -> None:
        db.delete(db_prop)
        db.commit()

    @staticmethod
    def seed_default_properties(db: Session) -> None:
        count = db.query(Property).count()
        if count > 0:
            return

        defaults = [
            {
                "property_id": "PRP1001",
                "property_name": "Green Residency",
                "property_type": "PG",
                "category": "Co-Living",
                "location": "Whitefield",
                "address": "Whitefield, Bangalore",
                "status": "Available",
                "images": ["/properties/property1.jpeg"],
                "owner_name": "Rajesh Kumar",
                "owner_phone": "+91 9876543210",
                "caretaker_name": "Arun Kumar",
                "caretaker_phone": "+91 9123456789",
                "available_units": 12,
                "total_units": 30,
                "amenities": ["WiFi", "Power Backup", "Lift", "Parking"],
                "pg_options": [
                    {"sharing": "Single", "furnishing": "Fully Furnished", "price": 18000},
                    {"sharing": "Double", "furnishing": "Semi Furnished", "price": 12000},
                    {"sharing": "Triple", "furnishing": "Fully Furnished", "price": 9000},
                ],
                "rental_options": [
                    {"type": "1 RK", "balcony": False, "furnishing": "Semi Furnished", "price": 15000},
                    {"type": "1 BHK", "balcony": True, "furnishing": "Fully Furnished", "price": 28000},
                    {"type": "2 BHK", "balcony": True, "furnishing": "Semi Furnished", "price": 38000},
                ],
                "preferred_for": "Anyone",
                "listed_date": "15 May 2026",
                "youtube_link": "",
            },
            {
                "property_id": "PRP1002",
                "property_name": "Vip Residency",
                "property_type": "PG",
                "category": "Co-Living",
                "location": "Whitefield",
                "address": "Whitefield, Bangalore",
                "status": "Available",
                "images": ["/properties/property2.jpeg"],
                "owner_name": "Rajesh Kumar",
                "owner_phone": "+91 9876543210",
                "caretaker_name": "Arun Kumar",
                "caretaker_phone": "+91 9123456789",
                "available_units": 12,
                "total_units": 30,
                "amenities": ["WiFi", "Power Backup", "Lift", "Parking"],
                "pg_options": [
                    {"sharing": "Single", "furnishing": "Fully Furnished", "price": 18000},
                    {"sharing": "Double", "furnishing": "Semi Furnished", "price": 12000},
                    {"sharing": "Triple", "furnishing": "Fully Furnished", "price": 9000},
                ],
                "rental_options": [
                    {"type": "1 RK", "balcony": False, "furnishing": "Semi Furnished", "price": 15000},
                    {"type": "1 BHK", "balcony": True, "furnishing": "Fully Furnished", "price": 28000},
                    {"type": "2 BHK", "balcony": True, "furnishing": "Semi Furnished", "price": 38000},
                ],
                "preferred_for": "Anyone",
                "listed_date": "15 May 2026",
                "youtube_link": "",
            },
        ]

        for item in defaults:
            prop = Property(**item)
            db.add(prop)
        db.commit()
