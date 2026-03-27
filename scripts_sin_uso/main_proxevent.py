import yt_dlp
import os
import re
import requests
import urllib3
import time
import json
from collections import defaultdict
import random # <--- Añadir al inicio

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURACIÓN DE RUTAS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_CHANNELS = os.path.join(BASE_DIR, 'channel.txt')
STATIC_LIST = os.path.join(BASE_DIR, 'static_list.m3u')
COOKIE_FILE = os.path.join(BASE_DIR, 'cookies.txt')
OUTPUT_FILE = os.path.join(BASE_DIR, 'combined_list.m3u')
CACHE_FILE = os.path.join(BASE_DIR, 'links_cache.json') # <-- Nueva Base de Datos

VIDEO_OFFLINE = "https://raw.githubusercontent.com/notanastrom/fallback-streams/main/offline.mp4"

GROUP_ORDER = [
    'Nacionales', 'Locales', 'Noticias', 'Variedades Nacionales', 
    'Infantiles', 'Deportes', 'Noticias Internacionales', 'Novelas', 
    'Peliculas', 'Variedades Internacionales', 'Documentales', 
    'Musica', 'Religiosos', 'Nacionales Interior', 'Internacionales','Radio'
]

# --- LÓGICA DE CACHÉ ---

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: return {}
    return {}

def save_cache(cache):
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, indent=4)

# --- FUNCIONES TÉCNICAS ---

def get_youtube_link(channel_url, cache):
    # 1. Intentar usar el caché primero
    if channel_url in cache:
        data = cache[channel_url]
        if data.get('link') and (time.time() - data['timestamp'] < 7200):
            if is_link_online(data['link']):
                return data['link']

    # 2. Configuración de búsqueda profunda
    clean_url = channel_url.split('/live')[0].split('/streams')[0].rstrip('/')
    search_url = f"{clean_url}/streams"

    ydl_opts_list = {
        'quiet': True, 
        'no_warnings': True, 
        'extract_flat': True,
        'playlist_items': '1-20', 
        'cookiefile': COOKIE_FILE,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts_list) as ydl:
            print(f" (Analizando canal...) ", end="")
            channel_info = ydl.extract_info(search_url, download=False)
            
            proximo_inicio = None
            
            if 'entries' in channel_info:
                # PASO A: Buscar el evento programado más cercano para el caché
                for entry in channel_info['entries']:
                    if entry.get('live_status') == 'upcoming':
                        ts = entry.get('release_timestamp')
                        if ts and (not proximo_inicio or ts < proximo_inicio):
                            proximo_inicio = ts

                # PASO B: Buscar el directo activo ahora
                for entry in channel_info['entries']:
                    title = entry.get('title', '').upper()
                    # Saltamos lo que explícitamente es a futuro
                    if "PROGRAMADO" in title or "ESPERA" in title or entry.get('live_status') == 'upcoming':
                        continue

                    video_url = f"https://www.youtube.com/watch?v={entry.get('id')}"
                    
                    ydl_opts_check = {
                        'quiet': True, 'no_warnings': True,
                        'format': '96/best', 'cookiefile': COOKIE_FILE,
                    }
                    
                    try:
                        with yt_dlp.YoutubeDL(ydl_opts_check) as ydl_check:
                            info = ydl_check.extract_info(video_url, download=False)
                            if info.get('is_live'):
                                link = info.get('url')
                                # Guardamos TODO: link actual y fecha del próximo
                                cache[channel_url] = {
                                    'link': link, 
                                    'timestamp': time.time(),
                                    'next_event': proximo_inicio
                                }
                                return link
                    except:
                        continue
        
        # 3. Si terminó el bucle y no hubo link, pero sí hay un evento futuro:
        if proximo_inicio:
            cache[channel_url] = {
                'link': None, 
                'timestamp': time.time(), 
                'next_event': proximo_inicio
            }
            
        return None
    except Exception as e:
        print(f" Error: {e} ", end="")
        return None

def is_link_online(url):
    """Verifica si el stream sigue activo."""
    if not url or url == VIDEO_OFFLINE: return False
    session = requests.Session()
    headers = {'User-Agent': 'VLC/3.0.14 LibVLC/3.0.14', 'Range': 'bytes=0-1'}
    try:
        r = session.get(url, headers=headers, timeout=5, stream=True, verify=False)
        return r.status_code in [200, 206]
    except: return False
    finally: session.close()

