import { ethers } from "ethers";
import { GasConfig } from "../../types";
import { DEFAULTS, TIMINGS } from "../../utils/constants";
import { gweiToWei, weiToGwei } from "../../utils/helpers";
import logger from "../../utils/logger";

/**
 * Gerenciador de preços de gas
 * Monitora e ajusta preços dinamicamente
 */
export class GasPriceManager {
  private currentBaseFee: bigint = 0n;
  private currentPriorityFee: bigint = 0n;
  private gasHistory: Array<{ timestamp: number; baseFee: bigint; priorityFee: bigint }> = [];
  private updateInterval?: NodeJS.Timeout;
  private isMonitoring: boolean = false;

  constructor(
    private provider: ethers.Provider,
    private maxGasPriceGwei: number = DEFAULTS.MAX_GAS_PRICE_GWEI
  ) {}

  /**
   * Inicia o monitoramento de preços de gas
   */
  public async start(): Promise<void> {
    if (this.isMonitoring) {
      logger.warn("Gas price manager already running");
      return;
    }

    logger.info("Starting gas price manager...");

    // Atualizar imediatamente
    await this.updateGasPrice();

    // Configurar atualizações periódicas
    this.updateInterval = setInterval(async () => {
      await this.updateGasPrice();
    }, TIMINGS.PRICE_UPDATE_INTERVAL);

    this.isMonitoring = true;
    logger.info("Gas price manager started");
  }

  /**
   * Para o monitoramento
   */
  public stop(): void {
    if (this.updateInterval) {
      clearInterval(this.updateInterval);
      this.updateInterval = undefined;
    }
    this.isMonitoring = false;
    logger.info("Gas price manager stopped");
  }

  /**
   * Atualiza os preços de gas da rede
   */
  private async updateGasPrice(): Promise<void> {
    try {
      const feeData = await this.provider.getFeeData();

      if (feeData.maxFeePerGas && feeData.maxPriorityFeePerGas) {
        // EIP-1559 network
        this.currentBaseFee = feeData.maxFeePerGas;
        this.currentPriorityFee = feeData.maxPriorityFeePerGas;
      } else if (feeData.gasPrice) {
        // Legacy network
        this.currentBaseFee = feeData.gasPrice;
        this.currentPriorityFee = 0n;
      }

      // Adicionar ao histórico
      this.gasHistory.push({
        timestamp: Date.now(),
        baseFee: this.currentBaseFee,
        priorityFee: this.currentPriorityFee,
      });

      // Manter apenas últimas 100 entradas
      if (this.gasHistory.length > 100) {
        this.gasHistory.shift();
      }

      logger.debug(
        `Gas updated - Base: ${weiToGwei(this.currentBaseFee)} gwei, Priority: ${weiToGwei(this.currentPriorityFee)} gwei`
      );
    } catch (error) {
      logger.error("Error updating gas price:", error);
    }
  }

  /**
   * Retorna configuração de gas para uma transação normal
   */
  public getGasConfig(): GasConfig {
    const maxFeePerGas = this.currentBaseFee + this.currentPriorityFee;

    // Aplicar limite máximo
    const maxGasWei = gweiToWei(this.maxGasPriceGwei);
    const cappedMaxFee = maxFeePerGas > maxGasWei ? maxGasWei : maxFeePerGas;

    return {
      maxFeePerGas: cappedMaxFee,
      maxPriorityFeePerGas: this.currentPriorityFee,
      gasLimit: BigInt(DEFAULTS.GAS_LIMIT_SANDWICH),
    };
  }

