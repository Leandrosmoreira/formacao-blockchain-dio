# Exemplos de Uso

## 🎯 Exemplo 1: Executar Bot Básico

```bash
# 1. Configure o ambiente
cp .env.example .env
# Edite .env com suas credenciais

# 2. Instale dependências
npm install

# 3. Compile contratos
npm run compile

# 4. Deploy em testnet
npx hardhat run scripts/deploy.ts --network sepolia

# 5. Execute o bot
npm start
```

## 📊 Exemplo 2: Análise de Oportunidade

```typescript
import { TransactionAnalyzer } from './bot/analyzer';
import { ProfitabilityCalculator } from './bot/calculator';

// Inicializar
const analyzer = new TransactionAnalyzer(provider);
const calculator = new ProfitabilityCalculator(provider, minProfit);

// Analisar transação
const tx = await provider.getTransaction(txHash);
const analysis = await analyzer.analyze(tx);

if (analysis?.isCandidate) {
  const gasConfig = gasPriceManager.getGasConfig();
  const simulation = await calculator.calculate(analysis, gasConfig);

  if (simulation?.isProfitable) {
    console.log('Oportunidade lucrativa encontrada!');
    console.log(`Lucro esperado: ${weiToEther(simulation.netProfit)} ETH`);
  }
}
```

## 🔄 Exemplo 3: Simulação Manual

```typescript
import { getAmountOut, calculatePriceImpact } from './utils/helpers';

// Parâmetros do swap da vítima
const victimAmountIn = ethers.parseEther("10"); // 10 ETH
const reserve0 = ethers.parseEther("1000"); // 1000 ETH no pool
const reserve1 = ethers.parseEther("2000000"); // 2M USDC no pool
const fee = 30; // 0.3%

// Calcular output da vítima
const victimOutput = getAmountOut(victimAmountIn, reserve0, reserve1, fee);
console.log(`Vítima receberá: ${ethers.formatUnits(victimOutput, 6)} USDC`);

// Calcular impacto de preço
const impact = calculatePriceImpact(victimAmountIn, reserve0, reserve1, fee);
console.log(`Impacto de preço: ${impact.toFixed(2)}%`);

// Simular nosso frontrun
const frontrunAmount = ethers.parseEther("5"); // 5 ETH
const frontrunOutput = getAmountOut(frontrunAmount, reserve0, reserve1, fee);

// Novas reservas após frontrun
const newReserve0 = reserve0 + frontrunAmount;
const newReserve1 = reserve1 - frontrunOutput;

// Vítima executa no novo preço
const victimNewOutput = getAmountOut(victimAmountIn, newReserve0, newReserve1, fee);

// Backrun
const finalReserve0 = newReserve0 + victimAmountIn;
const finalReserve1 = newReserve1 - victimNewOutput;
const backrunOutput = getAmountOut(frontrunOutput, finalReserve1, finalReserve0, fee);

// Lucro
const profit = backrunOutput - frontrunAmount;
console.log(`Lucro bruto: ${weiToEther(profit)} ETH`);
```

## 🎨 Exemplo 4: Customizar Filtros

```typescript
// src/bot/mempool/MempoolMonitor.ts

// Adicionar mais DEXs
private readonly DEX_ROUTERS = [
  ADDRESSES.UNISWAP_V2_ROUTER.toLowerCase(),
  ADDRESSES.UNISWAP_V3_ROUTER.toLowerCase(),
  ADDRESSES.SUSHISWAP_ROUTER.toLowerCase(),
  "0x...".toLowerCase(), // Curve
  "0x...".toLowerCase(), // Balancer
];

// Filtrar por tamanho mínimo
private async handlePendingTransaction(txHash: string): Promise<void> {
  const tx = await this.provider.getTransaction(txHash);

  // Filtro customizado: apenas swaps > 5 ETH
  if (tx.value < ethers.parseEther("5")) {
    return;
  }

  // Resto do processamento...
}
```

## 🔐 Exemplo 5: Gerenciar Fundos do Contrato

```typescript
import { ethers } from "hardhat";

async function manageFunds() {
  const [owner] = await ethers.getSigners();
  const contractAddress = process.env.SANDWICH_CONTRACT_ADDRESS!;

  const abi = [
    "function emergencyWithdraw(address token, uint256 amount) external",
    "function getTokenBalance(address token) external view returns (uint256)",
    "function withdrawProfits(address token) external"
  ];

  const contract = new ethers.Contract(contractAddress, abi, owner);

  // Verificar saldo de WETH
  const weth = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2";
  const balance = await contract.getTokenBalance(weth);
  console.log(`WETH balance: ${ethers.formatEther(balance)} WETH`);

  // Retirar lucros
  if (balance > 0n) {
    const tx = await contract.withdrawProfits(weth);
    await tx.wait();
    console.log("Lucros retirados!");
  }

  // Emergency withdraw (se necessário)
  // await contract.emergencyWithdraw(weth, 0); // 0 = tudo
}

manageFunds();
```

