#Created by Na9ash1 (ArtProgs), 2026
#Refactored by Krist1nA(created by Na9ash1 (Artprogs), 2024), 2026
import requests
import json
from typing import Optional, Dict, Any, List
from bs4 import BeautifulSoup
import re

# ========== НАСТРОЙКИ ==========
API_KEY = "30272273-1df0-42d4-a390-c74309777df4"  # Замени на свой ключ!
CITY = "Новокузнецк"
COMPANY_NAME = "Мартовский кот"
# ================================

BASE_URL = "https://catalog.api.2gis.com"


def find_region_id(city_name: str) -> Optional[str]:
    """
    Находит ID региона (города) по названию
    """
    url = f"{BASE_URL}/2.0/region/search"
    params = {
        'q': city_name,
        'key': API_KEY
    }

    try:
        response = requests.get(url, params=params)
        data = response.json()

        if data.get('result') and data['result'].get('items'):
            region = data['result']['items'][0]
            region_id = region['id']
            print(f"✅ Найден регион: {region['name']} (ID: {region_id}, тип: {region.get('type', 'unknown')})")
            return region_id
        else:
            print(f"❌ Город '{city_name}' не найден")
            return None

    except Exception as e:
        print(f"❌ Ошибка при поиске региона: {e}")
        return None


def search_company(company_name: str, region_id: str) -> Optional[List[Dict[str, Any]]]:
    """
    Ищет организации по названию в указанном регионе через Places API
    """
    url = f"{BASE_URL}/3.0/items"

    fields = [
        'items.name',
        'items.address_name',
        'items.rubrics',
        'items.reviews',
        'items.point',
        'items.region_id',
        'items.segment_id'
    ]

    paid_fields = [
        'items.contact_groups',
        'items.schedule',
        'items.org'
    ]

    all_fields = fields + paid_fields

    params = {
        'q': company_name,
        'region_id': region_id,
        'fields': ','.join(all_fields),
        'key': API_KEY,
        'count': 10,
        'page': 1
    }

    try:
        response = requests.get(url, params=params)
        data = response.json()

        if response.status_code != 200:
            print(f"❌ Ошибка API: {response.status_code}")
            return None

        if data.get('result') and data['result'].get('items'):
            items = data['result']['items']
            print(f"\n📊 Найдено организаций: {len(items)} из {data['result'].get('total', 0)}")
            return items
        else:
            print(f"❌ Организация '{company_name}' не найдена в {CITY}")
            return None

    except Exception as e:
        print(f"❌ Ошибка при поиске организации: {e}")
        return None


