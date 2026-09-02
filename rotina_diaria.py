import os
import time
import json
import random
import schedule
import subprocess
from datetime import datetime
from google import genai
from publicar_instagram import publicar_reels_instagram

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

NICHOS_CULINARIA = [
    "truques de culinária e receitas fáceis",
    "curiosidades surpreendentes da gastronomia mundial",
    "segredos de chefs e técnicas de cozinha",
    "história e origem de pratos famosos",
    "dicas de conservação e preparo de alimentos"
]

NICHOS_GERAIS = [
    "curiosidades surpreendentes do mundo",
    "truques de psicologia e comportamento humano",
    "fatos históricos inacreditáveis",
    "dicas de produtividade e foco"
]

PASTA_BASE = r"C:\FabricaVideos"
ARQ_HISTORICO_NICHOS = os.path.join(PASTA_BASE, "temp", "historico_nichos.json")
ARQ_HISTORICO_CONTEUDO = os.path.join(PASTA_BASE, "temp", "historico_conteudo.json")

def carregar_json(caminho):
    if os.path.exists(caminho):
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def salvar_json(caminho, dados):
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

def selecionar_nicho_balanceado():
    historico = carregar_json(ARQ_HISTORICO_NICHOS)
    if random.random() < 0.7:
        disponiveis = [n for n in NICHOS_CULINARIA if n not in historico]
        if not disponiveis:
            disponiveis = NICHOS_CULINARIA[:]
    else:
        disponiveis = [n for n in NICHOS_GERAIS if n not in historico]
        if not disponiveis:
            disponiveis = NICHOS_GERAIS[:]

    random.shuffle(disponiveis)
    escolhido = disponiveis[0]
    historico.append(escolhido)
    salvar_json(ARQ_HISTORICO_NICHOS, historico[-9:])
    return escolhido

def gerar_roteiro_ia(nicho, api_key):
    historico_conteudos = carregar_json(ARQ_HISTORICO_CONTEUDO)
    
    ultimos_ganchos = historico_conteudos[-15:] if historico_conteudos else []
    lista_exclusao = "\n".join([f"- {item}" for item in ultimos_ganchos])

    prompt = f"""
Você é o roteirista oficial da página Chefinho Gastro no Instagram Reels e TikTok.
Crie um conteúdo completo, dinâmico e INÉDITO sobre o tema: [{nicho}].

NÃO REPITA NENHUM DOS TEMAS OU GANCHOS ABAIXO:
{lista_exclusao}

REGRAS RÍGIDAS:
1. Retorne ESTRITAMENTE um JSON válido com cinco chaves: "gancho", "texto", "tema", "legenda", "hashtags".
2. "gancho": Frase impactante em português (máximo 15 palavras) para o topo do vídeo.
3. "texto": Narração completa em português (entre 35 e 55 palavras) diretamente relacionada ao gancho. Use português perfeito e espaçado.
4. "tema": Termo de busca em INGLÊS com 2 a 3 palavras para buscar vídeo de fundo no Pexels.
5. "legenda": Um texto envolvente explicando exatamente o tema abordado no vídeo em NO MÁXIMO 3 parágrafos curtos.
6. "hashtags": Linha com 5 a 8 hashtags altamente relevantes.
7. Sem formatação markdown extra fora do JSON.
"""
    client = genai.Client(api_key=api_key)

    # Modelos atuais suportados pela API do Gemini
    modelos_para_testar = ["gemini-3.6-flash", "gemini-3.5-flash-lite", "gemini-3.5-flash"]

    for model_name in modelos_para_testar:
        for tentativa in range(1, 4):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config={"response_mime_type": "application/json"}
                )
                if response and response.text:
                    dados = json.loads(response.text)
                    gancho = dados.get("gancho", "")
                    
                    historico_conteudos.append(gancho)
                    salvar_json(ARQ_HISTORICO_CONTEUDO, historico_conteudos)
                    print(f"✅ Roteiro inédito gerado com sucesso usando o modelo [{model_name}]!")
                    return dados
            except Exception as e:
                print(f"⚠️ Tentativa {tentativa}/3 no modelo [{model_name}] falhou: {e}")
                time.sleep(2)

    print("❌ Falha na geração do roteiro.")
    return None

def executar_postagem_unica():
    if not GEMINI_API_KEY:
        print("❌ Configure sua GEMINI_API_KEY na variável de ambiente!")
        return

    print(f"\n🚀 [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Iniciando ciclo...")
    nicho = selecionar_nicho_balanceado()

    print(f"🧠 Gerando roteiro para [{nicho.upper()}]...")
    ideia = gerar_roteiro_ia(nicho, GEMINI_API_KEY)
    
    if not ideia:
        print("⏭️ Cancelando ciclo por falta de roteiro inédito.")
        return

    print(f"📌 Gancho: {ideia['gancho']}")
    print(f"🔍 Tema Pexels: {ideia['tema']}")
    print("🎬 Renderizando Vídeo...")

    cmd = [
        "python", os.path.join(PASTA_BASE, "gerador_post.py"),
        "--gancho", ideia["gancho"],
        "--texto", ideia["texto"],
        "--tema", ideia["tema"]
    ]

    try:
        subprocess.run(cmd, check=True)
        print("✅ Vídeo renderizado com sucesso!")
        
        pasta_saida = os.path.join(PASTA_BASE, "saida")
        arquivos_mp4 = [os.path.join(pasta_saida, f) for f in os.listdir(pasta_saida) if f.endswith(".mp4")]
        
        if not arquivos_mp4:
            print("❌ Nenhum vídeo encontrado na pasta 'saida'.")
            return

        caminho_video_saida = max(arquivos_mp4, key=os.path.getctime)
        print(f"📁 Vídeo pronto em: {caminho_video_saida}")
        
        legenda_completa = f"{ideia['legenda']}\n\n{ideia['hashtags']}"
        
        print("📤 Enviando para o Instagram...")
        publicar_reels_instagram(caminho_video_saida, legenda_completa)
        print("🎉 Post publicado no Reels com sucesso!")
        
    except Exception as e:
        print(f"❌ Erro durante o processo: {e}")

if __name__ == "__main__":
    schedule.every().day.at("09:00").do(executar_postagem_unica)
    schedule.every().day.at("13:00").do(executar_postagem_unica)
    schedule.every().day.at("18:00").do(executar_postagem_unica)

    print("⏰ Robô ativado!")
    executar_postagem_unica()
    
    while True:
        schedule.run_pending()
        time.sleep(30)