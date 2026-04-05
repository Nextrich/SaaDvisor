#Created by Na9ash1 (ArtProgs), 2026
#Refactored by Krist1nA(created by Na9ash1 (Artprogs), 2024), 2026
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
from typing import Dict, List, Any, Optional
import json
import re
import ollama
from datetime import datetime


class AuditService:
    """Все проверки бизнеса"""

    @staticmethod
    def is_valid_website(url: str) -> bool:
        """Проверка, является ли URL валидным сайтом (не WhatsApp, не Telegram и т.д.)"""
        if not url:
            return False

        invalid_patterns = [
            'wa.me', 'whatsapp.com', 'whatsapp',  # WhatsApp
            't.me', 'telegram',  # Telegram
            'vk.com', 'vkontakte',  # VK
            'facebook.com', 'fb.com',  # Facebook
            'instagram.com',  # Instagram
            'youtube.com',  # YouTube
            'twitter.com', 'x.com',  # Twitter
            'tiktok.com',  # TikTok
            'mailto:',  # Email
            'tel:',  # Телефон
            'w3.org',  # Заглушка
            'example.com',  # Пример
            'localhost',  # Локальный
            '127.0.0.1',  # Локальный
        ]

        url_lower = url.lower()
        for pattern in invalid_patterns:
            if pattern in url_lower:
                return False

        # Проверка на наличие домена верхнего уровня
        domain_pattern = r'https?://(?:[a-zA-Z0-9\-]+\.)+[a-zA-Z]{2,}(?:/[^\s"\']*)?'
        if not re.match(domain_pattern, url):
            return False

        return True

    @staticmethod
    async def run_full_audit(business) -> Dict[str, Any]:
        """Запуск всех проверок"""
        coordinator = AuditCoordinator(business)
        return await coordinator.run_full_audit()

    @staticmethod
    async def check_meta_tags(url: str) -> Dict[str, Any]:
        """Проверка мета-тегов"""
        if not url or not AuditService.is_valid_website(url):
            return {'score': 0, 'issues': ['Сайт не указан или указан некорректно'], 'data': {}}

        try:
            response = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
            soup = BeautifulSoup(response.text, 'html.parser')

            title = soup.find('title')
            description = soup.find('meta', attrs={'name': 'description'})
            h1 = soup.find('h1')

            issues = []
            score = 100

            if not title or len(title.text.strip()) < 10:
                issues.append('Заголовок слишком короткий или отсутствует')
                score -= 40
            elif len(title.text) > 70:
                issues.append('Заголовок слишком длинный (больше 70 символов)')
                score -= 20

            if not description or not description.get('content'):
                issues.append('Отсутствует описание (meta description)')
                score -= 30
            elif len(description.get('content', '')) < 50:
                issues.append('Описание слишком короткое')
                score -= 15

            if not h1:
                issues.append('Нет заголовка H1 на странице')
                score -= 20

            return {
                'score': max(0, score),
                'issues': issues,
                'data': {
                    'title': title.text.strip() if title else None,
                    'description': description.get('content') if description else None,
                    'has_h1': bool(h1),
                    'h1_text': h1.text.strip() if h1 else None
                }
            }
        except Exception as e:
            return {'score': 0, 'issues': [f'Ошибка проверки: {str(e)[:100]}'], 'data': {}}

    @staticmethod
    async def check_speed(url: str) -> Dict[str, Any]:
        """Проверка скорости через PageSpeed API"""
        if not url or not AuditService.is_valid_website(url):
            return {'score': 0, 'issues': ['Сайт не указан']}

        try:
            api_url = f"https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url={url}&strategy=MOBILE"
            response = requests.get(api_url, timeout=15)

            if response.status_code == 200:
                data = response.json()
                score = data.get('lighthouseResult', {}).get('categories', {}).get('performance', {}).get('score', 0)
                score = int(score * 100)

                issues = []
                if score < 50:
                    issues.append('Сайт загружается очень медленно, клиенты уходят')
                elif score < 80:
                    issues.append('Скорость загрузки ниже среднего')

                return {'score': score, 'issues': issues}
        except:
            pass

        return {'score': 50, 'issues': ['Не удалось проверить скорость, но это важно для SEO']}

    @staticmethod
    async def check_search_visibility(business_name: str, city: str, website_url: str = None) -> Dict[str, Any]:
        """Проверка видимости в поиске - находится ли сайт в топе выдачи"""
        result = {
            'score': 0,
            'max_score': 7,
            'issues': [],
            'position': None,
            'search_query': None,
            'found_websites': [],
            'all_results': []
        }

        if not website_url or not AuditService.is_valid_website(website_url):
            result['issues'] = ['Сайт не указан или указан некорректно (WhatsApp, Telegram и т.д.)']
            return result

        try:
            query = f"{business_name} {city}" if city else business_name
            result['search_query'] = query

            search_url = f"https://www.google.com/search?q={quote_plus(query)}"

            response = requests.get(
                search_url,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'},
                timeout=15
            )

            soup = BeautifulSoup(response.text, 'html.parser')

            from urllib.parse import urlparse
            target_domain = urlparse(website_url).netloc.replace('www.', '')

            position = None
            position_count = 0
            found_websites = []
            all_results = []

            for link in soup.find_all('a'):
                href = link.get('href', '')
                if '/url?q=' in href and 'google.com' not in href:
                    position_count += 1
                    url = href.split('/url?q=')[1].split('&')[0]
                    parsed_url = urlparse(url)
                    current_domain = parsed_url.netloc.replace('www.', '')

                    title_elem = link.find_previous('h3')
                    title = title_elem.get_text() if title_elem else 'Без заголовка'

                    all_results.append({
                        'position': position_count,
                        'url': url,
                        'domain': current_domain,
                        'title': title
                    })

                    if AuditService.is_valid_website(url) and current_domain:
                        found_websites.append({
                            'position': position_count,
                            'url': url,
                            'domain': current_domain,
                            'title': title
                        })

                    if target_domain in current_domain or current_domain in target_domain:
                        position = position_count

                    if position_count >= 20:
                        break

            result['found_websites'] = found_websites
            result['all_results'] = all_results

            if position is None:
                result['issues'] = [f'Сайт не найден в топ-20 поисковой выдачи Google по запросу "{query}"']
                result['score'] = 0
            elif position <= 5:
                result['issues'] = []
                result['score'] = 7
            elif position <= 10:
                result['issues'] = ['Сайт не в топ-5 выдачи']
                result['score'] = 5
            elif position <= 15:
                result['issues'] = ['Сайт не в топ-10 выдачи']
                result['score'] = 3
            else:
                result['issues'] = ['Сайт не в топ-15 выдачи']
                result['score'] = 1

            return result

        except Exception as e:
            result['issues'] = [f'Не удалось проверить позицию в поиске: {str(e)[:100]}']
            return result

    @staticmethod
    async def check_content_quality(url: str) -> Dict[str, Any]:
        """Проверка качества контента сайта"""
        if not url or not AuditService.is_valid_website(url):
            return {'score': 0, 'issues': ['Сайт не указан'], 'found_keywords': []}

        keywords = {
            'services': ['услуг', 'услуги', 'услугах', 'предлагаем', 'оказываем', 'сервис', 'обслуживание'],
            'products': ['ассортимент', 'товар', 'продукция', 'каталог', 'магазин', 'купить', 'продажа'],
            'prices': ['цена', 'стоимость', 'прайс', 'прайс-лист', 'оплата', 'руб'],
            'contacts': ['контакт', 'связь', 'адрес', 'телефон', 'email', 'режим работы', 'график'],
            'about': ['о нас', 'компания', 'преимуществ', 'гарантия', 'доставка']
        }

        try:
            response = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
            soup = BeautifulSoup(response.text, 'html.parser')

            for script in soup(["script", "style"]):
                script.decompose()

            text = soup.get_text().lower()

            found_keywords = {}
            total_score = 0

            for category, words in keywords.items():
                found = [word for word in words if word in text]
                found_keywords[category] = found
                if found:
                    total_score += 3

            categories_found = len([k for k, v in found_keywords.items() if v])
            if categories_found >= 4:
                total_score += 3
            elif categories_found >= 3:
                total_score += 2
            elif categories_found >= 2:
                total_score += 1

            total_score = min(total_score, 15)

            issues = []
            if total_score < 5:
                issues.append('На сайте недостаточно информации об услугах и ассортименте')
            elif total_score < 10:
                issues.append('На сайте есть базовая информация, но можно добавить больше деталей')

            return {
                'score': total_score,
                'max_score': 15,
                'issues': issues,
                'found_keywords': found_keywords
            }

        except Exception as e:
            return {'score': 5, 'issues': [f'Не удалось проверить качество контента'], 'found_keywords': {}}

    @staticmethod
    async def parse_2gis_card_direct(card_url: str) -> Dict[str, Any]:
        """Прямой парсинг карточки 2ГИС"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
        }

        result = {
            'phone_from_html': None,
            'website_from_html': None,
            'schedule_from_html': None,
            'social_links': [],
            'vk_link': None
        }

        try:
            response = requests.get(card_url, headers=headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            html_text = response.text

            phone_patterns = [
                r'\+7[\s\-\(\)]*[\d][\s\-\(\)]*[\d]{3}[\s\-\(\)]*[\d]{2}[\s\-\(\)]*[\d]{2}[\s\-\(\)]*[\d]{2}',
                r'8[\s\-\(\)]*[\d]{3}[\s\-\(\)]*[\d]{3}[\s\-\(\)]*[\d]{2}[\s\-\(\)]*[\d]{2}',
            ]

            phones = []
            for pattern in phone_patterns:
                found = re.findall(pattern, html_text)
                phones.extend(found)

            clean_phones = []
            for phone in phones:
                clean = re.sub(r'[\s\-\(\)]', '', phone)
                if clean not in clean_phones:
                    clean_phones.append(clean)

            if clean_phones:
                result['phone_from_html'] = clean_phones[0]

            site_pattern = r'https?://(?:[a-zA-Z0-9\-]+\.)+[a-zA-Z]{2,}(?:/[^\s"\']*)?'
            sites = re.findall(site_pattern, html_text)

            for site in sites:
                if 'link.2gis.ru' in site:
                    continue
                if 'vk.com' in site or 'vkontakte' in site:
                    result['vk_link'] = site
                    result['social_links'].append(site)
                elif not result['website_from_html'] and '2gis' not in site and 'w3.org' not in site:
                    if AuditService.is_valid_website(site):
                        result['website_from_html'] = site

            scripts = soup.find_all('script', type='application/ld+json')
            for script in scripts:
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict) and data.get('@type') == 'LocalBusiness':
                        if data.get('telephone') and not result['phone_from_html']:
                            result['phone_from_html'] = data.get('telephone')
                        if data.get('url') and not result['website_from_html']:
                            if 'vk.com' not in data.get('url', '') and 'w3.org' not in data.get('url', ''):
                                if AuditService.is_valid_website(data.get('url', '')):
                                    result['website_from_html'] = data.get('url')
                except:
                    pass

            return result

        except Exception as e:
            return result

    @staticmethod
    async def check_2gis(business_name: str, city: str) -> Dict[str, Any]:
        """Проверка 2ГИС"""
        API_KEY = "30272273-1df0-42d4-a390-c74309777df4"

        result = {
            'has_page': False,
            'has_description': False,
            'has_address_and_contacts': False,
            'rating': None,
            'reviews_count': None,
            'phones': [],
            'website': None,
            'vk_link': None,
            'address': None,
            'card_url': None
        }

        issues = []
        score = 0

        def find_region_id(city_name: str) -> Optional[str]:
            url = f"https://catalog.api.2gis.com/2.0/region/search"
            params = {'q': city_name, 'key': API_KEY}
            try:
                response = requests.get(url, params=params, timeout=10)
                data = response.json()
                if data.get('result') and data['result'].get('items'):
                    return data['result']['items'][0]['id']
            except:
                pass
            return None

        def search_company(company_name: str, region_id: str) -> Optional[List[Dict]]:
            url = f"https://catalog.api.2gis.com/3.0/items"
            params = {
                'q': company_name,
                'region_id': region_id,
                'fields': 'items.name,items.address_name,items.rubrics,items.reviews,items.contact_groups,items.schedule',
                'key': API_KEY,
                'count': 5
            }
            try:
                response = requests.get(url, params=params, timeout=10)
                data = response.json()
                if data.get('result') and data['result'].get('items'):
                    return data['result']['items']
            except:
                pass
            return None

        try:
            region_id = find_region_id(city)
            if region_id:
                companies = search_company(business_name, region_id)
                if companies:
                    company = companies[0]
                    result['has_page'] = True
                    score += 6

                    if company.get('address_name'):
                        result['address'] = company['address_name']
                        result['has_address_and_contacts'] = True
                        score += 5

                    contact_groups = company.get('contact_groups', [])
                    for group in contact_groups:
                        for contact in group.get('contacts', []):
                            if contact.get('type') == 'phone':
                                phone = contact.get('value')
                                if phone and phone not in result['phones']:
                                    result['phones'].append(phone)
                            elif contact.get('type') == 'website':
                                website = contact.get('value')
                                if website and AuditService.is_valid_website(website):
                                    result['website'] = website

                    rubrics = company.get('rubrics', [])
                    if rubrics:
                        result['has_description'] = True
                        score += 4
                        result['rubrics'] = [r.get('name') for r in rubrics if r.get('name')]

                    reviews = company.get('reviews', {})
                    if reviews.get('general_rating'):
                        result['rating'] = reviews['general_rating']
                    if reviews.get('count'):
                        result['reviews_count'] = reviews['count']

                    company_id = company.get('id')
                    if company_id:
                        translit_map = {
                            'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'e',
                            'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
                            'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
                            'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
                            'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya'
                        }
                        city_slug = ''.join(translit_map.get(c, c) for c in city.lower()).replace(' ', '-')
                        result['card_url'] = f"https://2gis.ru/{city_slug}/firm/{company_id}"

                        parsed_data = await AuditService.parse_2gis_card_direct(result['card_url'])
                        if parsed_data['phone_from_html'] and parsed_data['phone_from_html'] not in result['phones']:
                            result['phones'].append(parsed_data['phone_from_html'])
                        if parsed_data['website_from_html'] and AuditService.is_valid_website(
                                parsed_data['website_from_html']):
                            result['website'] = parsed_data['website_from_html']
                        if parsed_data['vk_link']:
                            result['vk_link'] = parsed_data['vk_link']

            if not result['has_page']:
                issues.append('Нет страницы в 2ГИС')
            if not result['has_description']:
                issues.append('Нет описания в 2ГИС')
            if not result['has_address_and_contacts']:
                issues.append('Не указаны адрес и контакты в 2ГИС')

        except Exception as e:
            issues.append(f'Ошибка проверки 2ГИС: {str(e)[:50]}')

        return {
            'score': score,
            'max_score': 15,
            'issues': issues,
            'data': result
        }

    @staticmethod
    async def check_yandex_maps(business_name: str, city: str) -> Dict[str, Any]:
        """Проверка Яндекс Карт"""
        issues = []
        score = 15

        result = {
            'has_page': True,
            'has_description': True,
            'has_address_and_contacts': True,
            'rating': None,
            'reviews_count': None
        }

        return {
            'score': score,
            'max_score': 15,
            'issues': issues,
            'data': result
        }

    @staticmethod
    async def check_social_vk(group_url: str = None, business_name: str = None, city: str = "") -> Dict[str, Any]:
        """Проверка VK"""
        access_token = "vk1.a.JoKrQQ7Z0e6PqteQfxCBPmG87T5_LKyRYq-9qNP2c31Wz7ivGZrNGKEyRdYbt67G3whLACCfWyfGHkPRhzV5CjguWhyfHprvl6SxEjK9Ioz_nig5nN7fA2AUMBrwh9C9qDu7JIRPg49Dk1WhjSAqSs1AbJ57f5NVZZRZqSMVtl7kgMKIMMlbsNNfmxLrU8le-8U4429BlNdKW7xSf_e9gw"

        result = {
            'has_group': False,
            'group_id': None,
            'group_name': None,
            'members_count': 0,
            'description': None,
            'status': None,
            'url': None,
            'website_from_vk': None,
            'last_post_date': None,
            'last_post_date_str': None,
            'posts_count': 0,
            'activity_level': 'unknown'
        }

        issues = []
        score = 0

        if group_url:
            import re
            match = re.search(r'(?:vk\.com|vkontakte\.ru)/(?:club|public)?([0-9]+|[a-zA-Z0-9_]+)', group_url)
            if match:
                screen_name = match.group(1)
                try:
                    get_url = "https://api.vk.com/method/groups.getById"
                    params = {
                        'group_id': screen_name,
                        'fields': 'members_count,description,status,activity,website',
                        'access_token': access_token,
                        'v': '5.131'
                    }
                    response = requests.get(get_url, params=params, timeout=10)
                    data = response.json()

                    if 'error' not in data and data.get('response'):
                        group_info = data['response'][0]
                        group_id = group_info.get('id')
                        result['has_group'] = True
                        result['group_id'] = group_id
                        result['group_name'] = group_info.get('name')
                        result['members_count'] = group_info.get('members_count', 0)
                        result['description'] = group_info.get('description')
                        result['status'] = group_info.get('status')
                        result['url'] = group_url
                        website_from_vk = group_info.get('website')
                        if website_from_vk and AuditService.is_valid_website(website_from_vk):
                            result['website_from_vk'] = website_from_vk
                        score += 6

                        if group_id:
                            posts_data = await AuditService._get_vk_last_posts(group_id, access_token)
                            result['last_post_date'] = posts_data['last_post_date']
                            result['last_post_date_str'] = posts_data['last_post_date_str']
                            result['posts_count'] = posts_data['posts_count']
                            result['activity_level'] = posts_data['activity_level']

                except:
                    pass

        if not result['has_group'] and business_name:
            try:
                search_url = "https://api.vk.com/method/groups.search"
                search_params = {
                    'q': f"{business_name} {city}" if city else business_name,
                    'type': 'group',
                    'access_token': access_token,
                    'v': '5.131',
                    'count': 1
                }

                response = requests.get(search_url, params=search_params, timeout=10)
                data = response.json()

                if 'error' not in data and data.get('response', {}).get('items'):
                    group = data['response']['items'][0]
                    group_id = group['id']
                    result['has_group'] = True
                    score += 6
                    result['group_id'] = group_id
                    result['url'] = f"https://vk.com/club{group_id}"

                    details_url = "https://api.vk.com/method/groups.getById"
                    details_params = {
                        'group_id': group_id,
                        'fields': 'members_count,description,status,activity,website',
                        'access_token': access_token,
                        'v': '5.131'
                    }

                    details_response = requests.get(details_url, params=details_params, timeout=10)
                    details_data = details_response.json()

                    if 'error' not in details_data and details_data.get('response'):
                        group_info = details_data['response'][0]
                        result['group_name'] = group_info.get('name')
                        result['members_count'] = group_info.get('members_count', 0)
                        result['description'] = group_info.get('description')
                        result['status'] = group_info.get('status')
                        website_from_vk = group_info.get('website')
                        if website_from_vk and AuditService.is_valid_website(website_from_vk):
                            result['website_from_vk'] = website_from_vk

                        posts_data = await AuditService._get_vk_last_posts(group_id, access_token)
                        result['last_post_date'] = posts_data['last_post_date']
                        result['last_post_date_str'] = posts_data['last_post_date_str']
                        result['posts_count'] = posts_data['posts_count']
                        result['activity_level'] = posts_data['activity_level']

            except:
                pass

        if result['has_group']:
            if result['description'] or result['status']:
                score += 9
            else:
                issues.append('Нет описания или информации в сообществе VK')

            score += 6
            score += 4

            if result['activity_level'] == 'high':
                score += 5
            elif result['activity_level'] == 'medium':
                score += 3
            elif result['activity_level'] == 'low':
                score += 1
                issues.append(f'Низкая активность в VK: всего {result["posts_count"]} постов за 30 дней')
            elif result['activity_level'] == 'none':
                issues.append(f'Нет активности в VK: последний пост был {result["last_post_date_str"] or "никогда"}')

            members = result['members_count']
            if members >= 1000:
                score += 5
            elif members >= 500:
                score += 3
            elif members >= 100:
                score += 1
            else:
                issues.append(f'Мало подписчиков в VK ({members})')
        else:
            issues.append('Не найдена страница VK')

        return {
            'score': score,
            'max_score': 30,
            'issues': issues,
            'data': result
        }

    @staticmethod
    async def _get_vk_last_posts(group_id: int, access_token: str) -> Dict[str, Any]:
        """Получение информации о последних постах VK"""
        result = {
            'last_post_date': None,
            'last_post_date_str': None,
            'posts_count': 0,
            'activity_level': 'unknown'
        }

        try:
            wall_url = "https://api.vk.com/method/wall.get"
            wall_params = {
                'owner_id': -group_id,
                'count': 10,
                'access_token': access_token,
                'v': '5.131'
            }

            response = requests.get(wall_url, params=wall_params, timeout=10)
            data = response.json()

            if 'error' not in data and data.get('response', {}).get('items'):
                items = data['response']['items']

                thirty_days_ago = datetime.now().timestamp() - (30 * 24 * 60 * 60)
                recent_posts = [post for post in items if post.get('date', 0) > thirty_days_ago]
                result['posts_count'] = len(recent_posts)

                if result['posts_count'] >= 12:
                    result['activity_level'] = 'high'
                elif result['posts_count'] >= 4:
                    result['activity_level'] = 'medium'
                elif result['posts_count'] > 0:
                    result['activity_level'] = 'low'
                else:
                    result['activity_level'] = 'none'

                # ✅ ИСПРАВЛЕНО: пропускаем закреплённые посты
                normal_posts = [post for post in items if not post.get('is_pinned', 0)]

                if normal_posts:
                    # Берём самый новый пост (с максимальной датой)
                    last_post = max(normal_posts, key=lambda x: x.get('date', 0))
                    last_post_timestamp = last_post.get('date', 0)
                    if last_post_timestamp:
                        result['last_post_date'] = last_post_timestamp
                        last_post_datetime = datetime.fromtimestamp(last_post_timestamp)
                        result['last_post_date_str'] = last_post_datetime.strftime('%d.%m.%Y %H:%M')

                        days_since_last_post = (datetime.now() - last_post_datetime).days
                        if days_since_last_post > 30 and result['activity_level'] != 'none':
                            result['activity_level'] = 'none'

        except Exception as e:
            print(f"Error getting VK posts: {e}")

        return result

    @staticmethod
    async def check_website_with_content(business, existing_vk_url: str = None) -> Dict[str, Any]:
        """Расширенная проверка сайта с учетом контента и поисковой видимости"""
        result = {
            'has_website': False,
            'is_valid_website': False,
            'speed_score': 0,
            'meta_tags_score': 0,
            'content_score': 0,
            'search_visibility_score': 0,
            'website_url': None,
            'found_vk_on_site': None,
            'website_validation_error': None
        }

        issues = []
        score = 0

        website_url = getattr(business, 'website', None)
        is_valid = website_url and AuditService.is_valid_website(website_url)

        if website_url and website_url != "http://www.w3.org/2000/svg":
            result['has_website'] = True
            result['website_url'] = website_url
            result['is_valid_website'] = is_valid

            if not is_valid:
                if 'wa.me' in website_url or 'whatsapp' in website_url:
                    result['website_validation_error'] = 'Ссылка на WhatsApp вместо сайта'
                    issues.append('Указана ссылка на WhatsApp вместо полноценного сайта - это снижает доверие и SEO')
                elif 't.me' in website_url or 'telegram' in website_url:
                    result['website_validation_error'] = 'Ссылка на Telegram вместо сайта'
                    issues.append('Указана ссылка на Telegram вместо сайта - клиенты ожидают увидеть полноценный сайт')
                elif 'vk.com' in website_url:
                    result['website_validation_error'] = 'Ссылка на VK вместо сайта'
                    issues.append('Указана ссылка на VK вместо сайта - это не заменяет полноценный сайт')
                else:
                    result['website_validation_error'] = 'Некорректный URL сайта'
                    issues.append('Указан некорректный URL сайта')

                return {
                    'score': 0,
                    'max_score': 35,
                    'issues': issues,
                    'data': result
                }

            score += 8

            try:
                response = requests.get(website_url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
                html_text = response.text
                vk_pattern = r'https?://(?:vk\.com|vkontakte\.ru)/[^\s"\']*'
                vk_matches = re.findall(vk_pattern, html_text)
                if vk_matches:
                    result['found_vk_on_site'] = vk_matches[0]
            except:
                pass

            speed_result = await AuditService.check_speed(website_url)
            result['speed_score'] = speed_result['score']
            if speed_result['score'] >= 80:
                score += 5
            elif speed_result['score'] >= 50:
                score += 3
            else:
                issues.append('Сайт работает медленно')

            meta_result = await AuditService.check_meta_tags(website_url)
            result['meta_tags_score'] = meta_result['score']

            content_result = await AuditService.check_content_quality(website_url)
            result['content_score'] = content_result['score']

            info_score = (meta_result['score'] * 0.3 + content_result['score'] * 0.7)
            info_score = min(15, info_score)
            score += info_score
            result['info_constructive_score'] = info_score

            if meta_result['issues']:
                issues.extend(meta_result['issues'])
            if content_result['issues']:
                issues.extend(content_result['issues'])

            visibility_result = await AuditService.check_search_visibility(
                business.name,
                getattr(business, 'city', ''),
                website_url
            )
            result['search_visibility_score'] = visibility_result['score']
            result['search_position'] = visibility_result.get('position')
            result['search_query'] = visibility_result.get('search_query')
            result['found_websites_in_search'] = visibility_result.get('found_websites', [])
            result['all_search_results'] = visibility_result.get('all_results', [])

            score += visibility_result['score']
            if visibility_result['issues']:
                issues.extend(visibility_result['issues'])

        else:
            issues.append('Сайт не добавлен в систему или указан некорректно')

        return {
            'score': int(score),
            'max_score': 35,
            'issues': issues,
            'data': result
        }


class AuditCoordinator:
    """Координатор аудита - управляет порядком проверок"""

    def __init__(self, business):
        self.business = business
        self.city = getattr(business, 'city', '')

        self.found_website = None
        self.all_found_websites = []
        self.found_vk_url = None
        self.found_2gis_url = None

        original_website = getattr(business, 'website', None)
        if original_website and AuditService.is_valid_website(original_website):
            self.found_website = original_website
            self.all_found_websites.append({
                'source': 'business_profile',
                'url': original_website,
                'is_valid': True
            })

        self.results = {}

    async def run_full_audit(self) -> Dict[str, Any]:
        """Запуск полного аудита с правильным порядком"""

        gis_result = await AuditService.check_2gis(self.business.name, self.city)
        self.results['2gis'] = gis_result

        gis_data = gis_result.get('data', {})
        gis_website = gis_data.get('website')
        if gis_website and AuditService.is_valid_website(gis_website):
            if not self.found_website:
                self.found_website = gis_website
            self.all_found_websites.append({
                'source': '2gis',
                'url': gis_website,
                'is_valid': True
            })

        if gis_data.get('vk_link') and not self.found_vk_url:
            self.found_vk_url = gis_data['vk_link']

        original_website = self.business.website
        if self.found_website:
            self.business.website = self.found_website

        website_result = await AuditService.check_website_with_content(self.business, self.found_vk_url)
        self.results['website'] = website_result

        website_data = website_result.get('data', {})
        found_in_search = website_data.get('found_websites_in_search', [])
        for site in found_in_search:
            if site.get('url') and AuditService.is_valid_website(site['url']):
                if not any(existing['url'] == site['url'] for existing in self.all_found_websites):
                    self.all_found_websites.append({
                        'source': 'google_search',
                        'url': site['url'],
                        'position': site.get('position'),
                        'title': site.get('title'),
                        'is_valid': True
                    })

        if website_data.get('found_vk_on_site') and not self.found_vk_url:
            self.found_vk_url = website_data['found_vk_on_site']

        self.business.website = original_website

        vk_result = await AuditService.check_social_vk(
            group_url=self.found_vk_url,
            business_name=self.business.name,
            city=self.city
        )
        self.results['vk'] = vk_result

        vk_data = vk_result.get('data', {})
        vk_website = vk_data.get('website_from_vk')
        if vk_website and AuditService.is_valid_website(vk_website):
            if not self.found_website:
                self.found_website = vk_website
            self.all_found_websites.append({
                'source': 'vk',
                'url': vk_website,
                'is_valid': True
            })

            if self.found_website and (
                    not self.business.website or self.business.website == "http://www.w3.org/2000/svg"):
                self.business.website = self.found_website
                updated_website_result = await AuditService.check_website_with_content(self.business, self.found_vk_url)
                if updated_website_result['score'] > website_result['score'] or not website_result['data'][
                    'has_website']:
                    self.results['website'] = updated_website_result
                self.business.website = original_website

        # Убираем Яндекс Карты и перераспределяем баллы
        # Вместо yandex_maps добавляем бонусные баллы за полноту данных

        scores = []
        for key in ['website', 'vk', '2gis']:  # Убрали yandex_maps
            if key in self.results:
                scores.append(self.results[key]['score'])

        # Бонусные баллы (было 5, теперь 15, так как убрали Яндекс)
        bonus = 0
        if self.results.get('2gis', {}).get('score', 0) > 0:
            bonus += 5  # Есть в 2ГИС
        if self.results.get('vk', {}).get('score', 0) > 0:
            bonus += 5  # Есть в VK
        if self.results.get('website', {}).get('data', {}).get('has_website', False):
            bonus += 5  # Есть сайт

        scores.append(bonus)

        overall_score = sum(scores)

        all_issues = []
        for result in self.results.values():
            if isinstance(result, dict) and 'issues' in result:
                all_issues.extend(result['issues'])

        return {
            'overall_score': int(overall_score),
            'max_score': 100,
            'details': self.results,
            'bonus': bonus,
            'all_issues': all_issues,
            'found_connections': {
                'website_from_2gis': gis_data.get('website'),
                'website_from_2gis_valid': AuditService.is_valid_website(gis_data.get('website', '')),
                'vk_from_2gis': gis_data.get('vk_link'),
                'vk_from_website': website_data.get('found_vk_on_site'),
                'website_from_vk': vk_data.get('website_from_vk'),
                'website_from_vk_valid': AuditService.is_valid_website(vk_data.get('website_from_vk', ''))
            },
            'all_found_websites': self.all_found_websites,
            'search_query_used': website_data.get('search_query')
        }


class LLMService:
    """Генерация советов через нейросеть Llama с глубоким анализом"""

    @staticmethod
    async def generate_advice(business_name: str, city: str, audit_results: Dict) -> List[Dict]:
        """Генерация персонализированных советов на основе детального JSON"""

        print(f"🔍 LLMService.generate_advice called for {business_name}, {city}")

        # Сначала пробуем получить советы из fallback (гарантированно работают)
        fallback_advice = await LLMService._generate_fallback_advice(audit_results, business_name, city)
        print(f"📋 Fallback advice generated: {len(fallback_advice)} items")

        # Пробуем получить улучшенные советы от LLM
        try:
            # Проверяем, доступен ли ollama
            import ollama
            print("✅ Ollama module imported successfully")

            # Проверяем, запущен ли сервер
            try:
                # Пробуем получить список моделей
                models = ollama.list()
                print(f"✅ Ollama server available. Models: {models}")
            except Exception as e:
                print(f"❌ Ollama server not responding: {e}")
                return fallback_advice[:5]

            details = audit_results.get('details', {})

            gis = details.get('2gis', {})
            gis_data = gis.get('data', {})

            website = details.get('website', {})
            website_data = website.get('data', {})

            vk = details.get('vk', {})
            vk_data = vk.get('data', {})

            prompt = f"""Ты эксперт по цифровому маркетингу. Проанализируй ТОЛЬКО эти реальные данные и дай 3-5 конкретных советов.

    БИЗНЕС: {business_name}
    ГОРОД: {city}

    === ТЕКУЩЕЕ СОСТОЯНИЕ ===

    1. 2ГИС (оценка {gis.get('score', 0)} из {gis.get('max_score', 15)}):
       - Есть страница: {gis_data.get('has_page', False)}
       - Рейтинг: {gis_data.get('rating', 'нет')}
       - Отзывы: {gis_data.get('reviews_count', 0)} шт.

    2. САЙТ (оценка {website.get('score', 0)} из {website.get('max_score', 35)}):
       - Есть сайт: {website_data.get('has_website', False)}
       - Скорость: {website_data.get('speed_score', 0)} баллов
       - Мета-теги: {website_data.get('meta_tags_score', 0)} баллов
       - Позиция в Google: {website_data.get('search_position', 'не найдена')}

    3. VK (оценка {vk.get('score', 0)} из {vk.get('max_score', 30)}):
       - Есть группа: {vk_data.get('has_group', False)}
       - Подписчиков: {vk_data.get('members_count', 0)} чел.

    Верни ТОЛЬКО JSON. Пример:
    {{"advice": [{{"category": "website", "title": "Ускорьте сайт", "description": "Скорость {website_data.get('speed_score', 0)} баллов - это медленно", "action": "1. Сжать изображения\\n2. Включить кэш", "urgency": "high", "expected_impact": "Рост конверсии"}}]}}"""

            print(f"📤 Sending prompt to Ollama (length: {len(prompt)})")

            response = ollama.chat(
                model='llama3',
                messages=[
                    {
                        'role': 'system',
                        'content': 'Ты эксперт по маркетингу. Отвечай только в формате JSON. Будь максимально конкретным. Используй русский язык.'
                    },
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                stream=False,
                options={
                    'temperature': 0.3,
                    'top_p': 0.9,
                }
            )

            print(f"📥 Received response from Ollama")

            advice_text = response['message']['content']
            print(f"Response preview: {advice_text[:200]}...")

            import json
            import re
            json_match = re.search(r'\{.*\}', advice_text, re.DOTALL)
            if json_match:
                advice_data = json.loads(json_match.group())
                llm_advice = advice_data.get('advice', [])
                print(f"🤖 LLM generated {len(llm_advice)} advice items")
                if llm_advice and len(llm_advice) > 0:
                    # Объединяем с fallback, но не дублируем
                    existing_titles = set([a.get('title') for a in fallback_advice])
                    for adv in llm_advice:
                        if adv.get('title') not in existing_titles:
                            fallback_advice.append(adv)
                            print(f"  Added: {adv.get('title')}")
            else:
                print("❌ No JSON found in response")

        except ImportError as e:
            print(f"❌ Ollama not installed: {e}")
            print("💡 Run: pip install ollama")
        except Exception as e:
            print(f"❌ LLM error: {type(e).__name__}: {e}")

        print(f"📋 Total advice items: {len(fallback_advice)}")
        return fallback_advice[:5]

    @staticmethod
    async def _generate_fallback_advice(audit_results: Dict, business_name: str, city: str) -> List[Dict]:
        """Генерация fallback советов (всегда работает)"""
        advice = []
        details = audit_results.get('details', {})

        # ===== 2ГИС =====
        gis = details.get('2gis', {})
        gis_data = gis.get('data', {})
        gis_score = gis.get('score', 0)
        gis_max = gis.get('max_score', 15)

        if gis_score < gis_max:
            if not gis_data.get('has_page'):
                advice.append({
                    "category": "2gis",
                    "title": f"Добавьте компанию в 2ГИС",
                    "description": f"В {city} 2ГИС - основной инструмент поиска. Без карточки вас не находят большинство потенциальных клиентов",
                    "action": "1. Зарегистрируйтесь в 2ГИС Бизнес\n2. Добавьте компанию\n3. Укажите точный адрес и телефон\n4. Загрузите 5-10 фото\n5. Напишите описание",
                    "urgency": "critical",
                    "expected_impact": "Новый канал клиентов, +30-50% обращений"
                })
            elif gis_data.get('reviews_count') is None or gis_data.get('reviews_count', 0) < 3:
                advice.append({
                    "category": "2gis",
                    "title": "Соберите отзывы в 2ГИС",
                    "description": f"У вас хороший рейтинг {gis_data.get('rating', '')}, но мало отзывов. Компании с 10+ отзывами получают в 2-3 раза больше звонков",
                    "action": "1. Попросите 5-7 постоянных клиентов оставить отзыв\n2. Предложите скидку 5-10% за отзыв\n3. Ответьте на все отзывы\n4. Разместите QR-код на кассе",
                    "urgency": "high",
                    "expected_impact": "Рост доверия и звонков на 30-40%"
                })

        # ===== САЙТ =====
        website = details.get('website', {})
        website_data = website.get('data', {})
        website_score = website.get('score', 0)
        website_max = website.get('max_score', 35)
        is_valid_website = website_data.get('is_valid_website', False)
        validation_error = website_data.get('website_validation_error', '')

        if website_score < website_max:
            if not is_valid_website:
                if 'WhatsApp' in validation_error:
                    advice.append({
                        "category": "website",
                        "title": "Замените ссылку на WhatsApp полноценным сайтом",
                        "description": f"Сейчас вместо сайта указана ссылка на WhatsApp. Это отпугивает 70% клиентов и убивает SEO-продвижение",
                        "action": "1. Зарегистрируйте домен\n2. Создайте одностраничный сайт-визитку (Tilda, Wix, Nethouse)\n3. Укажите адрес, телефон, режим работы, цены\n4. Добавьте фото товаров\n5. Перенаправьте трафик с WhatsApp на новый сайт",
                        "urgency": "critical",
                        "expected_impact": "Рост доверия и конверсии в 2-3 раза, появление в поиске Google"
                    })
                elif 'Telegram' in validation_error:
                    advice.append({
                        "category": "website",
                        "title": "Создайте сайт вместо ссылки на Telegram",
                        "description": "Telegram-канал не заменяет сайт. Клиенты ожидают увидеть полноценный сайт с информацией о компании",
                        "action": "1. Создайте сайт-визитку\n2. Перенесите важную информацию из Telegram\n3. Добавьте форму обратной связи\n4. Настройте аналитику\n5. Оставьте Telegram как дополнительный канал",
                        "urgency": "critical",
                        "expected_impact": "Увеличение конверсии из поиска на 50-80%"
                    })
                elif 'VK' in validation_error:
                    advice.append({
                        "category": "website",
                        "title": "Создайте отдельный сайт вместо группы VK",
                        "description": "Группа VK - это хорошо, но она не заменяет полноценный сайт. Клиенты хотят видеть цены и услуги в удобном формате",
                        "action": "1. Создайте сайт-визитку\n2. Скопируйте информацию из VK\n3. Добавьте форму заказа\n4. Настройте аналитику\n5. Оставьте VK для коммуникации",
                        "urgency": "high",
                        "expected_impact": "Рост доверия и конверсии на 40-60%"
                    })
            elif not website_data.get('has_website'):
                advice.append({
                    "category": "website",
                    "title": f"У {business_name} нет сайта",
                    "description": "Без сайта вы теряете клиентов, которые ищут информацию в интернете. Конкуренты с сайтом обходят вас",
                    "action": "1. Создайте сайт-визитку (Tilda, Wix, Nethouse)\n2. Укажите адрес, телефон, режим работы\n3. Добавьте фото товаров\n4. Опубликуйте цены\n5. Подключите онлайн-запись",
                    "urgency": "critical",
                    "expected_impact": "Новый канал клиентов, +40-60% заказов"
                })
            elif website_data.get('speed_score', 100) < 50:
                advice.append({
                    "category": "website",
                    "title": "Срочно ускорьте сайт",
                    "description": f"Скорость сайта {website_data.get('speed_score', 0)} баллов. При загрузке >3 секунд 40% посетителей уходят",
                    "action": "1. Оптимизируйте изображения (WebP формат)\n2. Включите кэширование\n3. Используйте CDN\n4. Удалите тяжелые скрипты\n5. Проверьте хостинг",
                    "urgency": "high",
                    "expected_impact": "Снижение отказов на 20-30%, рост конверсии"
                })
            elif website_data.get('search_position') is None or website_data.get('search_position', 20) > 10:
                advice.append({
                    "category": "website",
                    "title": f"Продвиньте сайт в поиске {city}",
                    "description": f"Сайт не в топ-10 Google. Клиенты не могут вас найти",
                    "action": "1. Добавьте на сайт ключевые фразы с городом\n2. Зарегистрируйтесь в Яндекс.Вебмастер\n3. Настройте карту сайта\n4. Разместите ссылки на соцсети\n5. Закажите SEO-аудит",
                    "urgency": "high",
                    "expected_impact": "Рост органического трафика на 50-100%"
                })

        # ===== VK =====
        vk = details.get('vk', {})
        vk_data = vk.get('data', {})
        vk_score = vk.get('score', 0)
        vk_max = vk.get('max_score', 30)

        if vk_score < vk_max:
            if not vk_data.get('has_group'):
                advice.append({
                    "category": "vk",
                    "title": f"Создайте сообщество VK для {business_name}",
                    "description": "Активное VK-сообщество - бесплатный канал коммуникации с клиентами и продвижения",
                    "action": "1. Создайте сообщество VK\n2. Заполните описание и контакты\n3. Добавьте адрес и телефон\n4. Загрузите обложку и аватар\n5. Пригласите первых клиентов",
                    "urgency": "high",
                    "expected_impact": "Прямой канал связи с 500+ клиентами за 3 месяца"
                })
            elif vk_data.get('activity_level') == 'none':
                advice.append({
                    "category": "vk",
                    "title": "Возобновите активность в VK",
                    "description": f"Последний пост был {vk_data.get('last_post_date_str', 'давно')}. Клиенты думают, что бизнес закрыт",
                    "action": "1. Опубликуйте пост о возобновлении работы\n2. Начните публиковать новости 3-4 раза в неделю\n3. Делайте фото товаров\n4. Показывайте процесс работы\n5. Отвечайте на комментарии",
                    "urgency": "high",
                    "expected_impact": "Рост охвата и возврат лояльных клиентов"
                })
            elif vk_data.get('members_count', 0) < 500 and vk_data.get('members_count', 0) > 0:
                advice.append({
                    "category": "vk",
                    "title": f"Привлеките подписчиков в VK (сейчас {vk_data.get('members_count', 0)})",
                    "description": "Мало подписчиков = низкий охват. Конкуренты в вашей нише имеют 2000+ подписчиков",
                    "action": "1. Добавьте виджет группы на сайт\n2. Приглашайте клиентов подписаться при покупке\n3. Запустите конкурс 'Приведи друга'\n4. Сделайте полезный бесплатный контент\n5. Используйте таргетированную рекламу",
                    "urgency": "medium",
                    "expected_impact": "Рост подписчиков до 2000+ за 2 месяца"
                })

        return advice