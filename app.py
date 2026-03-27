from flask import Flask, render_template, request, jsonify, send_file
import os
import shutil
import string
import requests
import re
import ssl
import urllib.parse
from urllib.parse import urlparse
import sys
import random
import json
import tempfile
import gdown
import base64
from collections import Counter

sys.setrecursionlimit(10000)
ssl._create_default_https_context = ssl._create_unverified_context

app = Flask(__name__, template_folder='.')


# ============================================================
# TEMPLATE ENGINE DETECTION
# ============================================================

def detect_template_engine(template_dir):
    """
    Автоматически определяет тип движка по содержимому example.html.
    Поддерживаемые движки: 'SUSHI', 'KROSS', 'SLOTSITE'

    Приоритетный способ переопределения: создайте файл '_engine.txt'
    внутри папки шаблона с содержимым SUSHI, KROSS или SLOTSITE.
    """
    # Приоритет: ручное переопределение через файл
    engine_override = os.path.join(template_dir, '_engine.txt')
    if os.path.exists(engine_override):
        try:
            with open(engine_override, 'r', encoding='utf-8') as f:
                engine = f.read().strip().upper()
            if engine in ('SUSHI', 'KROSS', 'SLOTSITE', 'SUSHI2'):
                print(f"[ENGINE] Переопределён из _engine.txt: {engine}")
                return engine
        except:
            pass

    # Авто-определение по содержимому example.html
    example_path = os.path.join(template_dir, 'example.html')
    if not os.path.exists(example_path):
        # Берём первый попавшийся HTML-файл
        for fname in os.listdir(template_dir):
            if fname.endswith('.html'):
                example_path = os.path.join(template_dir, fname)
                break

    try:
        with open(example_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Elementor-шаблоны — движок SLOTSITE
        if 'data-elementor-type' in content or 'data-widget_type' in content:
            print("[ENGINE] Определён: SLOTSITE (Elementor)")
            return 'SLOTSITE'

        # SUSHI2: обфусцированные CSS-классы этого шаблона (fe601a4c=main, n0dc0f73=wrapper, hf0d9=nav)
        if ('fe601a4c' in content or 'n0dc0f73' in content) and 'hf0d9' in content:
            print("[ENGINE] Определён: SUSHI2")
            return 'SUSHI2'

        # Bootstrap / кастомный стиль — движок KROSS
        if ('seo-content-inject' in content
                or 'modern-card' in content
                or 'menu-header' in content
                or 'menu-footer-1' in content):
            print("[ENGINE] Определён: KROSS (Bootstrap)")
            return 'KROSS'

        # По умолчанию — движок SUSHI
        print("[ENGINE] Определён: SUSHI (default)")
        return 'SUSHI'
    except Exception as e:
        print(f"[ENGINE] Ошибка при определении: {e}. Используем SUSHI по умолчанию.")
        return 'SUSHI'


# ============================================================
# ROUTE: ANALYZE COLORS — определение цветов шаблона
# ============================================================

@app.route('/analyze_colors', methods=['POST'])
def analyze_colors():
    data = request.json
    template_name = data.get('template_name')

    if not template_name:
        return jsonify({"status": "error", "message": "Шаблон не указан"})

    template_dir = os.path.join("templates_pool", template_name)
    if not os.path.exists(template_dir):
        return jsonify({"status": "error", "message": "Папка шаблона не найдена"})

    engine = detect_template_engine(template_dir)
    color_counts = Counter()

    if engine in ('SUSHI', 'SUSHI2'):  # SUSHI/WINZ: hex + var() fallback; HTML/CSS/JSON; top-20
        pattern_elementor = re.compile(
            r'--e-global-color-[\w-]+:\s*(#[0-9a-fA-F]{3,8})(?![0-9a-fA-F])', re.IGNORECASE)
        pattern_var_fallback = re.compile(
            r'var\(--[\w-]+,\s*(#[0-9a-fA-F]{3,8})\)', re.IGNORECASE)
        pattern_any_hex = re.compile(
            r'(#[0-9a-fA-F]{6}|#[0-9a-fA-F]{3})(?![0-9a-fA-F])', re.IGNORECASE)
        scan_ext = ('.html', '.css', '.json')
        excluded = {'#FFFFFF', '#000000'}

        for root, dirs, files in os.walk(template_dir):
            for file_name in files:
                if file_name.endswith(scan_ext):
                    file_path = os.path.join(root, file_name)
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        found = (pattern_elementor.findall(content)
                                 + pattern_var_fallback.findall(content)
                                 + pattern_any_hex.findall(content))
                        for c in found:
                            c = c.upper()
                            if len(c) == 4:
                                c = '#' + c[1]*2 + c[2]*2 + c[3]*2
                            if c not in excluded:
                                color_counts[c] += 1
                    except:
                        pass
        top_colors = [color for color, _ in color_counts.most_common(20)]

    elif engine == 'KROSS':
        # KROSS: любые CSS-переменные + любые hex; HTML/CSS/JSON/JS; top-30
        pattern_vars = re.compile(
            r'--[\w-]+:\s*(#[0-9a-fA-F]{3,8})(?![0-9a-fA-F])', re.IGNORECASE)
        pattern_any_hex = re.compile(
            r'(#[0-9a-fA-F]{6}|#[0-9a-fA-F]{3})(?![0-9a-fA-F])', re.IGNORECASE)
        scan_ext = ('.html', '.css', '.json', '.js')
        excluded = {'#FFFFFF', '#000000', '#FFF', '#000'}

        for root, dirs, files in os.walk(template_dir):
            for file_name in files:
                if file_name.endswith(scan_ext):
                    file_path = os.path.join(root, file_name)
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        found = pattern_vars.findall(content) + pattern_any_hex.findall(content)
                        for c in found:
                            c = c.upper()
                            if len(c) == 4:
                                c = '#' + c[1]*2 + c[2]*2 + c[3]*2
                            if c not in excluded:
                                color_counts[c] += 1
                    except:
                        pass
        top_colors = [color for color, _ in color_counts.most_common(30)]

    else:  # SLOTSITE
        # SLOTSITE: только Elementor глобальные цвета; HTML/CSS/JSON; top-30
        pattern_global = re.compile(
            r'--e-global-color-[\w-]+:\s*(#[0-9a-fA-F]{3,8})(?![0-9a-fA-F])', re.IGNORECASE)
        scan_ext = ('.html', '.css', '.json')

        for root, dirs, files in os.walk(template_dir):
            for file_name in files:
                if file_name.endswith(scan_ext):
                    file_path = os.path.join(root, file_name)
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        for c in pattern_global.findall(content):
                            c = c.upper()
                            if len(c) == 4:
                                c = '#' + c[1]*2 + c[2]*2 + c[3]*2
                            color_counts[c] += 1
                    except:
                        pass
        top_colors = [color for color, _ in color_counts.most_common(30)]

    return jsonify({"status": "success", "colors": top_colors})


# ============================================================
# SHARED UTILITY FUNCTIONS (общие для всех движков)
# ============================================================

def hex_to_rgb_str(hex_str):
    """Конвертирует HEX-цвет в строку RGB-компонентов."""
    hex_str = hex_str.lstrip('#')
    if len(hex_str) == 3:
        hex_str = ''.join(c*2 for c in hex_str)
    if len(hex_str) >= 6:
        try:
            return f"{int(hex_str[0:2], 16)}, {int(hex_str[2:4], 16)}, {int(hex_str[4:6], 16)}"
        except:
            return None
    return None


def replace_custom_colors(dst_site_dir, old_colors, new_colors):
    """Заменяет цвета (HEX, short-HEX, RGB, RGBA) во всех файлах сайта."""
    replacements = []
    for old, new in zip(old_colors, new_colors):
        old_clean = old.strip().lower()
        new_clean = new.strip().lower()

        if old_clean and new_clean and new_clean != old_clean and new_clean != "без изм.":
            replacements.append((
                re.compile(re.escape(old_clean) + r'(?![0-9a-fA-F])', re.IGNORECASE),
                new_clean
            ))
            # Короткая HEX-форма (#aabbcc → #abc)
            if (len(old_clean) == 7
                    and old_clean[1] == old_clean[2]
                    and old_clean[3] == old_clean[4]
                    and old_clean[5] == old_clean[6]):
                short_hex = '#' + old_clean[1] + old_clean[3] + old_clean[5]
                replacements.append((
                    re.compile(re.escape(short_hex) + r'(?![0-9a-fA-F])', re.IGNORECASE),
                    new_clean
                ))
            # RGB / RGBA
            old_rgb = hex_to_rgb_str(old_clean)
            new_rgb = hex_to_rgb_str(new_clean)
            if old_rgb and new_rgb:
                old_rgb_regex = old_rgb.replace(' ', r'\s*')
                replacements.append((
                    re.compile(r'rgb\(\s*' + old_rgb_regex + r'\s*\)', re.IGNORECASE),
                    f"rgb({new_rgb})"
                ))
                replacements.append((
                    re.compile(r'rgba\(\s*' + old_rgb_regex + r'\s*,', re.IGNORECASE),
                    f"rgba({new_rgb},"
                ))

    if not replacements:
        return

    for root, dirs, files in os.walk(dst_site_dir):
        for file_name in files:
            if file_name.endswith(('.html', '.css', '.js', '.json', '.svg')):
                file_path = os.path.join(root, file_name)
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    new_content = content
                    for pattern, replacement in replacements:
                        new_content = pattern.sub(replacement, new_content)
                    if content != new_content:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                except:
                    pass


def bust_browser_css_cache(dst_site_dir):
    """Добавляет версионный суффикс ?v=XXXXX к ссылкам на CSS/JS файлы."""
    cache_buster = str(random.randint(10000, 99999))
    for root, dirs, files in os.walk(dst_site_dir):
        for file_name in files:
            if file_name.endswith('.html'):
                file_path = os.path.join(root, file_name)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    content = re.sub(
                        r'(\.css|\.js)(?:\?[^\"\'\\s>]+)?([\"\']])',
                        r'\1?v=' + cache_buster + r'\2',
                        content
                    )
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                except:
                    pass


def shift_elements(dst_site_dir):
    """Сдвигает body и img на 1px для сброса пиксельной идентичности (антифрод)."""
    x_shift = '0px'
    y_shift = random.choice(['-1px', '1px, 0'])
    img_x = '0px'
    img_y = random.choice(['-1px', '1px'])

    shift_style = f"""
    <style id="anti-fraud-shift">
        body {{ position: relative !important; left: {x_shift} !important; top: {y_shift} !important; }}
        img {{ transform: translate({img_x}, {img_y}) !important; }}
    </style>
    """
    for root, dirs, files in os.walk(dst_site_dir):
        for file_name in files:
            if file_name.endswith('.html'):
                file_path = os.path.join(root, file_name)
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                if '</head>' in content:
                    content = content.replace('</head>', f'{shift_style}\n</head>')
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)


def generate_sitemap_and_robots(dst_site_dir, domain, pages_to_keep):
    """Генерирует sitemap.xml и robots.txt."""
    sitemap_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
    sitemap_content += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    sitemap_content += (
        f'  <url>\n    <loc>https://{domain}/</loc>\n'
        f'    <changefreq>daily</changefreq>\n    <priority>1.0</priority>\n  </url>\n'
    )
    for item in pages_to_keep:
        if (item not in ['index.html', 'image', 'images', 'css', 'js', 'fonts']
                and not item.endswith(('.html', '.js', '.css', '.png', '.jpg'))):
            sitemap_content += (
                f'  <url>\n    <loc>https://{domain}/{item}/</loc>\n'
                f'    <changefreq>weekly</changefreq>\n    <priority>0.8</priority>\n  </url>\n'
            )
    sitemap_content += '</urlset>'

    with open(os.path.join(dst_site_dir, 'sitemap.xml'), 'w', encoding='utf-8') as f:
        f.write(sitemap_content)

    robots_content = f"User-agent: *\nAllow: /\n\nSitemap: https://{domain}/sitemap.xml\n"
    with open(os.path.join(dst_site_dir, 'robots.txt'), 'w', encoding='utf-8') as f:
        f.write(robots_content)


def generate_policy_slug(name):
    """Конвертирует название политики в URL-slug (поддержка RU/EN/ES/PL)."""
    lower_name = name.lower()
    if any(w in lower_name for w in ['privacy', 'конфиденц', 'privacidad']):
        return 'privacy'
    if any(w in lower_name for w in ['terms', 'услови', 'regulamin', 'términos', 'terminos']):
        return 'terms'
    if any(w in lower_name for w in ['cookie', 'куки']):
        return 'cookie'
    if any(w in lower_name for w in ['responsible', 'ответствен', 'odpowiedzialna', 'responsable']):
        return 'responsible'
    return re.sub(r'[^a-z0-9]+', '-', lower_name).strip('-')


def get_old_brand_name(example_path):
    """Извлекает название бренда из существующего HTML-шаблона."""
    try:
        with open(example_path, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f.read(), 'lxml')
        og_site_name = soup.find('meta', attrs={'property': 'og:site_name'})
        if og_site_name and og_site_name.get('content'):
            return og_site_name['content'].split(':')[0].split('-')[0].strip()
        if soup.title and soup.title.string:
            match = re.search(r'^(.*?)(?:\s+Login|\s+Demo|\s+\-|\s+\:)', soup.title.string, re.I)
            if match:
                return match.group(1).strip()
    except:
        pass
    return None


def get_old_aff_url(example_path):
    """Извлекает партнёрскую ссылку из существующего HTML-шаблона."""
    try:
        with open(example_path, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f.read(), 'lxml')
        links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if href.startswith('http') and 'google.com' not in href:
                links.append(href)
        for btn in soup.find_all(attrs={'data-sf-a': True}):
            links.append(btn['data-sf-a'])
        if links:
            return Counter(links).most_common(1)[0][0]
    except:
        pass
    return None


def get_old_domain(example_path):
    """Извлекает домен из og:url шаблона. Используется только движком SUSHI."""
    try:
        with open(example_path, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f.read(), 'lxml')
        og_url = soup.find('meta', attrs={'property': 'og:url'})
        if og_url and og_url.get('content'):
            parsed_url = urlparse(og_url['content'])
            if parsed_url.netloc:
                return parsed_url.netloc.replace('www.', '')
    except:
        pass
    return None


def cleanup_unused_folders(dst_site_dir, pages_to_keep):
    """Удаляет неиспользуемые папки и служебные файлы (example.html, policy.html)."""
    protected = ['image', 'images', 'css', 'js', 'fonts', 'webfonts',
                 'wp-content', 'wp-includes', 'promo']
    for item in os.listdir(dst_site_dir):
        item_path = os.path.join(dst_site_dir, item)
        if os.path.isdir(item_path):
            if item not in pages_to_keep and item not in protected:
                shutil.rmtree(item_path)
    for cleanup_file in ['example.html', 'policy.html']:
        path = os.path.join(dst_site_dir, cleanup_file)
        if os.path.exists(path):
            os.remove(path)


