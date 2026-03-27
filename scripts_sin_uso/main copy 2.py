import yt_dlp
import os
import re
from collections import defaultdict

# --- CONFIGURACIÓN ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_CHANNELS = os.path.join(BASE_DIR, 'channel.txt')
STATIC_LIST = os.path.join(BASE_DIR, 'static_list.m3u')
VIDEO_OFFLINE = "http://181.209.79.77:8097/error/offline.m3u8"

# Rutas de salida (puedes poner tantas como quieras)
OUTPUT_PATHS = [
    os.path.join(BASE_DIR, 'combined_list.m3u'),
    '/home/estranet/streammaster/config/PlayLists/M3U/combined_list.m3u'
]

GROUP_ORDER = [
    'Nacionales', 'Locales', 'Noticias', 'Variedades Nacionales', 
    'Infantiles', 'Deportes', 'Noticias Internacionales', 'Novelas', 
    'Peliculas', 'Variedades Internacionales', 'Documentales', 
    'Musica', 'Religiosos', 'Nacionales Interior', 'Internacionales','Radio'
]

# --- FUNCIONES DE EXTRACCIÓN Y PARSEO ---

def get_youtube_link(url):
    ydl_opts = {'quiet': True, 'no_warnings': True, 'format': 'best', 'skip_download': True}
    if os.path.exists(os.path.join(BASE_DIR, 'cookies.txt')):
        ydl_opts['cookiefile'] = os.path.join(BASE_DIR, 'cookies.txt')
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if 'entries' in info:
                for e in info['entries']:
                    if e and e.get('is_live'): return e.get('url')
            return info.get('url')
    except: return None

def parse_static_m3u(file_path):
    channels = []
    if not os.path.exists(file_path): return []
    with open(file_path, 'r', encoding='utf-8') as f:
        current = {}
        for line in f:
            line = line.strip()
            if line.startswith('#EXTINF'):
                current['group-title'] = re.search(r'group-title="([^"]+)"', line).group(1) if 'group-title="' in line else "Otros"
                current['tvg-id'] = re.search(r'tvg-id="([^"]+)"', line).group(1) if 'tvg-id="' in line else ""
                current['tvg-logo'] = re.search(r'tvg-logo="([^"]+)"', line).group(1) if 'tvg-logo="' in line else ""
                current['name'] = line.split(',')[-1].strip()
            elif line.startswith('http'):
                current['url'] = line
                channels.append(current)
                current = {}
    return channels

# --- PROCESO PRINCIPAL ---

def main():
    combined_data = defaultdict(list)

    # 1. PROCESAR CANALES DINÁMICOS (YouTube)
    if os.path.exists(INPUT_CHANNELS):
        print("📺 Procesando canales dinámicos...")
        with open(INPUT_CHANNELS, 'r', encoding='utf-8') as f:
            header_info = None
            for line in f:
                line = line.strip()
                if not line or line.startswith('~~'): continue
                if not line.startswith('http'):
                    parts = [p.strip() for p in line.split('|')]
                    if len(parts) >= 4:
                        header_info = {'name': parts[0], 'group': parts[1], 'logo': parts[2], 'id': parts[3]}
                else:
                    print(f"   -> {header_info['name']}", end="... ")
                    url = get_youtube_link(line) if "youtube" in line else line
                    link = url if url else VIDEO_OFFLINE
                    combined_data[header_info['group']].append({
                        'group-title': header_info['group'], 'tvg-id': header_info['id'],
                        'tvg-logo': header_info['logo'], 'name': header_info['name'], 'url': link
                    })
                    print("✅" if url else "⚠️ Offline")

    # 2. PROCESAR CANALES ESTÁTICOS
    print("🔗 Cargando canales estáticos...")
    static_channels = parse_static_m3u(STATIC_LIST)
    for chan in static_channels:
        combined_data[chan['group-title']].append(chan)

    # 3. ESCRIBIR ARCHIVOS DE SALIDA CON ORDENAMIENTO
    for out_path in OUTPUT_PATHS:
        try:
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            with open(out_path, 'w', encoding='utf-8') as f:
                f.write('#EXTM3U\n')
                # Escribir grupos en orden
                for group in GROUP_ORDER + [g for g in combined_data if g not in GROUP_ORDER]:
                    for chan in combined_data[group]:
                        f.write(f'#EXTINF:-1 group-title="{chan["group-title"]}" tvg-id="{chan["tvg-id"]}" tvg-logo="{chan["tvg-logo"]}", {chan["name"]}\n')
                        f.write(f'{chan["url"]}\n')
            print(f"✨ Lista guardada en: {out_path}")
        except Exception as e:
            print(f"❌ Error al escribir en {out_path}: {e}")

if __name__ == "__main__":
    main()