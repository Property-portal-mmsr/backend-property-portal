from sqlalchemy.orm import Session, selectinload
from typing import List, Optional, Tuple
from app.models.property import Property, PropertyPricing
from app.schemas.property import PropertyCreate, PropertyUpdate


from sqlalchemy import or_, func, cast, String

class PropertyRepository:
    @staticmethod
    def get_all(
        db: Session,
        location: Optional[str] = None,
        propertyType: Optional[str] = None,
        category: Optional[str] = None,
        categories: Optional[List[str]] = None,
        sharingType: Optional[str] = None,
        unitType: Optional[str] = None,
        balcony: Optional[str] = None,
        furnishing: Optional[str] = None,
        status: Optional[str] = None,
        units: Optional[str] = None,
        priceRange: Optional[str] = None,
        minPrice: Optional[float] = None,
        maxPrice: Optional[float] = None,
        search: Optional[str] = None,
        sort: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Property], int]:
        query = db.query(Property)
        
        # 1. Search
        if search and search.strip():
            term = f"%{search.strip().lower()}%"
            query = query.filter(
                or_(
                    func.lower(Property.property_name).like(term),
                    func.lower(Property.property_id).like(term),
                    func.lower(Property.location).like(term),
                    func.lower(Property.city).like(term),
                    func.lower(Property.address).like(term),
                    func.lower(Property.owner_name).like(term),
                )
            )

        # 2. Location
        if location and location.strip():
            loc_term = f"%{location.strip().lower()}%"
            query = query.filter(
                or_(
                    func.lower(Property.location).like(loc_term),
                    func.lower(Property.city).like(loc_term),
                    func.lower(Property.state).like(loc_term),
                    func.lower(Property.address).like(loc_term),
                )
            )

        # 3. Categories (Multi-category OR logic)
        cat_list = []
        if categories:
            if isinstance(categories, str):
                cat_list = [c.strip() for c in categories.split(",") if c.strip()]
            elif isinstance(categories, list):
                for item in categories:
                    if isinstance(item, str):
                        cat_list.extend([c.strip() for c in item.split(",") if c.strip()])
                    elif item:
                        cat_list.append(str(item).strip())
        elif category and category.strip():
            cat_list = [c.strip() for c in category.split(",") if c.strip()]

        if cat_list:
            cat_filters = []
            for cat in cat_list:
                cat_filters.append(Property.category == cat)
                cat_filters.append(cast(Property.categories, String).like(f'%"category": "{cat}"%'))
                cat_filters.append(cast(Property.categories, String).like(f'%"{cat}"%'))
            query = query.filter(or_(*cat_filters))

        # 4. Status
        if status and status.strip() and status != "All Status":
            query = query.filter(func.lower(Property.status) == status.strip().lower())

        # 5. PG Sharing Type
        if sharingType and sharingType.strip():
            st = sharingType.strip()
            query = query.filter(
                or_(
                    cast(Property.pg_options, String).like(f'%"sharing": "{st}"%'),
                    cast(Property.pg_options, String).like(f"%'sharing': '{st}'%")
                )
            )

        # 6. Rental Unit Type
        target_unit_type = unitType or propertyType
        if target_unit_type and target_unit_type.strip():
            ut = target_unit_type.strip()
            query = query.filter(
                or_(
                    Property.property_type == ut,
                    cast(Property.property_type, String).like(f'%{ut}%'),
                    cast(Property.rental_options, String).like(f'%"unitType": "{ut}"%'),
                    cast(Property.rental_options, String).like(f'%"type": "{ut}"%'),
                    cast(Property.rental_options, String).like(f"%'unitType': '{ut}'%"),
                    cast(Property.rental_options, String).like(f"%'type': '{ut}'%")
                )
            )

        # 7. Balcony
        if balcony and balcony.strip():
            b = balcony.strip()
            query = query.filter(
                or_(
                    cast(Property.rental_options, String).like(f'%"balcony": "{b}"%'),
                    cast(Property.rental_options, String).like(f"%'balcony': '{b}'%")
                )
            )

        # 8. Furnishing
        if furnishing and furnishing.strip():
            f = furnishing.strip()
            query = query.filter(
                or_(
                    Property.furnishing == f,
                    cast(Property.pg_options, String).like(f'%"furnishing": "{f}"%'),
                    cast(Property.pg_options, String).like(f"%'furnishing': '{f}'%"),
                    cast(Property.rental_options, String).like(f'%"furnishing": "{f}"%'),
                    cast(Property.rental_options, String).like(f"%'furnishing': '{f}'%")
                )
            )

        # 9. Price Filtering & Pagination Execution
        low_price = minPrice
        high_price = maxPrice
        if priceRange:
            if priceRange == "Under ₹10,000" or priceRange == "₹5,000 - ₹10,000":
                low_price, high_price = 0, 10000
            elif priceRange == "₹10,000 - ₹20,000" or priceRange == "₹10,001 - ₹15,000" or priceRange == "₹15,001 - ₹20,000":
                low_price, high_price = 10000, 20000
            elif priceRange == "₹20,000 - ₹35,000" or priceRange == "₹20,001 - ₹30,000":
                low_price, high_price = 20000, 35000
            elif priceRange == "₹35,000+" or priceRange == "₹30,001+":
                low_price, high_price = 35000, 99999999

        if low_price is not None or high_price is not None:
            low = low_price if low_price is not None else 0
            high = high_price if high_price is not None else 999999999.0

            all_candidates = query.options(
                selectinload(Property.property_pricing),
                selectinload(Property.property_images),
                selectinload(Property.property_amenities)
            ).distinct().all()

            def matches_price_range(p: Property) -> bool:
                if p.property_pricing:
                    sp = p.property_pricing.starting_price or p.property_pricing.single_price
                    if sp is not None and low <= float(sp) <= high:
                        return True

                if p.pg_options:
                    for v in p.pg_options:
                        rent = v.get("rent") if v.get("rent") is not None else v.get("price")
                        if rent is not None:
                            try:
                                if low <= float(rent) <= high:
                                    return True
                            except (ValueError, TypeError):
                                pass

                if p.rental_options:
                    for v in p.rental_options:
                        rent = v.get("rent") if v.get("rent") is not None else v.get("price")
                        if rent is not None:
                            try:
                                if low <= float(rent) <= high:
                                    return True
                            except (ValueError, TypeError):
                                pass

                return False

            matching_props = [p for p in all_candidates if matches_price_range(p)]

            if sort == "price-low":
                matching_props.sort(key=lambda p: (p.property_pricing.starting_price if p.property_pricing and p.property_pricing.starting_price is not None else 99999999))
            elif sort == "price-high":
                matching_props.sort(key=lambda p: (p.property_pricing.starting_price if p.property_pricing and p.property_pricing.starting_price is not None else 0), reverse=True)
            elif sort == "name":
                matching_props.sort(key=lambda p: (p.property_name or "").lower())
            else:
                matching_props.sort(key=lambda p: p.id, reverse=True)

            total = len(matching_props)
            items = matching_props[skip:skip+limit]
            return items, total

        total = query.distinct().count()

        # 10. Default Query Execution & Sorting
        items_all = query.options(
            selectinload(Property.property_pricing),
            selectinload(Property.property_images),
            selectinload(Property.property_amenities)
        ).distinct().all()

        def has_valid_images(p: Property) -> bool:
            if getattr(p, 'property_images', None) and len([img for img in p.property_images if getattr(img, 'image_url', None) and not getattr(img, 'is_deleted', False)]) > 0:
                return True
            if isinstance(p.images, list) and len([u for u in p.images if u]) > 0:
                return True
            return False

        if sort == "price-low":
            items_all.sort(key=lambda p: (0 if has_valid_images(p) else 1, p.property_pricing.starting_price if p.property_pricing and p.property_pricing.starting_price is not None else 99999999))
        elif sort == "price-high":
            items_all.sort(key=lambda p: (0 if has_valid_images(p) else 1, -(p.property_pricing.starting_price if p.property_pricing and p.property_pricing.starting_price is not None else 0)))
        elif sort == "name":
            items_all.sort(key=lambda p: (0 if has_valid_images(p) else 1, (p.property_name or "").lower()))
        else:
            items_all.sort(key=lambda p: (0 if has_valid_images(p) else 1, -p.id))

        items = items_all[skip:skip+limit]
        return items, total

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
        onboarded_by_name = prop_data.onboardedBy.name if hasattr(prop_data, 'onboardedBy') and prop_data.onboardedBy else None
        onboarded_by_phone = prop_data.onboardedBy.phone if hasattr(prop_data, 'onboardedBy') and prop_data.onboardedBy else None

        cats = prop_data.categories if (hasattr(prop_data, 'categories') and prop_data.categories) else ([prop_data.category] if prop_data.category else [])
        primary_cat = cats[0] if cats else prop_data.category

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
            category=primary_cat,
            categories=cats,
            location=prop_data.location,
            address=prop_data.address,
            status=prop_data.status,
            images=prop_data.images,
            owner_name=owner_name,
            owner_phone=owner_phone,
            caretaker_name=caretaker_name,
            caretaker_phone=caretaker_phone,
            onboarded_by_name=onboarded_by_name,
            onboarded_by_phone=onboarded_by_phone,
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
            "categories": "categories",
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
                
        if hasattr(update_data, 'onboardedBy') and update_data.onboardedBy:
            if update_data.onboardedBy.name is not None:
                db_prop.onboarded_by_name = update_data.onboardedBy.name
            if update_data.onboardedBy.phone is not None:
                db_prop.onboarded_by_phone = update_data.onboardedBy.phone
                
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

    @staticmethod
    def get_unique_locations(db: Session) -> List[str]:
        # Get all distinct non-null locations
        locations = db.query(Property.location).filter(Property.location != None).filter(Property.location != "").distinct().all()
        return sorted([loc[0] for loc in locations])