def update_file_content(file_path, replacements):
    """Простая замена плейсхолдеров в текстовом файле."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    for key, value in replacements.items():
        content = content.replace(key, str(value))
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)


# ============================================================
# IMAGE DOWNLOAD FUNCTIONS
# ============================================================

def download_gdrive_image(drive_url, save_path):
    """
    Простая загрузка одного файла с Google Drive через requests.
    Используется движком SLOTSITE.
    """
    match = re.search(r'/d/([a-zA-Z0-9_-]+)', drive_url)
    if match:
        file_id = match.group(1)
        url = f'https://drive.google.com/uc?id={file_id}'
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        try:
            session = requests.Session()
            response = session.get(
                url, params={'export': 'download'}, stream=True, verify=False, headers=headers)
            for key, value in response.cookies.items():
                if key.startswith('download_warning'):
                    response = session.get(
                        url, params={'export': 'download', 'confirm': value},
                        stream=True, verify=False, headers=headers)
                    break
            if response.status_code == 200:
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                with open(save_path, 'wb') as f:
                    for chunk in response.iter_content(32768):
                        if chunk:
                            f.write(chunk)
        except:
            pass


def download_and_convert_gdrive_images(drive_links_str, page_slug, dst_site_dir, is_logo_fav=False):
    """
    Загружает изображения через gdown с изоляцией по URL.
    Логотипы/фавиконы копируются как есть (с прозрачностью).
    Контентные картинки конвертируются в PNG.
    Используется движками SUSHI и KROSS.
    """
    if (not isinstance(drive_links_str, str)
            or not drive_links_str.strip()
            or drive_links_str.lower() == 'nan'):
        return []

    img_dir = os.path.join(dst_site_dir, 'images')
    os.makedirs(img_dir, exist_ok=True)
    downloaded_paths = []

    print(f"⏳ Скачиваем картинки для [{page_slug}]: {drive_links_str}")

    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            if 'folder' in drive_links_str:
                gdown.download_folder(
                    url=drive_links_str, output=temp_dir, quiet=True, use_cookies=False)
            else:
                urls = re.findall(r'(https?://[^\s,]+)', drive_links_str)
                if not urls:
                    urls = [drive_links_str]
                for url in urls:
                    gdown.download(url=url, output=temp_dir, quiet=True, fuzzy=True)
        except Exception as e:
            print(f"❌ Ошибка загрузки по ссылке: {e}")

        downloaded_files = []
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if (ext in ['.png', '.jpg', '.jpeg', '.webp', '.gif', '.svg',
                             '.ico', '.avif', '.heic'] or not ext):
                    downloaded_files.append(os.path.join(root, file))
        downloaded_files.sort()

        limit = 2 if is_logo_fav else 3
        files_to_process = downloaded_files[:limit]

        if not files_to_process:
            print(f"⚠️ Для [{page_slug}] картинки не найдены.")
            return []

        assigned_names = []

        for i, file_path in enumerate(files_to_process):
            try:
                original_name = os.path.basename(file_path).lower()
                ext = os.path.splitext(file_path)[1].lower()
                if not ext:
                    ext = '.png'

                if is_logo_fav:
                    # Логотип/фавикон: определяем имя по оригинальному имени файла
                    if 'fav' in original_name or 'icon' in original_name:
                        filename = f"fav{ext}"
                    elif 'logo' in original_name:
                        filename = f"logo{ext}"
                    else:
                        filename = f"logo{ext}" if i == 0 else f"fav{ext}"

                    # Защита от дублей имён
                    if filename in assigned_names:
                        filename = f"fav{ext}" if filename.startswith("logo") else f"logo{ext}"

                    assigned_names.append(filename)
                    save_path = os.path.join(img_dir, filename)
                    shutil.copy2(file_path, save_path)
                    downloaded_paths.append(f"images/{filename}")
                    print(f"✅ Сохранено (лого/фав): {filename} (исходник: {original_name})")
                else:
                    # Контентная картинка: конвертируем в PNG
                    filename = f"{page_slug}_{i+1}.png"
                    save_path = os.path.join(img_dir, filename)

                    try:
                        if ext in ['.svg', '.avif', '.heic', '.gif']:
                            raise ValueError(f"Формат {ext} не поддерживается PIL")
                        img = Image.open(file_path)
                        if (img.mode in ('RGBA', 'LA')
                                or (img.mode == 'P' and 'transparency' in img.info)):
                            img = img.convert('RGBA')
                        else:
                            img = img.convert('RGB')
                        img.save(save_path, 'PNG')
                    except Exception as pil_err:
                        print(f"⚠️ Конвертация пропущена, сохраняем как есть: {pil_err}")
                        filename = f"{page_slug}_{i+1}{ext}"
                        save_path = os.path.join(img_dir, filename)
                        shutil.copy2(file_path, save_path)

                    downloaded_paths.append(f"images/{filename}")
                    print(f"✅ Успешно сохранена: {filename}")
            except Exception as e:
                print(f"❌ Ошибка обработки файла {file_path}: {e}")

    return downloaded_paths


# ============================================================
# GOOGLE DOC FETCHING — _get_gdoc_*
# (три версии — одна на каждый движок)
# ============================================================

# Текст ошибки, которую Google Docs возвращает вместо документа
_GDOC_ERROR_PHRASES = [
    "google docs encountered an error",
    "please try reloading this page",
    "coming back to it in a few minutes",
]

def _fetch_gdoc_html(export_url, headers=None, max_retries=6, delay=4):
    """
    Загружает экспортированный HTML Google Doc с автоматическим повтором.
    Если Google вернул страницу с ошибкой — ждёт delay секунд и пробует снова.
    Выбрасывает RuntimeError, если все попытки исчерпаны.
    """
    import time
    kwargs = dict(verify=False, timeout=30)
    if headers:
        kwargs['headers'] = headers

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(export_url, **kwargs)
            lower_text = response.text.lower()
            if any(phrase in lower_text for phrase in _GDOC_ERROR_PHRASES):
                print(f"⚠️  Google Docs вернул страницу с ошибкой (попытка {attempt}/{max_retries}). "
                      f"Повтор через {delay}с…")
                time.sleep(delay)
                continue
            return response
        except requests.RequestException as e:
            print(f"⚠️  Сетевая ошибка при загрузке Google Doc (попытка {attempt}/{max_retries}): {e}")
            if attempt < max_retries:
                time.sleep(delay)
    raise RuntimeError(
        f"Не удалось загрузить Google Doc после {max_retries} попыток: {export_url}"
    )

def _get_gdoc_sushi(url, dst_site_dir, page_slug):
    """
    Загружает Google Doc и извлекает контент.
    Версия SUSHI: снимает все inline-стили, поддерживает services-table для таблиц.
    """
    export_url = (url.replace('/edit?usp=sharing', '/export?format=html')
                     .replace('/edit', '/export?format=html'))
    response = _fetch_gdoc_html(export_url)
    soup = BeautifulSoup(response.text, 'lxml')

    # Очищаем атрибуты у всех тегов
    for tag in soup.find_all(True):
        tag.attrs.pop('style', None)
        tag.attrs.pop('dir', None)
        if tag.name not in ['img', 'a']:
            tag.attrs.pop('class', None)

    img_dir = os.path.join(dst_site_dir, 'image')

    for span in soup.find_all(['span', 'a', 'img']):
        if span.name == 'span':
            span.unwrap()
        elif span.name == 'a':
            href = span.get('href', '')
            if 'google.com/url?q=' in href:
                raw_url = href.split('google.com/url?q=')[1].split('&')[0]
                span['href'] = urllib.parse.unquote(raw_url)
            span.attrs = {'href': span.get('href')}
        elif span.name == 'img':
            src = span.get('src')
            if src and src.startswith('http'):
                os.makedirs(img_dir, exist_ok=True)
                try:
                    img_data = requests.get(src, verify=False).content
                    filename = f"{page_slug}_doc_img_{len(os.listdir(img_dir))}.png"
                    filepath = os.path.join(img_dir, filename)
                    with open(filepath, 'wb') as f:
                        f.write(img_data)
                    span.attrs = {}
                    span['src'] = f"/image/{filename}"
                    parent = span.find_parent('p')
                    if parent:
                        classes = parent.get('class', [])
                        if isinstance(classes, str):
                            classes = [classes]
                        if 'auto-image-row' not in classes:
                            classes.append('auto-image-row')
                        parent['class'] = classes
                except:
                    pass

    lines = []
    for tag in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'table']):
        if tag.find_parent(['ul', 'ol', 'table']) and tag.name not in ['ul', 'ol', 'table']:
            continue

        if tag.name in ['ul', 'ol', 'table']:
            if tag.name == 'table':
                tag.attrs = {'class': 'services-table'}
                for sub_tag in tag.find_all(True):
                    for attr in ['class', 'id', 'style', 'width', 'height', 'valign',
                                 'align', 'cellpadding', 'cellspacing', 'border']:
                        sub_tag.attrs.pop(attr, None)
                    if sub_tag.name in ['td', 'th']:
                        if sub_tag.get('colspan') == '1': sub_tag.attrs.pop('colspan', None)
                        if sub_tag.get('rowspan') == '1': sub_tag.attrs.pop('rowspan', None)
                if not tag.find('tbody'):
                    tbody = soup.new_tag('tbody')
                    for child in list(tag.children):
                        if getattr(child, 'name', None) == 'tr':
                            tbody.append(child.extract())
                    tag.append(tbody)
            lines.append(str(tag))
        else:
            inner_html = "".join(str(c) for c in tag.contents)
            parts = re.split(r'<br\s*/?>', inner_html, flags=re.IGNORECASE)
            for part in parts:
                part_strip = part.strip()
                if not part_strip:
                    continue
                tmp_soup = BeautifulSoup(part, 'lxml')
                part_text = tmp_soup.get_text(strip=True).lstrip('\ufeff\u200b \t')
                lower_text = part_text.lower()
                if re.match(
                    r'^(h[1-6]|title|мт|mt|desc(?:ription)?|мд|md|заголовок|название|описание)\b',
                    lower_text
                ):
                    lines.append(part_text)
                else:
                    p_class = " ".join(tag.get('class', []))
                    class_attr = f" class='{p_class}'" if p_class else ""
                    tag_name = tag.name if tag.name in ['h1','h2','h3','h4','h5','h6'] else 'p'
                    lines.append(f"<{tag_name}{class_attr}>{part_strip}</{tag_name}>")

    return "\n".join(lines)


def _get_gdoc_kross(url, dst_site_dir, page_slug):
    """
    Загружает Google Doc и извлекает контент.
    Версия KROSS: поддерживает base64-изображения, User-Agent, таблицы без class.
    """
    export_url = (url.replace('/edit?usp=sharing', '/export?format=html')
                     .replace('/edit', '/export?format=html'))
    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
    }
    response = _fetch_gdoc_html(export_url, headers=headers)
    soup = BeautifulSoup(response.text, 'lxml')

    img_dir = os.path.join(dst_site_dir, 'image')
    img_counter = 1

    for span in soup.find_all(['span', 'a', 'img']):
        if span.name == 'span':
            span.unwrap()
        elif span.name == 'a':
            href = span.get('href', '')
            if 'google.com/url?q=' in href:
                raw_url = href.split('google.com/url?q=')[1].split('&')[0]
                span['href'] = urllib.parse.unquote(raw_url)
            span.attrs = {'href': span.get('href')}
        elif span.name == 'img':
            src = span.get('src')
            if src:
                os.makedirs(img_dir, exist_ok=True)
                try:
                    filename = f"{page_slug}_doc_img_{img_counter}.png"
                    filepath = os.path.join(img_dir, filename)
                    success = False

                    if src.startswith('http'):
                        img_response = requests.get(
                            src, headers=headers, verify=False, timeout=10)
                        if img_response.status_code == 200:
                            with open(filepath, 'wb') as f:
                                f.write(img_response.content)
                            success = True
                    elif src.startswith('data:image'):
                        encoded_data = src.split(',', 1)[1]
                        with open(filepath, 'wb') as f:
                            f.write(base64.b64decode(encoded_data))
                        success = True

                    if success:
                        span.attrs = {}
                        span['src'] = f"/image/{filename}"
                        img_counter += 1
                        parent = span.find_parent('p')
                        if parent:
                            classes = parent.get('class', [])
                            if isinstance(classes, str):
                                classes = [classes]
                            if 'auto-image-row' not in classes:
                                classes.append('auto-image-row')
                            parent['class'] = classes
                except Exception:
                    pass

    lines = []
    for tag in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'table']):
        if tag.find_parent(['ul', 'ol', 'table']) and tag.name not in ['ul', 'ol', 'table']:
            continue
        if tag.name in ['ul', 'ol', 'table']:
            if tag.name == 'table':
                tag.attrs = {}  # без class — KROSS сам стилизует таблицы
                for sub_tag in tag.find_all(True):
                    for attr in ['class', 'id', 'style', 'width', 'height', 'valign',
                                 'align', 'cellpadding', 'cellspacing', 'border']:
                        sub_tag.attrs.pop(attr, None)
                    if sub_tag.name in ['td', 'th']:
                        if sub_tag.get('colspan') == '1': sub_tag.attrs.pop('colspan', None)
                        if sub_tag.get('rowspan') == '1': sub_tag.attrs.pop('rowspan', None)
                if not tag.find('tbody'):
                    tbody = soup.new_tag('tbody')
                    for child in list(tag.children):
                        if getattr(child, 'name', None) == 'tr':
                            tbody.append(child.extract())
                    tag.append(tbody)
            lines.append(str(tag))
        else:
            inner_html = "".join(str(c) for c in tag.contents)
            parts = re.split(r'<br\s*/?>', inner_html, flags=re.IGNORECASE)
            for part in parts:
                part_strip = part.strip()
                if not part_strip:
                    continue
                tmp_soup = BeautifulSoup(part, 'lxml')
                part_text = tmp_soup.get_text(strip=True).lstrip('\ufeff\u200b \t')
                lower_text = part_text.lower()
                if re.match(r'^(h[1-6]|title|мт|mt|desc|description|мд|md)', lower_text):
                    lines.append(part_text)
                else:
                    p_class = " ".join(tag.get('class', []))
                    class_attr = f" class='{p_class}'" if p_class else ""
                    lines.append(f"<p{class_attr}>{part_strip}</p>")

    return "\n".join(lines)


def _get_gdoc_slotsite(url, dst_site_dir, page_slug):
    """
    Загружает Google Doc и извлекает контент.
    Версия SLOTSITE: минимальная обработка для Elementor-шаблонов.
    """
    export_url = (url.replace('/edit?usp=sharing', '/export?format=html')
                     .replace('/edit', '/export?format=html'))
    response = _fetch_gdoc_html(export_url)
    soup = BeautifulSoup(response.text, 'lxml')

    img_dir = os.path.join(dst_site_dir, 'image')

    for span in soup.find_all(['span', 'a', 'img']):
        if span.name == 'span':
            span.unwrap()
        elif span.name == 'a':
            href = span.get('href', '')
            if 'google.com/url?q=' in href:
                raw_url = href.split('google.com/url?q=')[1].split('&')[0]
                span['href'] = urllib.parse.unquote(raw_url)
            span.attrs = {'href': span.get('href')}
        elif span.name == 'img':
            src = span.get('src')
            if src and src.startswith('http'):
                os.makedirs(img_dir, exist_ok=True)
                try:
                    img_data = requests.get(src, verify=False).content
                    filename = f"{page_slug}_doc_img_{len(os.listdir(img_dir))}.png"
                    filepath = os.path.join(img_dir, filename)
                    with open(filepath, 'wb') as f:
                        f.write(img_data)
                    span.attrs = {}
                    span['src'] = f"/image/{filename}"
                    parent = span.find_parent('p')
                    if parent:
                        classes = parent.get('class', [])
                        if isinstance(classes, str):
                            classes = [classes]
                        if 'auto-image-row' not in classes:
                            classes.append('auto-image-row')
                        parent['class'] = classes
                except:
                    pass

    lines = []
    for tag in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'table']):
        if tag.find_parent(['ul', 'ol', 'table']) and tag.name not in ['ul', 'ol', 'table']:
            continue
        if tag.name in ['ul', 'ol', 'table']:
            lines.append(str(tag))
        else:
            inner_html = "".join(str(c) for c in tag.contents)
            parts = re.split(r'<br\s*/?>', inner_html, flags=re.IGNORECASE)
            for part in parts:
                part_strip = part.strip()
                if not part_strip:
                    continue
                tmp_soup = BeautifulSoup(part, 'lxml')
                part_text = tmp_soup.get_text(strip=True).lstrip('\ufeff\u200b \t')
                lower_text = part_text.lower()
                if re.match(r'^(h[1-6]|title|мт|mt|desc|description|мд|md)', lower_text):
                    lines.append(part_text)
                else:
                    p_class = " ".join(tag.get('class', []))
                    class_attr = f" class='{p_class}'" if p_class else ""
                    lines.append(f"<p{class_attr}>{part_strip}</p>")

    return "\n".join(lines)


def get_gdoc_text_and_assets(url, dst_site_dir, page_slug, engine='SUSHI'):
    """Диспетчер: выбирает версию загрузчика по движку."""
    if engine == 'KROSS':
        return _get_gdoc_kross(url, dst_site_dir, page_slug)
    elif engine == 'SLOTSITE':
        return _get_gdoc_slotsite(url, dst_site_dir, page_slug)
    else:  # SUSHI
        return _get_gdoc_sushi(url, dst_site_dir, page_slug)


# ============================================================
# DOCUMENT PARSING — parse_doc_to_json
# (две версии: сложная SUSHI и стандартная KROSS/SLOTSITE)
# ============================================================

def _parse_doc_sushi(text):
    """
    Сложный парсер SUSHI с эвристиками:
    - авто-определение H1/H2 без явных маркеров
    - hero_desc (подзаголовок под H1)
    - авто-определение FAQ-секций
    - поддержка HTML-тегов <h1>/<h2>/<h3> как маркеров
    """
    data = {"seo_title": "", "meta_desc": "", "h1": "", "hero_desc": "", "sections": {}}
    lines = [line.strip() for line in text.split('\n') if line.strip()]

    current_heading = "main_text"
    data["sections"][current_heading] = {"title": "", "content": []}

    patterns = {
        'seo_title': r'^\(?\(?(?:(?:seo\s*)?title|мт|mt|заголовок|название|title seo)\b\)?'
                     r'(?:\s*\([^)]+\))?\s*[:\-–—|]*',
        'meta_desc': r'^\(?\(?(?:(?:meta\s*)?desc(?:ription)?|мд|md|описание|description seo)\b\)?'
                     r'(?:\s*\([^)]+\))?\s*[:\-–—|]*',
        'h1':        r'^\(?\(?(?:h1|heading 1|заголовок 1|h 1)\b\)?(?:\s*\([^)]+\))?\s*[:\-–—|]*',
        'h2':        r'^\(?\(?(?:h2|heading 2|заголовок 2|h 2)\b\)?(?:\s*\([^)]+\))?\s*[:\-–—|]*',
        'h3':        r'^\(?\(?(?:h3|heading 3|заголовок 3|h 3)\b\)?(?:\s*\([^)]+\))?\s*[:\-–—|]*'
    }

    i = 0
    just_parsed_h1 = False
    content_started = False

    faq_keywords = ['faq', 'вопрос', 'pytania', 'frequent', 'fragen', 'частые', 'questions', 'q&a', 'qna']
    redundant_faq_titles = [
        'faq', 'frequently asked questions', 'frequently asked questions (faq)',
        'faq - frequently asked questions', 'частые вопросы', 'q&a',
        'questions and answers', 'frequent questions'
    ]
    faq_start_regex = r'^(faq|frequently asked questions|q&a|qna|частые вопросы|вопросы и ответы)\b'

    while i < len(lines):
        line = lines[i]
        clean_line = re.sub(r'<[^>]+>', '', line).strip()
        lower_clean = clean_line.lower()

        is_faq_context = any(w in current_heading.lower() for w in faq_keywords)
        is_faq_header_like = re.match(faq_start_regex, lower_clean)

        # Защита от дублей заголовков внутри FAQ-секции
        if is_faq_context:
            if ((is_faq_header_like and not lower_clean.endswith('?'))
                    or lower_clean in redundant_faq_titles) and len(clean_line) <= 150:
                i += 1
                continue

        matched_key = None
        marker_end_pos = 0

        # 1. Явные маркеры
        for key, pattern in patterns.items():
            match = re.match(pattern, lower_clean, re.IGNORECASE)
            if match:
                matched_key = key
                marker_end_pos = match.end()
                break

        # 2. HTML-теги как маркеры
        if not matched_key:
            ll = line.strip().lower()
            if ll.startswith('<h1') and '</h1' in ll:
                matched_key = 'h1'
            elif ll.startswith('<h2') and '</h2' in ll:
                matched_key = 'h1' if not data.get('h1') else 'h2'
            elif ll.startswith('<h3') and '</h3' in ll:
                matched_key = 'h3'
            if matched_key:
                marker_end_pos = 0

        # 3. Создание секции FAQ из заголовка-похожей строки
        if not matched_key:
            if ((is_faq_header_like or lower_clean in redundant_faq_titles)
                    and not is_faq_context and not lower_clean.endswith('?')):
                matched_key = 'h2'
                marker_end_pos = 0

        # 4. Эвристика для неявных заголовков
        if not matched_key and clean_line:
            length_ok = 3 <= len(clean_line) <= 150
            last_char = clean_line[-1] if clean_line else ''

            is_bold = False
            ll2 = line.strip().lower()
            if '<b>' in ll2 or '<strong>' in ll2 or ll2.startswith(('<b', '<strong')):
                bold_text = re.sub(
                    r'<[^>]+>', '',
                    "".join(re.findall(
                        r'<b[^>]*>.*?</b>|<strong[^>]*>.*?</strong>', line, re.IGNORECASE))
                )
                if len(bold_text.strip()) >= len(clean_line) * 0.7:
                    is_bold = True

            # А. Вопрос (H3) внутри FAQ
            if is_faq_context and last_char == '?':
                matched_key = 'h3'
                marker_end_pos = 0
            # Б. Неявный H1 (первая строка без маркера)
            elif not data.get('h1') and not content_started and length_ok:
                if ('<img' not in ll2 and '<a ' not in ll2 and 'http' not in ll2):
                    matched_key = 'h1'
                    marker_end_pos = 0
            # В. Неявный H2
            elif length_ok and (is_bold or last_char not in ['.', ',', ';', '!', ':', '?']):
                is_contact = re.match(
                    r'^(company|address|location|email|phone|телефон|адрес|почта|e-mail|'
                    r'website|contact|support|whatsapp|telegram|viber|skype|author|date)\s*:',
                    clean_line, re.IGNORECASE
                )
                if (not is_contact
                        and not re.match(r'^([\-•*]|\d+\.)', clean_line)
                        and '<img' not in ll2 and '<a ' not in ll2 and 'http' not in ll2):
                    if data.get('h1'):
                        matched_key = 'h2'
                    marker_end_pos = 0

        # 5. Обработка найденного маркера
        if matched_key:
            content_after = clean_line[marker_end_pos:].strip()
            content_after = re.sub(r'^[:\-–—|\s]+', '', content_after)
            val = content_after

            if not val and i + 1 < len(lines):
                next_clean = re.sub(r'<[^>]+>', '', lines[i+1]).strip()
                is_next_marker = any(
                    re.match(p, next_clean.lower(), re.IGNORECASE) for p in patterns.values())
                if not is_next_marker:
                    val = next_clean
                    i += 1

            if matched_key == 'seo_title':
                data['seo_title'] = val
                just_parsed_h1 = False
            elif matched_key == 'meta_desc':
                data['meta_desc'] = val
                just_parsed_h1 = False
            elif matched_key == 'h1':
                data['h1'] = val
                just_parsed_h1 = True
                content_started = True
            elif matched_key == 'h2':
                current_heading = val.lower() if val else f"section_{i}"
                if current_heading not in data["sections"]:
                    data["sections"][current_heading] = {"title": val, "content": []}
                just_parsed_h1 = False
                content_started = True
            elif matched_key == 'h3':
                # Защита от мусорных H3 внутри FAQ
                if is_faq_context and not val.strip().endswith('?'):
                    val_lc = val.lower().strip()
                    if any(w in val_lc for w in ['faq', 'question', 'вопрос', 'q&a']):
                        i += 1
                        continue
                # Пропускаем пустые H3 (в т.ч. с неразрывными пробелами \xa0)
                if val.replace('\xa0', '').strip():
                    data["sections"][current_heading]["content"].append(f"<h3>{val}</h3>")
                just_parsed_h1 = False
                content_started = True

        # 6. Обычный контент
        else:
            ll3 = line.strip().lower()
            is_media = any(t in ll3 for t in ['<img', '<table', '<ul', '<ol', '<iframe'])
            if clean_line or is_media:
                is_dup = False
                if clean_line:
                    is_dup = (clean_line == data.get('h1')
                              or clean_line == data.get('seo_title')
                              or clean_line == data.get('meta_desc'))
                if not is_dup:
                    content_started = True
                    if just_parsed_h1 and clean_line and not data.get('hero_desc'):
                        data['hero_desc'] = clean_line
                        just_parsed_h1 = False
                    else:
                        just_parsed_h1 = False
                        if line.strip().startswith('<'):
                            # Убираем services-table из таблиц внутри FAQ
                            if is_faq_context and ll3.startswith('<table'):
                                line = (line.replace(' class="services-table"', '')
                                            .replace(" class='services-table'", "")
                                            .replace('class="services-table"', ''))
                            data["sections"][current_heading]["content"].append(line)
                        else:
                            data["sections"][current_heading]["content"].append(f"<p>{line}</p>")
        i += 1

    for key in data["sections"]:
        data["sections"][key]["content"] = "\n".join(data["sections"][key]["content"])

    return data


def _parse_doc_kross_slotsite(text):
    """
    Стандартный парсер с явными маркерами (h1/h2/h3/title/desc).
    Используется движками KROSS и SLOTSITE.
    """
    data = {"seo_title": "", "meta_desc": "", "h1": "", "sections": {}}
    lines = [line.strip() for line in text.split('\n') if line.strip()]

    current_heading = "main_text"
    data["sections"][current_heading] = {"title": "", "content": []}

    patterns = {
        'seo_title': r'^(?:(?:seo\s*)?title|мт|mt)\b(?:\s*\([^)]+\))?\s*[:\-–—]*',
        'meta_desc': r'^(?:(?:meta\s*)?desc(?:ription)?|мд|md)\b(?:\s*\([^)]+\))?\s*[:\-–—]*',
        'h1':        r'^h1\b(?:\s*\([^)]+\))?\s*[:\-–—]*',
        'h2':        r'^h2\b(?:\s*\([^)]+\))?\s*[:\-–—]*',
        'h3':        r'^h3\b(?:\s*\([^)]+\))?\s*[:\-–—]*'
    }

    i = 0
    while i < len(lines):
        line = lines[i]
        clean_line = re.sub(r'<[^>]+>', '', line).strip()
        lower_clean = clean_line.lower()

        matched_key = None
        marker_end_pos = 0

        for key, pattern in patterns.items():
            match = re.match(pattern, lower_clean, re.IGNORECASE)
            if match:
                matched_key = key
                marker_end_pos = match.end()
                break

        if matched_key:
            content_after = clean_line[marker_end_pos:].strip()
            val = re.sub(r'^[:\-–—\s]+', '', content_after)

            if not val and i + 1 < len(lines):
                next_clean = re.sub(r'<[^>]+>', '', lines[i+1]).strip()
                if not any(re.match(p, next_clean.lower(), re.IGNORECASE) for p in patterns.values()):
                    val = next_clean
                    i += 1

            if matched_key == 'seo_title':
                data['seo_title'] = val
            elif matched_key == 'meta_desc':
                data['meta_desc'] = val
            elif matched_key == 'h1':
                data['h1'] = val
            elif matched_key == 'h2':
                current_heading = val.lower() if val else f"section_{i}"
                data["sections"][current_heading] = {"title": val, "content": []}
            elif matched_key == 'h3':
                data["sections"][current_heading]["content"].append(f"<h3>{val}</h3>")
        else:
            if (clean_line
                    and clean_line not in [data.get('h1'), data.get('seo_title'), data.get('meta_desc')]):
                if line.startswith('<'):
                    data["sections"][current_heading]["content"].append(line)
                else:
                    data["sections"][current_heading]["content"].append(f"<p>{line}</p>")
        i += 1

    for key in data["sections"]:
        data["sections"][key]["content"] = "\n".join(data["sections"][key]["content"])

    return data


def parse_doc_to_json(text, engine='SUSHI'):
    """Диспетчер: выбирает версию парсера по движку."""
    if engine == 'SUSHI':
        return _parse_doc_sushi(text)
    else:  # KROSS, SLOTSITE
        return _parse_doc_kross_slotsite(text)


# ============================================================
# ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ (только SUSHI)
# ============================================================

def clean_html_styles(html_content):
    """Снимает все inline-стили с HTML. Используется только движком SUSHI."""
    if not html_content or not isinstance(html_content, str):
        return html_content
    soup = BeautifulSoup(html_content, 'lxml')
    for tag in soup.find_all(True):
        if tag.has_attr('style'):
            del tag['style']
        if tag.name in ['font', 'center']:
            tag.unwrap()
    return "".join(str(c) for c in soup.body.contents) if soup.body else str(soup)

def uniqualize_file_names(dst_site_dir, engine='SUSHI'):
    """Диспетчер: выбирает версию уникализатора по движку."""
    if engine == 'KROSS':
        _uniqualize_kross(dst_site_dir)
    elif engine == 'SLOTSITE':
        _uniqualize_slotsite(dst_site_dir)
    elif engine == 'SUSHI2':
        _uniqualize_sushi(dst_site_dir)  # SUSHI2 использует ту же логику, что и SUSHI
    else:  # SUSHI
        _uniqualize_sushi(dst_site_dir)


def _uniqualize_sushi(site_dir):
    """
    SUSHI: переименовывает медиа-файлы (.png, .jpg, .css, .js и т.д.)
    кроме logo.png, fav.png, favicon.ico.
    Обновляет ссылки на них во всех текстовых файлах сайта.
    """
    media_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.ico', '.css', '.js')
    excluded_files = {'logo.png', 'fav.png', 'favicon.ico'}
    file_mapping = {}

    for root, dirs, files in os.walk(site_dir):
        for filename in files:
            if filename.lower() in excluded_files:
                continue
            if filename.lower().endswith(media_extensions):
                ext = os.path.splitext(filename)[1]
                new_name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=12)) + ext
                old_path = os.path.join(root, filename)
                new_path = os.path.join(root, new_name)
                os.rename(old_path, new_path)
                file_mapping[filename] = new_name

    text_extensions = ('.html', '.css', '.js', '.json', '.php')
    sorted_old_names = sorted(file_mapping.keys(), key=len, reverse=True)

    for root, dirs, files in os.walk(site_dir):
        for filename in files:
            if filename.lower().endswith(text_extensions):
                filepath = os.path.join(root, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    original_content = content
                    for old_name in sorted_old_names:
                        new_name = file_mapping[old_name]
                        escaped_old = re.escape(old_name)
                        encoded_old = re.escape(urllib.parse.quote(old_name))
                        pattern = r'(^|[/\\\"\'\(\s=,])(' + escaped_old + r'|' + encoded_old + r')([\"\'\)\?\s#>,]|$)'
                        content = re.sub(pattern, r'\g<1>' + new_name + r'\g<3>', content, flags=re.IGNORECASE)
                    if content != original_content:
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(content)
                except Exception as e:
                    print(f"Ошибка при уникализации файла {filepath}: {e}")


def _uniqualize_kross(dst_site_dir):
    """
    KROSS: переименовывает только JS, шрифты и видео (.js, .woff, .woff2, .ttf, .mp4).
    Обновляет ссылки во всех текстовых файлах сайта.
    """
    asset_extensions = ('.js', '.woff', '.woff2', '.ttf', '.mp4')
    excluded_files = {'index.html', 'sitemap.xml', 'robots.txt', 'app.js', 'main.js'}
    rename_map = {}

    for root, dirs, files in os.walk(dst_site_dir):
        for file_name in files:
            if file_name in excluded_files:
                continue
            if file_name.endswith(asset_extensions):
                if file_name not in rename_map:
                    ext_part = os.path.splitext(file_name)[1]
                    random_str = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))
                    rename_map[file_name] = f"asset_{random_str}{ext_part}"
                old_path = os.path.join(root, file_name)
                new_path = os.path.join(root, rename_map[file_name])
                os.rename(old_path, new_path)

    text_extensions = ('.html', '.css', '.js', '.json', '.xml', '.txt')
    sorted_old_names = sorted(rename_map.keys(), key=len, reverse=True)
    patterns = []
    for old_name in sorted_old_names:
        regex = re.compile(r'(^|[/\\"\',\(])' + re.escape(old_name) + r'([/\\"\',\)?\s#]|$)')
        patterns.append((regex, r'\g<1>' + rename_map[old_name] + r'\g<2>'))

    for root, dirs, files in os.walk(dst_site_dir):
        for file_name in files:
            if file_name.endswith(text_extensions):
                file_path = os.path.join(root, file_name)
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    new_content = content
                    for pattern, replacement in patterns:
                        new_content = pattern.sub(replacement, new_content)
                    if content != new_content:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                except:
                    pass


def _uniqualize_slotsite(dst_site_dir):
    """
    SLOTSITE: переименовывает все ассеты (.css, .js, изображения, шрифты, .mp4).
    Обновляет ссылки во всех текстовых файлах сайта.
    """
    asset_extensions = ('.css', '.js', '.png', '.jpg', '.jpeg', '.webp', '.svg', '.gif',
                        '.woff', '.woff2', '.ttf', '.ico', '.mp4')
    excluded_files = {'index.html', 'sitemap.xml', 'robots.txt', 'app.js'}
    rename_map = {}

    for root, dirs, files in os.walk(dst_site_dir):
        for file_name in files:
            if file_name in excluded_files:
                continue
            if file_name.endswith(asset_extensions):
                if file_name not in rename_map:
                    ext_part = os.path.splitext(file_name)[1]
                    random_str = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))
                    rename_map[file_name] = f"asset_{random_str}{ext_part}"
                old_path = os.path.join(root, file_name)
                new_path = os.path.join(root, rename_map[file_name])
                os.rename(old_path, new_path)

    text_extensions = ('.html', '.css', '.js', '.json', '.xml', '.txt')
    sorted_old_names = sorted(rename_map.keys(), key=len, reverse=True)
    patterns = []
    for old_name in sorted_old_names:
        regex = re.compile(r'(^|[/\\"\',\(])' + re.escape(old_name) + r'([/\\"\',\)?\s#]|$)')
        patterns.append((regex, r'\g<1>' + rename_map[old_name] + r'\g<2>'))

    for root, dirs, files in os.walk(dst_site_dir):
        for file_name in files:
            if file_name.endswith(text_extensions):
                file_path = os.path.join(root, file_name)
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    new_content = content
                    for pattern, replacement in patterns:
                        new_content = pattern.sub(replacement, new_content)
                    if content != new_content:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                except:
                    pass


# ============================================================
# SUSHI — ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ ВСТАВКИ КОНТЕНТА
# ============================================================

def generate_split_block(context_title):
    """Генерирует красивый блок «текст + картинка» для SUSHI."""
    text_first = random.choice([True, False])

    headings = [
        "Exclusive VIP Rewards",
        "Claim Your Special Bonus",
        "Unlock Premium Features",
        "Join the Winners Club",
        "Experience Top-Tier Gaming"
    ]
    texts = [
        "Experience the ultimate gaming adventure with {{BRAND_NAME}}. Sign up now to access top-tier promotions, lightning-fast payouts, and 24/7 dedicated support.",
        "Elevate your gameplay at {{BRAND_NAME}}. Discover a world of exclusive games, personalized offers, and massive rewards waiting just for you.",
        "Ready to boost your chances? {{BRAND_NAME}} offers incredible welcome packages and regular daily rewards to keep the excitement going."
    ]

    h3_text = random.choice(headings)
    p_text = random.choice(texts)
    clean_context = re.sub(r'<[^>]+>', '', context_title)
    alt_text = f"{{{{BRAND_NAME}}}} - {clean_context} Benefits"

    text_col = f'''<div class="split-text-col">
        <h3>{h3_text}</h3>
        <p>{p_text}</p>
        <a href="{{{{AFF_URL}}}}" class="btn btn-primary" rel="nofollow noopener" target="_blank">Join the Club</a>
    </div>'''

    img_col = f'''<div class="split-image-col">
        <img src="/images/banner.png" alt="{alt_text}">
    </div>'''

    inner = text_col + img_col if text_first else img_col + text_col
    return f'\n<div class="content-split-block">\n{inner}\n</div>\n'


def split_html_paragraph(html_str, limit=600):
    """Разбивает длинный HTML-абзац на две части для SUSHI."""
    clean_text = re.sub(r'<[^>]+>', '', html_str)
    if len(clean_text) <= limit:
        return html_str, ""

    split_point = -1
    in_tag = False

    for i in range(len(html_str)):
        if html_str[i] == '<':
            in_tag = True
        elif html_str[i] == '>':
            in_tag = False
            continue
        if not in_tag and i >= limit:
            if html_str[i] in ['.', '!', '?'] and i + 1 < len(html_str) and (
                    html_str[i + 1].isspace() or html_str[i + 1] == '<'):
                split_point = i + 1
                break

    if split_point == -1 or split_point > limit + 150:
        in_tag = False
        for i in range(min(limit, len(html_str)) - 1, -1, -1):
            if html_str[i] == '>':
                in_tag = True
            elif html_str[i] == '<':
                in_tag = False
                continue
            if not in_tag and html_str[i].isspace():
                split_point = i
                break

    if split_point == -1:
        return html_str, ""

    part1 = html_str[:split_point].strip()
    part2 = html_str[split_point:].strip()

    tags_open = re.findall(r'<([a-zA-Z0-9]+)[^>]*>', part1)
    tags_close = re.findall(r'</([a-zA-Z0-9]+)>', part1)
    void_tags = {'img', 'br', 'hr', 'input', 'meta', 'link'}
    tags_open = [t for t in tags_open if t.lower() not in void_tags]

    unclosed = []
    for t in tags_open:
        if t in tags_close:
            tags_close.remove(t)
        else:
            unclosed.append(t)

    for t in reversed(unclosed):
        part1 += f'</{t}>'

    prefix2 = ""
    for t in unclosed:
        match = re.search(r'<(' + re.escape(t) + r')[^>]*>(?!.*</\1>)', part1, flags=re.IGNORECASE | re.DOTALL)
        if match:
            prefix2 += match.group(0)
        else:
            prefix2 += f'<{t}>'

    part2 = prefix2 + part2
    return part1, part2


# ============================================================
# SUSHI — SMART_INJECT_HTML
# ============================================================

def _smart_inject_html_sushi(file_path, json_data, site_name=None):
    """
    Вставляет контент в HTML-шаблон для движка SUSHI.
    Поддерживает hero_desc, seo-content, FAQ-аккордеоны, красивые блоки с картинкой.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'lxml')

    # SEO-теги
    if json_data.get('seo_title'):
        if soup.title: soup.title.string = json_data['seo_title']
        for tag in soup.find_all('meta', attrs={'property': re.compile(r'title', re.I)}):
            tag['content'] = json_data['seo_title']
        for tag in soup.find_all('meta', attrs={'name': re.compile(r'title', re.I)}):
            tag['content'] = json_data['seo_title']
        for tag in soup.find_all('meta', attrs={'itemprop': 'name'}):
            tag['content'] = json_data['seo_title']

    if json_data.get('meta_desc'):
        for tag in soup.find_all('meta', attrs={'name': re.compile(r'description', re.I)}):
            tag['content'] = json_data['meta_desc']
        for tag in soup.find_all('meta', attrs={'property': re.compile(r'description', re.I)}):
            tag['content'] = json_data['meta_desc']
        for tag in soup.find_all('meta', attrs={'itemprop': 'description'}):
            tag['content'] = json_data['meta_desc']

    if site_name:
        for tag in soup.find_all('meta', attrs={'property': 'og:site_name'}):
            tag['content'] = site_name
        for tag in soup.find_all('meta', attrs={'name': 'apple-mobile-web-app-title'}):
            tag['content'] = site_name

    is_faq_only_page = any(kw in file_path.lower() for kw in ['faq', 'questions', 'вопросы'])

    h1_tag = soup.find('h1')
    h1_injected = False

    if is_faq_only_page:
        h1_injected = True
    else:
        if h1_tag and json_data.get('h1'):
            h1_tag.string = json_data['h1']
            h1_injected = True

    hero_desc_injected = False
    if is_faq_only_page:
        hero_desc_injected = True
    else:
        if json_data.get('hero_desc') and h1_tag:
            hero_desc_tag = soup.find('p', class_=re.compile(r'hero-description|hero-subtitle'))
            if not hero_desc_tag:
                for sibling in h1_tag.find_next_siblings():
                    if sibling.name == 'p':
                        hero_desc_tag = sibling
                        break
                    elif sibling.name in ['h1', 'h2', 'h3', 'div', 'section']:
                        break
            if hero_desc_tag:
                hero_desc_tag.string = json_data['hero_desc']
                hero_desc_injected = True

    seo_content = soup.find('div', class_='seo-content')
    faq_container = soup.find('div', class_='auto-faq-container')

    if is_faq_only_page:
        main_tag = soup.find('main')
        if main_tag:
            for child in list(main_tag.children):
                if child.name in ['section', 'div']:
                    if faq_container and (child == faq_container or child.find(class_='auto-faq-container')):
                        continue
                    child.decompose()
        for h1 in soup.find_all('h1'):
            h1.decompose()
        seo_content = None

    if seo_content:
        seo_content.clear()
    if faq_container:
        faq_container.clear()

    article_sections = []
    faq_sections = []
    for k, v in json_data.get('sections', {}).items():
        if k == 'main_text':
            continue
        if any(word in k.lower() for word in ['faq', 'вопрос', 'pytania', 'frequent']):
            faq_sections.append(v)
        else:
            article_sections.append(v)

    # Шаблон красивого блока с картинкой и кнопкой (SUSHI)
    custom_block_template = '''
        <div class="custom-feature-card" style="background-color: var(--bg-card, #14141C); border: 1px solid var(--border-color, rgba(212, 175, 55, 0.2)); border-radius: 16px; padding: 30px; margin: 40px 0; box-shadow: 0 8px 24px rgba(0,0,0,0.15);">
            <div style="display: flex; flex-wrap: wrap; gap: 30px; align-items: center;">
                <div style="flex: 1 1 300px; text-align: center;">
                    <img width="1016" height="920" src="/images/app.jpg" class="attachment-full size-full"
                        alt="images {{BRAND_NAME}}" loading="lazy" decoding="async"
                        sizes="(max-width: 1016px) 100vw, 1016px"
                        style="max-width: 100%; height: auto; border-radius: 12px;">
                </div>
                <div class="text-image__content" style="flex: 1.5 1 300px;">
                    {{TEXT}}
                </div>
            </div>
            <div style="text-align: center; margin-top: 30px;">
                <a href="{{AFF_URL}}" class="btn btn-primary btn-large" style="min-width: 200px; display: inline-block;" rel="nofollow noopener" target="_blank">
                    Play Casino
                </a>
            </div>
        </div>
    '''

    article_html = ""

    if not is_faq_only_page:
        if json_data.get('h1') and not h1_injected:
            article_html += f"<h1>{json_data['h1']}</h1>\n"
        if json_data.get('hero_desc') and not hero_desc_injected:
            article_html += f"<p>{json_data['hero_desc']}</p>\n"

    is_policy_page = any(kw in file_path.lower() for kw in [
        'policy', 'terms', 'conditions', 'privacy', 'rules', 'cookie', 'responsible',
        'richtlinie', 'datenschutzbestimmungen', 'verantwortungsvolles', 'nutzungsbedingungen'
    ])
    images_to_insert = 0 if is_policy_page or is_faq_only_page else 3
    remaining_images = images_to_insert

    # Вставляем первый блок с картинкой во вступительный текст
    if 'main_text' in json_data.get('sections', {}):
        main_content = json_data['sections']['main_text']['content'].strip()
        if main_content:
            if remaining_images > 0:
                paragraphs = main_content.split('\n')
                first_p_idx = -1
                for p_idx, p_str in enumerate(paragraphs):
                    p_lower = p_str.strip().lower()
                    if p_lower.startswith('<p') and not any(
                            tag in p_lower for tag in ['<table', '<ul', '<ol', '<iframe']):
                        first_p_idx = p_idx
                        break
                if first_p_idx != -1:
                    card_text, extra_rest = split_html_paragraph(paragraphs[first_p_idx], 600)
                    rest_parts = paragraphs[:first_p_idx]
                    if extra_rest:
                        rest_parts.append(extra_rest)
                    rest_parts.extend(paragraphs[first_p_idx + 1:])
                    rest_text = "\n".join(rest_parts)
                    article_html += custom_block_template.replace('{{TEXT}}', card_text) + "\n"
                    if rest_text:
                        article_html += f"{rest_text}\n"
                    remaining_images -= 1
                else:
                    article_html += f"{main_content}\n"
            else:
                article_html += f"{main_content}\n"

    # Вычисляем, в какие H2-секции вставить оставшиеся блоки
    sections_for_images = []
    if remaining_images > 0 and len(article_sections) > 0:
        step = max(1, len(article_sections) // remaining_images)
        for i in range(remaining_images):
            idx = min(i * step, len(article_sections) - 1)
            if idx not in sections_for_images:
                sections_for_images.append(idx)

    # Перебираем H2-секции
    for i, sec in enumerate(article_sections):
        article_html += f"<h2>{sec['title']}</h2>\n"
        content = sec['content'].strip()
        if i in sections_for_images and remaining_images > 0 and content:
            paragraphs = content.split('\n')
            first_p_idx = -1
            for p_idx, p_str in enumerate(paragraphs):
                p_lower = p_str.strip().lower()
                if p_lower.startswith('<p') and not any(
                        tag in p_lower for tag in ['<table', '<ul', '<ol', '<iframe']):
                    first_p_idx = p_idx
                    break
            if first_p_idx != -1:
                card_text, extra_rest = split_html_paragraph(paragraphs[first_p_idx], 600)
                rest_parts = paragraphs[:first_p_idx]
                if extra_rest:
                    rest_parts.append(extra_rest)
                rest_parts.extend(paragraphs[first_p_idx + 1:])
                rest_text = "\n".join(rest_parts)
                article_html += custom_block_template.replace('{{TEXT}}', card_text) + "\n"
                if rest_text:
                    article_html += f"{rest_text}\n"
                remaining_images -= 1
                sections_for_images.remove(i)
            else:
                article_html += f"{content}\n"
                if i + 1 < len(article_sections) and (i + 1) not in sections_for_images:
                    sections_for_images.append(i + 1)
        else:
            article_html += f"{content}\n"

    # Вставляем статью в шаблон (только если это не FAQ-страница)
    if not is_faq_only_page:
        if seo_content:
            if article_html.strip():
                _bs4_safe_append(seo_content, article_html)
            else:
                seo_section = seo_content.find_parent('section')
                if seo_section:
                    seo_section.decompose()
        elif article_html.strip():
            main_tag = soup.find('main')
            if main_tag:
                main_tag.append(BeautifulSoup(
                    f"<section class='seo-section'><div class='container'>"
                    f"<div class='seo-content'>{article_html}</div></div></section>", 'html.parser'))

    # FAQ-блок
    faq_html = ""
    if is_faq_only_page and article_html.strip():
        faq_html += f"<div class='seo-content'>{article_html}</div>\n"

    # Если есть классические вопросы (аккордеоны), добавляем их тоже
    if faq_sections:
        # Берем заголовок из первой секции FAQ, если он есть, иначе дефолтный "FAQ"
        main_faq_title = faq_sections[0].get('title', 'FAQ')
        if not main_faq_title:
            main_faq_title = "FAQ"

        # Не дублируем заголовок H2, если таблица уже вывелась
        if not is_faq_only_page or not article_html.strip():
            faq_html += f"<h2>{main_faq_title}</h2>\n"

        for sec in faq_sections:
            sec_title = sec.get('title', '')
            title_lower = sec_title.lower().strip()

            # Проверяем, нужно ли выводить заголовок секции как H3
            is_default_faq = title_lower in [
                'faq', 'f.a.q.', 'вопросы и ответы', 'частые вопросы', 'frequently asked questions']

            if not is_default_faq and sec_title != main_faq_title:
                faq_html += f"<h3>{sec_title}</h3>\n"

            # ВАЖНО: эта строка добавляет сами вопросы (H3) и ответы (P) из ТЗ
            # SUSHI-шаблоны рендерят FAQ через свой CSS на сырых тегах <h3>
            faq_html += f"{sec.get('content', '')}\n"

    # Финальная вставка FAQ-контента (таблицы и/или аккордеона)
    if faq_html.strip():
        if faq_container:
            _bs4_safe_append(faq_container, faq_html)
        else:
            main_tag = soup.find('main')
            if main_tag:
                main_tag.append(BeautifulSoup(
                    f"<section id='faq' class='faq-section'>"
                    f"<div class='container auto-faq-container'>{faq_html}</div>"
                    f"</section>", 'html.parser'))
    else:
        # Если FAQ-контента нет — удаляем пустой контейнер
        if faq_container:
            faq_section = faq_container.find_parent('section')
            if faq_section:
                faq_section.decompose()
            else:
                faq_container.decompose()

    # На FAQ-страницах убираем класс services-table с таблиц (он не нужен в FAQ-контексте)
    if is_faq_only_page:
        for table in soup.find_all('table', class_='services-table'):
            if 'services-table' in table.get('class', []):
                table['class'].remove('services-table')
            if not table.get('class'):
                del table['class']

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(str(soup))


# ============================================================
# KROSS — ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ И SMART_INJECT_HTML
# ============================================================

def _wrap_faq_content_kross(content):
    """
    Оборачивает FAQ-контент в Bootstrap Accordion (движок KROSS).
    """
    faq_soup = BeautifulSoup(content, 'html.parser')
    faq_items_html = ""
    elements = list((faq_soup.body if faq_soup.body else faq_soup).children)

    i, faq_count, has_h3 = 0, 0, False
    while i < len(elements):
        child = elements[i]
        if getattr(child, 'name', None) in ['h3', 'h4']:
            has_h3 = True
            faq_count += 1
            question = child.get_text(strip=True)
            answer_html = ""
            i += 1
            while i < len(elements) and getattr(elements[i], 'name', None) not in ['h3', 'h4']:
                if str(elements[i]).strip():
                    answer_html += str(elements[i])
                i += 1
            item_id = f"collapse_auto_{faq_count}"
            faq_items_html += f"""
            <div class="accordion-item">
                <h3 class="accordion-header">
                    <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#{item_id}">
                        {question}
                    </button>
                </h3>
                <div id="{item_id}" class="accordion-collapse collapse" data-bs-parent="#accordionFAQ">
                    <div class="accordion-body">{answer_html}</div>
                </div>
            </div>\n"""
        else:
            i += 1

    return faq_items_html if has_h3 else content


def _smart_inject_html_kross(file_path, json_data, page_slug, is_policy=False):
    """
    Вставляет контент в HTML-шаблон для движка KROSS (Bootstrap).
    Поддерживает seo-content-inject, modern-card, Bootstrap Accordion для FAQ.
    """
    has_articles = False
    for k, v in json_data.get('sections', {}).items():
        if k != 'main_text' and not any(word in k.lower() for word in ['faq', 'вопрос', 'pytania', 'frequent']):
            has_articles = True
            break

    original_main_text = json_data.get('sections', {}).get('main_text', {}).get('content', '').strip()
    is_faq_only = not has_articles and not original_main_text

    with open(file_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'lxml')

    css_styles = """
    <style class="auto-content-style">
    .auto-content-wrapper { font-family: inherit; line-height: 1.6; color: inherit; }
    .auto-content-wrapper p { margin-bottom: 15px; }
    .auto-content-wrapper h3 { font-size: 20px; font-weight: 700; margin: 25px 0 15px; }
    .auto-content-wrapper ul, .auto-content-wrapper ol { margin-bottom: 20px; padding-left: 20px; }
    .auto-content-wrapper li { margin-bottom: 8px; }
    .auto-content-wrapper table { width: 100%; border-collapse: collapse; margin: 25px 0; background: #ffffff; border: 1px solid #e5e7eb; border-radius: 8px; overflow: hidden; }
    .auto-content-wrapper th { background: #f3f4f6; font-weight: 600; text-align: left; padding: 12px 16px; border-bottom: 2px solid #d1d5db; }
    .auto-content-wrapper td { padding: 12px 16px; border-bottom: 1px solid #e5e7eb; color: #000; }
    .modern-card .auto-content-wrapper { margin-top: 0; }
    .btn-cta-main { display: inline-block; text-decoration: none; padding: 12px 25px; background-color: #a00000; color: #fff; border-radius: 8px; font-weight: bold; margin: 10px 0 20px; transition: 0.3s; }
    .btn-cta-main:hover { background-color: #f6b625; color: #5a2c10; }
    .split-side-img { width: 100%; height: auto; border-radius: 12px; box-shadow: 0 5px 15px rgba(0,0,0,0.1); }
    </style>
    """
    if not soup.find('style', class_='auto-content-style') and soup.head:
        _bs4_safe_append(soup.head, css_styles)

    if json_data.get('seo_title'):
        if soup.title: soup.title.string = json_data['seo_title']
        for tag in soup.find_all('meta', attrs={'property': re.compile(r'title', re.I)}):
            tag['content'] = json_data['seo_title']
        for tag in soup.find_all('meta', attrs={'name': re.compile(r'title', re.I)}):
            tag['content'] = json_data['seo_title']
    if json_data.get('meta_desc'):
        for tag in soup.find_all('meta', attrs={'name': re.compile(r'description', re.I)}):
            tag['content'] = json_data['meta_desc']
        for tag in soup.find_all('meta', attrs={'property': re.compile(r'description', re.I)}):
            tag['content'] = json_data['meta_desc']

    h1_tag = soup.find('h1')
    if h1_tag and json_data.get('h1'):
        h1_tag.string = json_data['h1']

    if 'main_text' in json_data['sections']:
        main_text_content = json_data['sections']['main_text']['content'].strip()
        if h1_tag and main_text_content:
            next_p = h1_tag.find_next_sibling('p')
            if next_p: next_p.decompose()
            wrapper = soup.new_tag('div', attrs={'class': 'auto-content-wrapper'})
            wrapper.append(BeautifulSoup(main_text_content, 'html.parser'))
            h1_tag.insert_after(wrapper)
            del json_data['sections']['main_text']

    article_sections = []
    faq_sections = []
    for k, v in json_data['sections'].items():
        if k == 'main_text': continue
        if any(word in k.lower() for word in ['faq', 'вопрос', 'pytania', 'frequent']):
            faq_sections.append(v)
        else:
            article_sections.append(v)

    # Политики: особый режим вставки
    if is_policy and h1_tag:
        container = h1_tag.parent
        for sibling in h1_tag.find_next_siblings():
            sibling.decompose()
        for sec in article_sections:
            new_card = soup.new_tag('article', attrs={'class': 'modern-card mb-4'})
            icon = soup.new_tag('i', attrs={'class': 'bi bi-journal-text modern-card-icon'})
            new_card.append(icon)
            if sec.get('title'):
                new_h2 = soup.new_tag('h2')
                new_h2.string = sec['title']
                new_card.append(new_h2)
            if sec.get('content'):
                wrapper = soup.new_tag('div', attrs={'class': 'auto-content-wrapper'})
                wrapper.append(BeautifulSoup(sec['content'], 'html.parser'))
                new_card.append(wrapper)
            container.append(new_card)
        for sec in faq_sections:
            faq_div = soup.new_tag('div', attrs={'class': 'accordion mb-4', 'id': 'accordionFAQ'})
            faq_h2 = soup.new_tag('h2', attrs={'class': 'text-center mb-4'})
            faq_h2.string = sec['title']
            faq_div.append(faq_h2)
            faq_div.append(BeautifulSoup(_wrap_faq_content_kross(sec['content']), 'html.parser'))
            container.append(faq_div)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(str(soup))
        return

    target_container = soup.find(id='seo-content-inject')

    if target_container:
        target_container.clear()
        doc_article_idx = 0
        for sec in article_sections:
            new_card = soup.new_tag('article', attrs={'class': 'modern-card mb-4'})
            icon = soup.new_tag('i', attrs={'class': 'bi bi-journal-text modern-card-icon'})
            new_card.append(icon)
            if not is_policy and doc_article_idx < 3:
                row = soup.new_tag('div', attrs={'class': 'row align-items-center mb-4'})
                col_text = soup.new_tag('div', attrs={'class': 'col-lg-7 col-md-12'})
                col_img = soup.new_tag('div', attrs={'class': 'col-lg-5 col-md-12 text-center'})
                new_h2 = soup.new_tag('h2')
                new_h2.string = sec['title']
                col_text.append(new_h2)
                content_soup = BeautifulSoup(sec['content'], 'html.parser')
                first_p = content_soup.find('p')
                if first_p:
                    extracted_p = first_p.extract()
                    wrapper_top = soup.new_tag('div', attrs={'class': 'auto-content-wrapper'})
                    wrapper_top.append(extracted_p)
                    btn = soup.new_tag('a', href="{{AFF_URL}}", attrs={'class': 'btn-cta-main'})
                    btn.string = "¡Jugar Ahora!"
                    wrapper_top.append(btn)
                    col_text.append(wrapper_top)
                else:
                    btn = soup.new_tag('a', href="{{AFF_URL}}", attrs={'class': 'btn-cta-main'})
                    btn.string = "¡Jugar Ahora!"
                    col_text.append(btn)
                img_tag = soup.new_tag('img',
                    src=f"/images/{page_slug}_{doc_article_idx + 1}.png",
                    attrs={'class': 'split-side-img', 'alt': sec['title']})
                col_img.append(img_tag)
                if random.choice([True, False]):
                    row.append(col_text); row.append(col_img)
                else:
                    row.append(col_img); row.append(col_text)
                new_card.append(row)
                remaining_html = str(content_soup).strip()
                if remaining_html:
                    wrapper_bottom = soup.new_tag('div', attrs={'class': 'auto-content-wrapper'})
                    wrapper_bottom.append(BeautifulSoup(remaining_html, 'html.parser'))
                    new_card.append(wrapper_bottom)
            else:
                new_h2 = soup.new_tag('h2')
                new_h2.string = sec['title']
                new_card.append(new_h2)
                wrapper = soup.new_tag('div', attrs={'class': 'auto-content-wrapper'})
                _bs4_safe_append(wrapper, sec['content'])
                new_card.append(wrapper)
            target_container.append(new_card)
            doc_article_idx += 1

        for sec in faq_sections:
            faq_div = soup.new_tag('div', attrs={'class': 'accordion mb-4', 'id': 'accordionFAQ'})
            faq_h2 = soup.new_tag('h2', attrs={'class': 'text-center mb-4'})
            faq_h2.string = sec['title']
            faq_div.append(faq_h2)
            faq_div.append(BeautifulSoup(_wrap_faq_content_kross(sec['content']), 'html.parser'))
            target_container.append(faq_div)

    else:
        # Фолбэк: ищем H2-теги в main и заменяем их
        main_content_node = soup.find('main', class_='container') or soup.body
        tags_raw = main_content_node.find_all(['h2'])
        
        # 1. Отфильтруем заголовки сайдбара и виджетов, чтобы не вставлять статьи туда
        valid_h2s = []
        for elem in tags_raw:
            if not elem.parent: continue
            h2_text = elem.get_text(strip=True).lower()
            if any(word in h2_text for word in ['top ', 'ranking', 'lista ', 'list of ', 'best ', 'najlepsz', 'popular', 'recent', 'related', 'podobne']):
                continue
            if 'casino' in h2_text and any(w in h2_text for w in ['play', 'graj', 'where']):
                continue
            valid_h2s.append(elem)

        doc_article_idx = 0
        last_article_element = None

        for elem in valid_h2s:
            h2_text = elem.get_text(strip=True).lower()

            # --- ОБРАБОТКА FAQ В ШАБЛОНЕ ---
            if any(word in h2_text for word in ['faq', 'pytania', 'preguntas', 'вопрос']):
                # ВАЖНО: Если дошли до FAQ, выгружаем все ОСТАВШИЕСЯ статьи строго ПЕРЕД ним
                while doc_article_idx < len(article_sections):
                    sec = article_sections[doc_article_idx]
                    new_card = soup.new_tag('article', attrs={'class': 'modern-card mb-4'})
                    icon = soup.new_tag('i', attrs={'class': 'bi bi-journal-text modern-card-icon'})
                    new_card.append(icon)
                    new_h2 = soup.new_tag('h2')
                    new_h2.string = sec['title']
                    new_card.append(new_h2)
                    wrapper = soup.new_tag('div', attrs={'class': 'auto-content-wrapper'})
                    wrapper.append(BeautifulSoup(sec['content'], 'html.parser'))
                    new_card.append(wrapper)

                    parent_card = elem.find_parent('article', class_='modern-card')
                    if parent_card:
                        parent_card.insert_before(new_card)
                    else:
                        elem.insert_before(new_card)
                    doc_article_idx += 1

                # Теперь рендерим сам FAQ
                if faq_sections:
                    sec = faq_sections.pop(0)
                    next_sib = elem.find_next_sibling()
                    if next_sib and 'accordion' in next_sib.get('class', []):
                        next_sib.decompose()
                    elem.string = sec['title']
                    if not elem.get('class'): elem['class'] = ['text-center', 'mb-4']
                    faq_div = soup.new_tag('div', attrs={'class': 'accordion mb-4', 'id': 'accordionFAQ'})
                    faq_div.append(BeautifulSoup(_wrap_faq_content_kross(sec['content']), 'html.parser'))
                    elem.insert_after(faq_div)
                    last_article_element = faq_div
                else:
                    parent_card = elem.find_parent('article', class_='modern-card')
                    if parent_card: parent_card.decompose()
                    else: elem.decompose()
                continue

            # --- ОБРАБОТКА ОБЫЧНЫХ СТАТЕЙ ---
            if doc_article_idx < len(article_sections):
                sec = article_sections[doc_article_idx]
                parent_card = elem.find_parent('article', class_='modern-card')
                content_block = soup.new_tag('div')

                if not is_policy and doc_article_idx < 3:
                    row = soup.new_tag('div', attrs={'class': 'row align-items-center mb-4'})
                    col_text = soup.new_tag('div', attrs={'class': 'col-lg-7 col-md-12'})
                    col_img = soup.new_tag('div', attrs={'class': 'col-lg-5 col-md-12 text-center'})
                    new_h2 = soup.new_tag('h2')
                    new_h2.string = sec['title']
                    col_text.append(new_h2)
                    content_soup = BeautifulSoup(sec['content'], 'html.parser')
                    first_p = content_soup.find('p')
                    if first_p:
                        extracted_p = first_p.extract()
                        wrapper_top = soup.new_tag('div', attrs={'class': 'auto-content-wrapper'})
                        wrapper_top.append(extracted_p)
                        btn = soup.new_tag('a', href="{{AFF_URL}}", attrs={'class': 'btn-cta-main'})
                        btn.string = "¡Jugar Ahora!"
                        wrapper_top.append(btn)
                        col_text.append(wrapper_top)
                    else:
                        btn = soup.new_tag('a', href="{{AFF_URL}}", attrs={'class': 'btn-cta-main'})
                        btn.string = "¡Jugar Ahora!"
                        col_text.append(btn)
                    img_tag = soup.new_tag('img',
                        src=f"/images/{page_slug}_{doc_article_idx + 1}.png",
                        attrs={'class': 'split-side-img', 'alt': sec['title']})
                    col_img.append(img_tag)
                    if random.choice([True, False]):
                        row.append(col_text); row.append(col_img)
                    else:
                        row.append(col_img); row.append(col_text)
                    content_block.append(row)
                    remaining_html = str(content_soup).strip()
                    if remaining_html:
                        wrapper_bottom = soup.new_tag('div', attrs={'class': 'auto-content-wrapper'})
                        wrapper_bottom.append(BeautifulSoup(remaining_html, 'html.parser'))
                        content_block.append(wrapper_bottom)
                else:
                    new_h2 = soup.new_tag('h2')
                    new_h2.string = sec['title']
                    content_block.append(new_h2)
                    wrapper = soup.new_tag('div', attrs={'class': 'auto-content-wrapper'})
                    wrapper.append(BeautifulSoup(sec['content'], 'html.parser'))
                    content_block.append(wrapper)

                if parent_card:
                    parent_card.clear()
                    icon = soup.new_tag('i', attrs={'class': 'bi bi-journal-text modern-card-icon'})
                    parent_card.append(icon)
                    for child in list(content_block.children): parent_card.append(child)
                    last_article_element = parent_card
                else:
                    new_card = soup.new_tag('article', attrs={'class': 'modern-card mb-4'})
                    icon = soup.new_tag('i', attrs={'class': 'bi bi-journal-text modern-card-icon'})
                    new_card.append(icon)
                    for child in list(content_block.children): new_card.append(child)
                    elem.replace_with(new_card)
                    last_article_element = new_card
                doc_article_idx += 1
            else:
                parent_card = elem.find_parent('article', class_='modern-card')
                if parent_card: parent_card.decompose()
                else: elem.decompose()

        # --- ДОБИВАЕМ ОСТАТКИ, ЕСЛИ В ШАБЛОНЕ БОЛЬШЕ НЕТ H2 ---
        append_target = main_content_node
        if last_article_element and last_article_element.parent:
            append_target = last_article_element.parent

        # 1. Если остались обычные статьи (шаблон кончился до FAQ)
        while doc_article_idx < len(article_sections):
            sec = article_sections[doc_article_idx]
            new_card = soup.new_tag('article', attrs={'class': 'modern-card mb-4'})
            icon = soup.new_tag('i', attrs={'class': 'bi bi-journal-text modern-card-icon'})
            new_card.append(icon)
            new_h2 = soup.new_tag('h2')
            new_h2.string = sec['title']
            new_card.append(new_h2)
            wrapper = soup.new_tag('div', attrs={'class': 'auto-content-wrapper'})
            wrapper.append(BeautifulSoup(sec['content'], 'html.parser'))
            new_card.append(wrapper)

            if last_article_element:
                last_article_element.insert_after(new_card)
            else:
                append_target.append(new_card)
            last_article_element = new_card
            doc_article_idx += 1

        # 2. Если остался FAQ, а в шаблоне не было слота под FAQ
        for sec in faq_sections:
            faq_div = soup.new_tag('div', attrs={'class': 'accordion mb-4', 'id': 'accordionFAQ'})
            faq_h2 = soup.new_tag('h2', attrs={'class': 'text-center mb-4'})
            faq_h2.string = sec['title']
            faq_div.append(faq_h2)
            faq_div.append(BeautifulSoup(_wrap_faq_content_kross(sec['content']), 'html.parser'))
            
            if last_article_element:
                last_article_element.insert_after(faq_div)
            else:
                append_target.append(faq_div)
            last_article_element = faq_div

    if is_faq_only:
        hero = soup.find('section', class_='hero-section')
        if hero: hero.decompose()
        toc = soup.find(id='toc-container')
        if toc:
            parent_toc = toc.find_parent('section', class_='container mb-4')
            if parent_toc: parent_toc.decompose()
            else: toc.decompose()

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(str(soup))


# ============================================================
# SLOTSITE — ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ И SMART_INJECT_HTML
# ============================================================

def _wrap_faq_content_slotsite(content):
    """
    Оборачивает FAQ-контент в div.faq-item (движок SLOTSITE / Elementor).
    """
    faq_soup = BeautifulSoup(content, 'lxml')
    faq_items_html = ""
    current_faq = ""
    for child in faq_soup.children:
        if child.name in ['h3', 'h4']:
            if current_faq:
                faq_items_html += f'<div class="faq-item">{current_faq}</div>\n'
            current_faq = str(child)
        else:
            if str(child).strip():
                current_faq += str(child)
    if current_faq:
        faq_items_html += f'<div class="faq-item">{current_faq}</div>\n'
    return faq_items_html


def _smart_inject_html_slotsite(file_path, json_data, template_name=""):
    """
    Вставляет контент в HTML-шаблон для движка SLOTSITE (Elementor).
    Ищет H2-теги в wp-page/single-post, вставляет контент и FAQ.
    Поддерживает кастомные кнопки для конкретных шаблонов.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'lxml')

    css_styles = """
    <style class="auto-content-style">
    .auto-content-wrapper { font-family: inherit; line-height: 1.6; margin-top: 15px; color: inherit; }
    .auto-content-wrapper p { margin-bottom: 15px; }
    .auto-content-wrapper h3 { font-size: 20px; font-weight: 700; margin: 25px 0 15px; }
    .auto-content-wrapper ul, .auto-content-wrapper ol { margin-bottom: 20px; padding-left: 20px; }
    .auto-content-wrapper li { margin-bottom: 8px; }
    .auto-content-wrapper table { width: 100%; border-collapse: collapse; margin: 25px 0; background: #ffffff; border: 1px solid #e5e7eb; border-radius: 8px; overflow: hidden; }
    .auto-content-wrapper th { background: #f3f4f6; font-weight: 600; text-align: left; padding: 12px 16px; border-bottom: 2px solid #d1d5db; }
    .auto-content-wrapper td { padding: 12px 16px; border-bottom: 1px solid #e5e7eb; color: #000; }
    .faq-item h3 { font-size: 17px; margin: 0 0 8px 0; font-weight: 700; }
    .faq-item p { margin: 0; font-size: 15px; margin: 0 0 1rem; }
    .auto-image-row { display: flex; flex-wrap: wrap; gap: 20px; justify-content: center; margin: 25px 0; }
    .auto-image-row img { max-width: 100%; height: auto; border-radius: 8px; }
    </style>
    """
    if not soup.find('style', class_='auto-content-style') and soup.head:
        _bs4_safe_append(soup.head, css_styles)

    if json_data.get('seo_title'):
        if soup.title: soup.title.string = json_data['seo_title']
        for tag in soup.find_all('meta', attrs={'property': re.compile(r'title', re.I)}):
            tag['content'] = json_data['seo_title']
    if json_data.get('meta_desc'):
        for tag in soup.find_all('meta', attrs={'name': re.compile(r'description', re.I)}):
            tag['content'] = json_data['meta_desc']
        for tag in soup.find_all('meta', attrs={'property': re.compile(r'description', re.I)}):
            tag['content'] = json_data['meta_desc']

    main_text = ""
    article_sections = []
    faq_sections = []

    if 'main_text' in json_data['sections']:
        main_text = json_data['sections']['main_text']['content'].strip()
    for k, v in json_data['sections'].items():
        if k == 'main_text': continue
        if any(word in k.lower() for word in ['faq', 'вопрос', 'pytania', 'frequent']):
            faq_sections.append(v)
        else:
            article_sections.append(v)

    main_content = soup.find('div', attrs={'data-elementor-type': 'wp-page'})
    if not main_content: main_content = soup.find('div', attrs={'data-elementor-type': 'single-post'})
    if not main_content: main_content = soup.find('main')
    if not main_content: main_content = soup.body if soup.body else soup

    tags_raw = main_content.find_all(['h1', 'h2', 'h3', 'h4', 'p', 'ul', 'ol', 'table'])
    tags = []
    for elem in tags_raw:
        if not elem.parent: continue
        if elem.find_parent(['header', 'footer', 'nav', 'aside']): continue
        if elem.find_parent('div', attrs={'data-elementor-type': ['header', 'footer', 'popup']}): continue
        tags.append(elem)

    doc_article_idx = 0
    last_h2_element = None

    # Кастомная кнопка (только для отдельных шаблонов SLOTSITE)
    play_button_html = ""
    if template_name == "temp-cas-2":
        play_button_html = """
        <div class="elementor-widget elementor-widget-button" style="margin-top: 25px; margin-bottom: 15px;">
            <div class="elementor-widget-container">
                <div class="elementor-button-wrapper">
                    <a class="elementor-button elementor-button-link elementor-size-sm" href="{{AFF_URL}}">
                        <span class="elementor-button-content-wrapper">
                            <span class="elementor-button-text">Play now</span>
                        </span>
                    </a>
                </div>
            </div>
        </div>
        """

    for elem in tags:
        if not elem.parent: continue

        is_article = False
        if elem.name in ['p', 'h3', 'h4', 'ul', 'ol', 'table']:
            is_article = True
            if elem.has_attr('class'):
                classes = " ".join(elem.get('class', []))
                if any(c in classes for c in ['elementor-', 'ekit-', 'e-con', 'menu', 'nav', 'btn', 'button', 'auto-image-row']):
                    is_article = False

        if elem.name == 'h1':
            if json_data.get('h1'): elem.string = json_data['h1']
            if main_text:
                wrapper = soup.new_tag('div', attrs={'class': 'auto-content-wrapper'})
                _bs4_safe_append(wrapper, main_text)
                elem.insert_after(wrapper)
                main_text = ""
            continue

        if elem.name == 'h2':
            h2_text = elem.get_text(strip=True).lower()
            if any(word in h2_text for word in ['top ', 'ranking', 'lista ', 'list of ', 'best ', 'najlepsz']):
                continue
            if 'casino' in h2_text and any(w in h2_text for w in ['play', 'graj', 'where']):
                continue

            last_h2_element = elem

            if any(word in h2_text for word in ['faq', 'pytania', 'вопрос']) or (
                    elem.parent and 'auto-faq' in elem.parent.get('class', [])):
                if faq_sections:
                    sec = faq_sections[0]
                    elem.string = sec['title']
                    html = f"<div class='auto-faq'>{_wrap_faq_content_slotsite(sec['content'])}</div>"
                    for s in faq_sections[1:]:
                        html += (f"<h2 style='margin-top:30px;'>{s['title']}</h2>"
                                 f"<div class='auto-faq'>{_wrap_faq_content_slotsite(s['content'])}</div>")
                    parsed_faq = BeautifulSoup(html, 'html.parser')
                    faq_nodes = list(parsed_faq.children)
                    for node in reversed(faq_nodes):
                        elem.insert_after(node)
                    faq_sections = []
                else:
                    elem.decompose()
                continue

            if doc_article_idx < len(article_sections):
                sec = article_sections[doc_article_idx]
                elem.string = sec['title']
                wrapper = soup.new_tag('div', attrs={'class': 'auto-content-wrapper'})
                parsed_fragment = BeautifulSoup(sec['content'] + play_button_html, 'html.parser')
                for child in list(parsed_fragment.children):
                    wrapper.append(child)
                elem.insert_after(wrapper)
                doc_article_idx += 1
            else:
                elem.decompose()
            continue

        if is_article:
            elem.decompose()

    # Вставляем оставшиеся секции и FAQ, если шаблон не имел нужных H2
    html = ""
    while doc_article_idx < len(article_sections):
        sec = article_sections[doc_article_idx]
        html += (f"<h2 style='margin-top:30px;'>{sec['title']}</h2>"
                 f"<div class='auto-content-wrapper'>{sec['content']}{play_button_html}</div>\n")
        doc_article_idx += 1

    if faq_sections:
        for sec in faq_sections:
            html += (f"<h2 style='margin-top:30px;'>{sec['title']}</h2>"
                     f"<div class='auto-faq'>{_wrap_faq_content_slotsite(sec['content'])}</div>\n")

    if html:
        if last_h2_element and last_h2_element.parent:
            parsed_tail = BeautifulSoup(html, 'html.parser')
            for child in list(parsed_tail.children):
                last_h2_element.parent.append(child)
        elif main_content:
            parsed_tail = BeautifulSoup(html, 'html.parser')
            for child in list(parsed_tail.children):
                main_content.append(child)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(str(soup))


# ============================================================
# SMART_INJECT_HTML — ДИСПЕТЧЕР
# ============================================================

def smart_inject_html(file_path, json_data, engine='SUSHI',
                      site_name=None, page_slug=None, is_policy=False, template_name=""):
    """
    Диспетчер: вызывает нужную версию вставки контента по движку.

    Параметры:
        file_path    — путь к HTML-файлу шаблона
        json_data    — распарсенные данные из Google Doc
        engine       — 'SUSHI' | 'KROSS' | 'SLOTSITE'
        site_name    — название сайта (только SUSHI)
        page_slug    — slug страницы (только KROSS)
        is_policy    — True для страниц политик (только KROSS)
        template_name — имя папки шаблона (только SLOTSITE, для кастомных кнопок)
    """
    if engine == 'KROSS':
        _smart_inject_html_kross(file_path, json_data,
                                 page_slug=page_slug or '', is_policy=is_policy)
    elif engine == 'SLOTSITE':
        _smart_inject_html_slotsite(file_path, json_data, template_name=template_name)
    elif engine == 'SUSHI2':
        _smart_inject_html_sushi2(file_path, json_data, site_name=site_name)
    else:  # SUSHI
        _smart_inject_html_sushi(file_path, json_data, site_name=site_name)


# ============================================================
# INJECT_NAVIGATION_TO_ALL
# (две версии — Bootstrap для SUSHI/KROSS и Elementor для SLOTSITE)
# ============================================================

def _inject_navigation_bootstrap(dst_site_dir, header_links, footer_links):
    """
    Вставляет навигацию в Bootstrap-шаблоны (SUSHI и KROSS).
    Ищет ul#menu-header, ul#menu-footer-1, ul#menu-footer-2.
    """
    h_links = []
    seen_h = set()
    for l in header_links:
        if l['url'] not in seen_h:
            seen_h.add(l['url'])
            h_links.append(l)

    f_links = []
    seen_f = set()
    for l in footer_links:
        if l['url'] not in seen_f:
            seen_f.add(l['url'])
            f_links.append(l)

    for root, dirs, files in os.walk(dst_site_dir):
        if 'index.html' in files:
            file_path = os.path.join(root, 'index.html')
            rel_path = os.path.relpath(root, dst_site_dir)
            current_url = '/' if rel_path == '.' else f'/{rel_path}/'
            current_url = current_url.replace('\\', '/')

            with open(file_path, 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f.read(), 'lxml')

            nav_ul = soup.find('ul', id='menu-header')
            if nav_ul:
                nav_ul.clear()
                for link in h_links:
                    li_classes = ['menu-item', 'nav-item']
                    if link['url'] == current_url: li_classes.append('current-menu-item')
                    li = soup.new_tag('li', attrs={'class': ' '.join(li_classes)})
                    wrapper = soup.new_tag('div', attrs={'class': 'link-wrapper'})
                    a = soup.new_tag('a', href=link['url'], attrs={'class': 'nav-link'})
                    span = soup.new_tag('span', attrs={'itemprop': 'name'})
                    span.string = link['title']
                    a.append(span)
                    wrapper.append(a)
                    li.append(wrapper)
                    nav_ul.append(li)

            footer_main_ul = soup.find('ul', id='menu-footer-1')
            if footer_main_ul:
                footer_main_ul.clear()
                for link in h_links:
                    li = soup.new_tag('li', attrs={'class': 'menu-item nav-item'})
                    a = soup.new_tag('a', href=link['url'])
                    a.string = link['title']
                    li.append(a)
                    footer_main_ul.append(li)

            footer_rules_ul = soup.find('ul', id='menu-footer-2')
            if footer_rules_ul:
                footer_rules_ul.clear()
                for link in f_links:
                    li = soup.new_tag('li', attrs={'class': 'menu-item nav-item'})
                    a = soup.new_tag('a', href=link['url'])
                    a.string = link['title']
                    li.append(a)
                    footer_rules_ul.append(li)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(str(soup))


def _inject_navigation_elementor(dst_site_dir, header_links, footer_links):
    """
    Вставляет навигацию в Elementor-шаблоны (SLOTSITE).
    Ищет data-elementor-type="header" и data-elementor-type="footer".
    """
    h_links = []
    seen_h = set()
    for l in header_links:
        if l['url'] not in seen_h:
            seen_h.add(l['url'])
            h_links.append(l)

    f_links = []
    seen_f = set()
    for l in footer_links:
        if l['url'] not in seen_f:
            seen_f.add(l['url'])
            f_links.append(l)

    for root, dirs, files in os.walk(dst_site_dir):
        if 'index.html' in files:
            file_path = os.path.join(root, 'index.html')
            rel_path = os.path.relpath(root, dst_site_dir)
            current_url = '/' if rel_path == '.' else f'/{rel_path}/'
            current_url = current_url.replace('\\', '/')

            with open(file_path, 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f.read(), 'lxml')

            header = soup.find('div', attrs={'data-elementor-type': 'header'})
            if header:
                nav_widgets = header.find_all(
                    'div', attrs={'data-widget_type': re.compile(r'(nav-menu|navigation-menu)', re.I)})
                for widget in nav_widgets:
                    for old_ul in widget.find_all('ul'):
                        ul_classes = old_ul.get('class', [])
                        ul_id = old_ul.get('id', '')
                        new_ul = soup.new_tag('ul', attrs={'class': ul_classes, 'id': ul_id})
                        for link in h_links:
                            li_classes = ['menu-item']
                            a_classes = ['menu-link', 'hfe-menu-item', 'elementor-item']
                            if link['url'] == current_url:
                                li_classes.extend(['current-menu-item', 'current_page_item'])
                                a_classes.extend(['elementor-item-active', 'hfe-menu-item-active'])
                            li = soup.new_tag('li', attrs={'class': ' '.join(li_classes)})
                            a = soup.new_tag('a', href=link['url'], attrs={'class': ' '.join(a_classes)})
                            a.string = link['title']
                            li.append(a)
                            new_ul.append(li)
                        old_ul.replace_with(new_ul)

            footer = soup.find('div', attrs={'data-elementor-type': 'footer'})
            if footer:
                icon_lists = footer.find_all(
                    'div', attrs={'data-widget_type': re.compile(r'icon-list', re.I)})
                for widget in icon_lists:
                    for old_ul in widget.find_all('ul'):
                        ul_text = str(old_ul).lower()
                        if any(kw in ul_text for kw in ['privacy', 'terms', 'policy', 'polityka', 'useful', 'link', 'cookie']):
                            ul_classes = old_ul.get('class', [])
                            new_ul = soup.new_tag('ul', attrs={'class': ul_classes})
                            for link in f_links:
                                li_classes = ['elementor-icon-list-item']
                                if link['url'] == current_url:
                                    li_classes.append('current-menu-item')
                                li = soup.new_tag('li', attrs={'class': ' '.join(li_classes)})
                                a = soup.new_tag('a', href=link['url'])
                                span = soup.new_tag('span', attrs={'class': 'elementor-icon-list-text'})
                                span.string = link['title']
                                a.append(span)
                                li.append(a)
                                new_ul.append(li)
                            old_ul.replace_with(new_ul)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(str(soup))


def _inject_navigation_sushi(dst_site_dir, header_links, footer_links):
    """
    Вставляет навигацию в SUSHI-шаблоны.
    Ищет nav.main-nav (шапка) и div.footer-column (подвал) — оригинальная структура SUSHI.
    """
    h_links = []
    seen_h = set()
    for l in header_links:
        if l['url'] not in seen_h:
            seen_h.add(l['url'])
            h_links.append(l)

    f_links = []
    seen_f = set()
    for l in footer_links:
        if l['url'] not in seen_f:
            seen_f.add(l['url'])
            f_links.append(l)

    for root, dirs, files in os.walk(dst_site_dir):
        if 'index.html' in files:
            file_path = os.path.join(root, 'index.html')

            with open(file_path, 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f.read(), 'lxml')

            main_nav = soup.find('nav', class_='main-nav')
            if main_nav:
                for a in main_nav.find_all('a', recursive=False):
                    a.decompose()
                dropdown = main_nav.find('div', class_='nav-dropdown')
                for link in h_links:
                    new_a = soup.new_tag('a', href=link['url'])
                    new_a.string = link['title']
                    if dropdown:
                        dropdown.insert_before(new_a)
                    else:
                        main_nav.append(new_a)

            footer_col = soup.find('div', class_='footer-column')
            if footer_col:
                for a in footer_col.find_all('a'):
                    a.decompose()
                for link in f_links:
                    new_a = soup.new_tag('a', href=link['url'])
                    new_a.string = link['title']
                    footer_col.append(new_a)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(str(soup))


def inject_navigation_to_all(dst_site_dir, header_links, footer_links, engine='SUSHI'):
    """Диспетчер навигации: SUSHI/SUSHI2 — nav.main-nav, KROSS — ul#menu-header, SLOTSITE — Elementor."""
    if engine == 'SLOTSITE':
        _inject_navigation_elementor(dst_site_dir, header_links, footer_links)
    elif engine == 'KROSS':
        _inject_navigation_bootstrap(dst_site_dir, header_links, footer_links)
    elif engine == 'SUSHI2':
        _inject_navigation_sushi2(dst_site_dir, header_links, footer_links)
    else:  # SUSHI
        _inject_navigation_sushi(dst_site_dir, header_links, footer_links)


# ============================================================
# UPDATE_JS_MENU (SUSHI и KROSS)
# ============================================================

def update_js_menu(dst_site_dir, menu_items_js):
    """
    Обновляет массив menuItems в JS-файле шаблона (SUSHI и KROSS).
    Ищет app.js, main.js и стандартные пути к ним.
    """
    js_targets = ['app.js', 'main.js', 'js/main.js', 'assets/js/main.js']
    pattern = re.compile(r'(const|let|var)\s+menuItems\s*=\s*\[.*?\];', re.DOTALL | re.IGNORECASE)
    replacement = r'\g<1> menuItems = [' + '\n' + menu_items_js + '];'
    for js_file in js_targets:
        js_path = os.path.join(dst_site_dir, js_file)
        if os.path.exists(js_path):
            try:
                with open(js_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                new_content = pattern.sub(replacement, content)
                if new_content != content:
                    with open(js_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
            except:
                pass


# ============================================================
# REPLACE_GLOBALS
# (три версии: SUSHI — с old_domain, KROSS — с &amp;, SLOTSITE — минимальная)
# ============================================================

def replace_globals(dst_site_dir, domain, site_name, aff_url,
                    old_brand_name=None, old_aff_url=None, old_domain=None, engine='SUSHI'):
    """
    Диспетчер: заменяет глобальные плейсхолдеры и старые значения во всех файлах сайта.

    SUSHI: подставляет old_domain (из og:url шаблона).
    KROSS: заменяет &amp; на & (HTML-энтити).
    SLOTSITE: минимальная замена без old_domain и &amp;.
    """
    extensions = ('.html', '.json', '.xml', '.txt', '.js', '.webmanifest')
    for root, dirs, files in os.walk(dst_site_dir):
        for file_name in files:
            if file_name.endswith(extensions):
                file_path = os.path.join(root, file_name)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Базовые плейсхолдеры (все движки)
                    replacements = {
                        "{{DOMAIN}}": domain,
                        "{{BRAND_NAME}}": site_name,
                        "{{AFF_URL}}": aff_url
                    }
                    for key, value in replacements.items():
                        content = content.replace(key, str(value))

                    # Замена старой партнёрской ссылки (SUSHI, SUSHI2 и KROSS)
                    if engine in ('SUSHI', 'KROSS', 'SUSHI2'):
                        if old_aff_url and aff_url and old_aff_url != aff_url:
                            content = content.replace(old_aff_url, aff_url)
                        # Нормализация дефисов и HTML-энтити
                        content = content.replace("—", "-").replace("–", "-").replace("&amp;", "&")
                    else:  # SLOTSITE
                        content = content.replace("—", "-").replace("–", "-")

                    # Замена старого домена (SUSHI и SUSHI2)
                    if engine in ('SUSHI', 'SUSHI2') and old_domain and old_domain != domain:
                        content = content.replace(old_domain, domain)

                    # Замена старого бренда (все движки)
                    if old_brand_name and len(old_brand_name) > 2 and old_brand_name.lower() != site_name.lower():
                        pattern_brand = re.compile(re.escape(old_brand_name), re.IGNORECASE)
                        content = pattern_brand.sub(site_name, content)

                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                except:
                    pass



# ============================================================
# SUSHI2 — SMART_INJECT_HTML
# ============================================================

def _smart_inject_html_sushi2(file_path, json_data, site_name=None):
    """
    Вставляет контент в HTML-шаблон для движка SUSHI2.
    Шаблон: main.fe601a4c > div.n0dc0f73 > section#intro + секции c H2.
    Три банерных картинки: div.w7d52ae61 > div.o2118d2 > picture > img.b19fbc.
    Сервисные страницы (policy/cookie/terms/…) → div.policy.
    AI-questions / FAQ-only → удаляем intro+games, показываем таблицу/аккордеон.
    Секция с играми (ul.la9c2) всегда сохраняется нетронутой.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'lxml')

    # ---- SEO-теги ----
    if json_data.get('seo_title'):
        if soup.title:
            soup.title.string = json_data['seo_title']
        for tag in soup.find_all('meta', attrs={'property': re.compile(r'title', re.I)}):
            tag['content'] = json_data['seo_title']
        for tag in soup.find_all('meta', attrs={'name': re.compile(r'title', re.I)}):
            tag['content'] = json_data['seo_title']

    if json_data.get('meta_desc'):
        for tag in soup.find_all('meta', attrs={'name': re.compile(r'description', re.I)}):
            tag['content'] = json_data['meta_desc']
        for tag in soup.find_all('meta', attrs={'property': re.compile(r'description', re.I)}):
            tag['content'] = json_data['meta_desc']

    if site_name:
        for tag in soup.find_all('meta', attrs={'property': 'og:site_name'}):
            tag['content'] = site_name

    # ---- Тип страницы ----
    path_lower = file_path.lower()
    is_policy_page = any(kw in path_lower for kw in [
        'policy', 'terms', 'conditions', 'privacy', 'rules', 'cookie', 'responsible',
        'richtlinie', 'datenschutz', 'verantwortung', 'nutzungsbedingungen',
        'agb', 'allgemeine', 'impressum', 'disclaimer', 'legal', 'regulamin', 
        'prywatnosci', 'condiciones', 'privacidad', 'terminos'
    ])
    is_faq_only_page = any(kw in path_lower for kw in [
        'ai-questions', 'ai_questions', 'faq', 'questions', 'вопросы'
    ])

    # ============================================================
    # СЕРВИСНАЯ СТРАНИЦА (policy.html)
    # ============================================================
    if is_policy_page:
        main_wrapper = soup.find('div', class_='n0dc0f73')
        if not main_wrapper:
            main_wrapper = soup.find('main')

        policy_div = soup.find('div', class_='policy')
        
        # 1. Если div.policy нет в шаблоне, динамически создаем его, чтобы текст не обрезался
        if not policy_div:
            intro_sec = soup.find('section', id='intro')
            if intro_sec:
                intro_sec.clear()
                policy_div = soup.new_tag('div', class_='policy')
                intro_sec.append(policy_div)
            elif main_wrapper:
                new_sec = soup.new_tag('section')
                policy_div = soup.new_tag('div', class_='policy')
                new_sec.append(policy_div)
                main_wrapper.insert(0, new_sec)

        # 2. Очищаем ВЕСЬ лишний контент из шаблона (чтобы старые секции не попали на сайт)
        if main_wrapper and policy_div:
            policy_parent_sec = policy_div.find_parent('section')
            # Проходимся по всем section внутри main_wrapper и удаляем те, где нет нашей политики
            for sec in list(main_wrapper.find_all('section', recursive=False)):
                if sec != policy_parent_sec:
                    sec.decompose()

        # 3. Заполняем политику всем контентом из ТЗ
        if policy_div:
            policy_div.clear()
            if json_data.get('h1'):
                h1 = soup.new_tag('h1')
                h1.string = json_data['h1']
                policy_div.append(h1)
            
            if 'main_text' in json_data.get('sections', {}):
                mt = json_data['sections']['main_text']['content'].strip()
                if mt:
                    policy_div.append(BeautifulSoup(mt, 'html.parser'))
            
            faq_keywords = [
                'faq', 'вопрос', 'pytania', 'frequent', 
                'häufig', 'gestellte', 'fragen', 
                'vragen', 'veelgestelde', 
                'preguntas', 'frecuentes', 
                'domande', 'frequenti', 
                'ceisteanna', 'coitianta', 
                'foire', 'questions'
            ]
            
            for k, v in json_data.get('sections', {}).items():
                if k == 'main_text':
                    continue
                
                # Используем регулярные выражения \b для поиска точного слова, а не подстроки
                is_faq = False
                for w in faq_keywords:
                    if re.search(rf'\b{re.escape(w)}\b', k.lower(), re.UNICODE):
                        is_faq = True
                        break
                
                if is_faq:
                    continue
                    
                if v.get('title'):
                    h2 = soup.new_tag('h2')
                    h2.string = v['title']
                    policy_div.append(h2)
                if v.get('content'):
                    policy_div.append(BeautifulSoup(v['content'], 'html.parser'))

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(str(soup))
        return

    # ============================================================
    # FAQ-ONLY СТРАНИЦА (AI Questions / вопросы-ответы)
    # ============================================================
    if is_faq_only_page:
        main_wrapper = soup.find('div', class_='n0dc0f73')
        if not main_wrapper:
            main_wrapper = soup.find('main')

        # Удаляем intro-секцию (H1 + hero + первый баннер)
        intro_sec = soup.find('section', id='intro')
        if intro_sec:
            intro_sec.decompose()

        # Удаляем секции с играми (ul.la9c2) и все прочие контентные секции
        if main_wrapper:
            for sec in list(main_wrapper.find_all('section', recursive=False)):
                if sec.get('id') != 'faq':
                    sec.decompose()

        # Собираем весь контент (SEO-заголовок → H1, таблицы, FAQ H3/P)
        faq_html = ''
        if json_data.get('h1'):
            faq_html += f'<h1>{json_data["h1"]}</h1>\n'

        if 'main_text' in json_data.get('sections', {}):
            mt = json_data['sections']['main_text']['content'].strip()
            if mt:
                faq_html += mt + '\n'

        for k, v in json_data.get('sections', {}).items():
            if k == 'main_text':
                continue
            if v.get('title'):
                faq_html += f'<h2>{v["title"]}</h2>\n'
            if v.get('content'):
                faq_html += v['content'] + '\n'

        # Вставляем в section#faq или создаём
        faq_sec = soup.find('section', id='faq')
        if not faq_sec and main_wrapper:
            faq_sec = soup.new_tag('section', id='faq')
            main_wrapper.append(faq_sec)

        if faq_sec:
            faq_sec.clear()
            
            # Парсим собранный HTML, чтобы найти таблицы и добавить им класс
            faq_soup_content = BeautifulSoup(faq_html, 'html.parser')
            for tbl in faq_soup_content.find_all('table'):
                existing_classes = tbl.get('class', [])
                if isinstance(existing_classes, str):
                    existing_classes = [existing_classes]
                # Добавляем наш особый класс
                tbl['class'] = existing_classes + ['ai-questions-table']
                
            # Вставляем обновленный контент с классами
            faq_sec.append(faq_soup_content)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(str(soup))
        return

    # ============================================================
    # ГЛАВНАЯ / ОБЫЧНАЯ СТРАНИЦА
    # ============================================================

    BANNER_BLOCK = (
        '<div class="w7d52ae61">'
        '<div class="o2118d2">'
        '<picture>'
        '<img class="b19fbc" src="{src}" alt="{{BRAND_NAME}}">'
        '</picture>'
        '</div>'
        '</div>'
    )

    def make_section(h2_text, content_html, banner_src=None):
        sec = soup.new_tag('section')
        h2 = soup.new_tag('h2')
        h2.string = h2_text
        sec.append(h2)
        if content_html:
            sec.append(BeautifulSoup(content_html, 'html.parser'))
        if banner_src:
            sec.append(BeautifulSoup(BANNER_BLOCK.format(src=banner_src), 'html.parser'))
        return sec

    main_wrapper = soup.find('div', class_='n0dc0f73')
    if not main_wrapper:
        main_wrapper = soup.find('main')

    # ---- Hero (section#intro) ----
    intro_section = soup.find('section', id='intro')
    if intro_section:
        h1_tag = intro_section.find('h1')
        if h1_tag and json_data.get('h1'):
            h1_tag.string = json_data['h1']

        hero_content_div = intro_section.find('div', class_='hero__content')
        if hero_content_div:
            hero_p = hero_content_div.find('p')
            if hero_p:
                desc = json_data.get('hero_desc', '')
                if not desc:
                    mt = json_data.get('sections', {}).get('main_text', {}).get('content', '').strip()
                    if mt:
                        desc = re.sub(r'<[^>]+>', '', mt.split('\n')[0]).strip()
                if desc:
                    hero_p.string = desc

    # ---- Разбираем секции ----
    article_sections = []
    faq_sections = []
    
    # ---- Разбираем секции ----
    article_sections = []
    faq_sections = []
    
    faq_keywords = [
        'faq', 'вопрос', 'pytania', 'frequent', 
        'häufig', 'gestellte', 'fragen', 
        'vragen', 'veelgestelde', 
        'preguntas', 'frecuentes', 
        'domande', 'frequenti', 
        'ceisteanna', 'coitianta', 
        'foire', 'questions'
    ]
    
    for k, v in json_data.get('sections', {}).items():
        if k == 'main_text':
            continue
            
        # Защита от срабатывания на частях слов (например "Datenschutzanfragen")
        is_faq = False
        for w in faq_keywords:
            if re.search(rf'\b{re.escape(w)}\b', k.lower(), re.UNICODE):
                is_faq = True
                break
                
        if is_faq:
            faq_sections.append(v)
        else:
            article_sections.append(v)

    BANNER_SRCS = [
        '/images/banner_main_1.webp',
        '/images/banner_main_2.webp',
        '/images/banner_main_3.webp',
    ]

    # Собираем «слоты» — шаблонные секции, пригодные для замены контентом.
    # Пропускаем: intro, faq, секции с играми (ul.la9c2)
    existing_slots = []
    if main_wrapper:
        for sec in main_wrapper.find_all('section', recursive=False):
            sid = sec.get('id', '')
            if sid in ('intro', 'faq'):
                continue
            if sec.find('ul', class_='la9c2'):
                # Секция с играми — оставляем нетронутой
                continue
            existing_slots.append(sec)

    # Заполняем слоты контентом из ТЗ.
    # banner_main_1 зарезервирован для hero/intro → первый article_section получает banner_main_2
    for i, art_sec in enumerate(article_sections):
        b_idx = (i + 1) % len(BANNER_SRCS)   # 1, 2, 0, 1, 2, … → banner_main_2/3/1 …
        banner_src = BANNER_SRCS[b_idx]

        if i < len(existing_slots):
            sec = existing_slots[i]

            # Обновляем H2
            h2 = sec.find('h2')
            if h2:
                h2.string = art_sec.get('title', '')
            else:
                h2 = soup.new_tag('h2')
                h2.string = art_sec.get('title', '')
                sec.insert(0, h2)

            # Удаляем старый контент (кроме H2 и div.w7d52ae61)
            for child in list(sec.children):
                tag_name = getattr(child, 'name', None)
                if not tag_name:
                    continue
                if tag_name == 'h2':
                    continue
                child_classes = (child.get('class', [])
                                 if hasattr(child, 'get') else [])
                if isinstance(child_classes, str):
                    child_classes = [child_classes]
                if 'w7d52ae61' in child_classes:
                    continue
                child.extract()

            # Вставляем новый контент
            content_html = art_sec.get('content', '').strip()
            banner_div = sec.find('div', class_='w7d52ae61')

            if content_html:
                content_soup = BeautifulSoup(content_html, 'html.parser')
                if banner_div:
                    banner_div.insert_before(content_soup)
                else:
                    h2_tag = sec.find('h2')
                    if h2_tag:
                        h2_tag.insert_after(content_soup)
                    else:
                        sec.append(content_soup)
                    sec.append(BeautifulSoup(BANNER_BLOCK.format(src=banner_src), 'html.parser'))
        else:
            # Создаём новую секцию
            new_sec = make_section(
                art_sec.get('title', ''),
                art_sec.get('content', ''),
                banner_src
            )
            faq_sec_tag = main_wrapper.find('section', id='faq') if main_wrapper else None
            if faq_sec_tag:
                faq_sec_tag.insert_before(new_sec)
            elif main_wrapper:
                main_wrapper.append(new_sec)

    # Удаляем лишние шаблонные слоты (ТЗ меньше шаблона)
    for j in range(len(article_sections), len(existing_slots)):
        existing_slots[j].decompose()

    # ---- FAQ в section#faq ----
    faq_sec_tag = main_wrapper.find('section', id='faq') if main_wrapper else None
    if faq_sections:
        faq_html = ''
        for faq_sec in faq_sections:
            faq_title = faq_sec.get('title', 'FAQ')
            faq_html += f'<h2>{faq_title}</h2>\n'
            # Контент уже содержит <h3>вопрос</h3><p>ответ</p>
            faq_html += faq_sec.get('content', '') + '\n'
        if faq_sec_tag:
            faq_sec_tag.clear()
            faq_sec_tag.append(BeautifulSoup(faq_html, 'html.parser'))
        elif main_wrapper:
            new_faq = soup.new_tag('section', id='faq')
            new_faq.append(BeautifulSoup(faq_html, 'html.parser'))
            main_wrapper.append(new_faq)
    else:
        if faq_sec_tag:
            faq_sec_tag.decompose()

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(str(soup))


# ============================================================
# SUSHI2 — INJECT_NAVIGATION
# ============================================================

def _inject_navigation_sushi2(dst_site_dir, header_links, footer_links):
    """
    Вставляет навигацию в SUSHI2-шаблоны.
    Шапка: ul.hf0d9 (desktop) + ul.e7cb498 (мобильное меню).
    Подвал: ul.p0e1ad8b.
    """
    h_links = list({l['url']: l for l in header_links}.values())
    f_links = list({l['url']: l for l in footer_links}.values())

    for root, dirs, files in os.walk(dst_site_dir):
        if 'index.html' not in files:
            continue
        file_path = os.path.join(root, 'index.html')

        with open(file_path, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f.read(), 'lxml')

        for ul_class in ['hf0d9', 'e7cb498']:
            nav_ul = soup.find('ul', class_=ul_class)
            if nav_ul:
                nav_ul.clear()
                for link in h_links:
                    li = soup.new_tag('li')
                    a = soup.new_tag('a', rel='nofollow', href=link['url'])
                    a.string = link['title']
                    li.append(a)
                    nav_ul.append(li)

        footer_ul = soup.find('ul', class_='p0e1ad8b')
        if footer_ul:
            footer_ul.clear()
            for link in f_links:
                li = soup.new_tag('li')
                a = soup.new_tag('a', href=link['url'])
                a.string = link['title']
                li.append(a)
                footer_ul.append(li)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(str(soup))


# ============================================================
# SUSHI2 — PROCESS_PAGES
# ============================================================

def _process_pages_sushi2(tz_df, dst_site_dir, site_name):
    """
    Обрабатывает все страницы ТЗ для движка SUSHI2.
    - 'main'          → example.html, 3 контентных баннера
    - 'eeat'          → парсим вложенные Google Doc-ссылки → сервисные страницы
    - ai-questions/faq → example.html без intro/games, только таблица/аккордеон
    - сервисные        → policy.html (div.policy)
    - остальные        → example.html
    Лого: только <a id="logo-container-*"> контейнеры в шапке/aside.
    Фавикон: <link rel="icon">.
    Баннеры: div.w7d52ae61 > div.o2118d2 > picture > img, cycling через downloaded_images.
    Возвращает: pages_to_keep, menu_items_js, old_brand_name, old_aff_url, old_domain
    """
    pages_to_keep = []
    menu_items_js = ""
    header_nav_links = []
    footer_nav_links = []

    example_path = os.path.join(dst_site_dir, 'example.html')
    policy_path  = os.path.join(dst_site_dir, 'policy.html')

    if not os.path.exists(example_path):
        raise Exception("❌ Ошибка: Шаблон 'example.html' не найден!")

    old_brand_name = get_old_brand_name(example_path)
    old_aff_url    = get_old_aff_url(example_path)
    old_domain     = get_old_domain(example_path)

    # ---- Лого / Фав ----
    global_logo_path = None
    global_fav_path  = None

    for index, row in tz_df.iterrows():
        raw_url = str(row.get('ЧПУ | URL', '')).strip().lower().replace(' ', '')
        if raw_url in ['fav/logo', 'fav|logo', 'logo/fav', 'logo|fav']:
            img_link = str(row.get('Картинки / Image', '')).strip()
            doc_link = str(row.get('Текст / Article', '')).strip()
            links_to_use = img_link if img_link and img_link.lower() != 'nan' else doc_link
            print(f"\n🔍 [SUSHI2] Лого/Фав: {links_to_use}")
            logo_fav_paths = download_and_convert_gdrive_images(
                links_to_use, 'global', dst_site_dir, is_logo_fav=True)
            for path in logo_fav_paths:
                fn = os.path.basename(path).lower()
                if 'logo' in fn:
                    global_logo_path = path
                elif 'fav' in fn:
                    global_fav_path = path
            if 'images' not in pages_to_keep:
                pages_to_keep.append('images')
            break

    # ---- Основной цикл ----
    for index, row in tz_df.iterrows():
        raw_url = row.get('ЧПУ | URL')
        raw_doc = row.get('Текст / Article')
        raw_img = row.get('Картинки / Image') if 'Картинки / Image' in tz_df.columns else None

        if pd.isna(raw_url) or pd.isna(raw_doc):
            continue

        page_url = str(raw_url).strip()
        doc_link = str(raw_doc).strip()
        img_link = str(raw_img).strip() if pd.notna(raw_img) else ""

        if not page_url or page_url.lower() == 'nan':
            continue
        if not doc_link or doc_link.lower() == 'nan':
            continue

        page_slug      = page_url.lower().replace(' ', '-')
        normalized_url = page_url.lower().replace(' ', '')

        if normalized_url in ['fav/logo', 'fav|logo', 'logo/fav', 'logo|fav']:
            continue

        # ---- EEAT: вложенные сервисные страницы ----
        if page_slug == 'eeat':
            doc_text_eeat = get_gdoc_text_and_assets(
                doc_link, dst_site_dir, 'eeat', engine='SUSHI')
            soup_eeat = BeautifulSoup(doc_text_eeat, 'lxml')
            template_to_use = policy_path if os.path.exists(policy_path) else example_path

            for a_tag in soup_eeat.find_all('a'):
                policy_url  = a_tag.get('href')
                link_text   = a_tag.get_text(strip=True)
                parent_text = (a_tag.find_parent().get_text(strip=True)
                               if a_tag.find_parent() else "")
                clean_parent = re.sub(r'[:\-–—\d]+$', '', parent_text).strip()
                display_title = link_text if len(link_text) > 4 else clean_parent
                if not display_title:
                    display_title = f"Policy {len(footer_nav_links) + 1}"

                if policy_url and 'docs.google.com' in policy_url:
                    policy_slug = generate_policy_slug(
                        display_title + ' ' + link_text)
                    footer_nav_links.append({
                        'title': display_title.capitalize(),
                        'url': f'/{policy_slug}/'
                    })

                    policy_text = get_gdoc_text_and_assets(
                        policy_url, dst_site_dir, policy_slug, engine='SUSHI')
                    policy_json = parse_doc_to_json(policy_text, engine='SUSHI')

                    policy_dir  = os.path.join(dst_site_dir, policy_slug)
                    os.makedirs(policy_dir, exist_ok=True)
                    policy_file = os.path.join(policy_dir, 'index.html')
                    shutil.copy2(template_to_use, policy_file)

                    smart_inject_html(
                        policy_file, policy_json, engine='SUSHI2', site_name=site_name)
                    pages_to_keep.append(policy_slug)

                    # Применяем лого/фав к сервисной странице
                    if global_logo_path or global_fav_path:
                        try:
                            with open(policy_file, 'r', encoding='utf-8') as f:
                                sp = BeautifulSoup(f.read(), 'html.parser')
                            if global_logo_path:
                                logo_ext = os.path.splitext(global_logo_path)[1]
                                for la in sp.find_all(
                                        'a', id=re.compile(r'logo-container', re.I)):
                                    for img in la.find_all('img'):
                                        img['src'] = f"/images/logo{logo_ext}"
                                        img.attrs.pop('srcset', None)
                                        img.attrs.pop('sizes', None)
                            if global_fav_path:
                                fav_ext = os.path.splitext(global_fav_path)[1]
                                for lnk in sp.find_all(
                                        'link',
                                        rel=lambda r: r and 'icon' in ' '.join(r).lower()):
                                    lnk['href'] = f"/images/fav{fav_ext}"
                            with open(policy_file, 'w', encoding='utf-8') as f:
                                f.write(str(sp))
                        except Exception:
                            pass
            continue

        # ---- Загружаем текст ----
        raw_doc_text = get_gdoc_text_and_assets(
            doc_link, dst_site_dir, page_slug, engine='SUSHI')
        doc_text  = clean_html_styles(raw_doc_text)
        json_data = parse_doc_to_json(doc_text, engine='SUSHI')

        # ---- Определяем целевой файл ----
        is_service = any(kw in page_slug for kw in [
            'policy', 'privacy', 'terms', 'cookie', 'responsible',
            'richtlinie', 'datenschutz', 'cookies', 'rules', 'nutzungsbedingungen',
            'agb', 'allgemeine', 'impressum', 'disclaimer', 'legal', 'regulamin', 
            'prywatnosci', 'condiciones', 'privacidad', 'terminos'
        ])

        # ---- Скачиваем картинки (строго max 3, пропускаем для сервисных страниц) ----
        downloaded_images = []
        if not is_service and img_link and img_link.lower() != 'nan':
            downloaded_images = download_and_convert_gdrive_images(
                img_link, page_slug, dst_site_dir, is_logo_fav=False)
            
            # Ограничиваем количество картинок строго 3 штуками
            downloaded_images = downloaded_images[:3]
            
            if downloaded_images and 'images' not in pages_to_keep:
                pages_to_keep.append('images')

        if page_slug == 'main':
            pages_to_keep.append('index.html')
            target_file = os.path.join(dst_site_dir, 'index.html')
            if not os.path.exists(target_file):
                shutil.copy2(example_path, target_file)
            if len(page_url) <= 15:
                header_nav_links.append({'title': page_url.capitalize(), 'url': '/'})
                menu_items_js += (
                    f'{{ text: "{page_url.capitalize()}", href: "/", '
                    f'url: "/", position: "start" }},\n'
                )
            # Manifest
            main_title = json_data.get('seo_title')
            main_desc  = json_data.get('meta_desc')
            if main_title or main_desc:
                for m_name in ['manifest.json', 'manifest.webmanifest',
                               'site.webmanifest']:
                    m_path = os.path.join(dst_site_dir, m_name)
                    if os.path.exists(m_path):
                        try:
                            with open(m_path, 'r', encoding='utf-8') as mf:
                                m_data = json.load(mf)
                            if main_title:
                                m_data['name'] = main_title
                            if main_desc:
                                m_data['description'] = main_desc
                            with open(m_path, 'w', encoding='utf-8') as mf:
                                json.dump(m_data, mf, ensure_ascii=False, indent=4)
                        except Exception:
                            pass
        else:
            template_src = (policy_path
                            if (is_service and os.path.exists(policy_path))
                            else example_path)
            pages_to_keep.append(page_slug)
            page_dir = os.path.join(dst_site_dir, page_slug)
            os.makedirs(page_dir, exist_ok=True)
            target_file = os.path.join(page_dir, 'index.html')
            shutil.copy2(template_src, target_file)

            if len(page_url) <= 15:
                header_nav_links.append({
                    'title': page_url.capitalize(),
                    'url': f'/{page_slug}/'
                })
                menu_items_js += (
                    f'{{ text: "{page_url.capitalize()}", '
                    f'href: "/{page_slug}/", url: "/{page_slug}/", '
                    f'position: "end" }},\n'
                )

        # ---- Вставляем контент ----
        smart_inject_html(target_file, json_data, engine='SUSHI2', site_name=site_name)

        # ---- Замена картинок ----
        if downloaded_images or global_logo_path or global_fav_path:
            try:
                with open(target_file, 'r', encoding='utf-8') as f:
                    soup_final = BeautifulSoup(f.read(), 'html.parser')

                # Логотип — только внутри <a id="logo-container-*">
                # (не трогаем баннерные img.b19fbc в hero/секциях)
                if global_logo_path:
                    logo_ext = os.path.splitext(global_logo_path)[1]
                    for logo_a in soup_final.find_all(
                            'a', id=re.compile(r'logo-container', re.I)):
                        for img in logo_a.find_all('img'):
                            img['src'] = f"/images/logo{logo_ext}"
                            img.attrs.pop('srcset', None)
                            img.attrs.pop('sizes', None)
                    for meta in soup_final.find_all(
                            'meta',
                            attrs={'property': re.compile(r'og:image', re.I)}):
                        meta['content'] = f"/images/logo{logo_ext}"

                # Фавикон
                if global_fav_path:
                    fav_ext = os.path.splitext(global_fav_path)[1]
                    for lnk in soup_final.find_all(
                            'link',
                            rel=lambda r: r and 'icon' in ' '.join(r).lower()):
                        lnk['href'] = f"/images/fav{fav_ext}"

                # 1. Отдельно обрабатываем баннер в #intro (вставляем логотип)
                intro_sec = soup_final.find('section', id='intro')
                intro_banner = intro_sec.find('div', class_='w7d52ae61') if intro_sec else None

                if intro_banner and global_logo_path:
                    intro_img = intro_banner.find('img')
                    if intro_img:
                        logo_ext = os.path.splitext(global_logo_path)[1]
                        intro_img['src'] = f"/images/logo{logo_ext}"
                        intro_img.attrs.pop('srcset', None)
                        intro_img.attrs.pop('sizes', None)

                # 2. Ищем все контентные баннеры на странице
                banner_wrappers = soup_final.find_all('div', class_='w7d52ae61')

                # Обязательно убираем intro_banner из списка, чтобы скрипт не перезаписал наш логотип!
                if intro_banner in banner_wrappers:
                    banner_wrappers.remove(intro_banner)

                # 3. Распределяем скачанные картинки (без зацикливания, лишние слоты удаляем)
                if downloaded_images:
                    for b_i, wrapper in enumerate(banner_wrappers):
                        if b_i < len(downloaded_images):
                            pic = wrapper.find('picture')
                            if not pic:
                                continue
                            img_tag = pic.find('img')
                            if not img_tag:
                                continue
                            
                            # Берём картинку по индексу (никакого cycling)
                            img_path = downloaded_images[b_i]
                            img_tag['src'] = f"/{img_path}"
                            img_tag['alt'] = f"{page_slug} {b_i + 1}"
                            img_tag.attrs.pop('srcset', None)
                            img_tag.attrs.pop('sizes', None)
                        else:
                            # Если слотов для картинок больше, чем самих картинок (например, картинок 2, а слотов 4)
                            wrapper.decompose()
                else:
                    # Если скачанных картинок вообще нет — убираем все контентные баннеры
                    for bw in banner_wrappers:
                        bw.decompose()

                with open(target_file, 'w', encoding='utf-8') as f:
                    f.write(str(soup_final))
            except Exception as e:
                print(f"❌ [SUSHI2] Ошибка замены картинок на {page_slug}: {e}")

    inject_navigation_to_all(
        dst_site_dir, header_nav_links, footer_nav_links, engine='SUSHI2')

    return pages_to_keep, menu_items_js, old_brand_name, old_aff_url, old_domain

# ============================================================
# PROCESS_PAGES — ДВИЖОК SUSHI
# ============================================================

def _process_pages_sushi(tz_df, dst_site_dir, site_name):
    """
    Обрабатывает все страницы из ТЗ для движка SUSHI.
    Возвращает: pages_to_keep, menu_items_js, old_brand_name, old_aff_url, old_domain
    """
    pages_to_keep = []
    menu_items_js = ""
    header_nav_links = []
    footer_nav_links = []

    example_path = os.path.join(dst_site_dir, 'example.html')
    policy_path = os.path.join(dst_site_dir, 'policy.html')

    if not os.path.exists(example_path):
        raise Exception("❌ Ошибка: Шаблон 'example.html' не найден!")

    old_brand_name = get_old_brand_name(example_path)
    old_aff_url = get_old_aff_url(example_path)
    old_domain = get_old_domain(example_path)

    # Предварительный поиск логотипа и фавикона
    global_logo_path = None
    global_fav_path = None

    for index, row in tz_df.iterrows():
        raw_url = str(row.get('ЧПУ | URL', '')).strip().lower().replace(' ', '')
        if raw_url in ['fav/logo', 'fav|logo', 'logo/fav', 'logo|fav']:
            img_link = str(row.get('Картинки / Image', '')).strip()
            doc_link = str(row.get('Текст / Article', '')).strip()
            links_to_use = img_link if img_link and img_link.lower() != 'nan' else doc_link

            print(f"\n🔍 Нашли строку ЛОГО/ФАВ. Ссылка: {links_to_use}")
            logo_fav_paths = download_and_convert_gdrive_images(
                links_to_use, 'global', dst_site_dir, is_logo_fav=True)
            for path in logo_fav_paths:
                fn = os.path.basename(path).lower()
                if 'logo' in fn: global_logo_path = path
                elif 'fav' in fn: global_fav_path = path
            if 'images' not in pages_to_keep: pages_to_keep.append('images')
            break

    for index, row in tz_df.iterrows():
        raw_url = row.get('ЧПУ | URL')
        raw_doc = row.get('Текст / Article')
        raw_img = row.get('Картинки / Image') if 'Картинки / Image' in tz_df.columns else None

        if pd.isna(raw_url) or pd.isna(raw_doc): continue

        page_url = str(raw_url).strip()
        doc_link = str(raw_doc).strip()
        img_link = str(raw_img).strip() if pd.notna(raw_img) else ""

        if not page_url or page_url.lower() == 'nan' or not doc_link or doc_link.lower() == 'nan': continue

        page_slug = page_url.lower().replace(' ', '-')
        normalized_url = page_url.lower().replace(' ', '')

        if normalized_url in ['fav/logo', 'fav|logo', 'logo/fav', 'logo|fav']: continue

        # Страница EEAT — парсим политики из Google Doc
        if page_slug == 'eeat':
            doc_text = get_gdoc_text_and_assets(doc_link, dst_site_dir, 'eeat', engine='SUSHI')
            soup_eeat = BeautifulSoup(doc_text, 'lxml')
            template_to_use = policy_path if os.path.exists(policy_path) else example_path

            for a_tag in soup_eeat.find_all('a'):
                policy_url = a_tag.get('href')
                link_text = a_tag.get_text(strip=True)
                parent_text = a_tag.find_parent().get_text(strip=True) if a_tag.find_parent() else ""
                clean_parent = re.sub(r'[:\-–—\d]+$', '', parent_text).strip()
                display_title = link_text if len(link_text) > 4 else clean_parent
                if not display_title: display_title = f"Policy {len(footer_nav_links)+1}"

                if policy_url and 'docs.google.com' in policy_url:
                    policy_slug = generate_policy_slug(display_title + " " + link_text)
                    footer_nav_links.append({'title': display_title.capitalize(), 'url': f'/{policy_slug}/'})

                    policy_text = get_gdoc_text_and_assets(policy_url, dst_site_dir, policy_slug, engine='SUSHI')
                    policy_json = parse_doc_to_json(policy_text, engine='SUSHI')

                    policy_dir = os.path.join(dst_site_dir, policy_slug)
                    os.makedirs(policy_dir, exist_ok=True)
                    policy_file = os.path.join(policy_dir, 'index.html')
                    shutil.copy2(template_to_use, policy_file)

                    smart_inject_html(policy_file, policy_json, engine='SUSHI', site_name=site_name)
                    pages_to_keep.append(policy_slug)
            continue

        raw_doc_text = get_gdoc_text_and_assets(doc_link, dst_site_dir, page_slug, engine='SUSHI')
        doc_text = clean_html_styles(raw_doc_text)
        json_data = parse_doc_to_json(doc_text, engine='SUSHI')

        # Скачиваем картинки контента
        downloaded_images = []
        if img_link and img_link.lower() != 'nan':
            downloaded_images = download_and_convert_gdrive_images(
                img_link, page_slug, dst_site_dir, is_logo_fav=False)
            if downloaded_images and 'images' not in pages_to_keep:
                pages_to_keep.append('images')

        if page_slug == 'main':
            pages_to_keep.append('index.html')
            target_file = os.path.join(dst_site_dir, 'index.html')
            if not os.path.exists(target_file):
                shutil.copy2(example_path, target_file)
            if len(page_url) <= 15:
                header_nav_links.append({'title': page_url.capitalize(), 'url': '/'})
                menu_items_js += f'{{ text: "{page_url.capitalize()}", href: "/", url: "/", position: "start" }},\n'

            main_title = json_data.get('seo_title')
            main_desc = json_data.get('meta_desc')
            if main_title or main_desc:
                for m_name in ['manifest.json', 'manifest.webmanifest', 'site.webmanifest']:
                    m_path = os.path.join(dst_site_dir, m_name)
                    if os.path.exists(m_path):
                        try:
                            with open(m_path, 'r', encoding='utf-8') as mf: m_data = json.load(mf)
                            if main_title: m_data['name'] = main_title
                            if main_desc: m_data['description'] = main_desc
                            with open(m_path, 'w', encoding='utf-8') as mf:
                                json.dump(m_data, mf, ensure_ascii=False, indent=4)
                        except Exception: pass
        else:
            pages_to_keep.append(page_slug)
            page_dir = os.path.join(dst_site_dir, page_slug)
            os.makedirs(page_dir, exist_ok=True)
            target_file = os.path.join(page_dir, 'index.html')
            if len(page_url) <= 15:
                header_nav_links.append({'title': page_url.capitalize(), 'url': f'/{page_slug}/'})
                shutil.copy2(example_path, target_file)
                menu_items_js += f'{{ text: "{page_url.capitalize()}", href: "/{page_slug}/", url: "/{page_slug}/", position: "end" }},\n'

        # Вставляем текст
        smart_inject_html(target_file, json_data, engine='SUSHI', site_name=site_name)

        # Подмена картинок
        if downloaded_images or global_logo_path or global_fav_path:
            try:
                with open(target_file, 'r', encoding='utf-8') as f:
                    soup_final = BeautifulSoup(f.read(), 'html.parser')

                if global_logo_path:
                    for img in soup_final.find_all('img'):
                        if 'logo' in img.get('src', '').lower():
                            img['src'] = f"/{global_logo_path}"
                            if 'srcset' in img.attrs: del img['srcset']
                            if 'sizes' in img.attrs: del img['sizes']

                if global_fav_path:
                    for link in soup_final.find_all('link', rel=lambda r: r and 'icon' in r.lower()):
                        link['href'] = f"/{global_fav_path}"

                if downloaded_images:
                    target_blocks = soup_final.find_all(
                        'div', class_=lambda c: c and ('custom-feature-card' in c or 'text-image' in c))
                    content_imgs = []
                    for block in target_blocks:
                        img = block.find('img')
                        if img: content_imgs.append(img)
                    if content_imgs:
                        for i, img_tag in enumerate(content_imgs[:3]):
                            img_path = downloaded_images[i % len(downloaded_images)]
                            img_tag['src'] = f"/{img_path}"
                            img_tag['alt'] = f"{page_slug} {i+1}"
                            if 'srcset' in img_tag.attrs: del img_tag['srcset']
                            if 'sizes' in img_tag.attrs: del img_tag['sizes']

                with open(target_file, 'w', encoding='utf-8') as f:
                    f.write(str(soup_final))
            except Exception as e:
                print(f"❌ Ошибка подмены HTML картинок на странице {page_slug}: {e}")

    inject_navigation_to_all(dst_site_dir, header_nav_links, footer_nav_links, engine='SUSHI')

    return pages_to_keep, menu_items_js, old_brand_name, old_aff_url, old_domain


# ============================================================
# PROCESS_PAGES — ДВИЖОК KROSS
# ============================================================

def _download_and_convert_kross(drive_links_str, page_slug, dst_site_dir, is_logo_fav=False):
    """
    Скачивает картинки для движка KROSS через gdown.
    Использует SUB-DIRECTORY ISOLATION: каждая ссылка скачивается в отдельную
    подпапку (0/, 1/, 2/, …), чтобы файлы с одинаковыми именами из разных
    ссылок не перезаписывали друг друга (характерно для KROSS-ТЗ с 3 раздельными
    ссылками на картинки для каждой секции).
    Логика конвертации — идентична оригинальному kross.py.
    """
    if (not isinstance(drive_links_str, str)
            or not drive_links_str.strip()
            or drive_links_str.lower() == 'nan'):
        return []
 
    img_dir = os.path.join(dst_site_dir, 'images')
    os.makedirs(img_dir, exist_ok=True)
    downloaded_paths = []
 
    print(f"⏳ [KROSS] Скачиваем картинки для [{page_slug}]: {drive_links_str}")
 
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            if 'folder' in drive_links_str:
                gdown.download_folder(
                    url=drive_links_str, output=temp_dir, quiet=True, use_cookies=False)
            else:
                urls = re.findall(r'(https?://[^\s,]+)', drive_links_str)
                if not urls:
                    urls = [drive_links_str]
                for idx, url in enumerate(urls):
                    # ИЗОЛЯЦИЯ: отдельная папка на каждую ссылку, чтобы
                    # файлы с одинаковыми именами не перезаписывали друг друга
                    sub_dir = os.path.join(temp_dir, str(idx))
                    os.makedirs(sub_dir, exist_ok=True)
                    gdown.download(url=url, output=sub_dir + '/', quiet=True, fuzzy=True)
        except Exception as e:
            print(f"❌ [KROSS] Ошибка загрузки: {e}")
 
        downloaded_files = []
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if (ext in ['.png', '.jpg', '.jpeg', '.webp', '.gif', '.svg',
                             '.ico', '.avif', '.heic'] or not ext):
                    downloaded_files.append(os.path.join(root, file))
        downloaded_files.sort()
 
        limit = 2 if is_logo_fav else 3
        files_to_process = downloaded_files[:limit]
 
        if not files_to_process:
            print(f"⚠️ [KROSS] Для [{page_slug}] картинки не найдены.")
            return []
 
        assigned_names = []
 
        for i, file_path in enumerate(files_to_process):
            try:
                original_name = os.path.basename(file_path).lower()
                ext = os.path.splitext(file_path)[1].lower()
                if not ext:
                    ext = '.png'
 
                if is_logo_fav:
                    if 'fav' in original_name or 'icon' in original_name:
                        filename = f"fav{ext}"
                    elif 'logo' in original_name:
                        filename = f"logo{ext}"
                    else:
                        filename = f"logo{ext}" if i == 0 else f"fav{ext}"
 
                    if filename in assigned_names:
                        filename = f"fav{ext}" if filename.startswith("logo") else f"logo{ext}"
 
                    assigned_names.append(filename)
                    save_path = os.path.join(img_dir, filename)
                    shutil.copy2(file_path, save_path)
                    downloaded_paths.append(f"images/{filename}")
                    print(f"✅ [KROSS] Сохранено (лого/фав): {filename} (исходник: {original_name})")
                else:
                    filename = f"{page_slug}_{i+1}.png"
                    save_path = os.path.join(img_dir, filename)
 
                    try:
                        if ext in ['.svg', '.avif', '.heic', '.gif']:
                            raise ValueError(f"Формат {ext} не поддерживается PIL")
                        img = Image.open(file_path)
                        if (img.mode in ('RGBA', 'LA')
                                or (img.mode == 'P' and 'transparency' in img.info)):
                            img = img.convert('RGBA')
                        else:
                            img = img.convert('RGB')
                        img.save(save_path, 'PNG')
                    except Exception as pil_err:
                        print(f"⚠️ [KROSS] Конвертация пропущена, сохраняем как есть: {pil_err}")
                        filename = f"{page_slug}_{i+1}{ext}"
                        save_path = os.path.join(img_dir, filename)
                        shutil.copy2(file_path, save_path)
 
                    downloaded_paths.append(f"images/{filename}")
                    print(f"✅ [KROSS] Успешно сохранена: {filename}")
            except Exception as e:
                print(f"❌ [KROSS] Ошибка обработки файла {file_path}: {e}")
 
    return downloaded_paths

def _process_pages_kross(tz_df, dst_site_dir):
    """
    Обрабатывает все страницы из ТЗ для движка KROSS.
    Возвращает: pages_to_keep, menu_items_js, old_brand_name, old_aff_url
    """
    pages_to_keep = []
    menu_items_js = ""
    header_nav_links = []
    footer_nav_links = []

    example_path = os.path.join(dst_site_dir, 'example.html')
    policy_path = os.path.join(dst_site_dir, 'policy.html')

    if not os.path.exists(example_path):
        raise Exception("❌ Ошибка: Шаблон 'example.html' не найден!")

    old_brand_name = get_old_brand_name(example_path)
    old_aff_url = get_old_aff_url(example_path)

    # Предварительный поиск логотипа и фавикона
    global_logo_path = None
    global_fav_path = None

    for index, row in tz_df.iterrows():
        raw_url = str(row.get('ЧПУ | URL', '')).strip().lower().replace(' ', '')
        if raw_url in ['fav/logo', 'fav|logo', 'logo/fav', 'logo|fav']:
            img_link = str(row.get('Картинки / Image', '')).strip()
            doc_link = str(row.get('Текст / Article', '')).strip()
            links_to_use = img_link if img_link and img_link.lower() != 'nan' else doc_link

            logo_fav_paths = _download_and_convert_kross(
                links_to_use, 'global', dst_site_dir, is_logo_fav=True)
            for path in logo_fav_paths:
                fn = os.path.basename(path).lower()
                if 'logo' in fn: global_logo_path = path
                elif 'fav' in fn: global_fav_path = path
            if 'images' not in pages_to_keep: pages_to_keep.append('images')
            break

    for index, row in tz_df.iterrows():
        raw_url = row.get('ЧПУ | URL')
        raw_doc = row.get('Текст / Article')
        raw_img = row.get('Картинки / Image') if 'Картинки / Image' in tz_df.columns else None

        if pd.isna(raw_url) or pd.isna(raw_doc): continue

        page_url = str(raw_url).strip()
        doc_link = str(raw_doc).strip()
        img_link = str(raw_img).strip() if pd.notna(raw_img) else ""

        if not page_url or page_url.lower() == 'nan' or not doc_link or doc_link.lower() == 'nan': continue

        page_slug = page_url.lower().replace(' ', '-')
        normalized_url = page_url.lower().replace(' ', '')

        if normalized_url in ['fav/logo', 'fav|logo', 'logo/fav', 'logo|fav']: continue

        if page_slug == 'eeat':
            doc_text = get_gdoc_text_and_assets(doc_link, dst_site_dir, 'eeat', engine='KROSS')
            soup_eeat = BeautifulSoup(doc_text, 'lxml')
            template_to_use = policy_path if os.path.exists(policy_path) else example_path

            for a_tag in soup_eeat.find_all('a'):
                policy_url = a_tag.get('href')
                link_text = a_tag.get_text(strip=True)
                parent_text = a_tag.find_parent().get_text(strip=True) if a_tag.find_parent() else ""
                clean_parent = re.sub(r'[:\-–—\d]+$', '', parent_text).strip()
                display_title = link_text if len(link_text) > 4 else clean_parent
                if not display_title: display_title = f"Policy {len(footer_nav_links)+1}"

                if policy_url and 'docs.google.com' in policy_url:
                    policy_slug = generate_policy_slug(display_title)
                    footer_nav_links.append({'title': display_title.capitalize(), 'url': f'/{policy_slug}/'})

                    policy_text = get_gdoc_text_and_assets(policy_url, dst_site_dir, policy_slug, engine='KROSS')
                    policy_json = parse_doc_to_json(policy_text, engine='KROSS')

                    policy_dir = os.path.join(dst_site_dir, policy_slug)
                    os.makedirs(policy_dir, exist_ok=True)
                    policy_file = os.path.join(policy_dir, 'index.html')
                    shutil.copy2(template_to_use, policy_file)

                    smart_inject_html(policy_file, policy_json, engine='KROSS',
                                      page_slug=policy_slug, is_policy=True)
                    pages_to_keep.append(policy_slug)

                    # Подмена логотипа в политике
                    if global_logo_path or global_fav_path:
                        try:
                            with open(policy_file, 'r', encoding='utf-8') as f:
                                soup_pol = BeautifulSoup(f.read(), 'html.parser')
                            if global_logo_path:
                                for img in soup_pol.find_all('img'):
                                    if 'logo' in img.get('src', '').lower():
                                        skip = False
                                        for parent in img.parents:
                                            if parent.name == 'body': break
                                            p_cls = " ".join(parent.get('class', [])).lower()
                                            if 'provider' in p_cls or 'payment' in p_cls:
                                                skip = True; break
                                        if skip: continue
                                        img['src'] = f"/{global_logo_path}"
                                        if 'srcset' in img.attrs: del img['srcset']
                                        if 'sizes' in img.attrs: del img['sizes']
                            if global_fav_path:
                                for lnk in soup_pol.find_all('link', rel=lambda r: r and 'icon' in r.lower()):
                                    lnk['href'] = f"/{global_fav_path}"
                            with open(policy_file, 'w', encoding='utf-8') as f:
                                f.write(str(soup_pol))
                        except Exception as e:
                            print(f"❌ Ошибка подмены лого на политике {policy_slug}: {e}")
            continue

        doc_text = get_gdoc_text_and_assets(doc_link, dst_site_dir, page_slug, engine='KROSS')
        json_data = parse_doc_to_json(doc_text, engine='KROSS')

        downloaded_images = []
        if img_link and img_link.lower() != 'nan':
            downloaded_images = _download_and_convert_kross(
                img_link, page_slug, dst_site_dir, is_logo_fav=False)
            if downloaded_images and 'images' not in pages_to_keep:
                pages_to_keep.append('images')

        if page_slug in ['main', 'home']:
            pages_to_keep.append('index.html')
            target_file = os.path.join(dst_site_dir, 'index.html')
            if not os.path.exists(target_file):
                shutil.copy2(example_path, target_file)
            if len(page_url) <= 15:
                header_nav_links.append({'title': page_url.capitalize(), 'url': '/'})
                menu_items_js += f'{{ text: "{page_url.capitalize()}", href: "/", url: "/", position: "start" }},\n'
            for manifest_name in ['manifest.json', 'site.webmanifest']:
                manifest_path = os.path.join(dst_site_dir, manifest_name)
                if os.path.exists(manifest_path):
                    try:
                        with open(manifest_path, 'r', encoding='utf-8') as mf: manifest_data = json.load(mf)
                        if json_data.get('seo_title'): manifest_data['name'] = json_data['seo_title']
                        if json_data.get('meta_desc'): manifest_data['description'] = json_data['meta_desc']
                        with open(manifest_path, 'w', encoding='utf-8') as mf:
                            json.dump(manifest_data, mf, ensure_ascii=False, indent=4)
                    except Exception: pass
        else:
            pages_to_keep.append(page_slug)
            page_dir = os.path.join(dst_site_dir, page_slug)
            os.makedirs(page_dir, exist_ok=True)
            target_file = os.path.join(page_dir, 'index.html')
            if len(page_url) <= 15:
                header_nav_links.append({'title': page_url.capitalize(), 'url': f'/{page_slug}/'})
                shutil.copy2(example_path, target_file)
                menu_items_js += f'{{ text: "{page_url.capitalize()}", href: "/{page_slug}/", url: "/{page_slug}/", position: "end" }},\n'

        smart_inject_html(target_file, json_data, engine='KROSS',
                          page_slug=page_slug, is_policy=False)

        # Подмена картинок
        if downloaded_images or global_logo_path or global_fav_path:
            try:
                with open(target_file, 'r', encoding='utf-8') as f:
                    soup_final = BeautifulSoup(f.read(), 'html.parser')

                if global_logo_path:
                    for img in soup_final.find_all('img'):
                        if 'logo' in img.get('src', '').lower():
                            skip_img = False
                            for parent in img.parents:
                                if parent.name == 'body': break
                                p_classes = " ".join(parent.get('class', [])).lower()
                                if 'provider' in p_classes or 'payment' in p_classes:
                                    skip_img = True; break
                            if skip_img: continue
                            img['src'] = f"/{global_logo_path}"
                            if 'srcset' in img.attrs: del img['srcset']
                            if 'sizes' in img.attrs: del img['sizes']

                if global_fav_path:
                    for lnk in soup_final.find_all('link', rel=lambda r: r and 'icon' in r.lower()):
                        lnk['href'] = f"/{global_fav_path}"

                if downloaded_images:
                    target_blocks = soup_final.find_all(
                        'article', class_=lambda c: c and 'modern-card' in c)
                    content_imgs = []
                    for block in target_blocks:
                        img = block.find('img', class_=lambda c: c and 'split-side-img' in c)
                        if img: content_imgs.append(img)
                    if not content_imgs:
                        content_imgs = soup_final.find_all(
                            'img', class_=lambda c: c and 'split-side-img' in c)
                    if content_imgs:
                        for i, img_tag in enumerate(content_imgs[:3]):
                            img_path = downloaded_images[i % len(downloaded_images)]
                            img_tag['src'] = f"/{img_path}"
                            img_tag['alt'] = f"{page_slug} {i+1}"
                            if 'srcset' in img_tag.attrs: del img_tag['srcset']
                            if 'sizes' in img_tag.attrs: del img_tag['sizes']

                with open(target_file, 'w', encoding='utf-8') as f:
                    f.write(str(soup_final))
            except Exception as e:
                print(f"❌ Ошибка подмены HTML картинок на странице {page_slug}: {e}")

    inject_navigation_to_all(dst_site_dir, header_nav_links, footer_nav_links, engine='KROSS')

    return pages_to_keep, menu_items_js, old_brand_name, old_aff_url


# ============================================================
# PROCESS_PAGES — ДВИЖОК SLOTSITE
# ============================================================

def _download_and_convert_slotsite(drive_links_str, page_slug, dst_site_dir, is_logo_fav=False):
    """
    Скачивает картинки для движка SLOTSITE через gdown.
    Использует SUB-DIRECTORY ISOLATION (аналогично KROSS): каждая ссылка
    скачивается в отдельную подпапку (0/, 1/, 2/, …), чтобы файлы с одинаковыми
    именами из разных ссылок не перезаписывали друг друга.
    В отличие от KROSS, сохраняет файлы в папку /image/ (не /images/),
    что соответствует структуре SLOTSITE-шаблонов.
    Логотипы/фавиконы копируются как есть (с прозрачностью).
    Контентные картинки конвертируются в PNG.
    """
    if (not isinstance(drive_links_str, str)
            or not drive_links_str.strip()
            or drive_links_str.lower() == 'nan'):
        return []

    img_dir = os.path.join(dst_site_dir, 'image')
    os.makedirs(img_dir, exist_ok=True)
    downloaded_paths = []

    print(f"⏳ [SLOTSITE] Скачиваем картинки для [{page_slug}]: {drive_links_str}")

    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            if 'folder' in drive_links_str:
                gdown.download_folder(
                    url=drive_links_str, output=temp_dir, quiet=True, use_cookies=False)
            else:
                urls = re.findall(r'(https?://[^\s,]+)', drive_links_str)
                if not urls:
                    urls = [drive_links_str]
                for idx, url in enumerate(urls):
                    # ИЗОЛЯЦИЯ: отдельная папка на каждую ссылку, чтобы
                    # файлы с одинаковыми именами не перезаписывали друг друга
                    sub_dir = os.path.join(temp_dir, str(idx))
                    os.makedirs(sub_dir, exist_ok=True)
                    gdown.download(url=url, output=sub_dir + '/', quiet=True, fuzzy=True)
        except Exception as e:
            print(f"❌ [SLOTSITE] Ошибка загрузки: {e}")

        downloaded_files = []
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if (ext in ['.png', '.jpg', '.jpeg', '.webp', '.gif', '.svg',
                             '.ico', '.avif', '.heic'] or not ext):
                    downloaded_files.append(os.path.join(root, file))
        downloaded_files.sort()

        limit = 2 if is_logo_fav else 3
        files_to_process = downloaded_files[:limit]

        if not files_to_process:
            print(f"⚠️ [SLOTSITE] Для [{page_slug}] картинки не найдены.")
            return []

        assigned_names = []

        for i, file_path in enumerate(files_to_process):
            try:
                original_name = os.path.basename(file_path).lower()
                ext = os.path.splitext(file_path)[1].lower()
                if not ext:
                    ext = '.png'

                if is_logo_fav:
                    # Логотип/фавикон: определяем имя по оригинальному имени файла
                    if 'fav' in original_name or 'icon' in original_name:
                        filename = f"fav{ext}"
                    elif 'logo' in original_name:
                        filename = f"logo{ext}"
                    else:
                        filename = f"logo{ext}" if i == 0 else f"fav{ext}"

                    # Защита от дублей имён
                    if filename in assigned_names:
                        filename = f"fav{ext}" if filename.startswith("logo") else f"logo{ext}"

                    assigned_names.append(filename)
                    save_path = os.path.join(img_dir, filename)
                    shutil.copy2(file_path, save_path)
                    downloaded_paths.append(f"image/{filename}")
                    print(f"✅ [SLOTSITE] Сохранено (лого/фав): {filename} (исходник: {original_name})")
                else:
                    # Контентная картинка: конвертируем в PNG
                    filename = f"{page_slug}_{i+1}.png"
                    save_path = os.path.join(img_dir, filename)

                    try:
                        if ext in ['.svg', '.avif', '.heic', '.gif']:
                            raise ValueError(f"Формат {ext} не поддерживается PIL")
                        img = Image.open(file_path)
                        if (img.mode in ('RGBA', 'LA')
                                or (img.mode == 'P' and 'transparency' in img.info)):
                            img = img.convert('RGBA')
                        else:
                            img = img.convert('RGB')
                        img.save(save_path, 'PNG')
                    except Exception as pil_err:
                        print(f"⚠️ [SLOTSITE] Конвертация пропущена, сохраняем как есть: {pil_err}")
                        filename = f"{page_slug}_{i+1}{ext}"
                        save_path = os.path.join(img_dir, filename)
                        shutil.copy2(file_path, save_path)

                    downloaded_paths.append(f"image/{filename}")
                    print(f"✅ [SLOTSITE] Успешно сохранена: {filename}")
            except Exception as e:
                print(f"❌ [SLOTSITE] Ошибка обработки файла {file_path}: {e}")

    return downloaded_paths


def _process_pages_slotsite(tz_df, dst_site_dir, template_name):
    """
    Обрабатывает все страницы из ТЗ для движка SLOTSITE (Elementor).
    Возвращает: pages_to_keep, menu_items_js, old_brand_name
    """
    pages_to_keep = []
    menu_items_js = ""
    header_nav_links = []
    footer_nav_links = []

    example_path = os.path.join(dst_site_dir, 'example.html')
    policy_path = os.path.join(dst_site_dir, 'policy.html')

    if not os.path.exists(example_path):
        raise Exception("❌ Ошибка: Шаблон 'example.html' не найден!")

    old_brand_name = get_old_brand_name(example_path)

    # Предварительный поиск логотипа и фавикона
    global_logo_path = None
    global_fav_path = None

    for index, row in tz_df.iterrows():
        raw_url = str(row.get('ЧПУ | URL', '')).strip().lower().replace(' ', '')
        if raw_url in ['fav/logo', 'fav|logo', 'logo/fav', 'logo|fav']:
            img_link = str(row.get('Картинки / Image', '')).strip()
            doc_link = str(row.get('Текст / Article', '')).strip()
            links_to_use = img_link if img_link and img_link.lower() != 'nan' else doc_link

            print(f"\n🔍 [SLOTSITE] Нашли строку ЛОГО/ФАВ. Ссылка: {links_to_use}")
            logo_fav_paths = _download_and_convert_slotsite(
                links_to_use, 'global', dst_site_dir, is_logo_fav=True)
            for path in logo_fav_paths:
                fn = os.path.basename(path).lower()
                if 'logo' in fn: global_logo_path = path
                elif 'fav' in fn: global_fav_path = path
            if 'image' not in pages_to_keep: pages_to_keep.append('image')
            break

    for index, row in tz_df.iterrows():
        raw_url = row.get('ЧПУ | URL')
        raw_doc = row.get('Текст / Article')
        raw_img = row.get('Картинки / Image') if 'Картинки / Image' in tz_df.columns else None

        if pd.isna(raw_url) or pd.isna(raw_doc): continue

        page_url = str(raw_url).strip()
        doc_link = str(raw_doc).strip()
        img_link = str(raw_img).strip() if pd.notna(raw_img) else ""

        if not page_url or page_url.lower() == 'nan' or not doc_link or doc_link.lower() == 'nan': continue

        page_slug = page_url.lower().replace(' ', '-')
        normalized_url = page_url.lower().replace(' ', '')

        # Пропускаем строку лого/фав — уже обработана выше
        if normalized_url in ['fav/logo', 'fav|logo', 'logo/fav', 'logo|fav']: continue

        if page_slug == 'eeat':
            doc_text = get_gdoc_text_and_assets(doc_link, dst_site_dir, 'eeat', engine='SLOTSITE')
            soup_eeat = BeautifulSoup(doc_text, 'lxml')
            template_to_use = policy_path if os.path.exists(policy_path) else example_path

            for a_tag in soup_eeat.find_all('a'):
                policy_url = a_tag.get('href')
                policy_name = a_tag.get_text(strip=True)

                if policy_url and 'docs.google.com' in policy_url:
                    policy_slug = generate_policy_slug(policy_name)
                    footer_nav_links.append({'title': policy_name.capitalize(), 'url': f'/{policy_slug}/'})

                    policy_text = get_gdoc_text_and_assets(policy_url, dst_site_dir, policy_slug, engine='SLOTSITE')
                    policy_json = parse_doc_to_json(policy_text, engine='SLOTSITE')

                    policy_dir = os.path.join(dst_site_dir, policy_slug)
                    os.makedirs(policy_dir, exist_ok=True)
                    policy_file = os.path.join(policy_dir, 'index.html')
                    shutil.copy2(template_to_use, policy_file)

                    smart_inject_html(policy_file, policy_json, engine='SLOTSITE',
                                      template_name=template_name)
                    pages_to_keep.append(policy_slug)

                    # Подмена логотипа/фавикона на страницах политик
                    if global_logo_path or global_fav_path:
                        try:
                            with open(policy_file, 'r', encoding='utf-8') as f:
                                soup_pol = BeautifulSoup(f.read(), 'html.parser')
                            if global_logo_path:
                                for img in soup_pol.find_all('img'):
                                    src_basename = os.path.basename(
                                        img.get('src', '').lower().split('?')[0])
                                    if src_basename.startswith('logo.'):
                                        img['src'] = f"/{global_logo_path}"
                                        if 'srcset' in img.attrs: del img['srcset']
                                        if 'sizes' in img.attrs: del img['sizes']
                            if global_fav_path:
                                for lnk in soup_pol.find_all('link', rel=lambda r: r and 'icon' in r.lower()):
                                    lnk['href'] = f"/{global_fav_path}"
                            with open(policy_file, 'w', encoding='utf-8') as f:
                                f.write(str(soup_pol))
                        except Exception as e:
                            print(f"❌ [SLOTSITE] Ошибка подмены лого на политике {policy_slug}: {e}")
            continue

        doc_text = get_gdoc_text_and_assets(doc_link, dst_site_dir, page_slug, engine='SLOTSITE')
        json_data = parse_doc_to_json(doc_text, engine='SLOTSITE')

        # Скачиваем до 3 контентных картинок для страницы
        downloaded_images = []
        if img_link and img_link.lower() != 'nan':
            downloaded_images = _download_and_convert_slotsite(
                img_link, page_slug, dst_site_dir, is_logo_fav=False)
            if downloaded_images and 'image' not in pages_to_keep:
                pages_to_keep.append('image')

        if page_slug in ['main', 'home']:
            pages_to_keep.append('index.html')
            target_file = os.path.join(dst_site_dir, 'index.html')
            shutil.copy2(example_path, target_file)
            if len(page_url) <= 15:
                header_nav_links.append({'title': page_url.capitalize(), 'url': '/'})
            manifest_path = os.path.join(dst_site_dir, 'manifest.json')
            if os.path.exists(manifest_path):
                try:
                    with open(manifest_path, 'r', encoding='utf-8') as mf: manifest_data = json.load(mf)
                    if json_data.get('seo_title'): manifest_data['name'] = json_data['seo_title']
                    if json_data.get('meta_desc'): manifest_data['description'] = json_data['meta_desc']
                    with open(manifest_path, 'w', encoding='utf-8') as mf:
                        json.dump(manifest_data, mf, ensure_ascii=False, indent=4)
                except Exception as e:
                    print(f"Ошибка при обновлении manifest.json: {e}")
        else:
            pages_to_keep.append(page_slug)
            page_dir = os.path.join(dst_site_dir, page_slug)
            os.makedirs(page_dir, exist_ok=True)
            target_file = os.path.join(page_dir, 'index.html')
            if len(page_url) <= 15:
                header_nav_links.append({'title': page_url.capitalize(), 'url': f'/{page_slug}/'})
                shutil.copy2(example_path, target_file)
                menu_items_js += f'{{ text: "{page_url.capitalize()}", url: "/{page_slug}/", position: "end" }},\n'

        smart_inject_html(target_file, json_data, engine='SLOTSITE', template_name=template_name)

        # Подмена картинок в HTML после вставки контента
        if downloaded_images or global_logo_path or global_fav_path:
            try:
                with open(target_file, 'r', encoding='utf-8') as f:
                    soup_final = BeautifulSoup(f.read(), 'html.parser')

                # Замена логотипа: только img у которых ИМЯФАЙЛА начинается с 'logo.'
                # (чтобы не трогать спонсорские изображения типа Leovegas-Logo.webp)
                if global_logo_path:
                    for img in soup_final.find_all('img'):
                        src_basename = os.path.basename(
                            img.get('src', '').lower().split('?')[0])
                        if src_basename.startswith('logo.'):
                            img['src'] = f"/{global_logo_path}"
                            if 'srcset' in img.attrs: del img['srcset']
                            if 'sizes' in img.attrs: del img['sizes']

                # Замена фавикона: link rel="icon" / rel="shortcut icon"
                if global_fav_path:
                    for lnk in soup_final.find_all('link', rel=lambda r: r and 'icon' in r.lower()):
                        lnk['href'] = f"/{global_fav_path}"

                # Замена контентных картинок.
                # SLOTSITE-шаблоны используют два вида слотов для контентных изображений:
                #   1. Elementor image-виджеты: div[data-widget_type="image.default"] > img
                #      (оба шаблона; шаблон 2 — login1.webp, main(1).png)
                #   2. Блоки img_flex: div.img_flex > img
                #      (шаблон 1 — promo1, promo3; шаблон 2 — login3)
                # Исключаем "карточки спонсоров" — их отличительный признак: наличие
                # виджета rating.default внутри того же блока-карточки (e-con).
                # Исключаем также изображения внутри header/footer/nav.
                if downloaded_images:
                    main_content = soup_final.find('div', attrs={'data-elementor-type': 'wp-page'})
                    if not main_content:
                        main_content = soup_final.find('div', attrs={'data-elementor-type': 'single-post'})
                    if not main_content:
                        main_content = soup_final.body if soup_final.body else soup_final

                    def _is_sponsor_card_img(img_tag):
                        """
                        Возвращает True только если img является слотом изображения
                        в карточке казино/спонсора.

                        Логика определения карточки спонсора:
                        ─────────────────────────────────────
                        1. img внутри div.img_flex → всегда контентная картинка (False).
                           img_flex используется только для контентных блоков
                           (icon-box, heading и т.п.), не для карточек казино.

                        2. img внутри image.default виджета → находим БЛИЖАЙШИЙ e-con
                           родитель этого виджета (card_econ). Это и есть потенциальный
                           контейнер карточки.
                           Карточка спонсора подтверждается, если внутри card_econ есть
                           rating.default или tp-button.default виджет, при этом между
                           card_econ и найденным rating-виджетом не более одной
                           дополнительной e-con границы (допускается разбивка карточки
                           на колонки через вложенный e-con).

                        Почему не «идём вверх по всем предкам»:
                        ─────────────────────────────────────────
                        • Шаблон А (login-тип): login1.webp завёрнут в свой e-con e-child
                          (643e5e1e), который чистый. Внешний e-con e-child (77ed75f7)
                          содержит казино-карточки в другой колонке — ходить туда нельзя.
                        • Шаблон Б (promo-тип): promo1/promo3 лежат в img_flex внутри
                          больших секционных e-con e-child, которые могут содержать
                          казино-таблицы ниже на странице — ходить туда тоже нельзя.
                        Оба случая решаются одним правилом: смотрим только ВНУТРЬ
                        ближайшего e-con родителя виджета, не выше.
                        """
                        # ── Правило 1: img_flex → всегда контентная картинка ──────────
                        if img_tag.find_parent(
                                'div', class_=lambda c: c and 'img_flex' in c):
                            return False

                        # ── Правило 2: image.default → проверяем карточный контейнер ──
                        image_widget = img_tag.find_parent(
                            'div', attrs={'data-widget_type': 'image.default'})
                        if not image_widget:
                            return False

                        # Ближайший e-con родитель виджета — потенциальный контейнер карточки
                        card_econ = image_widget.find_parent(
                            'div', class_=lambda c: c and 'e-con' in c.split())
                        if not card_econ:
                            return False

                        # Ищем rating/button виджет ВНУТРИ card_econ,
                        # но считаем сколько e-con границ отделяет его от card_econ.
                        # В настоящей карточке казино: rating и image в одном e-con
                        # (0 границ) или разделены максимум одним вложенным e-con-столбцом
                        # (1 граница). Если границ больше — это вложенная подсекция,
                        # не часть той же карточки.
                        rating_re = re.compile(r'(rating|tp-button)\.default', re.I)
                        for rating_tag in card_econ.find_all(
                                'div', attrs={'data-widget_type': rating_re}):
                            econ_boundaries = 0
                            for ancestor in rating_tag.parents:
                                if ancestor is card_econ:
                                    break
                                if (hasattr(ancestor, 'get')
                                        and 'e-con' in (ancestor.get('class') or [])):
                                    econ_boundaries += 1
                            if econ_boundaries <= 1:
                                return True  # Карточка спонсора подтверждена

                        return False

                    content_imgs = []
                    seen_img_ids = set()

                    for img in main_content.find_all('img'):
                        src = img.get('src', '').lower()
                        src_basename = os.path.basename(src.split('?')[0])
                        # Пропускаем файл логотипа и фавикона
                        if src_basename.startswith('logo.') or src_basename.startswith('fav.'):
                            continue
                        # Пропускаем img вне контентных зон
                        if img.find_parent(['header', 'footer', 'nav', 'aside']):
                            continue
                        if img.find_parent('div', attrs={'data-elementor-type': ['header', 'footer', 'popup']}):
                            continue
                        # Пропускаем изображения внутри карточек спонсоров/казино
                        if _is_sponsor_card_img(img):
                            continue
                        # Контентный слот: внутри elementor-widget-image ИЛИ внутри img_flex
                        in_widget = bool(img.find_parent(
                            'div', attrs={'data-widget_type': 'image.default'}))
                        in_flex = bool(img.find_parent(
                            'div', class_=lambda c: c and 'img_flex' in c))
                        if (in_widget or in_flex) and id(img) not in seen_img_ids:
                            seen_img_ids.add(id(img))
                            content_imgs.append(img)

                    for i, img_tag in enumerate(content_imgs[:3]):
                        img_path = downloaded_images[i % len(downloaded_images)]
                        img_tag['src'] = f"/{img_path}"
                        img_tag['alt'] = f"{page_slug} image {i+1}"
                        if 'srcset' in img_tag.attrs: del img_tag['srcset']
                        if 'sizes' in img_tag.attrs: del img_tag['sizes']

                with open(target_file, 'w', encoding='utf-8') as f:
                    f.write(str(soup_final))
            except Exception as e:
                print(f"❌ [SLOTSITE] Ошибка подмены HTML картинок на странице {page_slug}: {e}")

    inject_navigation_to_all(dst_site_dir, header_nav_links, footer_nav_links, engine='SLOTSITE')

    return pages_to_keep, menu_items_js, old_brand_name


# ============================================================
# PROCESS_PAGES — ДИСПЕТЧЕР
# ============================================================

def process_pages(tz_df, dst_site_dir, engine='SUSHI', site_name=None, template_name=''):
    """
    Диспетчер: вызывает нужную версию process_pages по движку.

    Возвращает унифицированный словарь:
      { 'pages_to_keep', 'menu_items_js', 'old_brand_name',
        'old_aff_url' (None для SLOTSITE), 'old_domain' (только SUSHI) }
    """
    if engine == 'SUSHI':
        pages_to_keep, menu_items_js, old_brand_name, old_aff_url, old_domain = \
            _process_pages_sushi(tz_df, dst_site_dir, site_name)
        return {
            'pages_to_keep': pages_to_keep, 'menu_items_js': menu_items_js,
            'old_brand_name': old_brand_name, 'old_aff_url': old_aff_url,
            'old_domain': old_domain
        }
    elif engine == 'SUSHI2':
        pages_to_keep, menu_items_js, old_brand_name, old_aff_url, old_domain = \
            _process_pages_sushi2(tz_df, dst_site_dir, site_name)
        return {
            'pages_to_keep': pages_to_keep, 'menu_items_js': menu_items_js,
            'old_brand_name': old_brand_name, 'old_aff_url': old_aff_url,
            'old_domain': old_domain
        }
    elif engine == 'KROSS':
        pages_to_keep, menu_items_js, old_brand_name, old_aff_url = \
            _process_pages_kross(tz_df, dst_site_dir)
        return {
            'pages_to_keep': pages_to_keep, 'menu_items_js': menu_items_js,
            'old_brand_name': old_brand_name, 'old_aff_url': old_aff_url,
            'old_domain': None
        }
    else:  # SLOTSITE
        pages_to_keep, menu_items_js, old_brand_name = \
            _process_pages_slotsite(tz_df, dst_site_dir, template_name)
        return {
            'pages_to_keep': pages_to_keep, 'menu_items_js': menu_items_js,
            'old_brand_name': old_brand_name, 'old_aff_url': None,
            'old_domain': None
        }


# ============================================================
# FLASK ROUTES
# ============================================================

@app.route('/')
def index():
    pool_dir = "templates_pool"
    os.makedirs(pool_dir, exist_ok=True)
    templates = sorted([
        d for d in os.listdir(pool_dir)
        if os.path.isdir(os.path.join(pool_dir, d))
    ])
    return render_template('index.html', templates=templates)


@app.route('/generate', methods=['POST'])
def generate_site():
# Добавляем импорты СЮДА:
    global pd, Image, BeautifulSoup
    import pandas as pd
    from PIL import Image
    from bs4 import BeautifulSoup
    
    domain = request.form.get('domain')
    site_name = request.form.get('site_name')
    aff_url = request.form.get('aff_url')
    tz_url = request.form.get('tz_url')
    template_name = request.form.get('template_name')

    old_colors = request.form.getlist('old_colors[]')
    new_colors = request.form.getlist('new_colors[]')
    uniq_shift = request.form.get('uniq_shift') == 'yes'
    uniq_files = request.form.get('uniq_files') == 'yes'

    if not all([domain, site_name, aff_url, tz_url, template_name]):
        return jsonify({"status": "error", "message": "Заполните все поля в форме"})

    src_template_dir = os.path.join("templates_pool", template_name)
    base_generated_dir = "generated_sites"
    dst_site_dir = os.path.join(base_generated_dir, domain)

    try:
        # Определяем движок по содержимому шаблона
        engine = detect_template_engine(src_template_dir)
        print(f"\n🚀 Запуск генерации. Движок: {engine} | Шаблон: {template_name} | Домен: {domain}")

        # Очищаем и копируем шаблон
        os.makedirs(base_generated_dir, exist_ok=True)
        
        # Удаляем только папку КОНКРЕТНОГО сайта, а не весь пул
        if os.path.exists(dst_site_dir):
            shutil.rmtree(dst_site_dir)
            
        shutil.copytree(src_template_dir, dst_site_dir)

        # Читаем Google Таблицу ТЗ
        base_csv_url = tz_url.split('/edit')[0] + '/export?format=csv'
        gid_match = re.search(r'gid=(\d+)', tz_url)
        if gid_match:
            base_csv_url += f"&gid={gid_match.group(1)}"

        try:
            tz_df = pd.read_csv(base_csv_url)
        except Exception as e:
            err_str = str(e).lower()
            if "tokenizing data" in err_str or "expected" in err_str:
                return jsonify({
                    "status": "error",
                    "message": "Доступ к Google Таблице закрыт! Откройте доступ «Для всех, у кого есть ссылка»."
                })
            else:
                return jsonify({"status": "error", "message": f"Ошибка чтения таблицы: {str(e)}"})

        tz_df.columns = tz_df.columns.astype(str).str.strip()

        # Нормализация заголовков колонок
        for col in tz_df.columns:
            col_lower = col.lower()
            if 'чпу' in col_lower or 'url' in col_lower:
                tz_df.rename(columns={col: 'ЧПУ | URL'}, inplace=True)
            elif 'текст' in col_lower or 'article' in col_lower:
                tz_df.rename(columns={col: 'Текст / Article'}, inplace=True)
            elif 'картинки' in col_lower or 'image' in col_lower:
                tz_df.rename(columns={col: 'Картинки / Image'}, inplace=True)

        # Основная обработка страниц
        result = process_pages(
            tz_df, dst_site_dir,
            engine=engine,
            site_name=site_name,
            template_name=template_name
        )
        pages_to_keep = result['pages_to_keep']
        menu_items_js = result['menu_items_js']
        old_brand_name = result['old_brand_name']
        old_aff_url = result['old_aff_url']
        old_domain = result['old_domain']

        # Удаляем лишние папки
        cleanup_unused_folders(dst_site_dir, pages_to_keep)

        # Генерируем sitemap.xml и robots.txt
        generate_sitemap_and_robots(dst_site_dir, domain, pages_to_keep)

        # Обновляем JS-меню
        if engine in ('SUSHI', 'KROSS', 'SUSHI2'):
            update_js_menu(dst_site_dir, menu_items_js)
        else:  # SLOTSITE
            app_js_path = os.path.join(dst_site_dir, 'app.js')
            if os.path.exists(app_js_path):
                update_file_content(app_js_path, {"{{MENU_ITEMS_JS}}": menu_items_js})

        # Заменяем глобальные переменные
        replace_globals(
            dst_site_dir, domain, site_name, aff_url,
            old_brand_name=old_brand_name,
            old_aff_url=old_aff_url,
            old_domain=old_domain,
            engine=engine
        )

        # Замена цветов и сброс кэша CSS
        if old_colors and new_colors:
            replace_custom_colors(dst_site_dir, old_colors, new_colors)
            bust_browser_css_cache(dst_site_dir)

        # Уникализация имён файлов
        if uniq_files:
            uniqualize_file_names(dst_site_dir, engine=engine)

        # Сдвиг пикселей (антифрод)
        if uniq_shift:
            shift_elements(dst_site_dir)

        # Упаковываем в ZIP
        shutil.make_archive(dst_site_dir, 'zip', dst_site_dir)

        # Удаляем распакованную папку, чтобы не забивать память сервера
        shutil.rmtree(dst_site_dir)

        print(f"✅ Готово! Сайт {domain} собран и уникализирован (движок: {engine}).")
        return jsonify({
            "status": "success",
            "message": f"Сайт {domain} успешно собран и уникализирован! (движок: {engine})",
            "domain": domain
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)})


@app.route('/download/<domain>')
def download_site(domain):
    zip_path = os.path.join("generated_sites", f"{domain}.zip")
    if os.path.exists(zip_path):
        return send_file(zip_path, as_attachment=True)
    return "Архив не найден", 404


if __name__ == '__main__':
    app.run(debug=True, port=5000)