## 📈 Exemplo 6: Monitorar Métricas

```typescript
// Criar dashboard simples
import express from 'express';

const app = express();
const bot = new MEVSandwichBot();

app.get('/metrics', (req, res) => {
  const metrics = bot.getMetrics();
  res.json({
    uptime: `${Math.floor(metrics.uptime / 60)}m`,
    analyzed: metrics.transactionsAnalyzed,
    opportunities: metrics.opportunitiesFound,
    executed: metrics.sandwichesExecuted,
    successRate: `${((metrics.successfulSandwiches / metrics.sandwichesExecuted) * 100).toFixed(1)}%`,
    totalProfit: ethers.formatEther(metrics.totalProfit),
    netProfit: ethers.formatEther(metrics.netProfit)
  });
});

app.listen(3000, () => {
  console.log('Metrics dashboard: http://localhost:3000/metrics');
});

bot.start();
```

## 🧪 Exemplo 7: Testar em Fork Local

```typescript
// hardhat.config.ts
export default {
  networks: {
    hardhat: {
      forking: {
        url: process.env.MAINNET_RPC_URL!,
        blockNumber: 18000000, // Block específico
      },
    },
  },
};

// test/sandwich.fork.test.ts
import { ethers } from "hardhat";

describe("Sandwich Attack Fork Test", function () {
  it("Should execute sandwich on forked mainnet", async function () {
    // Deploy contrato
    const SandwichBot = await ethers.getContractFactory("SandwichBot");
    const bot = await SandwichBot.deploy();

    // Impersonate whale account
    await ethers.provider.send("hardhat_impersonateAccount", [
      "0x..." // Whale address
    ]);

    const whale = await ethers.getSigner("0x...");

    // Transferir WETH para contrato
    const weth = await ethers.getContractAt("IERC20", WETH_ADDRESS);
    await weth.connect(whale).transfer(
      await bot.getAddress(),
      ethers.parseEther("100")
    );

    // Executar swap de teste
    // ... teste o sandwich
  });
});
```

## 🎯 Exemplo 8: Estratégia Customizada

```typescript
// Implementar estratégia diferente: JIT Liquidity

class JITLiquidityBot extends MEVSandwichBot {
  protected async handleDexTransaction(tx: any): Promise<void> {
    const analysis = await this.analyzer.analyze(tx);

    // Em vez de sandwich, adicionar liquidez just-in-time
    if (analysis?.priceImpact > 2) { // Grande impacto
      // 1. Adicionar liquidez antes do swap
      await this.addLiquidity(analysis.pairInfo);

      // 2. Aguardar swap da vítima
      // 3. Remover liquidez (com lucro das fees)
      await this.removeLiquidity(analysis.pairInfo);
    }
  }
}
```

## 🔍 Exemplo 9: Debug Mode

```typescript
// .env
LOG_LEVEL=debug

// Código
import logger from './utils/logger';

// Logs detalhados aparecem
logger.debug('Transaction details:', {
  hash: tx.hash,
  from: tx.from,
  to: tx.to,
  value: ethers.formatEther(tx.value),
  gasPrice: ethers.formatUnits(tx.gasPrice, 'gwei')
});
```

## 📊 Exemplo 10: Análise de Sensibilidade

```typescript
import { ProfitabilityCalculator } from './bot/calculator';

const calculator = new ProfitabilityCalculator(provider, minProfit);

// Analisar como lucro varia com quantidade
const sensitivity = calculator.analyzeSensitivity(
  analysis,
  gasConfig,
  10 // 10 steps
);

console.log('Análise de Sensibilidade:');
sensitivity.forEach((point, i) => {
  console.log(
    `${((i + 1) * 10)}% do victim amount: ` +
    `${weiToEther(point.amount)} ETH → ` +
    `Lucro: ${weiToEther(point.profit)} ETH`
  );
});

// Encontrar quantidade ótima
const optimal = sensitivity.reduce((max, point) =>
  point.profit > max.profit ? point : max
);

console.log(`\nQuantidade ótima: ${weiToEther(optimal.amount)} ETH`);
console.log(`Lucro máximo: ${weiToEther(optimal.profit)} ETH`);
```

---

## 💡 Dicas

1. **Sempre teste primeiro em fork local**
2. **Use testnet antes de mainnet**
3. **Comece com parâmetros conservadores**
4. **Monitore custos de gas**
5. **Mantenha logs para análise**
6. **Ajuste thresholds baseado em resultados**
7. **Estude oportunidades perdidas**
8. **Otimize iterativamente**

## ⚠️ Avisos

- Nunca use chave privada real em código
- Sempre valide inputs antes de executar
- Tenha circuit breakers para limitar perdas
- Monitore constantemente em produção
- Entenda 100% do código antes de usar capital real
