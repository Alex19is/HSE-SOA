from pydantic import BaseModel, EmailStr, StringConstraints
from typing import Optional, Annotated
from datetime import date, datetime

PhoneNumber = Annotated[str, StringConstraints(pattern=r"^\+?[0-9]{7,15}$")]  # Телефонный номер

class UserBase(BaseModel):
    first_name: Optional[Annotated[str, StringConstraints(min_length=2, max_length=50)]] = None
    last_name: Optional[Annotated[str, StringConstraints(min_length=2, max_length=50)]] = None
    birth_date: Optional[date] = None
    phone_number: Optional[PhoneNumber] = None

class UserCreate(UserBase):
    login: Annotated[str, StringConstraints(min_length=4, max_length=30)]
    email: EmailStr
    password: Annotated[str, StringConstraints(min_length=6, max_length=100)]

class UserUpdate(BaseModel):
    first_name: Optional[Annotated[str, StringConstraints(min_length=2, max_length=50)]] = None
    last_name: Optional[Annotated[str, StringConstraints(min_length=2, max_length=50)]] = None
    birth_date: Optional[date] = None
    phone_number: Optional[PhoneNumber] = None
    email: Optional[EmailStr] = None

class LoginSchema(BaseModel):
    login: Annotated[str, StringConstraints(min_length=4, max_length=30)]
    password: Annotated[str, StringConstraints(min_length=6, max_length=100)]

class User(UserBase):
    id: int
    email: EmailStr
    login: str
    hashed_password: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True 