def parse_static_m3u(file_path):
    channels = []
    if not os.path.exists(file_path): return []
    with open(file_path, 'r', encoding='utf-8') as f:
        current = {}
        options = []
        for line in f:
            line = line.strip()
            if not line or line.startswith('#EXTM3U'): continue
            if line.startswith('#EXTINF'):
                get_val = lambda p, t: (re.search(p, t).group(1) if re.search(p, t) else "")
                current['tvg-id'] = get_val(r'tvg-id="([^"]+)"', line)
                current['tvg-logo'] = get_val(r'tvg-logo="([^"]+)"', line)
                current['group-title'] = get_val(r'group-title="([^"]+)"', line) or "Otros"
                current['name'] = line.split(',')[-1].strip()
                options = []
            elif line.startswith('#EXTVLCOPT'): options.append(line)
            elif line.startswith('http'):
                current['url'] = line
                current['options'] = options
                channels.append(current.copy())
                current = {}; options = []
    return channels

# --- PROCESO PRINCIPAL ---

def main():
    combined_data = defaultdict(list)
    cache = load_cache()

    # 1. CANALES DINÁMICOS
    if os.path.exists(INPUT_CHANNELS):
        print("📺 Procesando canales de YouTube...")
        with open(INPUT_CHANNELS, 'r', encoding='utf-8') as f:
            h = None
            for line in f:
                line = line.strip()
                if not line or line.startswith('~~'): continue
                if not line.startswith('http'):
                    p = [parts.strip() for parts in line.split('|')]
                    if len(p) >= 4: h = {'name': p[0], 'group': p[1], 'logo': p[2], 'id': p[3]}
                else:
                    # --- EL TOQUE DE CAMUFLAJE ---
                    # Solo aplicamos retraso si NO estamos usando el caché (petición pesada)
                    # O podrías aplicarlo siempre para ser más cauteloso
                    wait_time = random.uniform(2, 5) # Elige un número entre 2 y 5 segundos
                    print(f"   -> {h['name']} (esperando {wait_time:.1f}s...)", end=" ", flush=True)
                    time.sleep(wait_time)
                    url = get_youtube_link(line, cache) if "youtube" in line else line
                    final_url = url if url else VIDEO_OFFLINE
                    combined_data[h['group']].append({
                        'group-title': h['group'], 'tvg-id': h['id'], 
                        'tvg-logo': h['logo'], 'name': h['name'], 'url': final_url, 'options': []
                    })
                    print("✅" if url else "⚠️ Offline")

    # 2. CANALES ESTÁTICOS
    print("\n🔗 Verificando canales estáticos...")
    for chan in parse_static_m3u(STATIC_LIST):
        print(f"   -> {chan['name']}", end="... ", flush=True)
        if not is_link_online(chan['url']):
            chan['url'] = VIDEO_OFFLINE
            print("⚠️ Offline (Respaldo)", flush=True)
        else: print("✅")
        combined_data[chan['group-title']].append(chan)

    # 3. GUARDAR CACHÉ Y GENERAR M3U
    save_cache(cache)
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write('#EXTM3U x-tvg-url="https://github.com/botallen/epg/releases/download/latest/epg.xml"\n')
        all_groups = GROUP_ORDER + [g for g in combined_data if g not in GROUP_ORDER]
        for group in all_groups:
            for c in combined_data[group]:
                f.write(f'#EXTINF:-1 group-title="{c["group-title"]}" tvg-id="{c["tvg-id"]}" tvg-logo="{c["tvg-logo"]}", {c["name"]}\n')
                for opt in c.get('options', []): f.write(f'{opt}\n')
                f.write(f'{c["url"]}\n')

    # Quiero imprimir la hora a la cual termina el script para que el usuario tenga una referencia de cuánto tardó
    end_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    print(f"\n⏰ Proceso finalizado a las {end_time}.")
    # print(f"\n✨ ¡Listo! Lista combinada generada.")

if __name__ == "__main__":
    main()