def parse_2gis_card_direct(card_url: str) -> Dict[str, Any]:
    """
    Прямой парсинг карточки 2ГИС через requests + BeautifulSoup
    Извлекает телефон, сайт и другие данные из HTML
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
        'Connection': 'keep-alive',
    }

    result = {
        'phone_from_html': None,
        'website_from_html': None,
        'schedule_from_html': None,
        'social_links': []
    }

    try:
        response = requests.get(card_url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        html_text = response.text

        # 1. Поиск телефонов через регулярные выражения
        # Паттерн для российских номеров (разные форматы)
        phone_patterns = [
            r'\+7[\s\-\(\)]*[\d][\s\-\(\)]*[\d]{3}[\s\-\(\)]*[\d]{2}[\s\-\(\)]*[\d]{2}[\s\-\(\)]*[\d]{2}',
            r'8[\s\-\(\)]*[\d]{3}[\s\-\(\)]*[\d]{3}[\s\-\(\)]*[\d]{2}[\s\-\(\)]*[\d]{2}',
            r'[\+7|8][\s\-\(\)]*\d{3}[\s\-\(\)]*\d{3}[\s\-\(\)]*\d{2}[\s\-\(\)]*\d{2}'
        ]

        phones = []
        for pattern in phone_patterns:
            found = re.findall(pattern, html_text)
            phones.extend(found)

        # Очищаем и уникализируем телефоны
        clean_phones = []
        for phone in phones:
            clean = re.sub(r'[\s\-\(\)]', '', phone)
            if clean not in clean_phones:
                clean_phones.append(clean)

        if clean_phones:
            result['phone_from_html'] = clean_phones[0]  # Берём первый найденный

        # 2. Поиск сайта
        site_pattern = r'https?://(?:[a-zA-Z0-9\-]+\.)+[a-zA-Z]{2,}(?:/[^\s"\']*)?'
        sites = re.findall(site_pattern, html_text)

        # Фильтруем ссылки на 2GIS и соцсети
        for site in sites:
            if 'link.2gis.ru' in site and not any(
                    soc in site.lower() for soc in ['facebook', 'instagram', 't.me', 'vk.com', 'telegram', 'youtube']):
                result['website_from_html'] = site
                break

        # 3. Поиск соцсетей
        social_patterns = {
            'vk': r'https?://(?:vk\.com|vkontakte\.ru)[^\s"\']*',
            'telegram': r'https?://t\.me/[^\s"\']*',
            'instagram': r'https?://(?:www\.)?instagram\.com/[^\s"\']*',
            'facebook': r'https?://(?:www\.)?facebook\.com/[^\s"\']*'
        }

        for social_name, pattern in social_patterns.items():
            found = re.findall(pattern, html_text)
            if found:
                result['social_links'].extend(found)

        # 4. Поиск в JSON-LD (структурированные данные)
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get('@type') == 'LocalBusiness':
                    if data.get('telephone') and not result['phone_from_html']:
                        result['phone_from_html'] = data.get('telephone')
                    if data.get('url') and not result['website_from_html']:
                        result['website_from_html'] = data.get('url')
            except:
                pass

        # 5. Поиск часов работы
        schedule_patterns = [
            r'Часы работы[:\s]*([^<>\n]+)',
            r'Режим работы[:\s]*([^<>\n]+)',
            r'пн-вс[\s]*[^\n]+',
            r'ежедневно[\s]*[^\n]+'
        ]

        for pattern in schedule_patterns:
            found = re.findall(pattern, html_text, re.IGNORECASE)
            if found:
                result['schedule_from_html'] = found[0].strip()
                break

        print(f"      🔍 Парсинг карточки: сайт {'найден' if result['website_from_html'] else 'не найден'}, "
              f"телефон {'найден' if result['phone_from_html'] else 'не найден'}")

        return result

    except requests.exceptions.RequestException as e:
        print(f"      ⚠️ Ошибка при парсинге карточки: {e}")
        return result


def extract_company_info(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Извлекает информацию об организации из ответа API
    """
    result = {
        'id': item.get('id'),
        'name': item.get('name'),
        'address': item.get('address_name'),
        'type': item.get('type'),
        'rubrics': [],
        'rating': None,
        'reviews_count': None,
        'phones': [],
        'website': None,
        'social_links': [],
        'schedule': None,
        'coordinates': None
    }

    # Рубрики (категории)
    rubrics = item.get('rubrics', [])
    for rubric in rubrics:
        if rubric.get('name'):
            result['rubrics'].append(rubric['name'])

    # Рейтинг и отзывы
    reviews = item.get('reviews', {})
    if reviews.get('general_rating'):
        result['rating'] = reviews['general_rating']
    if reviews.get('count'):
        result['reviews_count'] = reviews['count']

    # Координаты
    point = item.get('point', {})
    if point.get('lat') and point.get('lon'):
        result['coordinates'] = f"{point['lat']}, {point['lon']}"

    # Контакты из API (если есть доступ)
    contact_groups = item.get('contact_groups', [])
    for group in contact_groups:
        for contact in group.get('contacts', []):
            contact_type = contact.get('type')
            contact_value = contact.get('value')

            if contact_type == 'phone':
                result['phones'].append(contact_value)
            elif contact_type == 'website':
                result['website'] = contact_value
            elif contact_type in ['vk', 'telegram', 'facebook', 'instagram']:
                result['social_links'].append(contact_value)

    # Часы работы из API (если есть доступ)
    schedule = item.get('schedule', {})
    if schedule.get('text'):
        result['schedule'] = schedule['text']

    return result


def get_2gis_card_url(region_slug: str, company_id: str) -> str:
    """
    Формирует URL карточки организации на сайте 2ГИС
    """
    return f"https://2gis.ru/{region_slug}/firm/{company_id}"


def find_region_slug(city_name: str) -> Optional[str]:
    """
    Находит URL-слаг города для формирования ссылки на карточку
    """
    translit_map = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'e',
        'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
        'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
        'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
        'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya'
    }
    slug = ''.join(translit_map.get(c, c) for c in city_name.lower())
    return slug


