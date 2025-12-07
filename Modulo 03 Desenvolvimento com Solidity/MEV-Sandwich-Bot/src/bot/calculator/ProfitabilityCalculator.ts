import { ethers } from "ethers";
import {
  TransactionAnalysis,
  SandwichSimulation,
  GasConfig,
} from "../../types";
import { DEFAULTS } from "../../utils/constants";
import {
  getAmountOut,
  calculateOptimalSandwichAmount,
  weiToEther,
} from "../../utils/helpers";
import logger from "../../utils/logger";

/**
 * Calculadora de lucratividade de sandwich attacks
 * Simula a execução e calcula lucros esperados
 */
export class ProfitabilityCalculator {
  constructor(
    private provider: ethers.Provider,
    private minProfitWei: bigint
  ) {}

  /**
   * Calcula a lucratividade de um potencial sandwich
   */
  public async calculate(
    analysis: TransactionAnalysis,
    gasConfig: GasConfig
  ): Promise<SandwichSimulation | null> {
    try {
      const { swapInfo, pairInfo } = analysis;

      // Calcular quantidade ótima para o frontrun
      const optimalAmount = calculateOptimalSandwichAmount(
        swapInfo.amountIn,
        pairInfo.reserve0,
        pairInfo.reserve1,
        pairInfo.fee
      );

      // Verificar se temos capital suficiente (safety check)
      const maxPosition = DEFAULTS.MAX_POSITION_SIZE_ETH;
      const maxPositionWei = ethers.parseEther(maxPosition.toString());

      if (optimalAmount > maxPositionWei) {
        logger.debug(
          `Optimal amount (${weiToEther(optimalAmount)} ETH) exceeds max position`
        );
        return null;
      }

      // Simular o sandwich
      const simulation = this.simulateSandwich(
        optimalAmount,
        swapInfo.amountIn,
        pairInfo.reserve0,
        pairInfo.reserve1,
        pairInfo.fee,
        analysis.transaction,
        gasConfig
      );

      // Verificar se atinge o lucro mínimo
      if (simulation.netProfit < this.minProfitWei) {
        logger.debug(
          `Net profit (${weiToEther(simulation.netProfit)} ETH) below minimum`
        );
        return null;
      }

      return simulation;
    } catch (error) {
      logger.error("Error calculating profitability:", error);
      return null;
    }
  }

  /**
   * Simula a execução de um sandwich attack
   */
  private simulateSandwich(
    frontrunAmount: bigint,
    victimAmount: bigint,
    reserve0: bigint,
    reserve1: bigint,
    fee: number,
    victimTx: any,
    gasConfig: GasConfig
  ): SandwichSimulation {
    // Estado inicial
    let currentReserve0 = reserve0;
    let currentReserve1 = reserve1;

    // 1. Frontrun: Comprar token
    const frontrunOutput = getAmountOut(
      frontrunAmount,
      currentReserve0,
      currentReserve1,
      fee
    );

    // Atualizar reservas após frontrun
    currentReserve0 = currentReserve0 + frontrunAmount;
    currentReserve1 = currentReserve1 - frontrunOutput;

    // Preço após frontrun (antes da vítima)
    const priceBeforeVictim = this.calculatePrice(
      currentReserve0,
      currentReserve1
    );

    // 2. Vítima: Executar swap da vítima
    const victimOutput = getAmountOut(
      victimAmount,
      currentReserve0,
      currentReserve1,
      fee
    );

    // Atualizar reservas após vítima
    currentReserve0 = currentReserve0 + victimAmount;
    currentReserve1 = currentReserve1 - victimOutput;

    // Preço após vítima
    const priceAfterVictim = this.calculatePrice(
      currentReserve0,
      currentReserve1
    );

    // 3. Backrun: Vender tokens adquiridos no frontrun
    const backrunOutput = getAmountOut(
      frontrunOutput,
      currentReserve1,
      currentReserve0,
      fee
    );

    // Calcular lucro bruto (backrun output - frontrun input)
    const grossProfit = backrunOutput > frontrunAmount
      ? backrunOutput - frontrunAmount
      : 0n;

    // Calcular custo de gas
    const gasCost = this.estimateGasCost(gasConfig);

    // Calcular lucro líquido
    const netProfit = grossProfit > gasCost ? grossProfit - gasCost : 0n;

    return {
      victimTx,
      frontrunAmount,
      backrunAmount: frontrunOutput,
      expectedProfit: grossProfit,
      gasCost,
      netProfit,
      isProfitable: netProfit > this.minProfitWei,
      priceBeforeVictim,
      priceAfterVictim,
    };
  }

  /**
   * Calcula preço do par (reserve1/reserve0)
   */
  private calculatePrice(reserve0: bigint, reserve1: bigint): bigint {
    if (reserve0 === 0n) return 0n;
    return (reserve1 * ethers.parseEther("1")) / reserve0;
  }

  /**
   * Estima custo total de gas para o sandwich
   * (frontrun + backrun)
   */
  private estimateGasCost(gasConfig: GasConfig): bigint {
    // Custo de gas por transação
    const gasPerTx = gasConfig.gasLimit;

    // Total de gas para 2 transações (frontrun + backrun)
    const totalGas = gasPerTx * 2n;

    // Custo em wei
    const gasCost = totalGas * gasConfig.maxFeePerGas;

    return gasCost;
  }

  /**
   * Calcula o máximo que podemos gastar em gas mantendo lucratividade
   */
  public calculateMaxGasPrice(
    expectedProfit: bigint,
    gasLimit: bigint
  ): bigint {
    // Queremos manter pelo menos o lucro mínimo
    const maxGasCost = expectedProfit - this.minProfitWei;

    if (maxGasCost <= 0n) return 0n;

    // Dividir por gas total (2 transações)
    const totalGas = gasLimit * 2n;
    const maxGasPrice = maxGasCost / totalGas;

    return maxGasPrice;
  }

  /**
   * Análise de sensibilidade: como o lucro varia com diferentes quantidades
   */
  public analyzeSensitivity(
    analysis: TransactionAnalysis,
    gasConfig: GasConfig,
    steps: number = 10
  ): Array<{ amount: bigint; profit: bigint }> {
    const { swapInfo, pairInfo } = analysis;
    const results: Array<{ amount: bigint; profit: bigint }> = [];

    // Testar diferentes frações do victim amount
    for (let i = 1; i <= steps; i++) {
      const fraction = i / steps;
      const amount = (swapInfo.amountIn * BigInt(Math.floor(fraction * 100))) / 100n;

      const simulation = this.simulateSandwich(
        amount,
        swapInfo.amountIn,
        pairInfo.reserve0,
        pairInfo.reserve1,
        pairInfo.fee,
        analysis.transaction,
        gasConfig
      );

      results.push({
        amount,
        profit: simulation.netProfit,
      });
    }

    return results;
  }

  /**
   * Retorna estatísticas de uma simulação
   */
  public getSimulationStats(simulation: SandwichSimulation): {
    frontrunEth: string;
    profitEth: string;
    gasCostEth: string;
    netProfitEth: string;
    roi: number;
  } {
    const frontrunEth = weiToEther(simulation.frontrunAmount);
    const profitEth = weiToEther(simulation.expectedProfit);
    const gasCostEth = weiToEther(simulation.gasCost);
    const netProfitEth = weiToEther(simulation.netProfit);

    const roi = simulation.frontrunAmount > 0n
      ? Number((simulation.netProfit * 10000n) / simulation.frontrunAmount) / 100
      : 0;

    return {
      frontrunEth,
      profitEth,
      gasCostEth,
      netProfitEth,
      roi,
    };
  }
}
