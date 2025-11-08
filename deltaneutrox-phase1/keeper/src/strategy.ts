import { PythPriceMonitor } from './pyth-monitor';
import { VaultManager, VaultStatus } from './vault-manager';
import { KeeperConfig } from './config';

/**
 * Delta Neutral Strategy Engine
 *
 * Implements the core strategy logic:
 * - Monitor price via Pyth + TWAP
 * - Exit when price moves outside tick range
 * - Reenter when TWAP returns + cooldown elapsed + within deadband
 */

export interface StrategyState {
  isRunning: boolean;
  lastCheckTimestamp: number;
  lastActionTimestamp: number;
  consecutiveErrors: number;
}

export class StrategyEngine {
  private priceMonitor: PythPriceMonitor;
  private vaultManager: VaultManager;
  private config: KeeperConfig;
  private state: StrategyState;
  private checkInterval: NodeJS.Timeout | null = null;

  constructor(
    priceMonitor: PythPriceMonitor,
    vaultManager: VaultManager,
    config: KeeperConfig
  ) {
    this.priceMonitor = priceMonitor;
    this.vaultManager = vaultManager;
    this.config = config;

    this.state = {
      isRunning: false,
      lastCheckTimestamp: 0,
      lastActionTimestamp: 0,
      consecutiveErrors: 0,
    };
  }

  /**
   * Start the strategy engine
   */
  async start(): Promise<void> {
    if (this.state.isRunning) {
      console.warn('Strategy engine is already running');
      return;
    }

    console.log('=== Starting DeltaNeutroX Strategy Engine ===');
    console.log(`Vault: ${this.vaultManager.getVaultPublicKey().toString()}`);
    console.log(`Keeper: ${this.vaultManager.getKeeperPublicKey().toString()}`);
    console.log(`Deadband: ${this.config.deadbandBps} bps (${this.config.deadbandBps / 100}%)`);
    console.log(`TWAP Window: ${this.config.twapWindowSecs} seconds`);
    console.log(`Cooldown: ${this.config.cooldownMs} ms (${this.config.cooldownMs / 1000} seconds)`);
    console.log(`Check Interval: ${this.config.checkIntervalMs} ms`);

    // Start price monitoring
    this.priceMonitor.startMonitoring(this.config.checkIntervalMs);

    // Wait for initial TWAP to fill
    console.log('\nWaiting for TWAP window to fill...');
    await this.waitForTWAPReady();

    this.state.isRunning = true;

    // Start strategy loop
    this.checkInterval = setInterval(() => {
      this.checkAndExecuteStrategy().catch(err => {
        console.error('Error in strategy loop:', err);
        this.state.consecutiveErrors++;

        // Stop if too many consecutive errors
        if (this.state.consecutiveErrors >= 10) {
          console.error('Too many consecutive errors. Stopping strategy engine.');
          this.stop();
        }
      });
    }, this.config.checkIntervalMs);

    console.log('\n✓ Strategy engine started successfully\n');
  }

  /**
   * Stop the strategy engine
   */
  stop(): void {
    if (!this.state.isRunning) {
      return;
    }

    console.log('Stopping strategy engine...');
    this.state.isRunning = false;

    if (this.checkInterval) {
      clearInterval(this.checkInterval);
      this.checkInterval = null;
    }

    this.priceMonitor.stopMonitoring();
    console.log('Strategy engine stopped');
  }

  /**
   * Wait for TWAP window to be sufficiently filled
   */
  private async waitForTWAPReady(): Promise<void> {
    return new Promise((resolve) => {
      const checkInterval = setInterval(() => {
        const stats = this.priceMonitor.getTWAPStatistics();
        console.log(`TWAP: ${stats.count} observations, ${stats.timeSpanSecs}s span (need ${this.config.twapWindowSecs * 0.8}s)`);

        if (this.priceMonitor.isTWAPReady()) {
          clearInterval(checkInterval);
          console.log('✓ TWAP window ready');
          resolve();
        }
      }, 2000);
    });
  }

