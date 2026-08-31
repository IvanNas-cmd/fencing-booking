from datetime import date, timedelta
from typing import List
# Добавили импорт Header для проверки токена
from fastapi import FastAPI, Depends, Query, HTTPException, Path, Header
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
    allow_headers=["*"], # Это позволяет нам отправлять кастомный заголовок с токеном
)

BASE_SLOTS = ["08:00", "08:30", "09:00", "09:30", "10:00", "15:00", "15:30", "16:00"]

# --- НАСТРОЙКИ ДОСТУПА ТРЕНЕРА ---
COACH_PASSWORD = "ilya_admin" # Пароль для входа (можешь поменять на свой)
COACH_TOKEN = "super_secret_coach_token_123" # Фейковый токен для имитации безопасности

class LoginRequest(BaseModel):
    password: str

class BookingCreate(BaseModel):
    name: str
    date: date
    time_slot: str

class BookingAdminResponse(BaseModel):
    id: int
    date: date
    time_slot: str
    user_name: str
    is_attended: bool

# --- ФУНКЦИЯ ПРОВЕРКИ ПРАВ (Защита) ---
def verify_admin(admin_token: str = Header(None)):
    """Если токена нет или он неверный — выдаем ошибку 401"""
    if admin_token != COACH_TOKEN:
        raise HTTPException(status_code=401, detail="Неверный пароль или сессия истекла")

# --- ЭНДПОИНТ АВТОРИЗАЦИИ ---
@app.post("/admin/login")
def login_admin(req: LoginRequest):
    if req.password == COACH_PASSWORD:
        return {"status": "success", "token": COACH_TOKEN}
    raise HTTPException(status_code=401, detail="Неверный пароль")

# --- ПУБЛИЧНЫЕ ЭНДПОИНТЫ (Ученик) ---
@app.get("/slots", response_model=List[str])
def get_available_slots(target_date: date = Query(...), db: Session = Depends(get_db)):
    bookings_for_date = db.query(models.Booking).filter(models.Booking.date == target_date).all()
    occupied_slots = {booking.time_slot for booking in bookings_for_date}
    return [slot for slot in BASE_SLOTS if slot not in occupied_slots]

@app.post("/bookings")
def create_booking(booking: BookingCreate, db: Session = Depends(get_db)):
    # --- НОВОЕ: Приводим фамилию к единому формату ---
    # .strip() убирает случайные пробелы по краям
    # .title() делает первую букву заглавной, а остальные строчными (Коваль)
    normalized_name = booking.name.strip().title()

    # 1. Проверка правильности времени
    if booking.time_slot not in BASE_SLOTS:
        raise HTTPException(status_code=400, detail="Неверное время занятия.")

    # 2. Проверка, занято ли уже это время
    existing_booking = db.query(models.Booking).filter(
        models.Booking.date == booking.date,
        models.Booking.time_slot == booking.time_slot
    ).first()
    
    if existing_booking:
        raise HTTPException(status_code=400, detail="Извините, это время уже заняли.")

    # 3. Ищем пользователя по НОРМАЛИЗОВАННОЙ фамилии
    user = db.query(models.User).filter(models.User.name == normalized_name).first()
    
    if user:
        # Вычисляем понедельник и воскресенье для выбранной даты
        start_of_week = booking.date - timedelta(days=booking.date.weekday())
        end_of_week = start_of_week + timedelta(days=6)

        # Считаем, сколько записей у этого ученика на этой неделе
        weekly_bookings_count = db.query(models.Booking).filter(
            models.Booking.user_id == user.id,
            models.Booking.date >= start_of_week,
            models.Booking.date <= end_of_week
        ).count()

        if weekly_bookings_count >= 3:
            raise HTTPException(
                status_code=400, 
                detail="Вы уже записаны на 3 занятия на этой неделе. Организму нужен отдых! 🧘‍♂️"
            )
    else:
        # Если пользователя нет, создаем его с красивой фамилией
        user = models.User(name=normalized_name)
        db.add(user)
        db.commit()
        db.refresh(user)

    # 4. Создаем саму запись
    new_booking = models.Booking(
        user_id=user.id,
        date=booking.date,
        time_slot=booking.time_slot
    )
    db.add(new_booking)
    db.commit()
    
    return {
        "status": "success",
        "message": "Вы успешно записаны!",
        "time_slot": new_booking.time_slot,
        "date": new_booking.date
    }
# --- ЗАЩИЩЕННЫЕ ЭНДПОИНТЫ (Тренер) ---
# Обрати внимание на `Depends(verify_admin)` — без токена сюда не попасть
@app.get("/admin/bookings", response_model=List[BookingAdminResponse])
def get_all_bookings(
    target_date: date = Query(...), 
    db: Session = Depends(get_db),
    _: str = Depends(verify_admin) 
):
    bookings = db.query(models.Booking).filter(models.Booking.date == target_date).all()
    result = [{
        "id": b.id, "date": b.date, "time_slot": b.time_slot,
        "user_name": b.user.name, "is_attended": b.is_attended
    } for b in bookings]
    result.sort(key=lambda x: x["time_slot"])
    return result

@app.patch("/admin/bookings/{booking_id}/attend")
def toggle_attendance(
    booking_id: int, 
    db: Session = Depends(get_db),
    _: str = Depends(verify_admin)
):
    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Не найдено")
    
    booking.is_attended = not booking.is_attended
    db.commit()
    return {"status": "success"}