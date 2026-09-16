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
    cloudinary_url = (os.environ.get("CLOUDINARY_URL") or "").strip()
    if not cloudinary_url:
        raise ValueError("[X] Variável de ambiente CLOUDINARY_URL não foi configurada!")

    # Força a configuração explícita para evitar falhas de credenciais no ambiente CI/Linux
    cloudinary.reset_config()
    os.environ["CLOUDINARY_URL"] = cloudinary_url
    cloudinary.config(cloudinary_url=cloudinary_url, secure=True)

    print(f"[+] Hospedando video no Cloudinary: {caminho_video}")
    if not os.path.exists(caminho_video):
        raise FileNotFoundError(f"Arquivo nao encontrado: {caminho_video}")

    resposta = cloudinary.uploader.upload(
        caminho_video,
        resource_type="video",
        folder="chefinho_gastro"
    )

    url_video = resposta.get("secure_url")
    if not url_video:
        raise RuntimeError(f"Falha ao obter URL pública do Cloudinary: {resposta}")
        
    print(f"[+] URL publica gerada: {url_video}")
    return url_video