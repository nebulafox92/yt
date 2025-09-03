from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from oauth2client.file import Storage
from oauth2client.client import flow_from_clientsecrets
from oauth2client.tools import run_flow
import argparse
import os

def upload_video(file_path, title):
    # Verificar si el archivo existe
    if not os.path.exists(file_path):
        print(f"Error: El archivo {file_path} no existe")
        return

    # Autenticación
    storage = Storage("oauth2.json")
    credentials = storage.get()
    if not credentials or credentials.invalid:
        flow = flow_from_clientsecrets("client_secret.json", 
                                     scope="https://www.googleapis.com/auth/youtube.upload")
        credentials = run_flow(flow, storage)

    youtube = build("youtube", "v3", credentials=credentials)

    try:
        # Configurar carga con fragmentación
        media = MediaFileUpload(file_path, mimetype='video/*', chunksize=-1, resumable=True)

        request = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": title,
                    "description": "STREAM TODO EL DIA ACAAAAAAAAAAAA!!!!!! - !betbox !1xbet !r1skins !kingslv !crew - META SUBS: 139/150 https://kick.com/vector/videos/31772784-a8d9-449d-b7ad-bec0329793dd",
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
    except Exception as e:
        print(f"Error durante la subida: {str(e)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="Path to video file")
    parser.add_argument("--title", required=True, help="Video title")
    args = parser.parse_args()
    
    upload_video(args.file, args.title)
