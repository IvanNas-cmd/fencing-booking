import models
from database import engine

print("Удаляем старые таблицы и данные...")
models.Base.metadata.drop_all(bind=engine)

print("Создаем новые таблицы (теперь с PIN-кодами!)...")
models.Base.metadata.create_all(bind=engine)

print("✅ База данных успешно обновлена и очищена!")