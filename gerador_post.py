import os
import re
import sys
import argparse
import asyncio
import edge_tts
import subprocess
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageOps
from baixar_fundo import buscar_e_baixar_fundo

def carregar_fonte(nome_fonte, tamanho):
    """Carrega fonte com fallback automático para compatibilidade Windows/Linux."""
    fontes_tentar = [
        nome_fonte,
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if "bd" in nome_fonte or "Bold" in nome_fonte else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if "bd" in nome_fonte or "Bold" in nome_fonte else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "DejaVuSans.ttf",
        "arial.ttf"
    ]
    for fonte in fontes_tentar:
        try:
            return ImageFont.truetype(fonte, tamanho)
        except (OSError, Exception):
            continue
    try:
        return ImageFont.load_default()
    except Exception:
        return ImageFont.load_default()

PASTA_BASE = os.path.dirname(os.path.abspath(__file__))

# --- CONFIGURAÇÕES FIXAS DO PERFIL ---
NOME_EXIBICAO = "Chefinho Gastro"
ARROBA = "@chefinhogastro"
GANCHO_PADRAO = "Culinária, notícias e curiosidades, nos siga para não perder mais nenhum conteúdo."
FOTO_PERFIL = os.path.join(PASTA_BASE, "assets", "perfil.png")

# Tenta encontrar verificado em jpg ou png
ICONE_VERIFICADO = os.path.join(PASTA_BASE, "assets", "verificado.jpg")
if not os.path.exists(ICONE_VERIFICADO):
    ICONE_VERIFICADO = os.path.join(PASTA_BASE, "assets", "verificado.png")

PASTA_TEMP = os.path.join(PASTA_BASE, "temp")
PASTA_SAIDA = os.path.join(PASTA_BASE, "saida")
ARQ_AUDIO = os.path.join(PASTA_TEMP, "audio.mp3")
ARQ_MOLDURA = os.path.join(PASTA_TEMP, "moldura.png")
ARQ_FUNDO = os.path.join(PASTA_BASE, "fundos", "fundo.mp4")

parser = argparse.ArgumentParser(description="Template de Post Viral com Vídeo Central")
parser.add_argument("--gancho", type=str, default=GANCHO_PADRAO, help="Texto do post no topo da moldura")
parser.add_argument("--texto", type=str, required=True, help="Roteiro completo narrado")
parser.add_argument("--tema", type=str, default="cooking food", help="Tema do Pexels")
parser.add_argument("--voz", type=str, default="pt-BR-AntonioNeural")
args = parser.parse_args()

