import { ethers } from "ethers";
import {
  PendingTransaction,
  SwapInfo,
  PairInfo,
  TransactionAnalysis,
  DEX,
} from "../../types";
import { ADDRESSES, ABIS, THRESHOLDS, DEX_FEES } from "../../utils/constants";
import { calculatePriceImpact, weiToEther } from "../../utils/helpers";
import logger from "../../utils/logger";

/**
 * Analisador de transações DEX
 * Decodifica e analisa transações de swap
 */
export class TransactionAnalyzer {
  private uniswapV2Router: ethers.Interface;
  private uniswapV2Factory: ethers.Contract;
  private uniswapV2Pair: ethers.Interface;

  constructor(private provider: ethers.Provider) {
    // Inicializar interfaces para decodificação
    this.uniswapV2Router = new ethers.Interface(ABIS.UNISWAP_V2_ROUTER);
    this.uniswapV2Pair = new ethers.Interface(ABIS.UNISWAP_V2_PAIR);

    // Contract da factory para buscar pares
    this.uniswapV2Factory = new ethers.Contract(
      ADDRESSES.UNISWAP_V2_FACTORY,
      ABIS.UNISWAP_V2_FACTORY,
      provider
    );
  }

  /**
   * Analisa uma transação pendente
   */
  public async analyze(
    tx: PendingTransaction
  ): Promise<TransactionAnalysis | null> {
    try {
      // Decodificar dados da transação
      const swapInfo = this.decodeSwapData(tx);
      if (!swapInfo) {
        return null;
      }

      // Verificar se o swap é grande o suficiente
      if (!this.isSignificantSwap(swapInfo)) {
        return null;
      }

      // Buscar informações do par
      const pairInfo = await this.getPairInfo(swapInfo.path[0], swapInfo.path[1]);
      if (!pairInfo) {
        logger.debug(`Pair not found for path: ${swapInfo.path.join(" -> ")}`);
        return null;
      }

      // Calcular impacto de preço
      const priceImpact = calculatePriceImpact(
        swapInfo.amountIn,
        pairInfo.reserve0,
        pairInfo.reserve1,
        pairInfo.fee
      );

      // Determinar se é um candidato para sandwich
      const isCandidate = this.isSandwichCandidate(swapInfo, pairInfo, priceImpact);

      return {
        transaction: tx,
        swapInfo,
        pairInfo,
        priceImpact,
        isCandidate,
      };
    } catch (error) {
      logger.debug(`Error analyzing transaction ${tx.hash.slice(0, 10)}...`, error);
      return null;
    }
  }

  /**
   * Decodifica dados de swap da transação
   */
  private decodeSwapData(tx: PendingTransaction): SwapInfo | null {
    try {
      const decoded = this.uniswapV2Router.parseTransaction({
        data: tx.data,
        value: tx.value,
      });

      if (!decoded) return null;

      const functionName = decoded.name;

      // Suportar diferentes funções de swap
      switch (functionName) {
        case "swapExactTokensForTokens":
        case "swapExactETHForTokens":
        case "swapExactTokensForETH":
          return this.parseExactInputSwap(decoded, tx);

        case "swapTokensForExactTokens":
        case "swapETHForExactTokens":
        case "swapTokensForExactETH":
          return this.parseExactOutputSwap(decoded, tx);

        default:
          return null;
      }
    } catch (error) {
      return null;
    }
  }

  /**
   * Parse swap com input exato
   */
  private parseExactInputSwap(
    decoded: ethers.TransactionDescription,
    tx: PendingTransaction
  ): SwapInfo {
    const dex = this.identifyDex(tx.to);

    return {
      dex,
      router: tx.to,
      path: decoded.args[2] as string[], // path
      amountIn: BigInt(decoded.args[0].toString()), // amountIn
      amountOutMin: BigInt(decoded.args[1].toString()), // amountOutMin
      deadline: Number(decoded.args[4]), // deadline
      recipient: decoded.args[3] as string, // to
      slippage: this.calculateSlippage(
        BigInt(decoded.args[0].toString()),
        BigInt(decoded.args[1].toString())
      ),
    };
  }

