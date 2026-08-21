from fastapi import HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.property import Property
from app.schemas.property import PropertyCreate, PropertyUpdate, PropertyResponse, PaginatedPropertyResponse
from app.repositories.property_repository import PropertyRepository
import math

def validate_and_normalize_property_variants(pg_options, rental_options):
    normalized_pg = []
    seen_pg = set()
    if pg_options:
        for idx, variant in enumerate(pg_options):
            sharing = variant.get("sharing") or f"Variant {idx+1}"
            
            # Rent check
            rent = variant.get("rent")
            if rent is None or rent == "":
                rent = variant.get("price")
            if rent is None or rent == "" or float(rent) <= 0:
                raise HTTPException(
                    status_code=422, 
                    detail=f"PG variant '{sharing}' requires a valid rent > 0."
                )

            # Deposit check - deposit MUST NOT BE NULL / NONE / EMPTY
            deposit = variant.get("deposit")
            if deposit is None or deposit == "":
                raise HTTPException(
                    status_code=422, 
                    detail=f"PG variant '{sharing}' requires a valid security deposit."
                )
            try:
                dep_val = float(deposit)
                if dep_val < 0:
                    raise HTTPException(status_code=422, detail=f"PG variant '{sharing}' deposit cannot be negative.")
            except (ValueError, TypeError):
                raise HTTPException(status_code=422, detail=f"PG variant '{sharing}' deposit must be a valid number.")

            # Maintenance check - OPTIONAL (null, empty, omitted allowed)
            maint = variant.get("maintenance")
            if maint is None or maint == "":
                maint_val = 0.0
            else:
                try:
                    maint_val = float(maint)
                except (ValueError, TypeError):
                    maint_val = 0.0

            # Deduplication
            if sharing in seen_pg:
                continue
            seen_pg.add(sharing)

            norm_var = dict(variant)
            norm_var["rent"] = float(rent)
            norm_var["deposit"] = float(deposit)
            norm_var["maintenance"] = maint_val
            normalized_pg.append(norm_var)

    normalized_rental = []
    seen_rental = set()
    if rental_options:
        for idx, variant in enumerate(rental_options):
            unit_type = variant.get("unitType") or variant.get("type") or f"Unit {idx+1}"
            balcony = variant.get("balcony") or "Standard"
            furnishing = variant.get("furnishing") or "Standard"
            identity = f"{unit_type} | {balcony} | {furnishing}".lower().strip()

            # Rent check
            rent = variant.get("rent")
            if rent is None or rent == "":
                rent = variant.get("price")
            if rent is None or rent == "" or float(rent) <= 0:
                raise HTTPException(
                    status_code=422, 
                    detail=f"Rental variant '{unit_type} - {balcony} - {furnishing}' requires a valid rent > 0."
                )

            # Deposit check - deposit MUST NOT BE NULL / NONE / EMPTY
            deposit = variant.get("deposit")
            if deposit is None or deposit == "":
                raise HTTPException(
                    status_code=422, 
                    detail=f"Rental variant '{unit_type} - {balcony} - {furnishing}' requires a valid security deposit."
                )
            try:
                dep_val = float(deposit)
                if dep_val < 0:
                    raise HTTPException(status_code=422, detail=f"Rental variant deposit cannot be negative.")
            except (ValueError, TypeError):
                raise HTTPException(status_code=422, detail=f"Rental variant deposit must be a valid number.")

            # Maintenance check - OPTIONAL (null, empty, omitted allowed)
            maint = variant.get("maintenance")
            if maint is None or maint == "":
                maint_val = 0.0
            else:
                try:
                    maint_val = float(maint)
                except (ValueError, TypeError):
                    maint_val = 0.0

            # Deduplication
            if identity in seen_rental:
                continue
            seen_rental.add(identity)

            norm_var = dict(variant)
            norm_var["rent"] = float(rent)
            norm_var["deposit"] = float(deposit)
            norm_var["maintenance"] = maint_val
            normalized_rental.append(norm_var)

    return normalized_pg, normalized_rental


class PropertyService:
    @staticmethod
    def get_all_properties(
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
        limit: int = 100
    ) -> PaginatedPropertyResponse:
        props, total = PropertyRepository.get_all(
            db, 
            location=location, 
            propertyType=propertyType,
            category=category, 
            categories=categories,
            sharingType=sharingType,
            unitType=unitType,
            balcony=balcony,
            furnishing=furnishing,
            status=status,
            units=units,
            priceRange=priceRange,
            minPrice=minPrice,
            maxPrice=maxPrice,
            search=search,
            sort=sort,
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
        norm_pg, norm_rental = validate_and_normalize_property_variants(
            prop_data.pgOptions, prop_data.rentalOptions
        )
        prop_data.pgOptions = norm_pg
        prop_data.rentalOptions = norm_rental
        new_prop = PropertyRepository.create(db, prop_data)
        return PropertyResponse.from_db(new_prop)

    @staticmethod
    def update_property(db: Session, prop_id: int, update_data: PropertyUpdate) -> Optional[PropertyResponse]:
        prop = PropertyRepository.get_by_id(db, prop_id)
        if not prop:
            return None

        if update_data.pgOptions is not None or update_data.rentalOptions is not None:
            pg_opts = update_data.pgOptions if update_data.pgOptions is not None else (prop.pg_options or [])
            rental_opts = update_data.rentalOptions if update_data.rentalOptions is not None else (prop.rental_options or [])
            norm_pg, norm_rental = validate_and_normalize_property_variants(pg_opts, rental_opts)
            if update_data.pgOptions is not None:
                update_data.pgOptions = norm_pg
            if update_data.rentalOptions is not None:
                update_data.rentalOptions = norm_rental

        updated_prop = PropertyRepository.update(db, prop, update_data)
        return PropertyResponse.from_db(updated_prop)

    @staticmethod
    def delete_property(db: Session, prop_id: int) -> bool:
        prop = PropertyRepository.get_by_id(db, prop_id)
        if not prop:
            return False
        PropertyRepository.delete(db, prop)
        return True

