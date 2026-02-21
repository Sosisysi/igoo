import time
import os
import requests

print("🚀 ТЕСТОВЫЙ ЗАПУСК")
print(f"Текущая директория: {os.getcwd()}")
print(f"Файлы в директории: {os.listdir('.')}")

try:
    token = os.environ.get("TOKEN") or os.environ.get("BOT") or "не найден"
    print(f"Токен получен: {token[:5]}..." if token != "не найден" else "Токен не найден")
    
    # Отправляем тестовое сообщение
    chat_id = "5401786063"  # ВРЕМЕННО вставь сюда свой ID
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {"chat_id": chat_id, "text": "✅ Тест: бот работает!"}
    r = requests.post(url, data=data)
    print(f"Статус отправки: {r.status_code}")
    
except Exception as e:
    print(f"ОШИБКА: {e}")

print("⏳ Ожидаю 30 секунд...")
time.sleep(30)
print("✅ Тест завершен")


