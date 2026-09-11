import os
from dotenv import load_dotenv
load_dotenv()
import requests
import random

# Substitua pela sua chave da API do Pexels
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")

PASTA_BASE = os.path.dirname(os.path.abspath(__file__))
PASTA_FUNDOS = os.path.join(PASTA_BASE, "fundos")
os.makedirs(PASTA_FUNDOS, exist_ok=True)

def buscar_e_baixar_fundo(termo_busca="satisfying nature"):
    if not PEXELS_API_KEY:
        print("[X] Atencao: Configure sua chave PEXELS_API_KEY no arquivo.")
        return None

    headers = {"Authorization": PEXELS_API_KEY}
    url = f"https://api.pexels.com/videos/search?query={termo_busca}&orientation=portrait&per_page=15"
    
    print(f"[+] Buscando fundo vertical no Pexels para: '{termo_busca}'...")
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"[X] Erro na API do Pexels: {response.status_code} - {response.text}")
        return None
        
    data = response.json()
    videos = data.get("videos", [])
    
    if not videos:
        print("[-] Nenhum video encontrado para o termo. Buscando tema generico 'abstract nature'...")
        return buscar_e_baixar_fundo("abstract nature")

    # Escolhe um vídeo aleatório da lista para variar os fundos
    video_escolhido = random.choice(videos)
    
    # Procura um arquivo com resolução HD vertical (720x1280 ou 1080x1920)
    video_files = video_escolhido.get("video_files", [])
    link_download = None
    
    for f in video_files:
        if f.get("width", 0) <= f.get("height", 0) and f.get("quality") == "hd":
            link_download = f.get("link")
            break
            
    if not link_download and video_files:
        link_download = video_files[0].get("link")

    if not link_download:
        print("[X] Nao foi possivel encontrar link de download valido.")
        return None

    caminho_arquivo = os.path.join(PASTA_FUNDOS, "fundo.mp4")
    
    print("[+] Baixando video de fundo...")
    r = requests.get(link_download, stream=True)
    with open(caminho_arquivo, "wb") as f:
        for chunk in r.iter_content(chunk_size=1024*1024):
            if chunk:
                f.write(chunk)
                
    print(f"[+] Fundo salvo com sucesso em: {caminho_arquivo}")
    return caminho_arquivo

if __name__ == "__main__":
    buscar_e_baixar_fundo("space mystery")