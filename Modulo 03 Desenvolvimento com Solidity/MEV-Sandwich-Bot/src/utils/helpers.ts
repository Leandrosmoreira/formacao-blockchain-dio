import { ethers } from "ethers";
import { BigNumberish } from "ethers";

/**
 * Converte Wei para Ether
 */
export function weiToEther(wei: bigint): string {
  return ethers.formatEther(wei);
}

/**
 * Converte Ether para Wei
 */
export function etherToWei(ether: string): bigint {
  return ethers.parseEther(ether);
}

/**
 * Converte Gwei para Wei
 */
export function gweiToWei(gwei: number): bigint {
  return ethers.parseUnits(gwei.toString(), "gwei");
}

/**
 * Converte Wei para Gwei
 */
export function weiToGwei(wei: bigint): number {
  return Number(ethers.formatUnits(wei, "gwei"));
}

/**
 * Calcula o impacto de preço de um swap
 * @param amountIn Quantidade de entrada
 * @param reserveIn Reserva do token de entrada
 * @param reserveOut Reserva do token de saída
 * @param fee Taxa do DEX em basis points
 */
export function calculatePriceImpact(
  amountIn: bigint,
  reserveIn: bigint,
  reserveOut: bigint,
  fee: number = 30
): number {
  if (reserveIn === 0n || reserveOut === 0n) return 0;

  const feeFactor = BigInt(10000 - fee);
  const amountInWithFee = amountIn * feeFactor;
  const numerator = amountInWithFee * reserveOut;
  const denominator = (reserveIn * 10000n) + amountInWithFee;
  const amountOut = numerator / denominator;

  const priceBeforeSwap = (reserveOut * ethers.parseEther("1")) / reserveIn;
  const newReserveIn = reserveIn + amountIn;
  const newReserveOut = reserveOut - amountOut;
  const priceAfterSwap = (newReserveOut * ethers.parseEther("1")) / newReserveIn;

  const impact = Number(
    ((priceAfterSwap - priceBeforeSwap) * 10000n) / priceBeforeSwap
  ) / 100;

  return Math.abs(impact);
}

/**
 * Calcula a quantidade de saída de um swap (fórmula x*y=k)
 */
export function getAmountOut(
  amountIn: bigint,
  reserveIn: bigint,
  reserveOut: bigint,
  fee: number = 30
): bigint {
  if (amountIn === 0n || reserveIn === 0n || reserveOut === 0n) return 0n;

  const feeFactor = BigInt(10000 - fee);
  const amountInWithFee = amountIn * feeFactor;
  const numerator = amountInWithFee * reserveOut;
  const denominator = (reserveIn * 10000n) + amountInWithFee;

  return numerator / denominator;
}

/**
 * Calcula a quantidade de entrada necessária para obter uma quantidade de saída
 */
export function getAmountIn(
  amountOut: bigint,
  reserveIn: bigint,
  reserveOut: bigint,
  fee: number = 30
): bigint {
  if (amountOut === 0n || reserveIn === 0n || reserveOut === 0n) return 0n;
  if (amountOut >= reserveOut) return 0n;

  const feeFactor = BigInt(10000 - fee);
  const numerator = reserveIn * amountOut * 10000n;
  const denominator = (reserveOut - amountOut) * feeFactor;

  return numerator / denominator + 1n;
}

/**
 * Calcula o optimal amount para maximizar lucro em um sandwich
 */
export function calculateOptimalSandwichAmount(
  victimAmountIn: bigint,
  reserveIn: bigint,
  reserveOut: bigint,
  fee: number = 30
): bigint {
  // Fórmula simplificada: aproximadamente 50% do victim amount
  // Para otimização real, seria necessário resolver equações quadráticas
  const optimalAmount = victimAmountIn / 2n;

  // Garantir que não seja muito grande para a liquidez
  const maxAmount = reserveIn / 10n; // Máximo 10% da reserva

  return optimalAmount < maxAmount ? optimalAmount : maxAmount;
}

/**
 * Verifica se um endereço é um contrato
 */
export async function isContract(
  provider: ethers.Provider,
  address: string
): Promise<boolean> {
  const code = await provider.getCode(address);
  return code !== "0x";
}

/**
 * Formata um endereço para exibição
 */
export function formatAddress(address: string): string {
  return `${address.slice(0, 6)}...${address.slice(-4)}`;
}

/**
 * Calcula deadline (timestamp futuro)
 */
export function getDeadline(secondsFromNow: number = 300): number {
  return Math.floor(Date.now() / 1000) + secondsFromNow;
}

/**
 * Sleep helper
 */
export function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Retry com backoff exponencial
 */
export async function retryWithBackoff<T>(
  fn: () => Promise<T>,
  maxRetries: number = 3,
  baseDelay: number = 1000
): Promise<T> {
  let lastError: Error;

  for (let i = 0; i < maxRetries; i++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error as Error;
      if (i < maxRetries - 1) {
        const delay = baseDelay * Math.pow(2, i);
        await sleep(delay);
      }
    }
  }

  throw lastError!;
}

/**
 * Valida se um endereço é válido
 */
export function isValidAddress(address: string): boolean {
  return ethers.isAddress(address);
}

/**
 * Calcula percentage
 */
export function percentage(part: bigint, total: bigint): number {
  if (total === 0n) return 0;
  return Number((part * 10000n) / total) / 100;
}
