from sqlalchemy import Column, Integer, String, Boolean, Date, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    is_admin = Column(Boolean, default=False)
    
    bookings = relationship("Booking", back_populates="user")


class Booking(Base):
    __tablename__ = "bookings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(Date, index=True, nullable=False)
    time_slot = Column(String, index=True, nullable=False)
    
    # Отметка о посещении
    is_attended = Column(Boolean, default=False) 

    user = relationship("User", back_populates="bookings")