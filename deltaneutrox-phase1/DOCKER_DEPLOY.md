# 🐳 Deploy DeltaNeutroX via Docker

## 📋 Pré-requisitos na VPS

- Ubuntu 20.04+ ou 22.04
- Docker instalado
- Docker Compose instalado
- Acesso SSH

## 🚀 Deploy Rápido (3 passos)

### 1️⃣ Clonar repositório na VPS

```bash
cd ~
git clone https://github.com/Leandrosmoreira/formacao-blockchain-dio.git
cd formacao-blockchain-dio/deltaneutrox-phase1
```

**OU enviar via SCP do seu computador:**

```bash
# No seu computador local:
cd ~/formacao-blockchain-dio
tar -czf deltaneutrox.tar.gz deltaneutrox-phase1/
scp deltaneutrox.tar.gz user@sua-vps-ip:~/

# Na VPS:
tar -xzf deltaneutrox.tar.gz
cd deltaneutrox-phase1
```

### 2️⃣ Dar permissão ao script

```bash
chmod +x docker-deploy.sh
```

### 3️⃣ Executar deploy automatizado

```bash
./docker-deploy.sh
```

Isso vai:
- ✅ Construir imagem Docker com todas as dependências
- ✅ Criar/usar keypair Solana
- ✅ Configurar para devnet
- ✅ Compilar o programa
- ✅ Fazer deploy na devnet

---

## 🔧 Comandos Úteis

### Acessar container

```bash
docker-compose exec deltaneutrox bash
```

### Ver logs

```bash
docker-compose logs -f
```

### Parar container

```bash
docker-compose down
```

### Rebuild (se mudar código)

```bash
docker-compose build --no-cache
docker-compose up -d
```

### Verificar saldo

```bash
docker-compose exec deltaneutrox solana balance
```

### Ver endereço da carteira

```bash
docker-compose exec deltaneutrox solana address
```

### Build manual dentro do container

```bash
docker-compose exec deltaneutrox bash
anchor build
```

### Deploy manual

```bash
docker-compose exec deltaneutrox bash
anchor deploy --provider.cluster devnet
```

---

## 💸 Adicionar SOL à Carteira

### Opção 1: Via Faucet Web

1. Obter endereço:
```bash
docker-compose exec deltaneutrox solana address
```

2. Acessar: https://faucet.solana.com

3. Colar endereço e solicitar SOL

### Opção 2: Via CLI

```bash
docker-compose exec deltaneutrox solana airdrop 2
```

### Opção 3: Usar sua keypair existente

```bash
# Copiar sua keypair para o container
docker cp ~/.config/solana/id.json deltaneutrox-builder:/root/.config/solana/id.json
```

---

## 🔍 Troubleshooting

### Build falhou?

```bash
# Limpar cache e rebuild
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
docker-compose exec deltaneutrox anchor build
```

### Problema de rede?

```bash
# Testar conectividade
docker-compose exec deltaneutrox ping -c 4 api.devnet.solana.com
```

### Ver logs detalhados do build

```bash
docker-compose exec deltaneutrox anchor build 2>&1 | tee build.log
```

---

## 📦 Estrutura de Volumes

Os seguintes volumes persistem dados:

- `solana-data`: Keypairs e configurações Solana
- `cargo-cache`: Cache do Cargo (acelera builds)
- `cargo-git`: Repositórios Git do Cargo

---

## 🎯 Deploy em Mainnet

**⚠️ ATENÇÃO:** Mainnet usa SOL real!

1. Alterar para mainnet:
```bash
docker-compose exec deltaneutrox solana config set --url mainnet-beta
```

2. Verificar saldo (precisa de SOL real!)

3. Deploy:
```bash
docker-compose exec deltaneutrox anchor deploy --provider.cluster mainnet-beta
```

---

## 🛡️ Segurança

- ✅ Keypairs ficam dentro do container (volumes Docker)
- ✅ Não commitar `id.json` no git
- ✅ Fazer backup da keypair:
  ```bash
  docker cp deltaneutrox-builder:/root/.config/solana/id.json ~/backup-keypair.json
  ```

---

## 💡 Dicas

1. **Primeira vez**: Pode demorar 10-15 min para build da imagem
2. **Builds seguintes**: ~3-5 min (usa cache)
3. **VPS mínima**: 2 GB RAM, 2 vCPU, 20 GB storage
4. **Rede estável**: Deploy precisa de boa conexão

---

## 📞 Suporte

Se encontrar problemas:

1. Ver logs: `docker-compose logs -f`
2. Entrar no container: `docker-compose exec deltaneutrox bash`
3. Verificar status: `docker-compose ps`

---

✅ **Pronto! Seu programa Solana está na devnet!** 🚀
