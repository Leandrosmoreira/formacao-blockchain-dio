# Arquitetura do MEV Sandwich Bot

## 📐 Visão Geral

O MEV Sandwich Bot é composto por múltiplos módulos especializados que trabalham juntos para detectar, analisar e executar oportunidades de MEV na rede Ethereum.

## 🏗️ Componentes Principais

### 1. **Mempool Monitor** (`src/bot/mempool/`)

**Responsabilidade:** Monitorar transações pendentes no mempool

**Tecnologias:**
- WebSocket connection para real-time updates
- EventEmitter para comunicação assíncrona

**Fluxo:**
```
WebSocket → Filtrar DEX txs → Emitir evento → Analyzer
```

**Características:**
- Reconexão automática
- Filtro por endereços de routers DEX
- Deduplicação de transações
- Rate limiting integrado

### 2. **Transaction Analyzer** (`src/bot/analyzer/`)

**Responsabilidade:** Decodificar e analisar transações DEX

**Processo:**
1. Decodifica dados da transação usando ABIs
2. Extrai informações de swap (tokens, quantidades, path)
3. Busca informações do par de liquidez
4. Calcula impacto de preço
5. Determina se é candidata para sandwich

**Suporte:**
- ✅ Uniswap V2
- ✅ SushiSwap
- ⚠️ Uniswap V3 (parcial)

### 3. **Profitability Calculator** (`src/bot/calculator/`)

**Responsabilidade:** Calcular lucratividade de sandwiches

**Algoritmo:**
```typescript
1. Calcular quantidade ótima de frontrun
2. Simular frontrun (calcular output)
3. Simular swap da vítima (atualizar reservas)
4. Simular backrun (calcular lucro)
5. Subtrair custos de gas
6. Verificar se > lucro mínimo
```

**Fórmulas Usadas:**
- **Constant Product Formula:** `x * y = k`
- **AmountOut:** `(amountIn * (1 - fee) * reserveOut) / (reserveIn + amountIn * (1 - fee))`
- **Price Impact:** `|priceAfter - priceBefore| / priceBefore * 100`

### 4. **Gas Price Manager** (`src/bot/gas/`)

**Responsabilidade:** Gerenciar preços de gas dinamicamente

**Funcionalidades:**
- Monitoramento contínuo de gas prices
- Histórico de preços (últimos 100 pontos)
- Cálculo de percentis
- Estratégia de bidding competitiva

**Estratégia de Frontrun:**
```
Competitive Gas = VictimGas * 1.10 + 1 gwei
Priority Fee = CompetitiveGas * 0.20
```

### 5. **Sandwich Executor** (`src/bot/executor/`)

**Responsabilidade:** Executar sandwiches via Flashbots

**Processo:**
1. Criar bundle de transações:
   - Frontrun (nossa tx antes)
   - Victim (tx original, já no mempool)
   - Backrun (nossa tx depois)
2. Simular bundle localmente
3. Submeter para Flashbots relay
4. Aguardar inclusão no bloco

**Vantagens Flashbots:**
- ✅ Privacidade (não expõe no mempool público)
- ✅ Sem falhas on-chain (só incluído se executado)
- ✅ MEV-share (parte do lucro vai para validadores)

### 6. **Smart Contract** (`src/contracts/`)

**SandwichBot.sol** - Contrato executor

**Funções Principais:**
```solidity
executeFrontrun()  // Compra tokens
executeBackrun()   // Vende tokens
emergencyWithdraw() // Recupera fundos
```

**Segurança:**
- Owner-only access control
- Deadline checks
- Slippage protection
- Emergency withdraw

## 🔄 Fluxo de Execução Completo

```
┌─────────────────┐
│  Mempool (WSS)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Filter DEX Txs  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     NO
│   Analyze Tx    ├────────→ [Discard]
└────────┬────────┘
         │ YES
         ▼
┌─────────────────┐     NO
│ Calculate Profit├────────→ [Log Opportunity]
└────────┬────────┘
         │ Profitable
         ▼
┌─────────────────┐
│  Get Gas Price  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Create Bundle  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     FAIL
│ Simulate Bundle ├────────→ [Log Error]
└────────┬────────┘
         │ SUCCESS
         ▼
┌─────────────────┐
│ Submit Flashbots│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Wait Response  │
└────────┬────────┘
         │
    ┌────┴─────┐
    │          │
INCLUDED    NOT INCLUDED
    │          │
    ▼          ▼
  [Profit]  [Retry/Log]
```

