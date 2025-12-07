# Tutorial: Como Usar o MEV Sandwich Bot

## ⚠️ AVISO IMPORTANTE

Este tutorial é **exclusivamente educacional**. O uso de MEV bots em produção:
- Envolve riscos financeiros significativos
- Requer capital substancial
- É extremamente competitivo
- Pode gerar questões éticas

**Use apenas em testnets para aprendizado!**

## 📚 Pré-requisitos

- Node.js 18+ instalado
- Conhecimento de Ethereum, Solidity e TypeScript
- Conta Alchemy ou Infura (para RPC)
- Wallet com ETH para gas (em testnet)
- Conhecimento de MEV e DEX

## 🚀 Passo 1: Instalação

```bash
# Clone o repositório
cd "Modulo 03 Desenvolvimento com Solidity/MEV-Sandwich-Bot"

# Instale dependências
npm install

# Copie arquivo de ambiente
cp .env.example .env
```

## 🔧 Passo 2: Configuração

Edite o arquivo `.env`:

```env
# Configure seu provedor RPC
MAINNET_RPC_URL=https://eth-sepolia.g.alchemy.com/v2/YOUR_KEY
MAINNET_WSS_URL=wss://eth-sepolia.g.alchemy.com/v2/YOUR_KEY

# Chave privada (crie uma wallet NOVA apenas para testes!)
PRIVATE_KEY=0x...

# Configurações do bot
MIN_PROFIT_WEI=100000000000000000  # 0.1 ETH
MAX_GAS_PRICE_GWEI=50
NETWORK=sepolia
FORKING=true
```

### ⚠️ Segurança da Chave Privada

**NUNCA:**
- Use sua wallet principal
- Commite o arquivo `.env`
- Compartilhe sua chave privada
- Use em mainnet sem entender os riscos

**SEMPRE:**
- Crie uma wallet separada para testes
- Use apenas testnets inicialmente
- Mantenha `.env` no `.gitignore`

## 📝 Passo 3: Deploy do Contrato

```bash
# Compile os contratos
npm run compile

# Deploy em Sepolia testnet
npx hardhat run scripts/deploy.ts --network sepolia
```

Você receberá um endereço de contrato. Copie-o!

```bash
# Adicione ao .env
echo "SANDWICH_CONTRACT_ADDRESS=0x..." >> .env
```

## 💰 Passo 4: Financiar o Contrato

O contrato precisa de tokens para executar swaps:

```bash
# 1. Obtenha ETH de testnet (faucet)
# Sepolia: https://sepoliafaucet.com/

# 2. Converta ETH em WETH (necessário para swaps)
# Use interface do WETH: https://sepolia.etherscan.io/

# 3. Transfira WETH para o contrato
# Envie pelo Metamask ou script
```

## 🧪 Passo 5: Testar em Fork Local

Antes de rodar em testnet real, teste em fork local:

```bash
# .env
FORKING=true
MAINNET_RPC_URL=https://eth-mainnet.g.alchemy.com/v2/YOUR_KEY

# Rodar bot em fork
npm run dev
```

O bot irá:
1. Conectar ao fork do mainnet
2. Monitorar mempool simulado
3. Detectar oportunidades
4. Simular execuções

## 🎯 Passo 6: Executar em Testnet

```bash
# .env
NETWORK=sepolia
FORKING=false

# Rodar bot
npm start
```

### O que esperar:

```
============================================================
Starting MEV Sandwich Bot...
============================================================
Bot wallet address: 0x...
All components initialized
Gas price manager started
Mempool monitor started successfully!
============================================================
Bot started successfully! Monitoring mempool...
============================================================
```

O bot agora está:
- ✅ Monitorando o mempool
- ✅ Analisando transações DEX
- ✅ Calculando lucratividade
- ✅ Aguardando oportunidades

## 📊 Passo 7: Monitorar Performance

Os logs são salvos em:
- `logs/combined.log` - Todos os logs
- `logs/error.log` - Apenas erros
- `logs/opportunities.log` - Oportunidades encontradas
- `logs/executions.log` - Execuções realizadas

