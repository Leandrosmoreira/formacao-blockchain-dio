import { ethers } from "ethers";
import { FlashbotsBundleProvider } from "@flashbots/ethers-provider-bundle";
import { SandwichSimulation, FlashbotsBundle, SandwichResult } from "../../types";
import { ADDRESSES, DEFAULTS } from "../../utils/constants";
import { getDeadline } from "../../utils/helpers";
import logger, { executionLogger } from "../../utils/logger";

/**
 * Executor de sandwich attacks
 * Responsável por criar e enviar bundles de transações
 */
export class SandwichExecutor {
  private sandwichContract: ethers.Contract;
  private flashbotsProvider?: FlashbotsBundleProvider;

  constructor(
    private wallet: ethers.Wallet,
    private provider: ethers.Provider,
    private contractAddress: string
  ) {
    // ABI do contrato (simplificado para as funções que usamos)
    const abi = [
      "function executeFrontrun(address router, address tokenIn, address tokenOut, uint256 amount, uint256 minAmountOut, uint256 deadline) external returns (uint256)",
      "function executeBackrun(address router, address tokenIn, address tokenOut, uint256 amount, uint256 minAmountOut, uint256 deadline) external returns (uint256)",
      "function getTokenBalance(address token) external view returns (uint256)",
    ];

    this.sandwichContract = new ethers.Contract(
      contractAddress,
      abi,
      wallet
    );
  }

  /**
   * Inicializa o provider Flashbots
   */
  public async initializeFlashbots(
    flashbotsRelayUrl: string,
    authKey?: string
  ): Promise<void> {
    try {
      const authSigner = authKey
        ? new ethers.Wallet(authKey)
        : ethers.Wallet.createRandom();

      this.flashbotsProvider = await FlashbotsBundleProvider.create(
        this.provider,
        authSigner,
        flashbotsRelayUrl
      );

      logger.info("Flashbots provider initialized");
    } catch (error) {
      logger.error("Failed to initialize Flashbots:", error);
      throw error;
    }
  }

  /**
   * Executa um sandwich attack usando Flashbots
   */
  public async executeSandwich(
    simulation: SandwichSimulation,
    gasPrice: bigint
  ): Promise<SandwichResult> {
    if (!this.flashbotsProvider) {
      return {
        success: false,
        error: "Flashbots provider not initialized",
      };
    }

    try {
      const { swapInfo } = simulation.victimTx;
      const targetBlock = (await this.provider.getBlockNumber()) + 1;

      // Criar transações do bundle
      const bundle = await this.createBundle(
        simulation,
        gasPrice,
        targetBlock
      );

      // Simular bundle localmente primeiro
      const simulation_result = await this.flashbotsProvider.simulate(
        bundle.signedTransactions,
        targetBlock
      );

      if ("error" in simulation_result) {
        logger.error("Bundle simulation failed:", simulation_result.error);
        return {
          success: false,
          error: `Simulation failed: ${simulation_result.error.message}`,
        };
      }

      logger.info("Bundle simulation successful:", {
        coinbaseDiff: simulation_result.coinbaseDiff.toString(),
        gasFees: simulation_result.gasFees.toString(),
        results: simulation_result.results,
      });

      // Enviar bundle
      const bundleSubmission = await this.flashbotsProvider.sendRawBundle(
        bundle.signedTransactions,
        targetBlock
      );

      logger.info(`Bundle submitted for block ${targetBlock}`);

      // Aguardar resultado
      const waitResponse = await bundleSubmission.wait();

      if (waitResponse === 0) {
        // Bundle incluído!
        executionLogger.info("Sandwich executed successfully!", {
          targetBlock,
          simulation: simulation,
        });

        return {
          success: true,
          bundleHash: bundleSubmission.bundleHash,
          blockNumber: targetBlock,
          actualProfit: simulation.netProfit, // TODO: calcular profit real da chain
        };
      } else {
        // Bundle não incluído
        const reason =
          waitResponse === 1
            ? "Block passed without inclusion"
            : "Unknown error";

        logger.warn(`Bundle not included: ${reason}`);

        return {
          success: false,
          error: reason,
        };
      }
    } catch (error) {
      logger.error("Error executing sandwich:", error);
      executionLogger.error("Sandwich execution failed", {
        error: (error as Error).message,
        simulation,
      });

      return {
        success: false,
        error: (error as Error).message,
      };
    }
  }

  /**
   * Cria bundle de transações Flashbots
   */
  private async createBundle(
    simulation: SandwichSimulation,
    gasPrice: bigint,
    targetBlock: number
  ): Promise<FlashbotsBundle> {
    const deadline = getDeadline(DEFAULTS.DEADLINE_SECONDS);
    const { swapInfo } = simulation.victimTx;

    // Determinar tokens e quantidades
    const tokenIn = swapInfo.path[0];
    const tokenOut = swapInfo.path[1];
    const router = swapInfo.router;

    // 1. Frontrun transaction
    const frontrunTx = await this.sandwichContract.executeFrontrun.populateTransaction(
      router,
      tokenIn,
      tokenOut,
      simulation.frontrunAmount,
      0, // minAmountOut - calculado off-chain
      deadline,
      {
        gasLimit: DEFAULTS.GAS_LIMIT_SANDWICH,
        gasPrice: gasPrice,
      }
    );

    const signedFrontrun = await this.wallet.signTransaction(frontrunTx);

    // 2. Victim transaction (já assinada e pendente no mempool)
    // Não incluímos no bundle, ela já está lá

    // 3. Backrun transaction
    const backrunTx = await this.sandwichContract.executeBackrun.populateTransaction(
      router,
      tokenOut,
      tokenIn,
      simulation.backrunAmount,
      simulation.frontrunAmount, // Mínimo: recuperar o que gastamos
      deadline,
      {
        gasLimit: DEFAULTS.GAS_LIMIT_SANDWICH,
        gasPrice: gasPrice,
      }
    );

    const signedBackrun = await this.wallet.signTransaction(backrunTx);

    return {
      signedTransactions: [signedFrontrun, signedBackrun],
      targetBlock,
    };
  }

  /**
   * Verifica se o contrato tem saldo suficiente
   */
  public async hassufficientBalance(
    token: string,
    amount: bigint
  ): Promise<boolean> {
    try {
      const balance = await this.sandwichContract.getTokenBalance(token);
      return balance >= amount;
    } catch (error) {
      logger.error("Error checking balance:", error);
      return false;
    }
  }

  /**
   * Retorna estatísticas do executor
   */
  public getStats(): {
    contractAddress: string;
    walletAddress: string;
    flashbotsEnabled: boolean;
  } {
    return {
      contractAddress: this.contractAddress,
      walletAddress: this.wallet.address,
      flashbotsEnabled: !!this.flashbotsProvider,
    };
  }
}