  /**
   * Main strategy logic loop
   */
  private async checkAndExecuteStrategy(): Promise<void> {
    this.state.lastCheckTimestamp = Date.now();

    // Get current state
    const vaultState = await this.vaultManager.fetchVaultState();
    const priceUpdate = this.priceMonitor.getLatestPrice();
    const twap = this.priceMonitor.getTWAP();
    const deviation = this.priceMonitor.calculateDeviationFromTWAP();

    if (!priceUpdate || !twap || deviation === null) {
      console.warn('Price data not available yet');
      return;
    }

    // Log current status
    this.logStatus(vaultState.status, priceUpdate.price, twap, deviation);

    // Strategy decision tree
    if (vaultState.status === VaultStatus.PositionOpen) {
      await this.handlePositionOpenState(vaultState, priceUpdate.price, twap, deviation);
    } else if (vaultState.status === VaultStatus.ExitedToUSDC) {
      await this.handleExitedState(vaultState, priceUpdate.price, twap, deviation);
    }

    // Reset error counter on successful check
    this.state.consecutiveErrors = 0;
  }

  /**
   * Handle logic when vault is in PositionOpen state
   */
  private async handlePositionOpenState(
    vaultState: any,
    currentPrice: number,
    twap: number,
    deviation: number
  ): Promise<void> {
    // TODO: Check if current price is outside the tick range
    // For now, we check if deviation exceeds deadband (simplified logic)

    const isOutsideDeadband = Math.abs(deviation) > this.config.deadbandBps;

    if (isOutsideDeadband) {
      console.log(`\n🚨 TRIGGER: Price outside deadband (${deviation.toFixed(2)} bps)`);
      console.log('Executing EXIT strategy...\n');

      try {
        const txSig = await this.vaultManager.executeExit(twap);
        console.log(`✅ Exit executed successfully: ${txSig}`);
        this.state.lastActionTimestamp = Date.now();
      } catch (error) {
        console.error('Failed to execute exit:', error);
        throw error;
      }
    }
  }

  /**
   * Handle logic when vault is in ExitedToUSDC state
   */
  private async handleExitedState(
    vaultState: any,
    currentPrice: number,
    twap: number,
    deviation: number
  ): Promise<void> {
    // Check cooldown
    const { canReenter, cooldownRemaining } = await this.vaultManager.canReenter();

    if (!canReenter) {
      console.log(`Cooldown remaining: ${(cooldownRemaining / 1000).toFixed(1)}s`);
      return;
    }

    // Check if price is back within deadband
    const isWithinDeadband = Math.abs(deviation) <= this.config.deadbandBps;

    if (isWithinDeadband) {
      console.log(`\n🚀 TRIGGER: Price back within deadband (${deviation.toFixed(2)} bps)`);
      console.log('Executing REENTRY strategy...\n');

      try {
        // Calculate target liquidity based on current vault balances
        // TODO: Implement proper liquidity calculation
        const targetLiquidity = BigInt(1000000); // Placeholder

        const txSig = await this.vaultManager.executeReentry(twap, targetLiquidity);
        console.log(`✅ Reentry executed successfully: ${txSig}`);
        this.state.lastActionTimestamp = Date.now();
      } catch (error) {
        console.error('Failed to execute reentry:', error);
        throw error;
      }
    } else {
      console.log(`Waiting for price to return within deadband (current: ${deviation.toFixed(2)} bps)`);
    }
  }

  /**
   * Log current status
   */
  private logStatus(
    status: VaultStatus,
    currentPrice: number,
    twap: number,
    deviation: number
  ): void {
    const statusNames = ['Idle', 'PositionOpen', 'ExitedToUSDC', 'Reentering'];
    const statusName = statusNames[status] || 'Unknown';

    console.log(
      `[${new Date().toISOString()}] ` +
      `Status: ${statusName} | ` +
      `Price: $${currentPrice.toFixed(4)} | ` +
      `TWAP: $${twap.toFixed(4)} | ` +
      `Deviation: ${deviation > 0 ? '+' : ''}${deviation.toFixed(2)} bps`
    );
  }

  /**
   * Get current strategy state
   */
  getState(): StrategyState {
    return { ...this.state };
  }

  /**
   * Check if strategy is running
   */
  isRunning(): boolean {
    return this.state.isRunning;
  }
}
