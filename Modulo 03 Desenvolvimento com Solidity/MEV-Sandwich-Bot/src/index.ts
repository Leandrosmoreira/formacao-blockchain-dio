import { ethers } from "ethers";
import { MempoolMonitor } from "./bot/mempool";
import { TransactionAnalyzer } from "./bot/analyzer";
import { ProfitabilityCalculator } from "./bot/calculator";
import { SandwichExecutor } from "./bot/executor";
import { GasPriceManager } from "./bot/gas";
import { BotMetrics } from "./types";
import { loadConfig } from "./utils/config";
import { weiToEther } from "./utils/helpers";
import logger, { opportunityLogger } from "./utils/logger";
import { TIMINGS } from "./utils/constants";

/**
 * MEV Sandwich Bot Principal
 */
class MEVSandwichBot {
  private provider: ethers.JsonRpcProvider;
  private wsProvider: ethers.WebSocketProvider;
  private wallet: ethers.Wallet;

  private mempoolMonitor!: MempoolMonitor;
  private analyzer!: TransactionAnalyzer;
  private calculator!: ProfitabilityCalculator;
  private executor!: SandwichExecutor;
  private gasManager!: GasPriceManager;

  private metrics: BotMetrics = {
    transactionsAnalyzed: 0,
    opportunitiesFound: 0,
    sandwichesExecuted: 0,
    successfulSandwiches: 0,
    failedSandwiches: 0,
    totalProfit: 0n,
    totalGasCost: 0n,
    netProfit: 0n,
    uptime: 0,
  };

  private startTime: number = 0;
  private isRunning: boolean = false;
  private metricsInterval?: NodeJS.Timeout;

  constructor() {
    // Carregar configuração
    const config = loadConfig();

    // Inicializar providers
    this.provider = new ethers.JsonRpcProvider(config.rpcUrl);
    this.wsProvider = new ethers.WebSocketProvider(config.wssUrl);

    // Inicializar wallet
    this.wallet = new ethers.Wallet(config.privateKey, this.provider);

    logger.info(`Bot wallet address: ${this.wallet.address}`);

    // Inicializar componentes
    this.initializeComponents(config);
  }

  /**
   * Inicializa todos os componentes do bot
   */
  private initializeComponents(config: any): void {
    // Mempool monitor
    this.mempoolMonitor = new MempoolMonitor(config.wssUrl);

    // Transaction analyzer
    this.analyzer = new TransactionAnalyzer(this.provider);

    // Profitability calculator
    this.calculator = new ProfitabilityCalculator(
      this.provider,
      config.minProfitWei
    );

    // Gas price manager
    this.gasManager = new GasPriceManager(
      this.provider,
      config.maxGasPriceGwei
    );

    // TODO: Deploy contract first to get address
    // For now, using placeholder
    const contractAddress = process.env.SANDWICH_CONTRACT_ADDRESS || "";
    if (contractAddress) {
      this.executor = new SandwichExecutor(
        this.wallet,
        this.provider,
        contractAddress
      );
    }

    logger.info("All components initialized");
  }

  /**
   * Inicia o bot
   */
  public async start(): Promise<void> {
    if (this.isRunning) {
      logger.warn("Bot already running");
      return;
    }

    try {
      logger.info("=".repeat(60));
      logger.info("Starting MEV Sandwich Bot...");
      logger.info("=".repeat(60));

      this.startTime = Date.now();
      this.isRunning = true;

      // Iniciar gas manager
      await this.gasManager.start();

      // Configurar listeners do mempool monitor
      this.setupMempoolListeners();

      // Iniciar mempool monitor
      await this.mempoolMonitor.start();

      // Inicializar Flashbots se executor disponível
      if (this.executor) {
        const config = loadConfig();
        await this.executor.initializeFlashbots(
          config.flashbotsRelayUrl,
          process.env.FLASHBOTS_AUTH_KEY
        );
      }

      // Configurar logging periódico de métricas
      this.metricsInterval = setInterval(() => {
        this.logMetrics();
      }, TIMINGS.METRICS_LOG_INTERVAL);

      logger.info("=".repeat(60));
      logger.info("Bot started successfully! Monitoring mempool...");
      logger.info("=".repeat(60));

      // Manter processo rodando
      process.on("SIGINT", () => this.stop());
      process.on("SIGTERM", () => this.stop());
    } catch (error) {
      logger.error("Failed to start bot:", error);
      await this.stop();
      throw error;
    }
  }

  /**
   * Configura listeners do mempool
   */
  private setupMempoolListeners(): void {
    this.mempoolMonitor.on("dexTransaction", async (tx) => {
      await this.handleDexTransaction(tx);
    });

    this.mempoolMonitor.on("connected", () => {
      logger.info("Mempool monitor connected");
    });

    this.mempoolMonitor.on("disconnected", () => {
      logger.warn("Mempool monitor disconnected");
    });

    this.mempoolMonitor.on("error", (error) => {
      logger.error("Mempool monitor error:", error);
    });
  }

