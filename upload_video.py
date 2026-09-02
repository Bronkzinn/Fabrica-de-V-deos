import os
from dotenv import load_dotenv
load_dotenv()
import cloudinary
import cloudinary.uploader

# A lib cloudinary lê CLOUDINARY_URL automaticamente no formato:
# cloudinary://api_key:api_secret@cloud_name
# Nenhuma configuração manual necessária quando a variável de ambiente está definida.
cloudinary.config(secure=True)

def hospedar_video_cloudinary(caminho_video):
    print(f"☁️ Hospedando vídeo no Cloudinary: {caminho_video}")
    if not os.path.exists(caminho_video):
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho_video}")

    resposta = cloudinary.uploader.upload(
        caminho_video,
        resource_type="video",
        folder="chefinho_gastro"
    )

    url_video = resposta.get("secure_url")
    print(f"🔗 URL pública gerada: {url_video}")
    return url_video