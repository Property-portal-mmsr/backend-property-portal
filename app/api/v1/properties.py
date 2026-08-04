from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database.database import get_db
from app.schemas.property import PropertyCreate, PropertyUpdate, PropertyResponse
from app.services.property_service import PropertyService
from app.services.audit_service import AuditService
from app.dependencies import get_current_admin_user
from app.models.employee import Employee

router = APIRouter(prefix="/properties", tags=["Properties"])


@router.get("", response_model=List[PropertyResponse])
def get_properties(db: Session = Depends(get_db)):
    return PropertyService.get_all_properties(db)


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

