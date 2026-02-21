import requests
import time
import re
from datetime import datetime
import json
import os
from collections import Counter

# ========== НАСТРОЙКИ ==========
TELEGRAM_TOKEN = os.environ.get("TOKEN") or os.environ.get("BOT")
CHAT_ID = int(os.environ.get("CHAT_ID"))
AVITO_URL = "https://m.avito.ru/rossiya/igrushki?q=мягкая+игрушка&s=104"

# Ключевые слова для отслеживания трендов
TREND_KEYWORDS = [
    "кукума", "плачущая лошадка", "грустная лошадка",
    "лабуба", "labubu", "мируми", "mirumi", 
    "чебурашка", "антистресс", "тянучка", "сквиш",
    "пегас", "лошадка 2026"
]

HISTORY_FILE = "trend_history.json"
# ================================

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"seen_items": [], "trends": {}}

def save_history(history):
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, data=data)
        print("Сообщение отправлено")
    except Exception as e:
        print(f"Ошибка отправки: {e}")

def parse_avito():
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1'
    }
    
    try:
        print("🔄 Парсинг мобильной версии...")
        response = requests.get(AVITO_URL, headers=headers, timeout=15)
        
        if response.status_code != 200:
            print(f"❌ Ошибка HTTP: {response.status_code}")
            return []
        
        text = response.text
        print(f"📄 Размер страницы: {len(text)} символов")
        
        # Для мобильной версии другие паттерны
        items = []
        
        # Ищем блоки с товарами
        blocks = re.findall(r'<div class="iva-item-root[^>]*>(.*?)</div>\s*</div>\s*</div>', text, re.DOTALL)
        print(f"Найдено блоков: {len(blocks)}")
        
        for block in blocks[:20]:  # берем первые 20
            # Ищем название
            title_match = re.search(r'item-title">(.*?)<', block)
            # Ищем цену
            price_match = re.search(r'price">(.*?)<', block)
            # Ищем ссылку
            link_match = re.search(r'href="(.*?)"', block)
            
            if title_match and price_match and link_match:
                items.append({
                    'title': title_match.group(1).strip(),
                    'price': price_match.group(1).strip(),
                    'link': 'https://m.avito.ru' + link_match.group(1),
                    'id': link_match.group(1).split('/')[-1]
                })
        
        print(f"✅ Собрано объявлений: {len(items)}")
        return items
        
    except Exception as e:
        print(f"💥 Ошибка парсинга: {e}")
        return []

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
    
    history['seen_items'] = history['seen_items'][-1000:]
    
    today = datetime.now().strftime("%Y-%m-%d")
    for keyword, count in today_trends.items():
        if keyword not in history['trends']:
            history['trends'][keyword] = {}
        history['trends'][keyword][today] = count
    
    return today_trends, new_items

def generate_report(today_trends, new_items):
    if not new_items:
        return None
    
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
        short_title = item['title'][:50] + "..." if len(item['title']) > 50 else item['title']
        report += f"• {short_title} — {item['price']}\n"
        report += f"  {item['link']}\n"
    
    return report

def check_trends():
    try:
        print(f"▶️ [{datetime.now()}] Проверка трендов")
        send_telegram("⏳ Начинаю проверку Авито...")  # ← диагностика
        
        history = load_history()
        items = parse_avito()
        
        if items is None:
            send_telegram("❌ Ошибка: парсинг вернул None")
            return
            
        send_telegram(f"📦 Получено объявлений: {len(items)}")  # ← диагностика
        
        if items:
            today_trends, new_items = analyze_trends(items, history)
            send_telegram(f"🆕 Новых объявлений: {len(new_items)}")  # ← диагностика
            
            report = generate_report(today_trends, new_items)
            if report:
                send_telegram(report)
                save_history(history)
                send_telegram("✅ Отчет отправлен")  # ← диагностика
            else:
                send_telegram("📭 Новых объявлений нет")
        else:
            send_telegram("❌ Не удалось получить объявления (пустой список)")
            
    except Exception as e:
        error_msg = f"💥 КРИТИЧЕСКАЯ ОШИБКА: {str(e)}"
        print(error_msg)
        send_telegram(error_msg)

def main():
    print("🚀 Тренд-агент ЗАПУЩЕН")
    send_telegram("🚀 <b>Тренд-агент запущен!</b>\nБуду присылать отчеты каждые 4 часа")
    
    # Сразу проверяем
    check_trends()
    
    # Основной цикл
    while True:
        time.sleep(4 * 60 * 60)  # 4 часа
        check_trends()

if __name__ == "__main__":
    main()