## 📊 Estrutura de Dados

### PendingTransaction
```typescript
{
  hash: string
  from: string
  to: string
  value: bigint
  gasPrice: bigint
  data: string
  ...
}
```

### TransactionAnalysis
```typescript
{
  transaction: PendingTransaction
  swapInfo: SwapInfo
  pairInfo: PairInfo
  priceImpact: number
  isCandidate: boolean
}
```

### SandwichSimulation
```typescript
{
  victimTx: PendingTransaction
  frontrunAmount: bigint
  backrunAmount: bigint
  expectedProfit: bigint
  gasCost: bigint
  netProfit: bigint
  isProfitable: boolean
}
```

## 🔐 Segurança

### 1. **Chaves Privadas**
- Armazenadas em `.env` (nunca commitadas)
- Validação de formato no startup
- Wallet separada recomendada

### 2. **Smart Contract**
- Owner-only modifiers
- Emergency withdraw function
- Reentrancy protection (implícita via CEI pattern)

### 3. **Validações**
- Gas price máximo
- Lucro mínimo
- Balance checks
- Deadline validation

### 4. **Monitoramento**
- Logs estruturados (Winston)
- Métricas em tempo real
- Alertas de erro

## ⚡ Otimizações

### 1. **Performance**
- WebSocket para baixa latência
- Caching de pares de liquidez
- Deduplicação de transações
- Paralelização de análises

### 2. **Custo**
- Flashbots (sem gas em falhas)
- Gas price otimizado
- Threshold de lucro mínimo

### 3. **Competitividade**
- Monitoramento real-time
- Gas bidding estratégico
- Bundle simulation antes de submit

## 📈 Métricas Coletadas

```typescript
{
  transactionsAnalyzed: number
  opportunitiesFound: number
  sandwichesExecuted: number
  successfulSandwiches: number
  failedSandwiches: number
  totalProfit: bigint
  totalGasCost: bigint
  netProfit: bigint
  uptime: number
}
```

## 🔮 Melhorias Futuras

### Curto Prazo
- [ ] Suporte completo para Uniswap V3
- [ ] Multi-DEX arbitrage
- [ ] Better optimal amount calculation
- [ ] Database para histórico

### Médio Prazo
- [ ] Machine Learning para predição
- [ ] Multi-hop path optimization
- [ ] Cross-DEX sandwiches
- [ ] Dashboard web

### Longo Prazo
- [ ] Suporte para L2s (Arbitrum, Optimism)
- [ ] MEV auction participation
- [ ] Builder integration
- [ ] Advanced strategies (JIT liquidity, etc)

## 🧪 Testes

### Níveis de Teste

1. **Unit Tests**
   - Testa funções individuais
   - Mock de dependências externas

2. **Integration Tests**
   - Testa interação entre módulos
   - Fork de mainnet

3. **E2E Tests**
   - Testa fluxo completo
   - Testnet deployment

### Executar Testes

```bash
# Unit tests
npm test

# Com coverage
npm run test:coverage

# Fork tests
npx hardhat test --network hardhat
```

## 📚 Dependências Chave

- **ethers.js** - Interação com Ethereum
- **@flashbots/ethers-provider-bundle** - Flashbots
- **winston** - Logging
- **hardhat** - Development environment
- **typescript** - Type safety

## 🎯 Considerações de Produção

### Antes de usar em Mainnet:

1. ✅ Testes extensivos em testnet
2. ✅ Capital suficiente (>100 ETH recomendado)
3. ✅ Infraestrutura própria (nó dedicado)
4. ✅ Monitoramento 24/7
5. ✅ Circuit breakers implementados
6. ✅ Entendimento completo de riscos
7. ✅ Conformidade legal verificada

### Riscos:

- 💸 Perda de capital
- ⚡ Competição com bots profissionais
- 🐛 Bugs podem causar perdas
- ⚖️ Questões éticas/legais
- 📉 Mudanças no protocolo

---

**Nota:** Esta arquitetura é educacional e pode não ser competitiva contra bots profissionais de MEV em produção.
