import requests
import time
import re
from datetime import datetime
import json
import os
from collections import Counter
def send_telegram_diagnostic(msg):
    """Отправка диагностических сообщений (дубль основной функции)"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {"chat_id": CHAT_ID, "text": f"🔧 {msg}"}
        requests.post(url, data=data)
    except:
        pass
# ========== НАСТРОЙКИ ==========
TELEGRAM_TOKEN = os.environ.get("TOKEN") or os.environ.get("BOT")
CHAT_ID = int(os.environ.get("CHAT_ID"))
AVITO_URL = "https://www.avito.ru/all/tovary_dlya_detey_i_igrushki?q=%D0%BC%D1%8F%D0%B3%D0%BA%D0%B8%D0%B5+%D0%B8%D0%B3%D1%80%D1%83%D1%88%D0%BA%D0%B8"

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
    """
    Парсинг Авито через внутреннее API (работает стабильно)
    """
    try:
        print("🔄 Запрос к API Авито...")
        
        # Формируем запрос к поисковому API Авито
        params = {
            'q': 'мягкая игрушка',  # поисковый запрос
            'p': 1,  # страница
            's': 104,  # сортировка: по дате
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
            'Accept': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        }
        
        # Используем API эндпоинт Авито
        url = 'https://www.avito.ru/web/1/main/items'
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"❌ Ошибка API: {response.status_code}")
            return []
        
        data = response.json()
        items = []
        
        # Парсим JSON-ответ
        if 'items' in data:
            for item in data['items']:
                items.append({
                    'title': item.get('title', ''),
                    'price': str(item.get('price', {}).get('value', 'Цена не указана')) + ' ₽',
                    'link': f"https://www.avito.ru{item.get('uriPath', '')}",
                    'id': str(item.get('id', ''))
                })
        
        print(f"✅ API вернул {len(items)} объявлений")
        
        # Если API не сработало, пробуем запасной вариант
        if not items:
            print("🔄 API не сработало, пробую прямую загрузку...")
            return parse_avito_fallback()
            
        return items
        
    except Exception as e:
        print(f"💥 Ошибка API: {e}")
        # Если API упало, пробуем запасной вариант
        return parse_avito_fallback()

def parse_avito_fallback():
     search_url = "https://www.avito.ru/all/tovary_dlya_detey_i_igrushki?q=%D0%BC%D1%8F%D0%B3%D0%BA%D0%B8%D0%B5+%D0%B8%D0%B3%D1%80%D1%83%D1%88%D0%BA%D0%B8"  # ← вставь СВОЮ ссылку
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        print(f"🔍 Парсинг категории: {search_url}")
        response = requests.get(search_url, headers=headers, timeout=10)
    """
    Запасной вариант парсинга с правильным сбором ссылок
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        url = 'https://www.avito.ru/rossiya/igrushki?q=мягкая+игрушка&s=104'
        print(f"🔍 Запасной парсинг: {url}")
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"❌ Ошибка запасного парсинга: {response.status_code}")
            return []
        
        text = response.text
        items = []
        
        # Ищем ВСЕ ссылки на товары (паттерн для Авито)
        # Ссылки на товары выглядят так: /moskva/igrushki/myagkaya_igrushka_123456789
        link_matches = re.findall(r'href="(/[^"]*?igrushki[^"]*?_[0-9]+)"', text)
        
        # Ищем заголовки товаров
        title_matches = re.findall(r'<h3[^>]*item-name[^>]*>(.*?)</h3>', text, re.DOTALL)
        
        # Ищем цены (цифры с символом ₽)
        price_matches = re.findall(r'<strong[^>]*>[^>]*>([0-9\s]+)\s*₽', text)
        
        print(f"Найдено ссылок: {len(link_matches)}")
        print(f"Найдено заголовков: {len(title_matches)}")
        print(f"Найдено цен: {len(price_matches)}")
        
        # Берем минимум из длин
        min_len = min(len(link_matches), len(title_matches), len(price_matches))
        
        for i in range(min_len):
            # Очищаем заголовок от HTML-тегов
            title = title_matches[i]
            title = re.sub(r'<[^>]+>', '', title)
            title = title.replace('&nbsp;', ' ').strip()
            
            # Очищаем цену от пробелов
            price = price_matches[i].replace(' ', '') + ' ₽'
            
            # Формируем полную ссылку
            link = link_matches[i]
            if not link.startswith('http'):
                link = 'https://www.avito.ru' + link
            
            # Извлекаем ID из ссылки
            item_id = link.split('_')[-1] if '_' in link else str(i)
            
            items.append({
                'title': title,
                'price': price,
                'link': link,
                'id': item_id
            })
        
        # Если не сработало с паттернами выше, пробуем другой подход
        if not items:
            print("🔄 Пробуем альтернативный метод парсинга...")
            
            # Ищем все ссылки, которые выглядят как товары
            all_links = re.findall(r'href="(https://www.avito.ru/[^"]*?_[0-9]+)"', text)
            
            # Ищем все заголовки в тегах h3
            all_titles = re.findall(r'<h3[^>]*>(.*?)</h3>', text, re.DOTALL)
            
            # Ищем все цены
            all_prices = re.findall(r'([0-9\s]+)\s*₽', text)
            
            print(f"Альтернатива - ссылок: {len(all_links)}, заголовков: {len(all_titles)}, цен: {len(all_prices)}")
            
            min_len2 = min(len(all_links), len(all_titles), len(all_prices))
            
            for i in range(min_len2):
                title = all_titles[i]
                title = re.sub(r'<[^>]+>', '', title).strip()
                
                price = all_prices[i].replace(' ', '') + ' ₽'
                link = all_links[i]
                item_id = link.split('_')[-1]
                
                items.append({
                    'title': title,
                    'price': price,
                    'link': link,
                    'id': item_id
                })
        
        # Фильтруем только те объявления, где в названии есть что-то похожее на игрушку
       # Жесткая фильтрация ТОЛЬКО мягких игрушек
