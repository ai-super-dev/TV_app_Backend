from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
import models
import schemas
from .auth import get_current_user

router = APIRouter()

@router.get("/", response_model=List[schemas.Device])
async def get_devices(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user)
):
    devices = db.query(models.Device).all()
    return devices

@router.post("/", response_model=schemas.Device)
async def create_device(
    device: schemas.DeviceCreate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user)
):
    db_device = models.Device(device_id=device.device_id)
    db.add(db_device)
    db.commit()
    db.refresh(db_device)
    return db_device

@router.put("/toggle/{device_id}")
async def toggle_device(
    device_id: str,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user)
):
    device = db.query(models.Device).filter(models.Device.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    device.is_active = not device.is_active
    db.commit()
    return {"status": "success"} 