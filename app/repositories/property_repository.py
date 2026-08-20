from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.property import Property
from app.schemas.property import PropertyCreate, PropertyUpdate


from sqlalchemy import or_, func

class PropertyRepository:
    @staticmethod
    def get_all(
        db: Session,
        location: Optional[str] = None,
        category: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        units: Optional[str] = None,
    ) -> List[Property]:
        query = db.query(Property)
        
        if search:
            search_term = f"%{search.lower()}%"
            query = query.filter(
                or_(
                    func.lower(Property.property_name).like(search_term),
                    func.lower(Property.location).like(search_term),
                    func.lower(Property.property_id).like(search_term)
                )
            )

        if location:
            query = query.filter(Property.location == location)
            
        if category:
            query = query.filter(Property.category == category)
            
        if status:
            query = query.filter(Property.status == status)
            
        if units:
            if units == "1-5 Units":
                query = query.filter(Property.available_units >= 1, Property.available_units <= 5)
            elif units == "6-10 Units":
                query = query.filter(Property.available_units >= 6, Property.available_units <= 10)
            elif units == "11-20 Units":
                query = query.filter(Property.available_units >= 11, Property.available_units <= 20)
            elif units == "20+ Units":
                query = query.filter(Property.available_units > 20)
                
        # We order by ID descending to get latest properties first
        return query.order_by(Property.id.desc()).all()

    @staticmethod
    def get_by_id(db: Session, property_id: int) -> Optional[Property]:
        return db.query(Property).filter(Property.id == property_id).first()

    @staticmethod
    def get_by_property_id(db: Session, property_id: str) -> Optional[Property]:
        return db.query(Property).filter(Property.property_id == property_id).first()

    @staticmethod
    def create(db: Session, prop_data: PropertyCreate) -> Property:
        owner_name = prop_data.owner.name if prop_data.owner else None
        owner_phone = prop_data.owner.phone if prop_data.owner else None
        caretaker_name = prop_data.caretaker.name if prop_data.caretaker else None
        caretaker_phone = prop_data.caretaker.phone if prop_data.caretaker else None

        new_prop = Property(
            property_id=prop_data.propertyId,
            property_name=prop_data.name,
            description=prop_data.description,
            city=prop_data.city,
            state=prop_data.state,
            pincode=prop_data.pincode,
            deposit=prop_data.deposit,
            unit_type=prop_data.unitType,
            furnishing=prop_data.furnishing,
            other_specifications=prop_data.otherSpecifications,
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
            sales_kit=prop_data.salesKit,
            preferred_for=prop_data.preferredFor,
            listed_date=prop_data.listedDate,
            youtube_link=prop_data.youtubeLink,
        )
        db.add(new_prop)
        db.commit()
        db.refresh(new_prop)
        
        # Handle pricing
        if hasattr(prop_data, 'price') and prop_data.price:
            from app.models.property import PropertyPricing
            new_pricing = PropertyPricing(
                property_id=new_prop.id,
                starting_price=prop_data.price.starting,
                single_price=prop_data.price.single,
                double_price=prop_data.price.double,
                triple_price=prop_data.price.triple,
                private_price=prop_data.price.private,
            )
            db.add(new_pricing)
            db.commit()
            db.refresh(new_prop)

        return new_prop

    @staticmethod
    def update(db: Session, db_prop: Property, update_data: PropertyUpdate) -> Property:
        update_dict = update_data.model_dump(exclude_unset=True)
        
        # Define mapping from schema names to DB model attributes
        field_mapping = {
            "name": "property_name",
            "propertyId": "property_id",
            "description": "description",
            "city": "city",
            "state": "state",
            "pincode": "pincode",
            "deposit": "deposit",
            "unitType": "unit_type",
            "furnishing": "furnishing",
            "otherSpecifications": "other_specifications",
            "propertyType": "property_type",
            "category": "category",
            "location": "location",
            "address": "address",
            "status": "status",
            "images": "images",
            "availableUnits": "available_units",
            "totalUnits": "total_units",
            "amenities": "amenities",
            "pgOptions": "pg_options",
            "rentalOptions": "rental_options",
            "salesKit": "sales_kit",
            "preferredFor": "preferred_for",
            "listedDate": "listed_date",
            "youtubeLink": "youtube_link",
        }

        for schema_field, db_field in field_mapping.items():
            if schema_field in update_dict and update_dict[schema_field] is not None:
                setattr(db_prop, db_field, update_dict[schema_field])

        if update_data.owner:
            if update_data.owner.name is not None:
                db_prop.owner_name = update_data.owner.name
            if update_data.owner.phone is not None:
                db_prop.owner_phone = update_data.owner.phone
                
        if update_data.caretaker:
            if update_data.caretaker.name is not None:
                db_prop.caretaker_name = update_data.caretaker.name
            if update_data.caretaker.phone is not None:
                db_prop.caretaker_phone = update_data.caretaker.phone
                
        # Handle pricing update
        if hasattr(update_data, 'price') and update_data.price:
            from app.models.property import PropertyPricing
            pricing = db.query(PropertyPricing).filter(PropertyPricing.property_id == db_prop.id).first()
            if pricing:
                if update_data.price.starting is not None: pricing.starting_price = update_data.price.starting
                if update_data.price.single is not None: pricing.single_price = update_data.price.single
                if update_data.price.double is not None: pricing.double_price = update_data.price.double
                if update_data.price.triple is not None: pricing.triple_price = update_data.price.triple
                if update_data.price.private is not None: pricing.private_price = update_data.price.private
            else:
                new_pricing = PropertyPricing(
                    property_id=db_prop.id,
                    starting_price=update_data.price.starting,
                    single_price=update_data.price.single,
                    double_price=update_data.price.double,
                    triple_price=update_data.price.triple,
                    private_price=update_data.price.private,
                )
                db.add(new_pricing)

        db.commit()
        db.refresh(db_prop)
        return db_prop

    @staticmethod
    def delete(db: Session, db_prop: Property) -> None:
        db.delete(db_prop)
        db.commit()

    @staticmethod
    def seed_default_properties(db: Session) -> None:
        # Prevent seeding fake properties as per requirements
        pass
