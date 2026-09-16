import os
from dotenv import load_dotenv
load_dotenv()
import time
import requests
from upload_video import hospedar_video_cloudinary

# ==========================================
# CONFIGURAÇÕES DO INSTAGRAM / META
# ==========================================
# Suporta tanto ACCESS_TOKEN quanto META_ACCESS_TOKEN
ACCESS_TOKEN = (os.environ.get("ACCESS_TOKEN") or os.environ.get("META_ACCESS_TOKEN", "")).strip()
IG_USER_ID = os.environ.get("IG_USER_ID", "").strip()

def validar_credenciais_instagram():
    if not ACCESS_TOKEN:
        raise ValueError("[X] Variável de ambiente ACCESS_TOKEN ou META_ACCESS_TOKEN não foi configurada!")
    if not IG_USER_ID:
        raise ValueError("[X] Variável de ambiente IG_USER_ID não foi configurada!")

def publicar_reels_instagram(caminho_video_mp4, legenda):
    validar_credenciais_instagram()
    print("[+] Iniciando processo de publicacao do Reels no Instagram...")
    
    if not os.path.exists(caminho_video_mp4):
        raise FileNotFoundError(f"Arquivo de vídeo não encontrado: {caminho_video_mp4}")
    
    tamanho_video = os.path.getsize(caminho_video_mp4)
    print(f"[+] Tamanho do arquivo: {tamanho_video / (1024*1024):.2f} MB")

    # =========================================================================
    # PASSO 1: Iniciar Sessão de Upload Direto (Sem depender de CDNs externas)
    # =========================================================================
    url_sessao = f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media"
    payload_sessao = {
        'media_type': 'REELS',
        'upload_type': 'resumable',
        'caption': legenda,
        'access_token': ACCESS_TOKEN
    }

    print("[+] Criando sessão de upload direto na Meta...")
    res_sessao = requests.post(url_sessao, data=payload_sessao).json()
    
    if "id" not in res_sessao or "uri" not in res_sessao:
        print(f"[!] Resumable upload não retornou URI. Tentando método por URL via Cloudinary como fallback...")
        url_video_publica = hospedar_video_cloudinary(caminho_video_mp4)
        time.sleep(10)
        res_sessao = requests.post(url_sessao, data={
            'media_type': 'REELS',
            'video_url': url_video_publica,
            'caption': legenda,
            'access_token': ACCESS_TOKEN
        }).json()
        if "id" not in res_sessao:
            raise RuntimeError(f"Erro ao criar contêiner no Instagram: {res_sessao}")
        creation_id = res_sessao["id"]
    else:
        creation_id = res_sessao["id"]
        upload_uri = res_sessao["uri"]
        print(f"[+] Sessão iniciada com sucesso! Container ID: {creation_id}")

        # =========================================================================
        # PASSO 2: Enviar os bytes do vídeo diretamente para a Meta
        # =========================================================================
        print("[+] Enviando bytes do vídeo diretamente para os servidores da Meta...")
        headers_upload = {
            'Authorization': f'OAuth {ACCESS_TOKEN}',
            'offset': '0',
            'file_size': str(tamanho_video),
            'Content-Type': 'application/octet-stream'
        }
        with open(caminho_video_mp4, 'rb') as f_video:
            res_upload = requests.post(upload_uri, headers=headers_upload, data=f_video)
        
        if res_upload.status_code not in [200, 201]:
            raise RuntimeError(f"Falha no envio direto do arquivo: {res_upload.status_code} - {res_upload.text}")
        print("[+] Envio direto de mídia concluído com sucesso!")

    # =========================================================================
    # PASSO 3: Consultar Status de Processamento
    # =========================================================================
    url_status = f"https://graph.facebook.com/v19.0/{creation_id}"
    params_status = {
        'fields': 'status_code,status',
        'access_token': ACCESS_TOKEN
    }

    print("[+] Aguardando os servidores da Meta processarem o vídeo...")
    tentativas = 0
    max_tentativas = 40  # Até ~6 minutos

    while tentativas < max_tentativas:
        time.sleep(10)
        tentativas += 1
        res_status = requests.get(url_status, params=params_status).json()
        status_code = res_status.get("status_code")

        print(f"[+] Verificando status na Meta ({tentativas * 10}s) - Status: {status_code}")

        if status_code == "FINISHED":
            print("[+] Vídeo 100% processado e liberado para postagem!")
            break
        elif status_code == "IN_PROGRESS":
            continue
        elif status_code == "ERROR":
            print(f"[X] A Meta encontrou um erro no processamento: {res_status}")
            raise RuntimeError(f"Erro no processamento da Meta: {res_status}")

    # =========================================================================
    # PASSO 4: Publicar a mídia
    # =========================================================================
    url_publicacao = f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media_publish"
    payload_pub = {
        'creation_id': creation_id,
        'access_token': ACCESS_TOKEN
    }
    
    print("[+] Publicando o vídeo no Reels do Chefinho Gastro...")
    resposta_pub = requests.post(url_publicacao, data=payload_pub)
    resultado_pub = resposta_pub.json()
    
    if "id" in resultado_pub:
        print(f"[+] Vídeo publicado com sucesso! Post ID: {resultado_pub['id']}")
        return True
    else:
        print(f"[X] Erro ao finalizar a publicação: {resultado_pub}")
        raise RuntimeError(f"Erro ao finalizar a publicação: {resultado_pub.get('error')}")

if __name__ == "__main__":
    pasta_base = os.path.dirname(os.path.abspath(__file__))
    caminho_teste = os.path.join(pasta_base, "saida", "video_teste.mp4")
    publicar_reels_instagram(caminho_teste, "Testando automação 100% em Python!  #ChefinhoGastro")