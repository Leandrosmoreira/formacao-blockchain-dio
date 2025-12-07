# MEV Sandwich Bot - Ethereum

> ⚠️ **AVISO**: Este projeto é **exclusivamente educacional**. O uso de MEV bots em produção envolve riscos financeiros significativos e considerações éticas. Use apenas para aprendizado e em testnets.

## 📋 Sobre

Bot MEV (Maximal Extractable Value) que implementa a estratégia de "sandwich attack" na rede Ethereum. O bot monitora o mempool em busca de grandes transações de swap em DEXs (Uniswap, SushiSwap) e executa transações antes (frontrun) e depois (backrun) para lucrar com o movimento de preço.

## 🏗️ Arquitetura

```
┌─────────────────────────────────────────────────────────┐
│                    MEV Sandwich Bot                      │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌─────────────┐      ┌──────────────┐                  │
│  │   Mempool   │─────▶│  Transaction │                  │
│  │   Monitor   │      │   Analyzer   │                  │
│  └─────────────┘      └──────┬───────┘                  │
│                              │                           │
│                              ▼                           │
│                      ┌──────────────┐                   │
│                      │ Profitability│                   │
│                      │  Calculator  │                   │
│                      └──────┬───────┘                   │
│                              │                           │
│                              ▼                           │
│  ┌─────────────┐      ┌──────────────┐                 │
│  │   Gas Price │◀─────│   Sandwich   │                 │
│  │   Manager   │      │   Executor   │                 │
│  └─────────────┘      └──────┬───────┘                 │
│                              │                           │
│                              ▼                           │
│                      ┌──────────────┐                   │
│                      │  Flashbots   │                   │
│                      │  Integration │                   │
│                      └──────────────┘                   │
└─────────────────────────────────────────────────────────┘
```

## 🚀 Funcionalidades

- ✅ Monitoramento em tempo real do mempool Ethereum
- ✅ Análise automática de transações DEX (Uniswap V2/V3)
- ✅ Cálculo de lucratividade considerando gas fees
- ✅ Execução atômica via smart contract
- ✅ Gestão dinâmica de gas price
- ✅ Integração com Flashbots para privacidade
- ✅ Sistema de logging e métricas
- ✅ Proteções contra MEV reverso

## 📦 Instalação

```bash
# Instalar dependências
npm install

# Copiar e configurar variáveis de ambiente
cp .env.example .env
# Edite o .env com suas credenciais

# Compilar contratos
npm run compile

# Compilar TypeScript
npm run build
```

## 🔧 Configuração

Edite o arquivo `.env`:

```env
# Configure seu RPC endpoint (Alchemy, Infura, ou nó próprio)
MAINNET_RPC_URL=https://eth-mainnet.g.alchemy.com/v2/YOUR_KEY
MAINNET_WSS_URL=wss://eth-mainnet.g.alchemy.com/v2/YOUR_KEY

# Chave privada (use wallet separada para testes!)
PRIVATE_KEY=your_key_here

# Parâmetros do bot
MIN_PROFIT_WEI=1000000000000000000  # Lucro mínimo: 1 ETH
MAX_GAS_PRICE_GWEI=300
```

## 🎯 Como Funciona

### 1. Detecção
O bot monitora transações pendentes no mempool e identifica swaps grandes em DEXs.

### 2. Análise
Para cada transação candidata:
- Decodifica os parâmetros do swap
- Calcula o impacto no preço do par
- Estima a lucratividade potencial

### 3. Execução
Se lucrativo:
1. **Frontrun**: Compra o token antes da vítima
2. **Vítima**: Transação original executa (aumenta preço)
3. **Backrun**: Vende o token com lucro

### 4. Submissão
Usa Flashbots para enviar o bundle de forma privada, evitando ser frontrunado.

## 📁 Estrutura do Projeto

```
MEV-Sandwich-Bot/
├── src/
│   ├── contracts/          # Smart contracts Solidity
│   │   ├── SandwichBot.sol
│   │   └── interfaces/
│   ├── bot/
│   │   ├── mempool/       # Monitor do mempool
│   │   ├── analyzer/      # Análise de transações
│   │   ├── calculator/    # Cálculo de lucratividade
│   │   └── executor/      # Execução de sandwiches
│   ├── utils/             # Utilitários
│   ├── types/             # Definições TypeScript
│   └── index.ts           # Entry point
├── test/                  # Testes
├── scripts/               # Scripts de deploy
└── hardhat.config.ts
```

## 🧪 Testes

```bash
# Rodar testes em fork local
npm test

# Testar em Sepolia testnet
NETWORK=sepolia npm run dev
```

## 🔐 Segurança

- **NUNCA** use sua wallet principal
- **SEMPRE** teste em testnet primeiro
- Configure `MIN_PROFIT_WEI` adequadamente
- Use limites de gas
- Implemente circuit breakers

## ⚖️ Considerações Éticas

MEV é uma área controversa:
- ✅ **Legítimo**: Arbitragem, liquidações, ordenação de transações
- ❌ **Questionável**: Sandwich attacks que prejudicam usuários
- ❌ **Ilegal**: Manipulação de mercado, insider trading

Este projeto é educacional para entender MEV, não para exploração predatória.

## 📚 Recursos

- [Flashbots Docs](https://docs.flashbots.net/)
- [MEV Explore](https://explore.flashbots.net/)
- [Uniswap V2 Docs](https://docs.uniswap.org/protocol/V2/introduction)
- [Uniswap V3 Docs](https://docs.uniswap.org/protocol/introduction)

## 📝 Licença

MIT - Uso educacional apenas

## ⚠️ Disclaimer

Este software é fornecido "como está". Os autores não se responsabilizam por perdas financeiras. Use por sua conta e risco.
