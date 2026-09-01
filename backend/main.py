from datetime import date, timedelta
from typing import List
from fastapi import FastAPI, Depends, Query, HTTPException, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

import models
from database import engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Fencing Booking API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- НАСТРОЙКИ ---
BASE_SLOTS = ["08:00", "08:30", "09:00", "09:30", "10:00", "15:00", "15:30", "16:00"]
COACH_PASSWORD = "admin" 
COACH_TOKEN = "super_secret_coach_token_123" 

# --- СХЕМЫ ДАННЫХ ---
class LoginRequest(BaseModel):
    password: str

class BookingCreate(BaseModel):
    name: str
    pin_code: str
    date: date
    time_slot: str

class BookingAdminResponse(BaseModel):
    id: int
    date: date
    time_slot: str
    user_name: str
    is_attended: bool

def verify_admin(admin_token: str = Header(None)):
    if admin_token != COACH_TOKEN:
        raise HTTPException(status_code=401, detail="Неверный пароль или сессия истекла")

# --- ЭНДПОИНТЫ ---
@app.post("/admin/login")
def login_admin(req: LoginRequest):
    if req.password == COACH_PASSWORD:
        return {"status": "success", "token": COACH_TOKEN}
    raise HTTPException(status_code=401, detail="Неверный пароль")

@app.get("/slots", response_model=List[str])
def get_available_slots(target_date: date = Query(...), db: Session = Depends(get_db)):
    bookings_for_date = db.query(models.Booking).filter(models.Booking.date == target_date).all()
    occupied_slots = {booking.time_slot for booking in bookings_for_date}
    return [slot for slot in BASE_SLOTS if slot not in occupied_slots]

@app.post("/bookings")
def create_booking(booking: BookingCreate, db: Session = Depends(get_db)):
    normalized_name = booking.name.strip().title()

    if booking.time_slot not in BASE_SLOTS:
        raise HTTPException(status_code=400, detail="Неверное время занятия.")

    existing_booking = db.query(models.Booking).filter(
        models.Booking.date == booking.date,
        models.Booking.time_slot == booking.time_slot
    ).first()
    
    if existing_booking:
        raise HTTPException(status_code=400, detail="Извините, это время уже заняли.")

    user = db.query(models.User).filter(models.User.name == normalized_name).first()
    
    if user:
        if user.pin_code != booking.pin_code:
            raise HTTPException(status_code=401, detail="Неверный PIN-код для этой фамилии!")

        start_of_week = booking.date - timedelta(days=booking.date.weekday())
        end_of_week = start_of_week + timedelta(days=6)

        weekly_bookings_count = db.query(models.Booking).filter(
            models.Booking.user_id == user.id,
            models.Booking.date >= start_of_week,
            models.Booking.date <= end_of_week
        ).count()

        if weekly_bookings_count >= 3:
            raise HTTPException(status_code=400, detail="Вы уже записаны на 3 занятия на этой неделе. Организму нужен отдых! 🧘‍♂️")
    else:
        user = models.User(name=normalized_name, pin_code=booking.pin_code)
        db.add(user)
        db.commit()
        db.refresh(user)

    new_booking = models.Booking(user_id=user.id, date=booking.date, time_slot=booking.time_slot)
    db.add(new_booking)
    db.commit()
    
    return {"status": "success", "message": "Вы успешно записаны!", "time_slot": new_booking.time_slot, "date": new_booking.date}

@app.get("/admin/bookings", response_model=List[BookingAdminResponse])
def get_all_bookings(target_date: date = Query(...), db: Session = Depends(get_db), _: str = Depends(verify_admin)):
    bookings = db.query(models.Booking).filter(models.Booking.date == target_date).all()
    result = [{"id": b.id, "date": b.date, "time_slot": b.time_slot, "user_name": b.user.name, "is_attended": b.is_attended} for b in bookings]
    result.sort(key=lambda x: x["time_slot"])
    return result

@app.patch("/admin/bookings/{booking_id}/attend")
def toggle_attendance(booking_id: int, db: Session = Depends(get_db), _: str = Depends(verify_admin)):
    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    booking.is_attended = not booking.is_attended
    db.commit()
    return {"status": "success"}

@app.get("/my-bookings")
def get_my_bookings(name: str = Query(...), pin_code: str = Query(...), db: Session = Depends(get_db)):
    normalized_name = name.strip().title()
    user = db.query(models.User).filter(models.User.name == normalized_name).first()
    
    if not user or user.pin_code != pin_code:
        raise HTTPException(status_code=401, detail="Неверная фамилия или PIN-код")
    
    today = date.today()
    bookings = db.query(models.Booking).filter(
        models.Booking.user_id == user.id,
        models.Booking.date >= today
    ).order_by(models.Booking.date, models.Booking.time_slot).all()
    
    return [{"id": b.id, "date": b.date, "time_slot": b.time_slot, "is_attended": b.is_attended} for b in bookings]

@app.delete("/bookings/{booking_id}")
def cancel_booking(booking_id: int, db: Session = Depends(get_db)):
    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    db.delete(booking)
    db.commit()
    return {"status": "success", "message": "Запись отменена"}