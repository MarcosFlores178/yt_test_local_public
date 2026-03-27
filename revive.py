import yt_dlp
import os
import requests
import urllib3

# Silenciamos los avisos de certificados inseguros
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURACIÓN ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
M3U_FILE = os.path.join(BASE_DIR, 'combined_list.m3u')
INPUT_CHANNELS = os.path.join(BASE_DIR, 'channel.txt')
STATIC_LIST = os.path.join(BASE_DIR, 'static_list.m3u')
COOKIE_FILE = os.path.join(BASE_DIR, 'cookies.txt')
VIDEO_OFFLINE = "offline.m3u8" 

# --- FUNCIONES DE VERIFICACIÓN ---

def get_youtube_link(url):
    """Intenta obtener link de YouTube si está live."""
    ydl_opts = {'quiet': True, 'no_warnings': True, 'format': 'best', 'skip_download': True, 'playlist_items': '1'}
    if os.path.exists(COOKIE_FILE): ydl_opts['cookiefile'] = COOKIE_FILE
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if 'entries' in info:
                for e in info['entries']:
                    if e and e.get('live_status') == 'is_live': return e.get('url')
            if info and info.get('live_status') == 'is_live': return info.get('url')
    except: pass
    return None

def is_static_online(url):
    """Verifica si un link estático revivió (Modo VLC)."""
    headers = {'User-Agent': 'VLC/3.0.14 LibVLC/3.0.14', 'Range': 'bytes=0-128'}
    try:
        r = requests.get(url, headers=headers, timeout=8, stream=True, verify=False, allow_redirects=True)
        return r.status_code in [200, 206]
    except: return False

def find_original_url(channel_name):
    """Busca la URL original en los archivos de origen."""
    # 1. Buscar en canales de YouTube/Directos
    if os.path.exists(INPUT_CHANNELS):
        with open(INPUT_CHANNELS, 'r', encoding='utf-8') as f:
            found = False
            for line in f:
                if channel_name in line: found = True
                elif found and line.strip().startswith('http'): return line.strip()
    
    # 2. Buscar en lista estática
    if os.path.exists(STATIC_LIST):
        with open(STATIC_LIST, 'r', encoding='utf-8') as f:
            found = False
            for line in f:
                if channel_name in line: found = True
                elif found and line.strip().startswith('http'): return line.strip()
    return None

# --- LÓGICA PRINCIPAL ---

def main():
    if not os.path.exists(M3U_FILE): return
    with open(M3U_FILE, 'r', encoding='utf-8') as f: lines = f.readlines()

    modified = False
    new_lines = []
    
    for i in range(len(lines)):
        line = lines[i]
        if VIDEO_OFFLINE in line:
            info_line = lines[i-1]
            channel_name = info_line.split(',')[-1].strip()
            print(f"🔍 Intentando revivir: {channel_name}...", end=" ", flush=True)
            
            orig_url = find_original_url(channel_name)
            if orig_url:
                if "youtube" in orig_url:
                    new_link = get_youtube_link(orig_url)
                else:
                    new_link = orig_url if is_static_online(orig_url) else None
                
                if new_link:
                    print("✅ ¡Revivió!")
                    new_lines.append(new_link + '\n')
                    modified = True
                    continue
            print("❌ Sigue caído")
        new_lines.append(line)

    if modified:
        # 1. Guardamos los cambios en el archivo de trabajo local
        with open(M3U_FILE, 'w', encoding='utf-8') as f: 
            f.writelines(new_lines)
        
        print("✨ Lista M3U actualizada localmente.")

        # 2. Copiamos el archivo al destino final de Jellyfin
        # Ajusta esta ruta a la que realmente use tu Jellyfin
        DESTINO_JELLYFIN = "/listas/combined_list.m3u" 
        try:
            import shutil
            shutil.copy2(M3U_FILE, DESTINO_JELLYFIN)
            print(f"🚀 Cambio sincronizado con Jellyfin en: {DESTINO_JELLYFIN}")
        except Exception as e:
            print(f"❌ Error al copiar a Jellyfin: {e}")

if __name__ == "__main__":
    main()