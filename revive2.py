import yt_dlp
import os
import random
import time
import requests
import urllib3
import json
import re
import shutil
from requests.exceptions import Timeout, ConnectionError

# Silenciamos avisos de certificados
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURACIÓN ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
M3U_FILE = os.path.join(BASE_DIR, 'combined_list.m3u')
INPUT_CHANNELS = os.path.join(BASE_DIR, 'channel.txt')
STATIC_LIST = os.path.join(BASE_DIR, 'static_list.m3u')
COOKIE_FILE = os.path.join(BASE_DIR, 'cookies.txt')
CACHE_FILE = os.path.join(BASE_DIR, 'links_cache.json')
BASE_ERROR_URL = "http://181.209.79.77:8097/error"
DESTINO_JELLYFIN = "/listas/combined_list.m3u"

# --- POOL DE IDENTIDADES ANDROID (Rotación) ---
USER_AGENTS = [
    'Dalvik/2.1.0 (Linux; U; Android 11; Pixel 5) VLC/3.3.4',
    'Dalvik/2.1.0 (Linux; U; Android 12; SM-S901B) VLC/3.4.2',
    'Dalvik/2.1.0 (Linux; U; Android 10; Mi A3) VLC/3.2.12',
    'Dalvik/2.1.0 (Linux; U; Android 13; Pixel 7 Pro) VLC/3.5.0'
]

def get_random_headers():
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Range': 'bytes=0-1024',
        'Accept-Encoding': 'identity',
        'Connection': 'keep-alive',
        'Accept-Language': 'es-AR,es;q=0.9,en;q=0.8'
    }

# --- MOTOR DE VERIFICACIÓN ---

def is_link_online_pro(url, tipo_canal="estatico"):
    """Verificación quirúrgica con identidad rotativa."""
    if not url or BASE_ERROR_URL in url: return False
    
    try:
        with requests.Session() as session:
            r = session.get(
                url, 
                headers=get_random_headers(), 
                timeout=12, 
                stream=True, 
                verify=False
            )
            if r.status_code in [200, 206]:
                # Verificar si el m3u8 tiene contenido real
                if ".m3u8" in url.lower():
                    for line in r.iter_lines():
                        if b"#EXT-X-ENDLIST" in line: return False
                        break 
                return True
    except: pass
    return False

def get_youtube_link_pro(url_canal):
    """Extrae link de YouTube usando cliente Android forzado."""
    ydl_opts = {
        'quiet': True, 'no_warnings': True, 'extract_flat': True,
        'cookiefile': COOKIE_FILE if os.path.exists(COOKIE_FILE) else None,
        'extractor_args': {'youtube': {'player_client': ['android']}}
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url_canal, download=False)
            # Si es una URL de canal/user, buscamos en los entries
            if 'entries' in info:
                for entry in info['entries']:
                    if entry and entry.get('live_status') == 'is_live':
                        return extract_direct_m3u8(entry.get('url'))
            # Si es URL directa de video
            if info and info.get('live_status') == 'is_live':
                return info.get('url')
    except: pass
    return None

def extract_direct_m3u8(video_url):
    """Obtiene el m3u8 final de un video de YouTube."""
    opts = {'quiet': True, 'format': '96/best', 'extractor_args': {'youtube': {'player_client': ['android']}}}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(video_url, download=False).get('url')
    except: return None

# --- LÓGICA DE ARCHIVOS ---

def find_original_url(channel_name):
    """Busca el origen en channel.txt o static_list.m3u."""
    for path in [INPUT_CHANNELS, STATIC_LIST]:
        if not os.path.exists(path): continue
        with open(path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for i, line in enumerate(lines):
                if channel_name.lower() in line.lower():
                    for search in lines[i:]:
                        if search.strip().startswith('http'): return search.strip()
    return None

# --- MAIN ---

def main():
    if not os.path.exists(M3U_FILE): return
    
    # Cargar Caché
    cache = {}
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f: cache = json.load(f)

    with open(M3U_FILE, 'r', encoding='utf-8') as f: lines = f.readlines()

    new_lines = []
    modified = False

    for i in range(len(lines)):
        line = lines[i]
        
        # Detectamos si es una URL de error de tu Nginx
        if BASE_ERROR_URL in line:
            info_line = lines[i-1]
            channel_name = info_line.split(',')[-1].strip()
            
            print(f"🔍 Revisando: {channel_name}...", end=" ", flush=True)
            
            orig_url = find_original_url(channel_name)
            if orig_url:
                # 1. Intentar con Caché primero (si tiene menos de 10 min)
                if orig_url in cache and (time.time() - cache[orig_url]['time'] < 600):
                    link_cacho = cache[orig_url]['link']
                    if is_link_online_pro(link_cacho):
                        print("⚡ Revivió (via Caché)")
                        new_lines.append(link_cacho + '\n')
                        modified = True
                        continue

                # 2. Intentar revivir activamente
                nuevo_link = None
                if "youtube" in orig_url:
                    nuevo_link = get_youtube_link_pro(orig_url)
                else:
                    nuevo_link = orig_url if is_link_online_pro(orig_url) else None
                
                if nuevo_link:
                    print("✅ ¡Revivió!")
                    new_lines.append(nuevo_link + '\n')
                    cache[orig_url] = {'link': nuevo_link, 'time': time.time()}
                    modified = True
                    continue
            
            print("❌ Sigue caído")
        
        new_lines.append(line)

    # Guardar cambios y Caché
    if modified:
        with open(M3U_FILE, 'w', encoding='utf-8') as f: f.writelines(new_lines)
        with open(CACHE_FILE, 'w') as f: json.dump(cache, f)
        try:
            shutil.copy2(M3U_FILE, DESTINO_JELLYFIN)
            print(f"🚀 Lista sincronizada en {DESTINO_JELLYFIN}")
        except: print("⚠️ Error al copiar a Jellyfin")

if __name__ == "__main__":
    main()