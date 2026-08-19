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
        # Pass standard fields to repository for SQL filtering
        props = PropertyRepository.get_all(
            db, 
            location=location, 
            category=category, 
            status=status,
            search=search,
            units=units
        )
        
        # We perform complex/JSON-based filtering in python
        # to ensure compatibility between SQLite and MySQL
        filtered_props = []
        for p in props:
            
            # Property Type filter (applies to main property_type or rental_options JSON)
            if propertyType:
                pt_match = (p.property_type == propertyType)
                if not pt_match and p.rental_options:
                    if any(isinstance(ro, dict) and ro.get("type") == propertyType for ro in p.rental_options):
                        pt_match = True
                if not pt_match:
                    continue
                    
            # Furnishing filter (applies to pg_options JSON or rental_options JSON)
            if furnishing:
                f_match = False
                if p.pg_options:
                    if any(isinstance(pg, dict) and pg.get("furnishing") == furnishing for pg in p.pg_options):
                        f_match = True
                if not f_match and p.rental_options:
                    if any(isinstance(ro, dict) and ro.get("furnishing") == furnishing for ro in p.rental_options):
                        f_match = True
                if not f_match:
                    continue
            
            # Price Range filter
            if priceRange:
                # Get the minimum available price from pricing logic (similar to frontend `starting || single || 0`)
                min_price = 0
                if getattr(p, "property_pricing", None):
                    pricing = p.property_pricing
                    min_price = float(pricing.starting_price or pricing.single_price or 0)
                else:
                    # Fallback to checking inside JSON options just in case
                    prices = []
                    if p.pg_options:
                        prices.extend([float(opt.get("price", 0)) for opt in p.pg_options if isinstance(opt, dict) and opt.get("price")])
                    if p.rental_options:
                        prices.extend([float(opt.get("price", 0)) for opt in p.rental_options if isinstance(opt, dict) and opt.get("price")])
                    if prices:
                        min_price = min(prices)
                
                if priceRange == "₹5,000 - ₹10,000" and not (5000 <= min_price <= 10000): continue
                elif priceRange == "₹10,001 - ₹15,000" and not (10001 <= min_price <= 15000): continue
                elif priceRange == "₹15,001 - ₹20,000" and not (15001 <= min_price <= 20000): continue
                elif priceRange == "₹20,001 - ₹30,000" and not (20001 <= min_price <= 30000): continue
                elif priceRange == "₹30,001+" and min_price <= 30000: continue
            
            filtered_props.append(p)
            
        total = len(filtered_props)
        pages = math.ceil(total / limit) if limit > 0 else 1
        page = (skip // limit) + 1 if limit > 0 else 1
        
        paginated_slice = filtered_props[skip : skip + limit]
            
        return PaginatedPropertyResponse(
            items=[PropertyResponse.from_db(p) for p in paginated_slice],
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
