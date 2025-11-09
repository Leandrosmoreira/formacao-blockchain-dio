FROM ubuntu:22.04

# Evitar prompts interativos
ENV DEBIAN_FRONTEND=noninteractive

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    git \
    build-essential \
    pkg-config \
    libssl-dev \
    libudev-dev \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Instalar Node.js 20.x
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Instalar Rust (versão 1.75.0 compatível com Anchor 0.30.1)
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain 1.75.0
ENV PATH="/root/.cargo/bin:$PATH"

# Instalar Solana CLI 1.18.22
RUN sh -c "$(curl -sSfL https://release.solana.com/v1.18.22/install)" || \
    (wget https://github.com/solana-labs/solana/releases/download/v1.18.22/solana-release-x86_64-unknown-linux-gnu.tar.bz2 && \
     tar jxf solana-release-x86_64-unknown-linux-gnu.tar.bz2 && \
     mv solana-release /root/.local/share/solana/ && \
     rm solana-release-x86_64-unknown-linux-gnu.tar.bz2)

ENV PATH="/root/.local/share/solana/install/active_release/bin:$PATH"

# Instalar Anchor via cargo (sem --locked para permitir atualização de deps)
RUN cargo install --git https://github.com/coral-xyz/anchor --tag v0.30.1 anchor-cli

# Criar diretório de trabalho
WORKDIR /workspace

# Copiar projeto
COPY . .

# Instalar dependências npm
RUN npm install

# Configurar Solana para devnet
RUN mkdir -p /root/.config/solana

# Expor porta (se necessário para testes)
EXPOSE 8899

CMD ["/bin/bash"]
