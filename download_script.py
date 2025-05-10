import json
import os
import re
import subprocess
import sys
import requests
import unicodedata
import shlex
from datetime import datetime
from internetarchive import upload

# Elimina acentos y caracteres especiales del texto.
def normalize_text(text):
    return unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')

# Crea un identificador a partir del título.
def create_identifier(title):
    text = normalize_text(title).lower()
    # Reemplaza la barra "/" por un guion bajo "_"
    text = text.replace("/", "_")
    # Permite letras, dígitos, espacios, guiones y guiones bajos
    text = re.sub(r'[^a-z0-9\s_-]', '', text)
    identifier = re.sub(r'\s+', '-', text)
    return identifier

# Función para sanitizar el nombre del archivo.
def sanitize_filename(filename):
    # Reemplaza el slash "/" por DIVISION SLASH "∕" (U+2215)
    filename = filename.replace("/", "∕")
    # Reemplaza otros caracteres prohibidos: \ : * ? " < > |
    return re.sub(r'[\\:*?"<>|]', "_", filename)

# Extrae la fecha de subida (uploadDate) desde el contenido HTML de la URL.
def get_upload_date(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            html_text = response.text

            # Estrategia 1: Buscar JSON-LD que contenga "uploadDate"
            json_ld_matches = re.findall(
                r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>',
                html_text,
                re.DOTALL
            )
            for json_ld in json_ld_matches:
                try:
                    data = json.loads(json_ld)
                    if isinstance(data, list):
                        for entry in data:
                            if isinstance(entry, dict) and entry.get("uploadDate"):
                                return entry["uploadDate"]
                    elif isinstance(data, dict):
                        if data.get("uploadDate"):
                            return data["uploadDate"]
                except Exception:
                    pass

            # Estrategia 2: Buscar "uploadDate" mediante regex
            matches = re.findall(r'"uploadDate"\s*:\s*"([^"]+)"', html_text)
            if matches:
                return matches[0]
    except Exception as e:
        print(f"Error al obtener la fecha de subida desde {url}: {e}")

    # Fallback: Se utiliza la fecha/hora actual
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

# Genera el diccionario de metadatos.
def create_metadata(title, url, upload_date):
    return {
        "title": title,
        "description": f"{title}\n{url}\n{upload_date}",
        "mediatype": "movies",
        "collection": "opensource_movies"
    }

# Función para crear un identificador "bucket" válido.
def create_bucket_identifier(prefix, title, upload_date):
    # Genera el "slug" con el título
    slug = create_identifier(title)
    # Asegura que la fecha no contenga caracteres no permitidos
    safe_date = upload_date.replace(":", "_")
    safe_prefix = prefix  # Por ejemplo: "vector_twitch"
    # Usamos el formato: prefix - slug - safe_date
    # Calculamos la longitud fija: prefijo + 2 guiones + safe_date
    fixed_len = len(safe_prefix) + len(safe_date) + 2
    # La longitud máxima permitida es 101 caracteres
    max_slug_len = 101 - fixed_len
    # Trunca el slug si es necesario
    if len(slug) > max_slug_len:
        slug = slug[:max_slug_len]
    identifier = f"{safe_prefix}-{slug}-{safe_date}"
    return identifier

# Descarga el archivo de video usando ffmpeg.
def download_video(m3u8_url, filename):
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel", 
        "error", 
        "-user_agent", "Mozilla/5.0",
        "-protocol_whitelist", "file,http,https,tcp,tls",
        "-err_detect", "ignore_err",
        "-timeout", "5000000",  # 5 segundos por intento (en microsegundos)
        "-rw_timeout", "5000000",  # 5 segundos de timeout de lectura
        "-max_reload", "2",  # intenta 2 veces por segmento antes de saltar
        "-i", m3u8_url,
        "-c", "copy",
        "-y",
        filename
    ]

    subprocess.run(cmd, check=False)
# Obtiene la URL directa del stream usando yt-dlp.
def get_stream_url(url):
    result = subprocess.run(
        ["yt-dlp", "-g", "-f", "best", url],
        capture_output=True,
        text=True,
        check=True
    )
    return result.stdout.strip()

# Procesa cada video individualmente.
def process_video(video):
    title = video.get("title")
    url   = video.get("url")
    if not title or not url:
        return

    # Nombre temporal para la descarga
    temp_filename = "output.ts"
    
    # Se extrae la fecha de subida.
    upload_date = get_upload_date(url)
    # Se crea un identificador que cumple las restricciones del bucket.
    identifier = create_bucket_identifier("vector_twitch", title, upload_date)
    
    # Se crea la metadata con título, URL y fecha.
    metadata = create_metadata(title, url, upload_date)
    m3u8_url = get_stream_url(url)

    print(f"ID Video: https://archive.org/details/{identifier}")
    
    # Descarga el video (se guarda en output.ts)
    download_video(m3u8_url, temp_filename)
    print(f"Descarga completada: {temp_filename}")
    
    # Renombra el archivo según el título sanitizado
    new_filename = sanitize_filename(title) + ".ts"
    try:
        os.rename(temp_filename, new_filename)
        print(f"Archivo renombrado a: {new_filename}")
    except Exception as e:
        print(f"Error al renombrar el archivo: {e}")
        return

    print("Iniciando la subida a Internet Archive...")
    upload_result = upload(
        identifier,
        files=[new_filename],
        metadata=metadata,
        retries=5,
        verbose=True
    )
    
    print(f"Video subido correctamente: https://archive.org/details/{identifier}")
    
    # Elimina el archivo descargado localmente.
    os.remove(new_filename)

# Función principal: procesa la lista de videos en orden inverso.
def main():
    if len(sys.argv) < 2:
        sys.exit("Uso: script.py <archivo_json>")
    
    json_file = sys.argv[1]
    with open(json_file, "r", encoding="utf-8") as f:
        videos = json.load(f)
    
    for video in reversed(videos):
        process_video(video)

if __name__ == "__main__":
    main()
