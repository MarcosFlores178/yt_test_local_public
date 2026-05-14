# Nuevo Proyecto M3U

Reconstrucción del proyecto original con estas mejoras:

- configuración centralizada en JSON
- código modular y reutilizable
- parsing más robusto de `channel.txt` y `static_list.m3u`
- escritura atómica de caché y playlist
- logging consistente
- separación entre generar, revivir y desplegar

## Estructura

- `generate.py`: genera `combined_list.m3u`
- `revive.py`: intenta revivir entradas offline en una lista ya generada
- `config.example.json`: ejemplo de configuración
- `m3u_app/`: lógica compartida

## Uso

1. Instala dependencias:

```bash
pip install -r requirements.txt
```

2. Copia `config.example.json` a `config.json`
3. Ajusta rutas y valores
4. Ejecuta:

```bash
python generate.py --config config.json
python revive.py --config config.json
```

También puedes usar el script de producción:

```bash
bash update_m3u.sh
```

O indicando otro archivo de configuración:

```bash
bash update_m3u.sh config.json
```

En Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\update_m3u.ps1
```

O con otro archivo de configuración:

```powershell
powershell -ExecutionPolicy Bypass -File .\update_m3u.ps1 -Config config.json
```

## Tests

Ejecuta los tests así:

```bash
pytest
```

En Windows, con entorno virtual:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup_venv.ps1
powershell -ExecutionPolicy Bypass -File .\run_tests.ps1
```

## Notas

- No modifica el proyecto actual.
- Si `deploy.enabled` es `false`, no copia el archivo final a ningún destino externo.