```bash
# Monitorar logs em tempo real
tail -f logs/combined.log

# Ver oportunidades
tail -f logs/opportunities.log
```

### Métricas Exibidas

A cada 1 minuto, o bot mostra:
```
============================================================
BOT METRICS
------------------------------------------------------------
Uptime: 300s (5m)
Transactions Analyzed: 1234
Opportunities Found: 5
Sandwiches Executed: 2
  Successful: 1
  Failed: 1
Total Profit: 0.15 ETH
Total Gas Cost: 0.05 ETH
Net Profit: 0.10 ETH
============================================================
```

## 🔍 Passo 8: Analisar Resultados

### Quando uma oportunidade é encontrada:

```
🎯 PROFITABLE OPPORTUNITY FOUND!
  Frontrun: 5.5 ETH
  Expected Profit: 0.25 ETH
  Gas Cost: 0.05 ETH
  Net Profit: 0.20 ETH
  ROI: 3.64%
```

### Se executado com sucesso:

```
✅ Sandwich executed successfully!
  Block: 12345678
  Bundle Hash: 0x...
```

### Se falhar:

```
❌ Sandwich execution failed: Block passed without inclusion
```

## 🛠️ Troubleshooting

### "WebSocket closed"
- Verifique sua URL WSS
- Alchemy/Infura podem ter limites de taxa

### "Insufficient balance"
- Contrato precisa de mais WETH/tokens
- Transfira fundos para o contrato

### "Bundle simulation failed"
- Gas price muito baixo
- Oportunidade não mais lucrativa
- Ajuste MIN_PROFIT_WEI

### "No opportunities found"
- Normal em testnets (menos volume)
- Reduza MIN_PROFIT_WEI
- Reduza MIN_SWAP_SIZE_ETH

## 📈 Otimizações Avançadas

### 1. Ajustar Parâmetros

```env
# Mais sensível (encontra mais oportunidades)
MIN_PROFIT_WEI=10000000000000000    # 0.01 ETH
MIN_SWAP_SIZE_ETH=1                  # 1 ETH

# Mais conservador (menos oportunidades, maior lucro)
MIN_PROFIT_WEI=500000000000000000   # 0.5 ETH
MIN_SWAP_SIZE_ETH=50                 # 50 ETH
```

### 2. Usar Nó Próprio

Para melhor performance:
- Execute seu próprio nó Ethereum
- Reduz latência
- Sem limites de taxa

### 3. Adicionar Mais DEXs

Edite `src/utils/constants.ts` para adicionar:
- Curve
- Balancer
- 1inch

## 🎓 Próximos Passos

1. **Entenda o Código**
   - Leia cada módulo
   - Experimente modificar parâmetros
   - Adicione logs customizados

2. **Melhore a Estratégia**
   - Implemente cálculo de quantidade ótima real
   - Adicione suporte para multi-hop swaps
   - Considere arbitragem em vez de sandwich

3. **Estude MEV**
   - Leia Flashbots docs
   - Explore MEV-Boost
   - Entenda PBS (Proposer-Builder Separation)

## ⚖️ Considerações Éticas

MEV é controverso:

**Aceitável:**
- Arbitragem (melhora eficiência)
- Liquidações (protege protocolos)
- Educação e pesquisa

**Questionável:**
- Sandwich attacks (prejudica usuários)
- Frontrunning malicioso

**Ilegal:**
- Insider trading
- Manipulação de mercado

Use seu conhecimento de forma ética!

## 📚 Recursos Adicionais

- [Flashbots Docs](https://docs.flashbots.net/)
- [MEV Wiki](https://www.mev.wiki/)
- [Ethereum.org - MEV](https://ethereum.org/en/developers/docs/mev/)
- [Uniswap V2 Docs](https://docs.uniswap.org/protocol/V2/introduction)

## 🆘 Suporte

Problemas? Abra uma issue no repositório com:
- Logs relevantes
- Configuração (sem chaves privadas!)
- Descrição do problema

---

**Lembre-se:** Este projeto é educacional. Use com responsabilidade!
