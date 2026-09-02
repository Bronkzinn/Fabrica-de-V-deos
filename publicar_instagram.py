import os
from dotenv import load_dotenv
load_dotenv()
import time
import requests
from upload_video import hospedar_video_cloudinary

# ==========================================
# CONFIGURAÇÕES DO INSTAGRAM / META
# ==========================================
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN", "")
IG_USER_ID = os.environ.get("IG_USER_ID", "")

def publicar_reels_instagram(caminho_video_mp4, legenda):
    print("🚀 Iniciando processo de publicação do Reels no Instagram...")
    
    # Faz o upload para o Cloudinary e obtém a URL pública
    url_video_publica = hospedar_video_cloudinary(caminho_video_mp4)

    # ==========================================
    # PASSO 1: Criar o contêiner de mídia (Reels)
    # ==========================================
    url_criacao = f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media"
    
    payload = {
        'media_type': 'REELS',
        'video_url': url_video_publica,
        'caption': legenda,
        'access_token': ACCESS_TOKEN
    }
    
    print("📦 Enviando solicitação de criação de contêiner...")
    resposta = requests.post(url_criacao, data=payload)
    resultado = resposta.json()
    
    if "id" not in resultado:
        print(f"❌ Erro ao criar o contêiner no Instagram: {resultado}")
        return False
        
    creation_id = resultado["id"]
    print(f"✅ Contêiner criado com sucesso! ID: {creation_id}")
    
    # ==========================================
    # PASSO 2: Consultar Status de Processamento
    # ==========================================
    url_status = f"https://graph.facebook.com/v19.0/{creation_id}"
    params_status = {
        'fields': 'status_code',
        'access_token': ACCESS_TOKEN
    }

    print("⏳ Aguardando os servidores da Meta processarem o vídeo...")
    tentativas = 0
    max_tentativas = 30  # Timeout de até 5 minutos (30 x 10s)

    while tentativas < max_tentativas:
        time.sleep(10)
        tentativas += 1
        res_status = requests.get(url_status, params=params_status).json()
        status_code = res_status.get("status_code")

        print(f"🔄 Verificando processamento na Meta ({tentativas * 10}s) - Status: {status_code}")

        if status_code == "FINISHED":
            print("✨ Vídeo processado e liberado para postagem!")
            break
        elif status_code == "ERROR":
            print(f"❌ A Meta encontrou um erro no processamento: {res_status}")
            return False

    # ==========================================
    # PASSO 3: Publicar a mídia
    # ==========================================
    url_publicacao = f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media_publish"
    payload_pub = {
        'creation_id': creation_id,
        'access_token': ACCESS_TOKEN
    }
    
    print("📢 Publicando o vídeo no perfil do Chefinho Gastro...")
    resposta_pub = requests.post(url_publicacao, data=payload_pub)
    resultado_pub = resposta_pub.json()
    
    if "id" in resultado_pub:
        print(f"🎉 Vídeo publicado com sucesso! Post ID: {resultado_pub['id']}")
        return True
    else:
        print(f"❌ Erro ao finalizar a publicação: {resultado_pub}")
        return False

if __name__ == "__main__":
    publicar_reels_instagram(r"C:\FabricaVideos\saida\video_teste.mp4", "Testando automação 100% em Python! 🍳 #ChefinhoGastro")