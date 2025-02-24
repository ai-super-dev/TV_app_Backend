from pydantic import BaseModel, EmailStr
from enum import Enum

class UserBase(BaseModel):
    email: EmailStr
    username: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: str | None = None

class DeviceStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"
    MAINTENANCE = "maintenance"

class DeviceBase(BaseModel):
    device_id: str
    url: str | None = None
    is_active: bool
    status: DeviceStatus = DeviceStatus.OFFLINE
    name: str | None = None

class DeviceCreate(DeviceBase):
    pass

class Device(DeviceBase):
    id: int

    class Config:
        from_attributes = True 