  /**
   * Parse swap com output exato
   */
  private parseExactOutputSwap(
    decoded: ethers.TransactionDescription,
    tx: PendingTransaction
  ): SwapInfo {
    const dex = this.identifyDex(tx.to);

    return {
      dex,
      router: tx.to,
      path: decoded.args[2] as string[], // path
      amountIn: BigInt(decoded.args[1].toString()), // amountInMax
      amountOutMin: BigInt(decoded.args[0].toString()), // amountOut
      deadline: Number(decoded.args[4]), // deadline
      recipient: decoded.args[3] as string, // to
      slippage: this.calculateSlippage(
        BigInt(decoded.args[1].toString()),
        BigInt(decoded.args[0].toString())
      ),
    };
  }

  /**
   * Identifica qual DEX está sendo usado
   */
  private identifyDex(router: string): DEX {
    const routerLower = router.toLowerCase();

    if (routerLower === ADDRESSES.UNISWAP_V2_ROUTER.toLowerCase()) {
      return DEX.UNISWAP_V2;
    } else if (routerLower === ADDRESSES.UNISWAP_V3_ROUTER.toLowerCase()) {
      return DEX.UNISWAP_V3;
    } else if (routerLower === ADDRESSES.SUSHISWAP_ROUTER.toLowerCase()) {
      return DEX.SUSHISWAP;
    }

    return DEX.UNISWAP_V2; // default
  }

  /**
   * Busca informações do par de liquidez
   */
  private async getPairInfo(
    token0: string,
    token1: string
  ): Promise<PairInfo | null> {
    try {
      // Buscar endereço do par
      const pairAddress = await this.uniswapV2Factory.getPair(token0, token1);

      if (pairAddress === ethers.ZeroAddress) {
        return null;
      }

      // Criar contrato do par
      const pairContract = new ethers.Contract(
        pairAddress,
        ABIS.UNISWAP_V2_PAIR,
        this.provider
      );

      // Buscar reservas e tokens
      const [reserves, pairToken0, pairToken1] = await Promise.all([
        pairContract.getReserves(),
        pairContract.token0(),
        pairContract.token1(),
      ]);

      // Determinar ordem das reservas
      const [reserve0, reserve1] =
        token0.toLowerCase() === pairToken0.toLowerCase()
          ? [BigInt(reserves[0].toString()), BigInt(reserves[1].toString())]
          : [BigInt(reserves[1].toString()), BigInt(reserves[0].toString())];

      return {
        address: pairAddress,
        token0: pairToken0,
        token1: pairToken1,
        reserve0,
        reserve1,
        fee: DEX_FEES.UNISWAP_V2,
      };
    } catch (error) {
      logger.debug(`Error fetching pair info for ${token0}/${token1}`);
      return null;
    }
  }

  /**
   * Verifica se o swap é significativo
   */
  private isSignificantSwap(swapInfo: SwapInfo): boolean {
    // Verificar se envolve WETH
    const hasWETH = swapInfo.path.some(
      (token) => token.toLowerCase() === ADDRESSES.WETH.toLowerCase()
    );

    if (!hasWETH) {
      return false;
    }

    // Calcular tamanho aproximado em ETH
    const wethIndex = swapInfo.path.findIndex(
      (token) => token.toLowerCase() === ADDRESSES.WETH.toLowerCase()
    );

    const wethAmount = wethIndex === 0 ? swapInfo.amountIn : swapInfo.amountOutMin;
    const ethAmount = Number(weiToEther(wethAmount));

    // Verificar se atinge o threshold mínimo
    return ethAmount >= THRESHOLDS.MIN_SWAP_SIZE_ETH;
  }

  /**
   * Determina se a transação é candidata para sandwich
   */
  private isSandwichCandidate(
    swapInfo: SwapInfo,
    pairInfo: PairInfo,
    priceImpact: number
  ): boolean {
    // Verificar impacto de preço mínimo
    if (priceImpact < THRESHOLDS.MIN_PRICE_IMPACT) {
      return false;
    }

    // Verificar slippage máximo
    if (swapInfo.slippage > THRESHOLDS.MAX_SLIPPAGE) {
      return false;
    }

    // Verificar liquidez mínima
    const minReserve = pairInfo.reserve0 < pairInfo.reserve1
      ? pairInfo.reserve0
      : pairInfo.reserve1;

    if (minReserve === 0n) {
      return false;
    }

    return true;
  }

  /**
   * Calcula slippage tolerance
   */
  private calculateSlippage(amountIn: bigint, amountOut: bigint): number {
    if (amountOut === 0n) return 0;
    const slippage = Number(((amountIn - amountOut) * 10000n) / amountIn) / 100;
    return Math.abs(slippage);
  }
}
