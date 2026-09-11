import os
import sys
import shutil
import glob
from typing import Optional
from fastapi import FastAPI, Header, HTTPException, BackgroundTasks, status
from pydantic import BaseModel
from rotina_diaria import (
    GEMINI_API_KEY,
    PASTA_BASE,
    selecionar_nicho_balanceado,
    gerar_roteiro_ia,
    executar_postagem_unica
)
from publicar_instagram import publicar_reels_instagram
from upload_video import hospedar_video_cloudinary
import subprocess

app = FastAPI(title="Fábrica de Vídeos API - Webhook Service")

WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")

class PostPayload(BaseModel):
    gancho: Optional[str] = None
    texto: Optional[str] = None
    tema: Optional[str] = None
    legenda: Optional[str] = None
    hashtags: Optional[str] = None
    nicho: Optional[str] = None

def limpar_pasta_temp():
    """Remove arquivos temporários da pasta temp/ para economizar espaço em disco."""
    pasta_temp = os.path.join(PASTA_BASE, "temp")
    if os.path.exists(pasta_temp):
        for f in os.listdir(pasta_temp):
            caminho = os.path.join(pasta_temp, f)
            try:
                if os.path.isfile(caminho) or os.path.islink(caminho):
                    os.unlink(caminho)
                elif os.path.isdir(caminho):
                    shutil.rmtree(caminho)
            except Exception as e:
                print(f"[-] Erro ao deletar {caminho}: {e}")

def tarefa_gerar_e_postar(payload_dict: dict):
    """Executa todo o pipeline pesado em segundo plano."""
    try:
        gancho = payload_dict.get("gancho")
        texto = payload_dict.get("texto")
        tema = payload_dict.get("tema")
        legenda = payload_dict.get("legenda")
        hashtags = payload_dict.get("hashtags")
        nicho = payload_dict.get("nicho")

        # Se o roteiro não foi fornecido via payload, gera dinamicamente via IA
        if not (gancho and texto and tema):
            if not GEMINI_API_KEY:
                print("[X] GEMINI_API_KEY não configurada no servidor.")
                return
            if not nicho:
                nicho = selecionar_nicho_balanceado()
            
            roteiro_ia = gerar_roteiro_ia(nicho, GEMINI_API_KEY)
            if not roteiro_ia:
                print("[X] Falha ao gerar roteiro via Gemini.")
                return
            
            gancho = gancho or roteiro_ia["gancho"]
            texto = texto or roteiro_ia["texto"]
            tema = tema or roteiro_ia["tema"]
            legenda = legenda or roteiro_ia["legenda"]
            hashtags = hashtags or roteiro_ia["hashtags"]

        # Renderizar o vídeo chamando o gerador_post.py
        script_gerador = os.path.join(PASTA_BASE, "gerador_post.py")
        cmd = [
            sys.executable, script_gerador,
            "--gancho", gancho,
            "--texto", texto,
            "--tema", tema
        ]

        subprocess.run(cmd, check=True, cwd=PASTA_BASE)

        pasta_saida = os.path.join(PASTA_BASE, "saida")
        arquivos_mp4 = [os.path.join(pasta_saida, f) for f in os.listdir(pasta_saida) if f.endswith(".mp4")]
        if not arquivos_mp4:
            print("[X] Nenhum vídeo renderizado foi encontrado na pasta 'saida'.")
            return

        caminho_video = max(arquivos_mp4, key=os.path.getctime)

        # Upload Cloudinary + Postagem no Instagram
        url_cloudinary = hospedar_video_cloudinary(caminho_video)
        
        legenda_completa = f"{legenda}\n\n{hashtags}".strip()
        publicar_reels_instagram(caminho_video, legenda_completa)

        # Limpeza pós-execução
        limpar_pasta_temp()
        print("[+] Tarefa em segundo plano finalizada com sucesso!")

    except Exception as e:
        limpar_pasta_temp()
        print(f"[X] Erro na execução da tarefa em segundo plano: {e}")

@app.get("/")
def health_check():
    return {"status": "online", "message": "Fábrica de Vídeos API operando normalmente."}

@app.post("/gerar-e-postar")
def gerar_e_postar(
    background_tasks: BackgroundTasks,
    payload: Optional[PostPayload] = None,
    x_api_key: Optional[str] = Header(None, alias="X-API-KEY")
):
    # Autenticação via Secret Header
    if WEBHOOK_SECRET:
        if not x_api_key or x_api_key != WEBHOOK_SECRET:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Cabeçalho de autenticação 'X-API-KEY' inválido ou ausente."
            )

    payload_dict = payload.dict() if payload else {}
    
    # Adiciona a tarefa pesada para rodar em segundo plano
    background_tasks.add_task(tarefa_gerar_e_postar, payload_dict)

    # Responde instantaneamente para o Make não dar timeout de 40s
    return {
        "sucesso": True,
        "mensagem": "Processamento de vídeo e postagem iniciado em segundo plano com sucesso!"
    }
