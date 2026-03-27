import yt_dlp
import os
import re
import requests
import urllib3
import time
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from collections import defaultdict

# --- CONFIGURACIÓN DE RUTAS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_CHANNELS = os.path.join(BASE_DIR, 'channel.txt')      # Tus canales de YouTube
STATIC_LIST = os.path.join(BASE_DIR, 'static_list.m3u')    # Tus canales IPTV fijos
COOKIE_FILE = os.path.join(BASE_DIR, 'cookies.txt')        # Cookies para YouTube
OUTPUT_FILE = os.path.join(BASE_DIR, 'combined_list.m3u')  # El resultado final

# URL del video de respaldo (Cámbialo por tu link de Nginx si prefieres)
VIDEO_OFFLINE = "https://raw.githubusercontent.com/notanastrom/fallback-streams/main/offline.mp4"

# Orden de los grupos en Jellyfin
GROUP_ORDER = [
    'Nacionales', 'Locales', 'Noticias', 'Variedades Nacionales', 
    'Infantiles', 'Deportes', 'Noticias Internacionales', 'Novelas', 
    'Peliculas', 'Variedades Internacionales', 'Documentales', 
    'Musica', 'Religiosos', 'Nacionales Interior', 'Internacionales','Radio'
]

# --- FUNCIONES TÉCNICAS ---

def get_youtube_link(url):
    """Extrae m3u8 de YouTube con soporte para /live y /streams."""
    if "/live" in url: url = url.replace("/live", "/streams")
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'format': '96/bestvideo+bestaudio/best', 
        'skip_download': True,
        'playlist_items': '1',
        'nocheckcertificate': True
    }
    if os.path.exists(COOKIE_FILE): ydl_opts['cookiefile'] = COOKIE_FILE
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if 'entries' in info:
                for e in info['entries']:
                    if e and e.get('live_status') == 'is_live': return e.get('url')
            if info and info.get('live_status') == 'is_live': return info.get('url')
            return None
    except: return None

def is_link_online(url):
    """Verifica links rebeldes usando una sesión persistente y headers de VLC."""
    # Creamos una sesión para que maneje cookies automáticamente
    session = requests.Session()
    
    headers = {
        'User-Agent': 'VLC/3.0.14 LibVLC/3.0.14',
        'Accept': '*/*',
        'Range': 'bytes=0-128',
        'Connection': 'keep-alive',
        'Accept-Language': 'es'
    }
    
    try:
        # verify=False evita errores de certificados SSL/TLS
        # stream=True para cerrar rápido la conexión
        r = session.get(
            url, 
            headers=headers, 
            timeout=10, 
            stream=True, 
            verify=False, 
            allow_redirects=True
        )
        
        # Si responde 200, 206 o incluso si el servidor nos da un 403 
        # pero el contenido es de video, lo damos por bueno.
        is_video = 'mpegurl' in r.headers.get('Content-Type', '').lower()
        
        if r.status_code in [200, 206] or is_video:
            return True
            
        return False
    except Exception as e:
        # Si quieres ver qué está pasando realmente, quita el '#' de abajo:
        # print(f"DEBUG Error en {url}: {e}")
        return False
    finally:
        session.close()

def parse_static_m3u(file_path):
    channels = []
    if not os.path.exists(file_path): return []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        current = {}
        options = [] # Nueva lista temporal para las opciones de VLC
        
        for line in f:
            line = line.strip()
            if not line or line.startswith('#EXTM3U'): continue

            if line.startswith('#EXTINF'):
                def get_val(pattern, text):
                    m = re.search(pattern, text)
                    return m.group(1) if m else ""

                current['tvg-id'] = get_val(r'tvg-id="([^"]+)"', line)
                current['tvg-logo'] = get_val(r'tvg-logo="([^"]+)"', line)
                current['group-title'] = get_val(r'group-title="([^"]+)"', line) or "Otros"
                current['name'] = line.split(',')[-1].strip()
                options = [] # Limpiamos opciones para el nuevo canal

            elif line.startswith('#EXTVLCOPT'):
                options.append(line) # Guardamos la línea de configuración

            elif line.startswith('http'):
                current['url'] = line
                current['options'] = options # Guardamos las opciones dentro del canal
                channels.append(current.copy())
                current = {}
                options = []
                
    return channels
# --- PROCESO PRINCIPAL ---

def main():
    combined_data = defaultdict(list)

    # 1. CANALES DINÁMICOS (YouTube/Directos en channel.txt)
    if os.path.exists(INPUT_CHANNELS):
        print("📺 Procesando channel.txt...")
        with open(INPUT_CHANNELS, 'r', encoding='utf-8') as f:
            h = None
            for line in f:
                line = line.strip()
                if not line or line.startswith('~~'): continue
                if not line.startswith('http'):
                    p = [parts.strip() for parts in line.split('|')]
                    if len(p) >= 4: h = {'name': p[0], 'group': p[1], 'logo': p[2], 'id': p[3]}
                else:
                    print(f"   -> {h['name']}", end="... ")
                    url = get_youtube_link(line) if "youtube" in line else line
                    final_url = url if url else VIDEO_OFFLINE
                    combined_data[h['group']].append({
                        'group-title': h['group'], 'tvg-id': h['id'], 
                        'tvg-logo': h['logo'], 'name': h['name'], 'url': final_url, 'options': []  # <--- Añadir esto para evitar errores al escribir
                    })
                    print("✅" if url else "⚠️ Offline")

 # 2. CANALES ESTÁTICOS (static_list.m3u)
    print("🔗 Verificando canales estáticos...")
    for chan in parse_static_m3u(STATIC_LIST):
        print(f"   -> {chan['name']}", end="... ", flush=True)
        
        if is_link_online(chan['url']):
            print("✅") # Si está online, solo sale el check verde
        else:
            chan['url'] = VIDEO_OFFLINE
            print("⚠️ Offline (Respaldo aplicado)") # Si está offline, explica el cambio
            
        combined_data[chan['group-title']].append(chan)

    # 3. GENERAR M3U FINAL
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write('#EXTM3U x-tvg-url="https://github.com/botallen/epg/releases/download/latest/epg.xml"\n')
        
        all_groups = GROUP_ORDER + [g for g in combined_data if g not in GROUP_ORDER]
        for group in all_groups:
            for c in combined_data[group]:
                # Escribimos el EXTINF
                f.write(f'#EXTINF:-1 group-title="{c["group-title"]}" tvg-id="{c["tvg-id"]}" tvg-logo="{c["tvg-logo"]}", {c["name"]}\n')
                
                # Escribimos las opciones de VLC si existen
                if 'options' in c and c['options']:
                    for opt in c['options']:
                        f.write(f'{opt}\n')
                
                # Escribimos la URL
                f.write(f'{c["url"]}\n')

    print(f"\n✨ ¡Listo! Archivo generado en: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()