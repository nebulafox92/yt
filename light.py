import sys
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from oauth2client.file import Storage
from oauth2client.client import flow_from_clientsecrets
from oauth2client.tools import run_flow

# Obtener argumentos del workflow
title = sys.argv[1] if len(sys.argv) > 1 else "Video sin título"
description = sys.argv[2] if len(sys.argv) > 2 else "Sin descripción"

# Autenticación
storage = Storage("oauth2.json")
credentials = storage.get()
if not credentials or credentials.invalid:
    flow = flow_from_clientsecrets("client_secret.json", "https://www.googleapis.com/auth/youtube.upload")
    credentials = run_flow(flow, storage)

youtube = build("youtube", "v3", credentials=credentials)

file_path = "output.ts"
media = MediaFileUpload(file_path, mimetype='video/*', chunksize=-1, resumable=True)

request = youtube.videos().insert(
    part="snippet,status",
    body={
        "snippet": {
            "title": title,
            "description": description,
            "categoryId": "22"
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False
        }
    },
    media_body=media
)

# Subir en partes
response = None
while response is None:
    status, response = request.next_chunk()
    if status:
        print(f"Progreso: {status.progress() * 100:.2f}%")

print("Subida completada.")
