from sqlalchemy import Column, Integer, String, Date, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    pin_code = Column(String)  # PIN-код для доступа к личным записям
    
    bookings = relationship("Booking", back_populates="user")

class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(Date, index=True)
    time_slot = Column(String)
    is_attended = Column(Boolean, default=False)
    
    user = relationship("User", back_populates="bookings")