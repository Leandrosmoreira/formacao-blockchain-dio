import { Connection, PublicKey } from '@solana/web3.js';
import { PythHttpClient, getPythProgramKeyForCluster } from '@pythnetwork/client';
import { TWAPCalculator } from './twap';

/**
 * Pyth Price Monitor
 *
 * Monitors Pyth price feeds and maintains TWAP calculation
 */

export interface PriceUpdate {
  price: number;
  confidence: number;
  timestamp: number;
  slot: number;
}

export class PythPriceMonitor {
  private connection: Connection;
  private pythClient: PythHttpClient;
  private priceFeedId: PublicKey;
  private twapCalculator: TWAPCalculator;
  private latestPrice: PriceUpdate | null = null;
  private isMonitoring: boolean = false;
  private monitorInterval: NodeJS.Timeout | null = null;

  constructor(
    connection: Connection,
    priceFeedId: PublicKey,
    twapWindowSecs: number
  ) {
    this.connection = connection;
    this.priceFeedId = priceFeedId;
    this.twapCalculator = new TWAPCalculator(twapWindowSecs);

    // Initialize Pyth client
    this.pythClient = new PythHttpClient(connection, getPythProgramKeyForCluster('devnet'));
  }

  /**
   * Fetch the latest price from Pyth
   */
  async fetchPrice(): Promise<PriceUpdate> {
    try {
      const data = await this.pythClient.getData();

      // Find our price feed
      const priceFeed = data.productPrice.get(this.priceFeedId.toString());

      if (!priceFeed || !priceFeed.price || !priceFeed.confidence) {
        throw new Error('Price feed data not available');
      }

      const price = priceFeed.price;
      const confidence = priceFeed.confidence;

      // Validate price is valid
      if (price <= 0) {
        throw new Error(`Invalid price: ${price}`);
      }

      const priceUpdate: PriceUpdate = {
        price,
        confidence,
        timestamp: Math.floor(Date.now() / 1000),
        slot: data.currentSlot || 0,
      };

      // Update latest price
      this.latestPrice = priceUpdate;

      // Add to TWAP calculator
      this.twapCalculator.addObservation(
        priceUpdate.price,
        priceUpdate.timestamp,
        priceUpdate.confidence
      );

      return priceUpdate;
    } catch (error) {
      console.error('Error fetching Pyth price:', error);
      throw error;
    }
  }

  /**
   * Start monitoring the price feed at regular intervals
   */
  startMonitoring(intervalMs: number = 5000): void {
    if (this.isMonitoring) {
      console.warn('Price monitoring is already active');
      return;
    }

    console.log(`Starting Pyth price monitoring (interval: ${intervalMs}ms)`);
    console.log(`Price Feed: ${this.priceFeedId.toString()}`);

    this.isMonitoring = true;

    // Fetch immediately
    this.fetchPrice().catch(err => {
      console.error('Initial price fetch failed:', err);
    });

    // Then fetch at intervals
    this.monitorInterval = setInterval(async () => {
      try {
        await this.fetchPrice();
      } catch (error) {
        console.error('Error in price monitoring loop:', error);
      }
    }, intervalMs);
  }

  /**
   * Stop monitoring the price feed
   */
  stopMonitoring(): void {
    if (!this.isMonitoring) {
      return;
    }

    console.log('Stopping Pyth price monitoring');
    this.isMonitoring = false;

    if (this.monitorInterval) {
      clearInterval(this.monitorInterval);
      this.monitorInterval = null;
    }
  }

  /**
   * Get the latest price
   */
  getLatestPrice(): PriceUpdate | null {
    return this.latestPrice;
  }

  /**
   * Get the current TWAP
   */
  getTWAP(): number | null {
    return this.twapCalculator.calculateTWAP();
  }

  /**
   * Get TWAP statistics
   */
  getTWAPStatistics() {
    return this.twapCalculator.getStatistics();
  }

  /**
   * Check if TWAP window is sufficiently filled
   */
  isTWAPReady(): boolean {
    return this.twapCalculator.isWindowFilled();
  }

  /**
   * Reset TWAP calculator (clears all price history)
   */
  resetTWAP(): void {
    this.twapCalculator.reset();
  }

  /**
   * Calculate price deviation from TWAP in basis points
   * Returns null if TWAP is not ready
   */
  calculateDeviationFromTWAP(): number | null {
    const twap = this.getTWAP();
    const latest = this.latestPrice;

    if (!twap || !latest) {
      return null;
    }

    // Deviation in basis points
    // Positive = price above TWAP, Negative = price below TWAP
    const deviation = ((latest.price - twap) / twap) * 10000;
    return deviation;
  }

  /**
   * Check if current price is outside the deadband from TWAP
   *
   * @param deadbandBps - Deadband in basis points (e.g., 50 = 0.5%)
   * @returns true if price is outside deadband, false otherwise, null if TWAP not ready
   */
  isOutsideDeadband(deadbandBps: number): boolean | null {
    const deviation = this.calculateDeviationFromTWAP();

    if (deviation === null) {
      return null;
    }

    return Math.abs(deviation) > deadbandBps;
  }

  /**
   * Get monitoring status
   */
  isActive(): boolean {
    return this.isMonitoring;
  }
}