os.makedirs(PASTA_SAIDA, exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
ARQ_SAIDA = os.path.join(PASTA_SAIDA, f"post_{timestamp}.mp4")

def get_audio_duration(file_path):
    abs_path = os.path.abspath(file_path)
    if not os.path.exists(abs_path) or os.path.getsize(abs_path) == 0:
        raise FileNotFoundError(f"O arquivo de áudio '{abs_path}' não foi gerado corretamente.")

    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        abs_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out = result.stdout.strip()
    if not out:
        raise ValueError(f"Falha ao ler duração do áudio via ffprobe. Saída de erro: {result.stderr}")
    return float(out)

# --- 1. MOLDURA BRANCA SUPERIOR VIA PILLOW ---
def criar_moldura_post(gancho_texto):
    print("[+] 1. Gerando moldura com proporcoes calibradas...")
    img = Image.new("RGBA", (1080, 1920), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)

    fonte_nome = carregar_fonte("arialbd.ttf", 44)
    fonte_arroba = carregar_fonte("arial.ttf", 36)
    fonte_gancho = carregar_fonte("arialbd.ttf", 42)

    tamanho_perfil = 130
    pos_x_perfil = 65
    pos_y_perfil = 65

    if os.path.exists(FOTO_PERFIL):
        perfil = Image.open(FOTO_PERFIL).convert("RGBA")
        perfil_quadrado = ImageOps.fit(perfil, (tamanho_perfil, tamanho_perfil), method=Image.Resampling.LANCZOS)

        mask = Image.new("L", (tamanho_perfil * 4, tamanho_perfil * 4), 0)
        draw_mask = ImageDraw.Draw(mask)
        draw_mask.ellipse((0, 0, tamanho_perfil * 4, tamanho_perfil * 4), fill=255)
        mask = mask.resize((tamanho_perfil, tamanho_perfil), resample=Image.Resampling.LANCZOS)

        img.paste(perfil_quadrado, (pos_x_perfil, pos_y_perfil), mask)

    offset_texto_x = pos_x_perfil + tamanho_perfil + 25
    pos_y_nome = 80
    pos_y_arroba = 138

    draw.text((offset_texto_x, pos_y_nome), NOME_EXIBICAO, fill=(15, 20, 25), font=fonte_nome)
    draw.text((offset_texto_x, pos_y_arroba), ARROBA, fill=(105, 114, 125), font=fonte_arroba)

    if os.path.exists(ICONE_VERIFICADO):
        tam_selo = 38
        verif = Image.open(ICONE_VERIFICADO).convert("RGBA")
        verif = verif.resize((tam_selo, tam_selo), Image.Resampling.LANCZOS)
        
        largura_nome = draw.textlength(NOME_EXIBICAO, font=fonte_nome)
        pos_selo_x = int(offset_texto_x + largura_nome + 12)
        pos_selo_y = pos_y_nome + 6
        
        img.paste(verif, (pos_selo_x, pos_selo_y), verif)

    palavras = gancho_texto.split()
    linhas = []
    linha_atual = ""
    for p in palavras:
        teste = f"{linha_atual} {p}".strip()
        if draw.textlength(teste, font=fonte_gancho) < 950:
            linha_atual = teste
        else:
            linhas.append(linha_atual)
            linha_atual = p
    if linha_atual:
        linhas.append(linha_atual)

    y_pos = 230
    for linha in linhas:
        draw.text((pos_x_perfil, y_pos), linha, fill=(15, 20, 25), font=fonte_gancho)
        y_pos += 56

    draw.rectangle([0, 480, 1080, 1480], fill=(0, 0, 0, 0))
    os.makedirs(PASTA_TEMP, exist_ok=True)
    img.save(ARQ_MOLDURA)

# --- 2. ÁUDIO CADENCIADO + CRIAÇÃO DE IMAGENS DE LEGENDA (PNG OVERLAYS) ---
subtitulos_timed = []

async def gerar_audio_e_legendas():
    global subtitulos_timed
    print("[+] 2. Sintetizando narracao e gerando legendas...")
    
    texto_limpo = re.sub(r'\s+', ' ', args.texto).strip()
    communicate = edge_tts.Communicate(texto_limpo, args.voz, rate="-5%")
    submaker = edge_tts.SubMaker()
    
    os.makedirs(PASTA_TEMP, exist_ok=True)

    if os.path.exists(ARQ_AUDIO):
        os.remove(ARQ_AUDIO)

    with open(ARQ_AUDIO, "wb") as file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                file.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                submaker.feed(chunk)

    if not os.path.exists(ARQ_AUDIO) or os.path.getsize(ARQ_AUDIO) == 0:
        raise RuntimeError("Falha na geracao do audio via Edge-TTS.")

    srt_content = submaker.get_srt()
    subtitulos_timed = []
    
    if srt_content:
        blocks = srt_content.strip().split("\n\n")
        idx = 0
        for block in blocks:
            lines = [line.strip() for line in block.split("\n") if line.strip()]
            if len(lines) >= 3:
                times = lines[1].split(" --> ")
                
                def srt_to_seconds(t_str):
                    parts = t_str.replace(',', '.').split(':')
                    return float(parts[0])*3600 + float(parts[1])*60 + float(parts[2])

                st = srt_to_seconds(times[0])
                et = srt_to_seconds(times[1])
                txt = " ".join(lines[2:]).strip().upper()
                
                img_leg = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
                draw_leg = ImageDraw.Draw(img_leg)
                fonte_leg = carregar_fonte("arialbd.ttf", 52)

                palavras = txt.split()
                linhas_leg = []
                l_atual = ""
                for p in palavras:
                    teste = f"{l_atual} {p}".strip()
                    if draw_leg.textlength(teste, font=fonte_leg) < 900:
                        l_atual = teste
                    else:
                        linhas_leg.append(l_atual)
                        l_atual = p
                if l_atual:
                    linhas_leg.append(l_atual)

                y_center = 1150
                for linha in linhas_leg:
                    w = draw_leg.textlength(linha, font=fonte_leg)
                    x = (1080 - w) / 2
                    
                    stroke_w = 5
                    for dx in range(-stroke_w, stroke_w + 1):
                        for dy in range(-stroke_w, stroke_w + 1):
                            if dx != 0 or dy != 0:
                                draw_leg.text((x + dx, y_center + dy), linha, fill=(0, 0, 0, 255), font=fonte_leg)
                    
                    draw_leg.text((x, y_center), linha, fill=(255, 255, 0, 255), font=fonte_leg)
                    y_center += 65

                caminho_png_leg = os.path.join(PASTA_TEMP, f"leg_{idx}.png")
                img_leg.save(caminho_png_leg)
                subtitulos_timed.append((st, et, caminho_png_leg))
                idx += 1

# --- 3. RENDERIZAÇÃO FFMPEG COM OVERLAYS DE IMAGEM POR TEMPO ---
def renderizar_video_post():
    print("[+] 3. Renderizando composicao final via FFmpeg Overlays...")
    
    arq_audio_abs = os.path.abspath(ARQ_AUDIO)
    arq_moldura_abs = os.path.abspath(ARQ_MOLDURA)
    arq_fundo_abs = os.path.abspath(ARQ_FUNDO)
    arq_saida_abs = os.path.abspath(ARQ_SAIDA)

    if not os.path.exists(arq_audio_abs) or os.path.getsize(arq_audio_abs) == 0:
        raise FileNotFoundError(f"Arquivo de áudio principal '{arq_audio_abs}' não foi encontrado ou está vazio.")
    
    if not os.path.exists(arq_moldura_abs):
        raise FileNotFoundError(f"Arquivo de moldura '{arq_moldura_abs}' não foi encontrado.")
        
    if not os.path.exists(arq_fundo_abs) or os.path.getsize(arq_fundo_abs) == 0:
        raise FileNotFoundError(f"Arquivo de vídeo de fundo '{arq_fundo_abs}' não foi encontrado ou está vazio.")

    duracao = get_audio_duration(arq_audio_abs)

    cmd_inputs = [
        "ffmpeg", "-y",
        "-stream_loop", "-1", "-i", arq_fundo_abs,
        "-i", arq_moldura_abs
    ]

    for _, _, caminho_png in subtitulos_timed:
        caminho_png_abs = os.path.abspath(caminho_png)
        if os.path.exists(caminho_png_abs):
            cmd_inputs.extend(["-i", caminho_png_abs])

    cmd_inputs.extend(["-i", arq_audio_abs])

    idx_audio = len(subtitulos_timed) + 2
    filter_parts = [
        f"[0:v]scale=1080:1000:force_original_aspect_ratio=increase,crop=1080:1000[vid]",
        f"color=c=white:s=1080x1920:d={duracao:.2f}[bg]",
        f"[bg][vid]overlay=0:480[c0]",
        f"[c0][1:v]overlay=0:0[c1]"
    ]

    last_label = "c1"
    for idx, (st, et, _) in enumerate(subtitulos_timed):
        in_idx = idx + 2
        next_label = f"c{idx + 2}"
        f_str = f"[{last_label}][{in_idx}:v]overlay=0:0:enable='between(t,{st:.2f},{et:.2f})'[{next_label}]"
        filter_parts.append(f_str)
        last_label = next_label

    filter_complex = ";".join(filter_parts)

    cmd = cmd_inputs + [
        "-t", str(duracao),
        "-filter_complex", filter_complex,
        "-map", f"[{last_label}]",
        "-map", f"{idx_audio}:a:0",
        "-c:v", "libx264",
        "-preset", "fast",
        "-c:a", "aac",
        "-b:a", "192k",
        arq_saida_abs
    ]

    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True, cwd=PASTA_BASE)
    except subprocess.CalledProcessError as e:
        print(f"[X] Erro na execução do FFmpeg:\n{e.stderr}")
        raise e

    print(f"\n[+] Video gerado com sucesso com legendas impressas: {ARQ_SAIDA}")

if __name__ == "__main__":
    criar_moldura_post(args.gancho)
    buscar_e_baixar_fundo(args.tema)
    asyncio.run(gerar_audio_e_legendas())
    renderizar_video_post()