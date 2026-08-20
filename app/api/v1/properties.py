from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
import shutil
import os
import uuid

from app.database.database import get_db
from app.schemas.property import PropertyCreate, PropertyUpdate, PropertyResponse, PaginatedPropertyResponse
from app.services.property_service import PropertyService
from app.services.audit_service import AuditService
from app.dependencies import get_current_admin_user
from app.models.employee import Employee

router = APIRouter(prefix="/properties", tags=["Properties"])


@router.get("", response_model=PaginatedPropertyResponse)
def get_properties(
    location: Optional[str] = Query(None),
    propertyType: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    furnishing: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    units: Optional[str] = Query(None),
    priceRange: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    return PropertyService.get_all_properties(
        db=db,
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


@router.get("/{property_id}", response_model=PropertyResponse)
def get_property(property_id: int, db: Session = Depends(get_db)):
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
    updated = PropertyService.update_property(db, property_id, prop_data)
    if not updated:
        raise HTTPException(status_code=404, detail="Property not found")
    AuditService.log_action(
        db, current_user.id, current_user.name or "Admin", "Updated Property", "Property", str(updated.id)
    )
    return updated


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
    try:
        os.makedirs("uploads/images", exist_ok=True)
        ext = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4().hex}{ext}"
        file_path = f"uploads/images/{unique_filename}"
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        return {"url": f"/{file_path}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
