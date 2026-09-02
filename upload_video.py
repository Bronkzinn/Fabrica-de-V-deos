import os
import cloudinary
import cloudinary.uploader

cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME", ""),
    api_key=os.environ.get("CLOUDINARY_API_KEY", ""),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET", ""),
    secure=True
)

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