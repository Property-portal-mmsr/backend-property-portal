from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

from app.database.database import get_db
from app.schemas.property import PropertyCreate, PropertyUpdate, PropertyResponse, PaginatedPropertyResponse
from app.services.property_service import PropertyService
from app.services.audit_service import AuditService
from app.dependencies import get_current_admin_user, get_current_user
from app.models.employee import Employee

router = APIRouter(prefix="/properties", tags=["Properties"])


from fastapi.responses import JSONResponse

@router.get("")
def get_properties(
    location: Optional[str] = Query(None),
    propertyType: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    categories: Optional[List[str]] = Query(None),
    sharingType: Optional[str] = Query(None),
    unitType: Optional[str] = Query(None),
    balcony: Optional[str] = Query(None),
    furnishing: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    units: Optional[str] = Query(None),
    priceRange: Optional[str] = Query(None),
    minPrice: Optional[float] = Query(None),
    maxPrice: Optional[float] = Query(None),
    search: Optional[str] = Query(None),
    sort: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    res = PropertyService.get_all_properties(
        db=db,
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
    # Bypass slow FastAPI jsonable_encoder for large lists
    return JSONResponse(content=res.dict())


@router.get("/locations", response_model=List[str])
def get_locations(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    from app.repositories.property_repository import PropertyRepository
    return PropertyRepository.get_unique_locations(db)


@router.get("/{property_id}", response_model=PropertyResponse)
def get_property(
    property_id: int, 
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    prop = PropertyService.get_property_by_id(db, property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    return prop


@router.post("", response_model=PropertyResponse, status_code=status.HTTP_201_CREATED)
def create_property(
    prop_data: PropertyCreate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_admin_user),
):
    new_prop = PropertyService.create_property(db, prop_data)
    AuditService.log_action(
        db, current_user.id, current_user.name or "Admin", "Created Property", "Property", str(new_prop.id)
    )
    return new_prop


@router.put("/{property_id}", response_model=PropertyResponse)
def update_property(
    property_id: int,
    prop_data: PropertyUpdate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_admin_user),
):
    try:
        updated = PropertyService.update_property(db, property_id, prop_data)
        if not updated:
            raise HTTPException(status_code=404, detail="Property not found")
        AuditService.log_action(
            db, current_user.id, current_user.name or "Admin", "Updated Property", "Property", str(updated.id)
        )
        return updated
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating property {property_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update property: {str(e)}")


@router.delete("/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_property(
    property_id: int,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_admin_user),
):
    success = PropertyService.delete_property(db, property_id)
    if not success:
        raise HTTPException(status_code=404, detail="Property not found")
    AuditService.log_action(
        db, current_user.id, current_user.name or "Admin", "Deleted Property", "Property", str(property_id)
    )
    return None

@router.post("/restore/{property_id}")
def restore_property(
    property_id: int,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_admin_user)
):
    restored = PropertyService.restore_property(db, property_id)
    if not restored:
        raise HTTPException(status_code=404, detail="Property not found or not deleted")
    AuditService.log_action(
        db, current_user.id, current_user.name or "Admin", "Restored Property", "Property", str(property_id)
    )
    return {"message": "Property restored successfully"}

@router.post("/upload", status_code=status.HTTP_201_CREATED)
def upload_property_image(
    file: UploadFile = File(...),
    current_user: Employee = Depends(get_current_admin_user)
):
    from app.utils.storage import store_image_bytes

    try:
        contents = file.file.read()
        url = store_image_bytes(contents, filename=file.filename or "", content_type=file.content_type)
        return {"url": url}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception:
        logger.exception("Property image upload failed")
        raise HTTPException(status_code=500, detail="Failed to upload image")