filtered_items = []
toy_keywords = [
    'мягк', 'игрушк', 'плюш', 'мишк', 'зайк', 'лошадк', 'пегас', 
    'дракон', 'единорог', 'слон', 'жираф', 'собак', 'кот', 'кошк',
    'кукум', 'лабуб', 'labubu', 'чебураш', 'антистресс', 'сквиш',
    'тянучк', 'брелок'
]

# Стоп-слова (то, что НЕ должно быть в названии)
stop_words = [
    'чехол', 'запчаст', 'авто', 'шина', 'колесо', 'телефон', 
    'прицеп', 'полуприцеп', 'samsung', 'iphone', 'xiaomi',
    'запчасти', 'автомобил', 'масло', 'аккумулятор'
]

for item in items:
    title_lower = item['title'].lower()
    
    # Проверяем, что это игрушка
    is_toy = any(keyword in title_lower for keyword in toy_keywords)
    
    # Проверяем, что это НЕ запчасть/телефон/авто
    is_not_junk = not any(stop in title_lower for stop in stop_words)
    
    if is_toy and is_not_junk:
        filtered_items.append(item)
    else:
        print(f"Отсеяно: {item['title'][:50]}...")

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
    count = 0
    for item in new_items:
        if count >= 5:  # показываем только 5
            break
            
        # Проверяем, что это действительно игрушка по ссылке
        if '/myagkie_igrushki/' not in item['link'] and '/igrushki/' not in item['link']:
            print(f"Пропущена ссылка не на игрушки: {item['link']}")
            continue
            
        short_title = item['title'][:50] + "..." if len(item['title']) > 50 else item['title']
        report += f"• {short_title} — {item['price']}\n"
        
        if item['link'] and item['link'] != "https://www.avito.ru":
            report += f"  {item['link']}\n"
        else:
            report += f"  (ссылка временно недоступна)\n"
        count += 1
    
    if count == 0:
        report += "• Нет ссылок на мягкие игрушки в выдаче\n"
    
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
            
           report += f"🆕 <b>Самые свежие:</b>\n"
for item in new_items[:5]:  # показываем 5 свежих
    short_title = item['title'][:50] + "..." if len(item['title']) > 50 else item['title']
    report += f"• {short_title} — {item['price']}\n"
    
    # Проверяем, что ссылка не пустая и не просто "https://www.avito.ru"
    if item['link'] and item['link'] != "https://www.avito.ru":
        report += f"  {item['link']}\n"
    else:
        # Если ссылки нет, добавляем предупреждение
        report += f"  (ссылка временно недоступна)\n"
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







