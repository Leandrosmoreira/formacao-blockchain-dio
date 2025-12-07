import { BigNumberish } from "ethers";

/**
 * Configuração do bot
 */
export interface BotConfig {
  rpcUrl: string;
  wssUrl: string;
  privateKey: string;
  flashbotsRelayUrl: string;
  minProfitWei: bigint;
  maxGasPriceGwei: number;
  slippageTolerance: number;
  network: string;
}

/**
 * Transação pendente do mempool
 */
export interface PendingTransaction {
  hash: string;
  from: string;
  to: string;
  value: bigint;
  gasPrice: bigint;
  gasLimit: bigint;
  data: string;
  nonce: number;
  timestamp: number;
}

/**
 * Informações de um swap DEX
 */
export interface SwapInfo {
  dex: DEX;
  router: string;
  path: string[];
  amountIn: bigint;
  amountOutMin: bigint;
  deadline: number;
  recipient: string;
  slippage: number;
}

/**
 * DEXs suportados
 */
export enum DEX {
  UNISWAP_V2 = "UniswapV2",
  UNISWAP_V3 = "UniswapV3",
  SUSHISWAP = "SushiSwap",
}

/**
 * Informações de um par de liquidez
 */
export interface PairInfo {
  address: string;
  token0: string;
  token1: string;
  reserve0: bigint;
  reserve1: bigint;
  fee: number;
}

/**
 * Resultado da análise de uma transação
 */
export interface TransactionAnalysis {
  transaction: PendingTransaction;
  swapInfo: SwapInfo;
  pairInfo: PairInfo;
  priceImpact: number;
  isCandidate: boolean;
}

/**
 * Simulação de sandwich attack
 */
export interface SandwichSimulation {
  victimTx: PendingTransaction;
  frontrunAmount: bigint;
  backrunAmount: bigint;
  expectedProfit: bigint;
  gasCost: bigint;
  netProfit: bigint;
  isProfitable: boolean;
  priceBeforeVictim: bigint;
  priceAfterVictim: bigint;
}

/**
 * Bundle de transações para Flashbots
 */
export interface FlashbotsBundle {
  signedTransactions: string[];
  targetBlock: number;
  minTimestamp?: number;
  maxTimestamp?: number;
}

/**
 * Resultado da execução de um sandwich
 */
export interface SandwichResult {
  success: boolean;
  bundleHash?: string;
  actualProfit?: bigint;
  gasCost?: bigint;
  error?: string;
  blockNumber?: number;
}

/**
 * Métricas do bot
 */
export interface BotMetrics {
  transactionsAnalyzed: number;
  opportunitiesFound: number;
  sandwichesExecuted: number;
  successfulSandwiches: number;
  failedSandwiches: number;
  totalProfit: bigint;
  totalGasCost: bigint;
  netProfit: bigint;
  uptime: number;
}

/**
 * Informações de token
 */
export interface TokenInfo {
  address: string;
  symbol: string;
  decimals: number;
  name: string;
}

/**
 * Preço de um par
 */
export interface PairPrice {
  token0: string;
  token1: string;
  price: bigint;
  timestamp: number;
}

/**
 * Configuração de gas
 */
export interface GasConfig {
  maxFeePerGas: bigint;
  maxPriorityFeePerGas: bigint;
  gasLimit: bigint;
}

/**
 * Estado do mempool
 */
export interface MempoolState {
  pendingTransactions: Map<string, PendingTransaction>;
  lastUpdate: number;
}

/**
 * Evento de oportunidade encontrada
 */
export interface OpportunityEvent {
  timestamp: number;
  simulation: SandwichSimulation;
  willExecute: boolean;
  reason?: string;
}
