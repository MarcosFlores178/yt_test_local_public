import yt_dlp
import os

# Configuración de archivos - Usa rutas relativas para mayor portabilidad
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE = os.path.join(BASE_DIR, 'channel.txt')
OUTPUT_FILE = os.path.join(BASE_DIR, 'lista_canales.m3u')
COOKIE_FILE = os.path.join(BASE_DIR, 'cookies.txt')

def get_live_link(youtube_url):
    """Extrae el enlace m3u8 real usando yt-dlp."""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'format': 'best',
        'skip_download': True,
        'nocheckcertificate': True,
        # 'ignoreerrors' ayuda a que el script no se detenga por un canal roto
        'ignoreerrors': True,
    }

    # Carga de cookies automática si el archivo existe
    if os.path.exists(COOKIE_FILE):
        ydl_opts['cookiefile'] = COOKIE_FILE

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=False)
            
            if not info:
                return None

            # Caso 1: Es una lista de videos o canal con múltiples vivos
            if 'entries' in info:
                for entry in info['entries']:
                    if entry and entry.get('is_live'):
                        return entry.get('url')
            
            # Caso 2: Es un objeto de video directo
            return info.get('url')
            
    except Exception as e:
        # Imprime el error solo si necesitas debugear
        return None

def generate_m3u():
    if not os.path.exists(INPUT_FILE):
        print(f"❌ Error: No se encuentra el archivo de entrada en {INPUT_FILE}")
        return

    print(f"🚀 Iniciando extracción desde: {INPUT_FILE}")
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as out:
        # Cabecera M3U con EPG
        out.write('#EXTM3U x-tvg-url="https://github.com/botallen/epg/releases/download/latest/epg.xml"\n')
        
        current_header = None
        
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                
                # Saltar líneas vacías, comentarios o separadores
                if not line or line.startswith('~~') or line.startswith('#'):
                    continue
                
                # Línea de metadatos del canal (Nombre | Grupo | Logo | ID)
                if not line.startswith('https:'):
                    parts = [p.strip() for p in line.split('|')]
                    if len(parts) >= 4:
                        ch_name, grp_title, tvg_logo, tvg_id = parts
                        current_header = f'\n#EXTINF:-1 group-title="{grp_title}" tvg-logo="{tvg_logo}" tvg-id="{tvg_id}", {ch_name}'
                
                # Línea de URL de YouTube
                else:
                    if current_header:
                        name_display = current_header.split(',')[-1].strip()
                        
                        # VERIFICACIÓN DE TIPO DE LINK
                        if "youtube.com" in line or "youtu.be" in line:
                            print(f"📺 Extraer YouTube: {name_display}...", end=" ", flush=True)
                            final_link = get_live_link(line)
                        else:
                            print(f"🔗 Link Directo/Local: {name_display}...", end=" ", flush=True)
                            final_link = line  # Se copia tal cual (para tus videos locales)
                        
                        if final_link:
                            out.write(current_header + '\n')
                            out.write(final_link + '\n')
                            print("✅")
                        else:
                            print("❌ Falló")
                        
                        current_header = None

    print(f"\n✨ ¡Proceso finalizado! Archivo generado: {OUTPUT_FILE}")

if __name__ == "__main__":
    generate_m3u()