  /**
   * Processa uma transação DEX detectada
   */
  private async handleDexTransaction(tx: any): Promise<void> {
    try {
      this.metrics.transactionsAnalyzed++;

      // 1. Analisar transação
      const analysis = await this.analyzer.analyze(tx);
      if (!analysis || !analysis.isCandidate) {
        return;
      }

      logger.info(`Candidate found: ${tx.hash.slice(0, 10)}...
        Impact: ${analysis.priceImpact.toFixed(2)}%`);

      // 2. Calcular lucratividade
      const gasConfig = this.gasManager.getCompetitiveGasConfig(tx.gasPrice);
      const simulation = await this.calculator.calculate(analysis, gasConfig);

      if (!simulation || !simulation.isProfitable) {
        return;
      }

      this.metrics.opportunitiesFound++;

      const stats = this.calculator.getSimulationStats(simulation);
      logger.info(`🎯 PROFITABLE OPPORTUNITY FOUND!`);
      logger.info(`  Frontrun: ${stats.frontrunEth} ETH`);
      logger.info(`  Expected Profit: ${stats.profitEth} ETH`);
      logger.info(`  Gas Cost: ${stats.gasCostEth} ETH`);
      logger.info(`  Net Profit: ${stats.netProfitEth} ETH`);
      logger.info(`  ROI: ${stats.roi.toFixed(2)}%`);

      // Log oportunidade
      opportunityLogger.info("Opportunity found", {
        txHash: tx.hash,
        simulation: stats,
        analysis: {
          priceImpact: analysis.priceImpact,
          path: analysis.swapInfo.path,
        },
      });

      // 3. Executar se temos executor configurado
      if (this.executor) {
        await this.executeSandwich(simulation, gasConfig.maxFeePerGas);
      } else {
        logger.warn("Executor not configured - skipping execution");
      }
    } catch (error) {
      logger.error("Error handling DEX transaction:", error);
    }
  }

  /**
   * Executa o sandwich attack
   */
  private async executeSandwich(
    simulation: any,
    gasPrice: bigint
  ): Promise<void> {
    try {
      this.metrics.sandwichesExecuted++;

      logger.info("Executing sandwich attack...");

      const result = await this.executor.executeSandwich(simulation, gasPrice);

      if (result.success) {
        this.metrics.successfulSandwiches++;
        this.metrics.totalProfit += result.actualProfit || 0n;

        logger.info("✅ Sandwich executed successfully!");
        logger.info(`  Block: ${result.blockNumber}`);
        logger.info(`  Bundle Hash: ${result.bundleHash}`);
      } else {
        this.metrics.failedSandwiches++;
        logger.warn(`❌ Sandwich execution failed: ${result.error}`);
      }
    } catch (error) {
      this.metrics.failedSandwiches++;
      logger.error("Error executing sandwich:", error);
    }
  }

  /**
   * Loga métricas do bot
   */
  private logMetrics(): void {
    const uptime = Math.floor((Date.now() - this.startTime) / 1000);
    this.metrics.uptime = uptime;
    this.metrics.netProfit = this.metrics.totalProfit - this.metrics.totalGasCost;

    logger.info("=".repeat(60));
    logger.info("BOT METRICS");
    logger.info("-".repeat(60));
    logger.info(`Uptime: ${uptime}s (${Math.floor(uptime / 60)}m)`);
    logger.info(`Transactions Analyzed: ${this.metrics.transactionsAnalyzed}`);
    logger.info(`Opportunities Found: ${this.metrics.opportunitiesFound}`);
    logger.info(`Sandwiches Executed: ${this.metrics.sandwichesExecuted}`);
    logger.info(`  Successful: ${this.metrics.successfulSandwiches}`);
    logger.info(`  Failed: ${this.metrics.failedSandwiches}`);
    logger.info(`Total Profit: ${weiToEther(this.metrics.totalProfit)} ETH`);
    logger.info(`Total Gas Cost: ${weiToEther(this.metrics.totalGasCost)} ETH`);
    logger.info(`Net Profit: ${weiToEther(this.metrics.netProfit)} ETH`);
    logger.info("=".repeat(60));

    // Métricas dos componentes
    const mempoolStats = this.mempoolMonitor.getStats();
    const gasStats = this.gasManager.getStats();

    logger.info("Component Status:");
    logger.info(`  Mempool: ${mempoolStats.isMonitoring ? "✓" : "✗"}`);
    logger.info(`  Gas Manager: ${gasStats.isMonitoring ? "✓" : "✗"}`);
    logger.info(`  Current Gas: ${gasStats.currentBaseFeeGwei.toFixed(2)} gwei`);
    logger.info("=".repeat(60));
  }

  /**
   * Para o bot
   */
  public async stop(): Promise<void> {
    if (!this.isRunning) {
      return;
    }

    logger.info("Stopping MEV Sandwich Bot...");

    this.isRunning = false;

    // Parar componentes
    await this.mempoolMonitor.stop();
    this.gasManager.stop();

    if (this.metricsInterval) {
      clearInterval(this.metricsInterval);
    }

    // Log métricas finais
    this.logMetrics();

    logger.info("Bot stopped");
    process.exit(0);
  }

  /**
   * Retorna métricas atuais
   */
  public getMetrics(): BotMetrics {
    return { ...this.metrics };
  }
}

// Executar bot se arquivo for executado diretamente
if (require.main === module) {
  const bot = new MEVSandwichBot();
  bot.start().catch((error) => {
    logger.error("Fatal error:", error);
    process.exit(1);
  });
}

export default MEVSandwichBot;
