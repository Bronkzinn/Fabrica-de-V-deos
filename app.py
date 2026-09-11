import os
import sys
import shutil
import glob
from typing import Optional
from fastapi import FastAPI, Header, HTTPException, Security, status
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

@app.get("/")
def health_check():
    return {"status": "online", "message": "Fábrica de Vídeos API operando normalmente."}

@app.post("/gerar-e-postar")
def gerar_e_postar(
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

    try:
        gancho = payload.gancho if payload else None
        texto = payload.texto if payload else None
        tema = payload.tema if payload else None
        legenda = payload.legenda if payload else None
        hashtags = payload.hashtags if payload else None
        nicho = payload.nicho if payload else None

        # Se o roteiro não foi fornecido via payload, gera dinamicamente via IA
        if not (gancho and texto and tema):
            if not GEMINI_API_KEY:
                raise HTTPException(
                    status_code=500,
                    detail="GEMINI_API_KEY não configurada no servidor."
                )
            if not nicho:
                nicho = selecionar_nicho_balanceado()
            
            roteiro_ia = gerar_roteiro_ia(nicho, GEMINI_API_KEY)
            if not roteiro_ia:
                raise HTTPException(
                    status_code=500,
                    detail="Falha ao gerar roteiro via Gemini."
                )
            
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
            raise FileNotFoundError("Nenhum vídeo renderizado foi encontrado na pasta 'saida'.")

        caminho_video = max(arquivos_mp4, key=os.path.getctime)

        # Upload Cloudinary + Postagem no Instagram
        url_cloudinary = hospedar_video_cloudinary(caminho_video)
        
        legenda_completa = f"{legenda}\n\n{hashtags}".strip()
        publicar_reels_instagram(caminho_video, legenda_completa)

        # Limpeza pós-execução
        limpar_pasta_temp()

        return {
            "sucesso": True,
            "gancho": gancho,
            "tema": tema,
            "url_cloudinary": url_cloudinary,
            "mensagem": "Vídeo renderizado e publicado no Reels com sucesso!"
        }

    except Exception as e:
        limpar_pasta_temp()
        return {
            "sucesso": False,
            "url_cloudinary": None,
            "mensagem_erro": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port)
