import { ethers } from "ethers";
import { EventEmitter } from "events";
import { PendingTransaction } from "../../types";
import { ADDRESSES, TIMINGS } from "../../utils/constants";
import logger from "../../utils/logger";

/**
 * Monitor do mempool Ethereum
 * Conecta via WebSocket e monitora transações pendentes
 */
export class MempoolMonitor extends EventEmitter {
  private provider: ethers.WebSocketProvider;
  private isMonitoring: boolean = false;
  private reconnectAttempts: number = 0;
  private maxReconnectAttempts: number = 5;
  private pendingTxHashes: Set<string> = new Set();

  // Endereços de routers DEX para filtrar
  private readonly DEX_ROUTERS = [
    ADDRESSES.UNISWAP_V2_ROUTER.toLowerCase(),
    ADDRESSES.UNISWAP_V3_ROUTER.toLowerCase(),
    ADDRESSES.SUSHISWAP_ROUTER.toLowerCase(),
  ];

  constructor(private wssUrl: string) {
    super();
    this.provider = new ethers.WebSocketProvider(wssUrl);
    this.setupEventListeners();
  }

  /**
   * Configura listeners do WebSocket
   */
  private setupEventListeners(): void {
    this.provider.websocket.on("error", (error) => {
      logger.error("WebSocket error:", error);
      this.handleDisconnect();
    });

    this.provider.websocket.on("close", () => {
      logger.warn("WebSocket closed");
      this.handleDisconnect();
    });
  }

  /**
   * Inicia o monitoramento do mempool
   */
  public async start(): Promise<void> {
    if (this.isMonitoring) {
      logger.warn("Mempool monitor already running");
      return;
    }

    try {
      logger.info("Starting mempool monitor...");

      // Escutar transações pendentes
      this.provider.on("pending", async (txHash: string) => {
        await this.handlePendingTransaction(txHash);
      });

      this.isMonitoring = true;
      this.reconnectAttempts = 0;
      logger.info("Mempool monitor started successfully");

      // Emitir evento de conexão
      this.emit("connected");
    } catch (error) {
      logger.error("Failed to start mempool monitor:", error);
      throw error;
    }
  }

  /**
   * Processa uma transação pendente
   */
  private async handlePendingTransaction(txHash: string): Promise<void> {
    // Evitar processar a mesma transação múltiplas vezes
    if (this.pendingTxHashes.has(txHash)) {
      return;
    }

    this.pendingTxHashes.add(txHash);

    // Limpar hashes antigos periodicamente (manter apenas últimas 10000)
    if (this.pendingTxHashes.size > 10000) {
      const toDelete = Array.from(this.pendingTxHashes).slice(0, 5000);
      toDelete.forEach(hash => this.pendingTxHashes.delete(hash));
    }

    try {
      // Buscar detalhes da transação
      const tx = await this.provider.getTransaction(txHash);

      if (!tx) {
        return;
      }

      // Verificar se é uma transação para um DEX router
      if (!this.isDexTransaction(tx.to)) {
        return;
      }

      // Converter para nosso formato
      const pendingTx: PendingTransaction = {
        hash: tx.hash,
        from: tx.from,
        to: tx.to || "",
        value: tx.value,
        gasPrice: tx.gasPrice || 0n,
        gasLimit: tx.gasLimit,
        data: tx.data,
        nonce: tx.nonce,
        timestamp: Date.now(),
      };

      // Emitir evento de nova transação DEX
      this.emit("dexTransaction", pendingTx);

      logger.debug(`DEX transaction detected: ${txHash.slice(0, 10)}...`);
    } catch (error) {
      // Ignorar erros de transações que foram mineradas antes de conseguirmos buscá-las
      if ((error as any).code !== "TRANSACTION_REPLACED") {
        logger.debug(`Error fetching transaction ${txHash.slice(0, 10)}...`);
      }
    }
  }

  /**
   * Verifica se a transação é para um DEX
   */
  private isDexTransaction(to: string | null): boolean {
    if (!to) return false;
    return this.DEX_ROUTERS.includes(to.toLowerCase());
  }

  /**
   * Lida com desconexão do WebSocket
   */
  private async handleDisconnect(): Promise<void> {
    if (!this.isMonitoring) return;

    this.isMonitoring = false;
    this.emit("disconnected");

    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      logger.error("Max reconnection attempts reached. Stopping monitor.");
      this.emit("error", new Error("Failed to reconnect to WebSocket"));
      return;
    }

    this.reconnectAttempts++;
    logger.info(
      `Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`
    );

    await new Promise((resolve) =>
      setTimeout(resolve, TIMINGS.WEBSOCKET_RECONNECT_DELAY)
    );

    try {
      // Criar nova conexão
      this.provider = new ethers.WebSocketProvider(this.wssUrl);
      this.setupEventListeners();
      await this.start();
    } catch (error) {
      logger.error("Reconnection failed:", error);
      await this.handleDisconnect();
    }
  }

  /**
   * Para o monitoramento
   */
  public async stop(): Promise<void> {
    if (!this.isMonitoring) {
      return;
    }

    logger.info("Stopping mempool monitor...");
    this.isMonitoring = false;

    // Remover todos os listeners
    this.provider.removeAllListeners();

    // Fechar WebSocket
    await this.provider.destroy();

    logger.info("Mempool monitor stopped");
  }

  /**
   * Retorna o status da conexão
   */
  public isConnected(): boolean {
    return this.isMonitoring;
  }

  /**
   * Retorna estatísticas do monitor
   */
  public getStats(): {
    isMonitoring: boolean;
    reconnectAttempts: number;
    trackedTransactions: number;
  } {
    return {
      isMonitoring: this.isMonitoring,
      reconnectAttempts: this.reconnectAttempts,
      trackedTransactions: this.pendingTxHashes.size,
    };
  }
}
