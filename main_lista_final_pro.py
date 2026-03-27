import yt_dlp
import os
import re
import requests
import urllib3
import time
import json
from collections import defaultdict
import random # <--- Añadir al inicio
from requests.exceptions import Timeout, ConnectionError

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURACIÓN DE RUTAS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_CHANNELS = os.path.join(BASE_DIR, 'channel.txt')
STATIC_LIST = os.path.join(BASE_DIR, 'static_list.m3u')
COOKIE_FILE = os.path.join(BASE_DIR, 'cookies.txt')
OUTPUT_FILE = os.path.join(BASE_DIR, 'combined_list.m3u')
CACHE_FILE = os.path.join(BASE_DIR, 'links_cache.json') # <-- Nueva Base de Datos
VIDEO_OFFLINE = "http://181.209.79.77:8097/error/offline.m3u8"
BASE_ERROR_URL = "http://181.209.79.77:8097/error"

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

def get_youtube_data(channel_url, cache, original_name):
    # 1. Caché igual que antes
    if channel_url in cache:
        data = cache[channel_url]
        if data.get('vivos') and (time.time() - data['timestamp'] < 1800):
            # IMPORTANTE: Probamos si el link del caché REALMENTE funciona
            # Si is_link_online falla, ignoramos el caché y buscamos de nuevo
            if is_link_online_pro(data['vivos'][0]['link'], original_name, tipo_canal="youtube"):
                return data['vivos'], data.get('next_event')
            else:
                # Si el link falló, borramos esa entrada específica para forzar el re-escaneo
                print(f" 🔄 Link caducado en caché para {original_name}, buscando nuevo...")
                del cache[channel_url]

    clean_url = channel_url.split('/live')[0].split('/streams')[0].rstrip('/')
    search_url = f"{clean_url}/streams"

    # 2. CONFIGURACIÓN ESPECIAL PARA CANALES INFANTILES (Equivalente a tu comando de consola)
    ydl_opts_list = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'playlist_items': '1-20',
        'cookiefile': COOKIE_FILE,
        # Aquí inyectamos los argumentos que pasaste por consola:
        'extractor_args': {
            'youtube': {
                'player_client': ['android'],
                'player_skip': ['web', 'tv']
            }
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts_list) as ydl:
            print(f" (Escaneando {original_name} con modo Android...) ", end="")
            channel_info = ydl.extract_info(search_url, download=False)
            
            vivos_temporales = []
            proximos_ts = []
            
            if 'entries' in channel_info:
                for entry in channel_info['entries']:
                    title = entry.get('title', '').upper()
                    estado = entry.get('live_status')

                    # Filtro de eventos programados
                    if estado == 'is_upcoming' or any(word in title for word in ["PROGRAMADO", "ESPERA", "PRÓXIMAMENTE"]):
                        ts = entry.get('release_timestamp')
                        if ts: proximos_ts.append(ts)
                        continue

                    # Filtro de seguridad: Solo si es vivo real
                    if estado != 'is_live':
                        continue 

                    v_id = entry.get('id')
                    
                    # 3. EXTRACCIÓN CON ARGUMENTOS DE CLIENTE ANDROID
                    # IMPORTANTE: Tu función extract_m3u8 debe aceptar estos mismos parámetros internos
                    link_m3u8 = extract_m3u8(f"https://www.youtube.com/watch?v={v_id}")
                    
                    if link_m3u8 and "yt_live_broadcast" in link_m3u8:
                        vivos_temporales.append(link_m3u8)
            # --- AQUÍ VA LA LÓGICA DE LIMPIEZA ---
            if not vivos_temporales:
                if channel_url in cache:
                    del cache[channel_url]
                # Calculamos el próximo evento antes de salir por si acaso
                res_event = min(proximos_ts) if proximos_ts else None
                return [], res_event
            # --------------------------------------

            # Lógica de nombres (Esto solo se ejecutará si SI hay vivos_temporales)
            # Lógica de nombres (Telefe vs Canal 26 - Señal 1)
            vivos_finales = []
            total = len(vivos_temporales)
            for i, link in enumerate(vivos_temporales):
                nombre = original_name if total == 1 else f"{original_name} - Señal {i+1}"
                vivos_finales.append({'name': nombre, 'link': link})

            res_event = min(proximos_ts) if proximos_ts else None
            cache[channel_url] = {'vivos': vivos_finales, 'timestamp': time.time(), 'next_event': res_event}
            
            return vivos_finales, res_event

    except Exception as e:
        print(f" Error en {original_name}: {e} ")
        return [], None

