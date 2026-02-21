import requests
import time
import re
from datetime import datetime
import json
import os
from collections import Counter

# ========== НАСТРОЙКИ ==========
# ВАЖНО: Токен и Chat ID берутся из переменных окружения на Bothost!
TELEGRAM_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

# Твоя ссылка на поиск Авито (это безопасно, ее можно оставить)
AVITO_URL = "https://www.avito.ru/rossiya/igrushki?q=мягкая+игрушка&s=104"

# Ключевые слова для отслеживания трендов
TREND_KEYWORDS = [
    "кукума", "плачущая лошадка", "грустная лошадка",
    "лабуба", "labubu", "мируми", "mirumi", 
    "чебурашка", "антистресс", "тянучка", "сквиш",
    "пегас", "лошадка 2026"
]

# Файл для хранения истории
HISTORY_FILE = "trend_history.json"
# ================================

# Проверка наличия переменных окружения
if not TELEGRAM_TOKEN or not CHAT_ID:
    print("ОШИБКА: Не заданы переменные окружения BOT_TOKEN и CHAT_ID")
    print("Добавьте их в настройках бота на Bothost")
    exit(1)

# Загружаем историю (если есть)
def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"seen_items": [], "trends": {}}

# Сохраняем историю
def save_history(history):
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

# Отправка сообщения в Telegram
def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        response = requests.post(url, data=data)
        print(f"Статус отправки: {response.status_code}")
    except Exception as e:
        print(f"Ошибка отправки: {e}")

# Парсинг Авито
def parse_avito():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(AVITO_URL, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"Ошибка HTTP: {response.status_code}")
            return []
        
        text = response.text
        
        # Простой поиск объявлений
        items = []
        titles = re.findall(r'item-name">(.*?)<', text)
        prices = re.findall(r'price">(.*?)<', text)
        links = re.findall(r'href="(https://www.avito.ru/[^"]+)"', text)
        
        min_len = min(len(titles), len(prices), len(links))
        for i in range(min_len):
            items.append({
                'title': titles[i].strip(),
                'price': prices[i].strip(),
                'link': links[i],
                'id': links[i].split('_')[-1] if '_' in links[i] else str(i)
            })
        
        print(f"Найдено объявлений: {len(items)}")
        return items
    except Exception as e:
        print(f"Ошибка парсинга: {e}")
        return []

# Анализ трендов
def analyze_trends(items, history):
    today_trends = Counter()
    new_items = []
    
    for item in items:
        if item['id'] not in history['seen_items']:
            new_items.append(item)
            title_lower = item['title'].lower()
            for keyword in TREND_KEYWORDS:
                if keyword.lower() in title_lower:
                    today_trends[keyword] += 1
        
        history['seen_items'].append(item['id'])
    
    # Храним только последние 1000 объявлений
    history['seen_items'] = history['seen_items'][-1000:]
    
    # Обновляем статистику по дням
    today = datetime.now().strftime("%Y-%m-%d")
    for keyword, count in today_trends.items():
        if keyword not in history['trends']:
            history['trends'][keyword] = {}
        history['trends'][keyword][today] = count
    
    return today_trends, new_items

# Формирование отчета
def generate_report(today_trends, new_items):
    if not new_items:
        return "📭 За последние 4 часа новых объявлений не найдено."
    
    report = f"📊 <b>ТРЕНД-ДАЙДЖЕСТ</b>\n"
    report += f"🕐 {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
    report += f"📦 Найдено новых объявлений: {len(new_items)}\n\n"
    
    if today_trends:
        report += "🔥 <b>ТРЕНДЫ ЭТОГО ЧАСА:</b>\n"
        for keyword, count in today_trends.most_common(5):
            report += f"• {keyword.title()}: {count} шт.\n"
        report += "\n"
    
    report += "🆕 <b>Самые свежие:</b>\n"
    for item in new_items[:3]:
        # Обрезаем длинные названия
        short_title = item['title'][:50] + "..." if len(item['title']) > 50 else item['title']
        report += f"• {short_title} — {item['price']}\n"
        report += f"  {item['link']}\n"
    
    return report

# Основная функция проверки трендов
def check_trends():
    print(f"[{datetime.now()}] Проверяю тренды...")
    history = load_history()
    items = parse_avito()
    
    if items:
        today_trends, new_items = analyze_trends(items, history)
        if new_items:
            report = generate_report(today_trends, new_items)
            send_telegram(report)
            save_history(history)
            print(f"Отправлен отчет, новых объявлений: {len(new_items)}")
        else:
            print("Новых объявлений нет")
    else:
        print("Не удалось получить объявления")

# Запуск
def main():
    print("🚀 Бот для отслеживания трендов запущен")
    print(f"Режим: проверка каждые 4 часа")
    
    # Отправляем сообщение о запуске
    send_telegram("🚀 <b>Тренд-агент запущен!</b>\nБуду присылать отчеты каждые 4 часа")
    
    # Сразу проверяем
    check_trends()
    
    # Основной цикл
    while True:
        time.sleep(4 * 60 * 60)  # 4 часа
        check_trends()

if __name__ == "__main__":
    main()