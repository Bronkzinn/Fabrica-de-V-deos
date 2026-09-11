FROM python:3.11-slim

# Evita arquivos .pyc e buffer de saída do Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Instala o FFmpeg e fontes do sistema para a renderização de vídeo e textos
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    fonts-dejavu-core \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Copia e instala as dependências do Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copia todo o código-fonte do projeto
COPY . .

# Garante a criação das pastas necessárias
RUN mkdir -p logs temp fundos saida assets

# Expõe a porta padrão para o Render/Railway (PORT lido via var de ambiente)
EXPOSE 8000

CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}"]
