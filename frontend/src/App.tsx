import { useState, useEffect } from 'react';
import './App.css';

// --- НАСТРОЙКА API ---
// Твой бэкенд на Render (без слэша на конце!)
const API_BASE_URL = "https://fencing-api-cd35.onrender.com";

interface AdminBooking {
  id: number;
  date: string;
  time_slot: string;
  user_name: string;
  is_attended: boolean;
}

function App() {
  // --- ТЕМА (Светлая/Темная) ---
  const [theme, setTheme] = useState(() => localStorage.getItem('theme') || 'light');
  
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  const toggleTheme = () => setTheme(prev => prev === 'light' ? 'dark' : 'light');

  // --- АВТОРИЗАЦИЯ ТРЕНЕРА ---
  const [adminToken, setAdminToken] = useState(() => localStorage.getItem('adminToken') || '');
  const [showLoginModal, setShowLoginModal] = useState(false);
  const [passwordInput, setPasswordInput] = useState('');
  const [loginError, setLoginError] = useState('');

  const isAdmin = Boolean(adminToken);

  const handleTrainerClick = () => {
    if (isAdmin) handleLogout();
    else setShowLoginModal(true);
  };

  const handleLogout = () => {
    setAdminToken('');
    localStorage.removeItem('adminToken');
  };

  const submitLogin = async () => {
    setLoginError('');
    try {
      const res = await fetch(`${API_BASE_URL}/admin/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password: passwordInput })
      });
      if (res.ok) {
        const data = await res.json();
        setAdminToken(data.token);
        localStorage.setItem('adminToken', data.token);
        setShowLoginModal(false);
        setPasswordInput('');
      } else {
        setLoginError("Неверный пароль!");
      }
    } catch (err) {
      setLoginError("Ошибка подключения к серверу");
    }
  };

  // --- СОСТОЯНИЯ ПРИЛОЖЕНИЯ ---
  const [selectedDate, setSelectedDate] = useState(() => new Date().toISOString().split('T')[0]);
  const [currentMonthDate, setCurrentMonthDate] = useState(() => new Date());
  
  const [slots, setSlots] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [adminBookings, setAdminBookings] = useState<AdminBooking[]>([]);
  
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedSlot, setSelectedSlot] = useState('');
  const [studentName, setStudentName] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // --- ЗАГРУЗКА ДАННЫХ ---
  const fetchSlots = () => {
    setLoading(true);
    fetch(`${API_BASE_URL}/slots?target_date=${selectedDate}`)
      .then(res => res.json())
      .then(data => { 
        setSlots(Array.isArray(data) ? data : []); 
        setLoading(false); 
      })
      .catch((err) => { 
        console.error("Ошибка загрузки слотов", err);
        setSlots([]);
        setLoading(false); 
      });
  };

  const fetchAdminBookings = () => {
    setLoading(true);
    fetch(`${API_BASE_URL}/admin/bookings?target_date=${selectedDate}`, {
      headers: { "admin-token": adminToken } 
    })
      .then(async res => {
        if (res.status === 401) {
          handleLogout();
          throw new Error("Неавторизован");
        }
        return res.json();
      })
      .then(data => { setAdminBookings(data); setLoading(false); })
      .catch(() => { setAdminBookings([]); setLoading(false); });
  };

  useEffect(() => {
    if (isAdmin) fetchAdminBookings();
    else fetchSlots();
  }, [selectedDate, isAdmin]);

  // --- ЛОГИКА КАЛЕНДАРЯ ---
  const getDaysInMonth = (year: number, month: number) => new Date(year, month + 1, 0).getDate();
  const getFirstDayOfMonth = (year: number, month: number) => {
    let day = new Date(year, month, 1).getDay();
    return day === 0 ? 6 : day - 1; // Понедельник = первый день
  };

  const year = currentMonthDate.getFullYear();
  const month = currentMonthDate.getMonth();
  const daysInMonth = getDaysInMonth(year, month);
  const firstDay = getFirstDayOfMonth(year, month);
  const monthNames = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"];

  const handlePrevMonth = () => setCurrentMonthDate(new Date(year, month - 1, 1));
  const handleNextMonth = () => setCurrentMonthDate(new Date(year, month + 1, 1));
  const onDateClick = (day: number) => {
    setSelectedDate(`${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`);
  };

  // --- ЗАПИСЬ НА ЗАНЯТИЕ ---
  const openBookingModal = (slot: string) => {
    setSelectedSlot(slot);
    setStudentName('');
    setIsModalOpen(true);
  };

  const confirmBooking = async () => {
    if (!studentName.trim()) return;
    setIsSubmitting(true);
    try {
      const response = await fetch(`${API_BASE_URL}/bookings`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: studentName, date: selectedDate, time_slot: selectedSlot })
      });
      
      const result = await response.json();
      
      if (response.ok) {
        setIsModalOpen(false);
        fetchSlots();
      } else {
        alert("Ошибка: " + result.detail);
      }
    } catch (err) {
      alert("Ошибка сети. Бэкенд не отвечает.");
    } finally {
      setIsSubmitting(false);
    }
  };

  // --- ОТМЕТКА О ПОСЕЩЕНИИ ---
  const toggleAttendance = async (bookingId: number) => {
    setAdminBookings(prev => prev.map(b => b.id === bookingId ? { ...b, is_attended: !b.is_attended } : b));
    try {
      await fetch(`${API_BASE_URL}/admin/bookings/${bookingId}/attend`, {
        method: "PATCH",
        headers: { "admin-token": adminToken }
      });
    } catch (error) {
      fetchAdminBookings(); 
    }
  };

  return (
    <>
      <div className="animated-bg">
        <div className="blob blob-1"></div>
        <div className="blob blob-2"></div>
      </div>

      <div className="app-layout">
        
        {/* ЛЕВАЯ КОЛОНКА */}
        <div className="sidebar">
          <div className="glass-panel" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <h2 style={{ margin: 0, fontSize: '1.4rem' }}>
              {isAdmin ? "Панель тренера" : "Запись 🤺"}
            </h2>
            <div className="header-actions">
              <button onClick={toggleTheme} className="icon-btn" title="Сменить тему">
                {theme === 'light' ? '🌙' : '☀️'}
              </button>
              <button 
                onClick={handleTrainerClick} 
                className="action-btn" 
                style={{ 
                  background: isAdmin ? 'var(--text-main)' : 'var(--btn-secondary)', 
                  color: isAdmin ? 'var(--bg-color)' : 'var(--btn-secondary-text)' 
                }}
              >
                {isAdmin ? "Выйти" : "Тренер"}
              </button>
            </div>
          </div>

          <div className="glass-panel">
            <div className="calendar-header">
              <button className="calendar-nav-btn" onClick={handlePrevMonth}>◀</button>
              <span>{monthNames[month]} {year}</span>
              <button className="calendar-nav-btn" onClick={handleNextMonth}>▶</button>
            </div>
            <div className="calendar-grid">
              {['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'].map(d => <div key={d} className="day-name">{d}</div>)}
              {Array.from({ length: firstDay }).map((_, i) => <div key={`empty-${i}`} className="calendar-day empty"></div>)}
              {Array.from({ length: daysInMonth }).map((_, i) => {
                const day = i + 1;
                const isSelected = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}` === selectedDate;
                return (
                  <button key={day} className={`calendar-day ${isSelected ? 'selected' : ''}`} onClick={() => onDateClick(day)}>
                    {day}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* ПРАВАЯ КОЛОНКА */}
        <div className="main-content">
          <div className="glass-panel" style={{ minHeight: '350px' }}>
            {loading ? (
              <div className="spinner"></div>
            ) : isAdmin ? (
              <div>
                <h3 style={{ marginTop: 0, color: 'var(--text-muted)' }}>Записи на {selectedDate}</h3>
                <div className="admin-cards-container">
                  {adminBookings.length > 0 ? (
                    adminBookings.map((b) => (
                      <div key={b.id} className={`admin-card ${b.is_attended ? 'attended' : ''}`}>
                        <div>
                          <div style={{ fontSize: '1.3rem', fontWeight: 700, color: b.is_attended ? 'var(--success)' : 'var(--primary)' }}>
                            {b.time_slot}
                          </div>
                          <div style={{ fontSize: '1rem', marginTop: '4px', fontWeight: 500 }}>{b.user_name}</div>
                        </div>
                        <button className="attend-btn" onClick={() => toggleAttendance(b.id)}>
                          {b.is_attended ? "✓ Был" : "Отметить"}
                        </button>
                      </div>
                    ))
                  ) : <p style={{ color: 'var(--text-muted)' }}>Никто не записан.</p>}
                </div>
              </div>
            ) : (
              <div>
                <h3 style={{ marginTop: 0, color: 'var(--text-muted)' }}>Свободное время на {selectedDate}</h3>
                <div className="slots-grid">
                  {slots.length > 0 ? (
                    slots.map(slot => (
                      <button key={slot} className="slot-btn" onClick={() => openBookingModal(slot)}>
                        {slot}
                      </button>
                    ))
                  ) : (
                    <p style={{ gridColumn: '1 / -1', color: 'var(--text-muted)', fontSize: '1.1rem' }}>Всё время занято (или это выходной) 😔</p>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* МОДАЛКА ЛОГИНА */}
        {showLoginModal && (
          <div className="modal-overlay" onClick={() => { setShowLoginModal(false); setLoginError(''); }}>
            <div className="modal-content" onClick={e => e.stopPropagation()}>
              <h3 style={{ margin: '0 0 15px 0' }}>Вход для тренера</h3>
              <input 
                type="password" 
                placeholder="Введите пароль" 
                value={passwordInput}
                onChange={e => { setPasswordInput(e.target.value); setLoginError(''); }}
                onKeyDown={e => e.key === 'Enter' && submitLogin()}
                autoFocus
              />
              {loginError && <p style={{ color: '#ef4444', fontSize: '0.85rem', margin: '0 0 10px 0' }}>{loginError}</p>}
              <div style={{ display: 'flex', gap: '10px', marginTop: '10px' }}>
                <button onClick={() => { setShowLoginModal(false); setLoginError(''); }} className="action-btn" style={{ flex: 1, padding: '12px' }}>Отмена</button>
                <button onClick={submitLogin} style={{ flex: 1, padding: '12px', borderRadius: '12px', border: 'none', background: 'var(--primary)', color: 'white', cursor: 'pointer', fontWeight: 600 }}>Войти</button>
              </div>
            </div>
          </div>
        )}

        {/* МОДАЛКА ЗАПИСИ (УЧЕНИК) */}
        {isModalOpen && (
          <div className="modal-overlay" onClick={() => setIsModalOpen(false)}>
            <div className="modal-content" onClick={e => e.stopPropagation()}>
              <h3 style={{ margin: '0 0 10px 0' }}>Запись на {selectedSlot}</h3>
              <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '0.9rem' }}>Дата: {selectedDate.split('-').reverse().join('.')}</p>
              <input 
                type="text" 
                placeholder="Ваша фамилия" 
                value={studentName}
                onChange={e => setStudentName(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && confirmBooking()}
                autoFocus
              />
              <div style={{ display: 'flex', gap: '10px', marginTop: '10px' }}>
                <button onClick={() => setIsModalOpen(false)} className="action-btn" style={{ flex: 1, padding: '12px' }}>Отмена</button>
                <button onClick={confirmBooking} disabled={isSubmitting || !studentName.trim()} style={{ flex: 1, padding: '12px', borderRadius: '12px', border: 'none', background: 'var(--primary)', color: 'white', cursor: 'pointer', fontWeight: 600, opacity: (!studentName.trim() || isSubmitting) ? 0.5 : 1 }}>
                  {isSubmitting ? "Запись..." : "Подтвердить"}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
}

export default App;