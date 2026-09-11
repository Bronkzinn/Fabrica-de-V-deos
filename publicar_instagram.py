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
    print("[+] Iniciando processo de publicacao do Reels no Instagram...")
    
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
    
    print("[+] Enviando solicitacao de criacao de conteiner...")
    resposta = requests.post(url_criacao, data=payload)
    resultado = resposta.json()
    
    if "id" not in resultado:
        print(f"[X] Erro ao criar o conteiner no Instagram: {resultado}")
        raise RuntimeError(f"Erro ao criar conteiner no Instagram: {resultado.get('error')}")
        
    creation_id = resultado["id"]
    print(f"[+] Conteiner criado com sucesso! ID: {creation_id}")
    
    # ==========================================
    # PASSO 2: Consultar Status de Processamento
    # ==========================================
    url_status = f"https://graph.facebook.com/v19.0/{creation_id}"
    params_status = {
        'fields': 'status_code',
        'access_token': ACCESS_TOKEN
    }

    print("[+] Aguardando os servidores da Meta processarem o video...")
    tentativas = 0
    max_tentativas = 30  # Timeout de até 5 minutos (30 x 10s)

    while tentativas < max_tentativas:
        time.sleep(10)
        tentativas += 1
        res_status = requests.get(url_status, params=params_status).json()
        status_code = res_status.get("status_code")

        print(f"[+] Verificando processamento na Meta ({tentativas * 10}s) - Status: {status_code}")

        if status_code == "FINISHED":
            print("[+] Video processado e liberado para postagem!")
            break
        elif status_code == "ERROR":
            print(f"[X] A Meta encontrou um erro no processamento: {res_status}")
            raise RuntimeError(f"Erro no processamento da Meta: {res_status}")

    # ==========================================
    # PASSO 3: Publicar a mídia
    # ==========================================
    url_publicacao = f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media_publish"
    payload_pub = {
        'creation_id': creation_id,
        'access_token': ACCESS_TOKEN
    }
    
    print("[+] Publicando o video no perfil do Chefinho Gastro...")
    resposta_pub = requests.post(url_publicacao, data=payload_pub)
    resultado_pub = resposta_pub.json()
    
    if "id" in resultado_pub:
        print(f"[+] Video publicado com sucesso! Post ID: {resultado_pub['id']}")
        return True
    else:
        print(f"[X] Erro ao finalizar a publicacao: {resultado_pub}")
        raise RuntimeError(f"Erro ao finalizar a publicacao: {resultado_pub.get('error')}")

if __name__ == "__main__":
    pasta_base = os.path.dirname(os.path.abspath(__file__))
    caminho_teste = os.path.join(pasta_base, "saida", "video_teste.mp4")
    publicar_reels_instagram(caminho_teste, "Testando automação 100% em Python!  #ChefinhoGastro")