# ========== ЗАПУСК ==========
if __name__ == "__main__":
    print("=" * 70)
    print(f"🔍 Поиск: '{COMPANY_NAME}' в городе {CITY}")
    print("=" * 70)

    # Шаг 1: Находим ID региона
    region_id = find_region_id(CITY)

    if not region_id:
        print("\n❌ Город не найден. Проверь название или API-ключ.")
        exit()

    # Шаг 2: Ищем организацию
    companies = search_company(COMPANY_NAME, region_id)

    if not companies:
        print("\n💡 Советы:")
        print("   - Проверь, есть ли организация в 2ГИС")
        print("   - Попробуй более короткое название")
        print("   - Убедись, что API-ключ активен")
        exit()

    # Шаг 3: Выводим результаты
    print("\n" + "=" * 70)
    print("📊 РЕЗУЛЬТАТЫ ПОИСКА:")
    print("=" * 70)

    region_slug = find_region_slug(CITY)

    for i, company in enumerate(companies, 1):
        # Получаем данные из API
        info = extract_company_info(company)

        print(f"\n{i}. 🏢 {info['name']}")
        print(f"   🆔 ID: {info['id']}")
        print(f"   📍 Адрес: {info['address']}")

        if info['rubrics']:
            print(f"   🏷️  Категории: {', '.join(info['rubrics'][:3])}")

        if info['rating']:
            print(f"   ⭐ Рейтинг: {info['rating']} ({info['reviews_count'] or 'нет'} отзывов)")

        # Данные из API (могут быть пустыми)
        if info['phones']:
            print(f"   📞 Телефоны (API): {', '.join(info['phones'])}")

        if info['website']:
            print(f"   🌐 Сайт (API): {info['website']}")

        if info['schedule']:
            print(f"   🕐 Часы работы (API): {info['schedule']}")

        # Формируем ссылку на карточку
        card_url = get_2gis_card_url(region_slug, info['id'])
        print(f"   🔗 Карточка 2ГИС: {card_url}")

        # Парсим карточку напрямую (пытаемся получить телефон и сайт)
        print(f"\n   🔍 Парсинг HTML карточки...")
        parsed_data = parse_2gis_card_direct(card_url)

        if parsed_data['phone_from_html']:
            print(f"   📞 Телефон (из HTML): {parsed_data['phone_from_html']}")

        if parsed_data['website_from_html']:
            print(f"   🌐 Сайт (из HTML): {parsed_data['website_from_html']}")

        if parsed_data['schedule_from_html']:
            print(f"   🕐 Часы работы (из HTML): {parsed_data['schedule_from_html']}")

        if parsed_data['social_links']:
            print(f"   🔗 Соцсети (из HTML): {', '.join(parsed_data['social_links'][:3])}")

        print("-" * 50)



import time

access_token = "vk1.a.JoKrQQ7Z0e6PqteQfxCBPmG87T5_LKyRYq-9qNP2c31Wz7ivGZrNGKEyRdYbt67G3whLACCfWyfGHkPRhzV5CjguWhyfHprvl6SxEjK9Ioz_nig5nN7fA2AUMBrwh9C9qDu7JIRPg49Dk1WhjSAqSs1AbJ57f5NVZZRZqSMVtl7kgMKIMMlbsNNfmxLrU8le-8U4429BlNdKW7xSf_e9gw"
name = "Мартовский кот Новокузнецк"

# Шаг 1: Ищем группы по ключевому слову
search_url = "https://api.vk.com/method/groups.search"
search_params = {
    'q': name,
    'type': 'group',
    'access_token': access_token,
    'v': '5.131',
    'count': 1
}

response = requests.get(search_url, params=search_params)
data = response.json()

if 'error' in data:
    print(f"❌ Ошибка: {data['error']['error_msg']}")
    exit()

groups = data['response']['items']
total_found = data['response']['count']

print("=" * 70)
print(f"🔍 РЕЗУЛЬТАТЫ ПОИСКА: '{name}'")
print("=" * 70)
print(f"📊 Всего найдено: {total_found} групп")
print(f"📋 Показано подробно: {len(groups)} групп")
print("-" * 70)

# Шаг 2: Для каждой группы получаем детальную информацию (включая количество участников)
for i, group in enumerate(groups, 1):
    group_id = group['id']

    # Получаем детальную информацию о группе
    details_url = "https://api.vk.com/method/groups.getById"
    details_params = {
        'group_id': group_id,
        'fields': 'members_count,description,status,activity',
        'access_token': access_token,
        'v': '5.131'
    }

    details_response = requests.get(details_url, params=details_params)
    details_data = details_response.json()

    # Небольшая задержка, чтобы не превысить лимиты API
    time.sleep(0.34)

    if 'error' not in details_data and details_data['response']:
        group_info = details_data['response'][0]

        # Красивый вывод
        print(f"\n{i}. 📌 {group_info.get('name', 'Без названия')}")
        print(f"   🆔 ID: {group_info.get('id', 'Нет данных')}")

        # Теперь количество участников будет отображаться корректно!
        members_count = group_info.get('members_count', 0)
        print(f"   👥 Участников: {members_count:,}")

        print(f"   🔗 Ссылка: https://vk.com/club{group_info.get('id', '')}")

        # Описание (если есть)
        if 'description' in group_info and group_info['description']:
            desc = group_info['description']
            print(f"   📝 Описание: {desc}")

        # Статус (если есть)
        if 'status' in group_info and group_info['status']:
            status = group_info['status'][:80] + '...' if len(group_info['status']) > 80 else group_info['status']
            print(f"   💬 Статус: {status}")

        # Деятельность (если есть)
        if 'activity' in group_info and group_info['activity']:
            print(f"   🏷️  Деятельность: {group_info['activity']}")
    else:
        # Если не удалось получить детали, выводим базовую информацию
        print(f"\n{i}. 📌 {group.get('name', 'Без названия')}")
        print(f"   🆔 ID: {group.get('id', 'Нет данных')}")
        print(f"   👥 Участников: не удалось получить")

    print("-" * 50)

print("\n" + "=" * 70)
print("✅ Поиск завершен")

print(parse_2gis_card_direct("https://2gis.ru/novokuznetsk/firm/70000001030166579"))