from sqlalchemy import Column, Integer, String, Date, DateTime, func
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, index=True, nullable = True)
    last_name = Column(String, index=True, nullable = True)
    birth_date = Column(Date, nullable = True) 
    email = Column(String, unique=True, index=True)
    phone_number = Column(String, unique=True, index=True, nullable = True)
    login = Column(String, unique=True, index=True)
    hashed_password = Column(String, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
