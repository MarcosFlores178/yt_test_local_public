#!/bin/bash

# Carpeta del proyecto
PROJECT_DIR="/home/estranet/m3ugrabber/ytm3u8"
cd $PROJECT_DIR

# Activar entorno virtual
#source venv/bin/activate

# 1. Ejecutamos el script de Python que hace todo el trabajo pesado.
# (Asegúrate de que el script genere el archivo final en una ruta temporal primero si quieres, 
# o simplemente deja que el script de Python lo haga y luego lo movemos).
python3 main.py

# 2. Supongamos que tu main.py genera "combined_list.m3u" en la carpeta actual.
# Vamos a moverlo a las rutas finales de forma segura.

FINAL_LIST="combined_list.m3u"
DEST_PUBLIC="/listas/combined_list.m3u"

# Verificamos si el archivo se generó y no está vacío antes de mover
if [ -s "$FINAL_LIST" ]; then
    cp "$FINAL_LIST" "$DEST_PUBLIC"
    echo "$(date): Listas actualizadas y distribuidas correctamente." >> cron_log.txt
else
    echo "$(date): ERROR - El archivo generado está vacío o no existe. No se sobreescribieron las listas." >> cron_log.txt
fi