  /**
   * Retorna configuração de gas competitiva para frontrun
   * Adiciona premium ao priority fee para garantir inclusão antes da vítima
   */
  public getCompetitiveGasConfig(victimGasPrice: bigint): GasConfig {
    // Calcular priority fee competitivo
    // Adicionar 10% + 1 Gwei ao gas price da vítima
    const premiumGwei = gweiToWei(1);
    const competitiveFee = (victimGasPrice * 110n) / 100n + premiumGwei;

    // Aplicar limite máximo
    const maxGasWei = gweiToWei(this.maxGasPriceGwei);
    const cappedFee = competitiveFee > maxGasWei ? maxGasWei : competitiveFee;

    // Para frontrun, usar priority fee mais alto
    const priorityFee = (cappedFee * 20n) / 100n; // 20% do total como priority

    return {
      maxFeePerGas: cappedFee,
      maxPriorityFeePerGas: priorityFee,
      gasLimit: BigInt(DEFAULTS.GAS_LIMIT_SANDWICH),
    };
  }

  /**
   * Calcula gas price para garantir inclusão antes de uma transação específica
   */
  public calculateFrontrunGasPrice(targetGasPrice: bigint, urgency: number = 1): bigint {
    // urgency: 1 = normal, 2 = high, 3 = critical
    const multiplier = 100n + BigInt(urgency * 10);
    const frontrunPrice = (targetGasPrice * multiplier) / 100n;

    // Adicionar buffer fixo
    const buffer = gweiToWei(1 * urgency);
    const finalPrice = frontrunPrice + buffer;

    // Aplicar limite máximo
    const maxGasWei = gweiToWei(this.maxGasPriceGwei);
    return finalPrice > maxGasWei ? maxGasWei : finalPrice;
  }

  /**
   * Retorna o preço médio de gas no período
   */
  public getAverageGasPrice(periodMinutes: number = 5): bigint {
    const cutoffTime = Date.now() - periodMinutes * 60 * 1000;
    const recentEntries = this.gasHistory.filter(
      (entry) => entry.timestamp >= cutoffTime
    );

    if (recentEntries.length === 0) {
      return this.currentBaseFee;
    }

    const sum = recentEntries.reduce(
      (acc, entry) => acc + entry.baseFee + entry.priorityFee,
      0n
    );

    return sum / BigInt(recentEntries.length);
  }

  /**
   * Retorna percentil de gas price
   */
  public getGasPricePercentile(percentile: number): bigint {
    if (this.gasHistory.length === 0) {
      return this.currentBaseFee;
    }

    const sorted = [...this.gasHistory]
      .map((entry) => entry.baseFee + entry.priorityFee)
      .sort((a, b) => (a < b ? -1 : 1));

    const index = Math.floor((sorted.length * percentile) / 100);
    return sorted[Math.min(index, sorted.length - 1)];
  }

  /**
   * Verifica se o preço de gas está dentro do limite aceitável
   */
  public isGasPriceAcceptable(gasPrice: bigint): boolean {
    const maxGasWei = gweiToWei(this.maxGasPriceGwei);
    return gasPrice <= maxGasWei;
  }

  /**
   * Estima se vale a pena pagar o gas para um dado lucro esperado
   */
  public isGasProfitable(
    expectedProfit: bigint,
    gasConfig: GasConfig
  ): boolean {
    // Calcular custo total de gas (2 transações: frontrun + backrun)
    const totalGas = gasConfig.gasLimit * 2n;
    const gasCost = totalGas * gasConfig.maxFeePerGas;

    // Verificar se o lucro é maior que o custo de gas + margem mínima
    const minProfit = DEFAULTS.MIN_PROFIT_WEI;
    const totalCost = gasCost + minProfit;

    return expectedProfit > totalCost;
  }

  /**
   * Retorna estatísticas do gerenciador
   */
  public getStats(): {
    isMonitoring: boolean;
    currentBaseFeeGwei: number;
    currentPriorityFeeGwei: number;
    averageGasPriceGwei: number;
    historySize: number;
  } {
    return {
      isMonitoring: this.isMonitoring,
      currentBaseFeeGwei: weiToGwei(this.currentBaseFee),
      currentPriorityFeeGwei: weiToGwei(this.currentPriorityFee),
      averageGasPriceGwei: weiToGwei(this.getAverageGasPrice()),
      historySize: this.gasHistory.length,
    };
  }

  /**
   * Retorna o gas price atual total
   */
  public getCurrentGasPrice(): bigint {
    return this.currentBaseFee + this.currentPriorityFee;
  }
}
