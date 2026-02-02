# Usa Python 3.12 Slim (Leve e seguro)
FROM python:3.12-slim

# Define diretório de trabalho dentro do container
WORKDIR /app

# Instala utilitários básicos de sistema (necessário para alguns comandos shell)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copia e instala dependências (Otimização de Cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- NOVO: Instala o navegador Chromium para o Web Arm ---
RUN playwright install --with-deps chromium

# Copia o código fonte do Jarvis
COPY . .

# Cria a pasta de logs para garantir permissões
RUN mkdir -p jarvis_logs

# Comando padrão de execução
CMD ["python", "jarvis.py"]