def extract_m3u8(video_url):
    """Extrae el link directo .m3u8 usando el cliente de Android para evitar bloqueos."""
    opts = {
        'quiet': True, 
        'no_warnings': True, 
        'format': '96/best', 
        'cookiefile': COOKIE_FILE,
        # Argumentos vitales para canales infantiles:
        'extractor_args': {
            'youtube': {
                'player_client': ['android'],
                'player_skip': ['web', 'tv']
            }
        }
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            # Extraemos la info del video específico
            info = ydl.extract_info(video_url, download=False)
            return info.get('url')
    except Exception as e:
        # Si quieres ver por qué falla un canal específico, quita el comentario:
        # print(f" Error en extracción: {e}")
        return None

def is_link_online_pro(url, nombre_canal, tipo_canal="estatico", max_intentos=3, timeout=12):
    """
    Validación quirúrgica para ISP: 3 intentos, delay aleatorio e identidad Android.
    Retorna True si está online, o la URL de error personalizada si falla.
    """
    
    # 1. Si no hay URL o ya es una URL de error, generamos la personalizada y salimos
    if not url or BASE_ERROR_URL in url:
        nombre_limpio = re.sub(r'[^a-zA-Z0-9]', '_', nombre_canal).lower()
        return f"{BASE_ERROR_URL}/{nombre_limpio}/offline.m3u8"
    
    # 2. Ajustes según tipo de canal
    if tipo_canal == "youtube":
        max_intentos = 2
        timeout = 15
        delays = [2 + random.random(), 4 + random.random()]
    else:
        delays = [random.uniform(1.5, 3.0) for _ in range(max_intentos)]
    
    headers = {
        'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 11; Pixel 5) VLC/3.3.4',
        'Range': 'bytes=0-1024',
        'Accept': '*/*',
        'Accept-Encoding': 'identity',
        'Connection': 'keep-alive'
    }
    
    if tipo_canal == "youtube":
        headers['Accept-Language'] = 'es-AR,es;q=0.9,en;q=0.8'
    
    # 3. Bucle de intentos
    with requests.Session() as session:
        for intento in range(1, max_intentos + 1):
            try:
                r = session.get(
                    url, 
                    headers=headers, 
                    timeout=timeout, 
                    stream=True, 
                    verify=False, 
                    allow_redirects=True
                )
                
                # Verificación de Código HTTP
                if r.status_code not in [200, 206]:
                    if intento < max_intentos:
                        time.sleep(delays[intento-1])
                        continue
                    break # Si fallaron los intentos, sale del for para ir al error final
                
                # Análisis de fin de stream (EXT-X-ENDLIST)
                es_finalizado = False
                if ".m3u8" in url.lower() or "manifest" in url.lower():
                    line_count = 0
                    try:
                        for line in r.iter_lines():
                            if line:
                                line_str = line.decode('utf-8', errors='ignore').upper()
                                if "#EXT-X-ENDLIST" in line_str:
                                    es_finalizado = True
                                    break
                            line_count += 1
                            if line_count > 60: break
                    except: pass
                
                if es_finalizado:
                    if intento < max_intentos:
                        time.sleep(delays[intento-1])
                        continue
                    break

                # SI TODO SALIÓ BIEN, RETORNAMOS TRUE
                return True
                
            except (Timeout, ConnectionError):
                if intento < max_intentos:
                    time.sleep(delays[intento-1])
                    continue
            except Exception:
                if intento < max_intentos:
                    time.sleep(delays[intento-1])
                    continue
                break

    # 4. FINAL DE SEGURIDAD: Si el código llega aquí, es que el canal FALLÓ.
    # Retornamos la URL personalizada para que Jellyfin no se rompa.
    nombre_limpio = re.sub(r'[^a-zA-Z0-9]', '_', nombre_canal).lower()
    return f"{BASE_ERROR_URL}/{nombre_limpio}/offline.m3u8"
    
   

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
                    wait_time = random.uniform(2, 5)
                    print(f"   -> {h['name']} (esperando {wait_time:.1f}s...)", end=" ", flush=True)
                    time.sleep(wait_time)
                    
                    if "youtube" in line:
                        vivos, next_ev = get_youtube_data(line, cache, h['name'])
                        
                        if vivos:
                            # Limpiamos la línea de consola para que el conteo sea real
                            total_vivos = len(vivos)
                            for idx, v in enumerate(vivos):
                                # LÓGICA DE ID: Solo agrega "-X" si hay más de una señal
                                # Así evitamos el "Canal-1" innecesario
                                id_final = h['id'] if total_vivos == 1 else f"{h['id']} {idx+1}"
                                
                                # --- MODIFICACIÓN AQUÍ ---
                                # Verificamos cada señal de YouTube encontrada
                                resultado = is_link_online_pro(v['link'], v['name'], tipo_canal="youtube")
                                url_final = v['link'] if resultado is True else resultado
                                # -------------------------

                                combined_data[h['group']].append({
                                        'group-title': h['group'], 
                                        'tvg-id': id_final, 
                                        'tvg-logo': h['logo'], 
                                        'name': v['name'], 
                                        'url': url_final, 
                                        'options': []
                                    })
                                print(f"✅ {total_vivos} señales reales)") # Aquí ya no te dirá "19"
                        else:
                            # --- MODIFICACIÓN AQUÍ ---
                            # Si no hay vivos, generamos la URL de error personalizada para el canal
                            url_error = is_link_online_pro(None, h['name'])
                            # -------------------------
                            # Si no hay vivos pero sí hay un evento pronto, o si está realmente offline
                            combined_data[h['group']].append({
                                'group-title': h['group'], 'tvg-id': h['id'], 
                                'tvg-logo': h['logo'], 'name': h['name'], 
                                'url': url_error, 'options': []
                            })
                            print("⚠️ Offline / Próximamente")
                    else:
                        # Para links que no son de YouTube (directos)
                        # --- MODIFICACIÓN AQUÍ ---
                        resultado = is_link_online_pro(line, h['name'], tipo_canal="directo")
                        url_final = line if resultado is True else resultado
                        # -------------------------
                        combined_data[h['group']].append({
                            'group-title': h['group'], 'tvg-id': h['id'], 
                            'tvg-logo': h['logo'], 'name': h['name'], 'url': url_final, 'options': []
                        })
                        print("✅" if resultado is True else "⚠️ Offline")

    # 2. CANALES ESTÁTICOS
    print("\n🔗 Verificando canales estáticos...")
    for chan in parse_static_m3u(STATIC_LIST):
        print(f"   -> {chan['name']}", end="... ", flush=True)
        resultado = is_link_online_pro(chan['url'], chan['name'], tipo_canal="directo")
        
        if resultado is not True:
            chan['url'] = resultado # Guardará la URL con el nombre del canal
            print("⚠️ Offline (Respaldo)", flush=True)
        else:
            print("✅")
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