#!/usr/bin/env node

import { Connection } from '@solana/web3.js';
import { loadConfig, validateConfig } from './config';
import { PythPriceMonitor } from './pyth-monitor';
import { VaultManager } from './vault-manager';
import { StrategyEngine } from './strategy';

/**
 * DeltaNeutroX Keeper Bot
 *
 * Automated keeper for managing delta-neutral vault positions on Solana
 * with Orca Whirlpool integration and Pyth price feeds.
 *
 * Features:
 * - TWAP-based price monitoring via Pyth
 * - Auto-exit when price moves outside range
 * - Auto-reentry with hysteresis (deadband + cooldown)
 * - Jupiter integration for optimal swaps
 */

async function main() {
  console.log('╔════════════════════════════════════════╗');
  console.log('║   DeltaNeutroX Keeper Bot v1.0.0      ║');
  console.log('║   Automated Delta-Neutral Strategy     ║');
  console.log('╚════════════════════════════════════════╝\n');

  try {
    // Load and validate configuration
    console.log('Loading configuration...');
    const config = loadConfig();
    validateConfig(config);
    console.log('✓ Configuration loaded\n');

    // Initialize connection
    console.log('Connecting to Solana...');
    const connection = new Connection(config.solanaRpcUrl, 'confirmed');
    const version = await connection.getVersion();
    console.log(`✓ Connected to Solana (version: ${version['solana-core']})\n`);

    // Initialize components
    console.log('Initializing components...');

    const priceMonitor = new PythPriceMonitor(
      connection,
      config.pythPriceFeedId,
      config.twapWindowSecs
    );
    console.log('✓ Pyth price monitor initialized');

    const vaultManager = new VaultManager(config);
    console.log('✓ Vault manager initialized');

    const strategyEngine = new StrategyEngine(
      priceMonitor,
      vaultManager,
      config
    );
    console.log('✓ Strategy engine initialized\n');

    // Start the keeper bot
    await strategyEngine.start();

    // Graceful shutdown handlers
    const shutdown = async () => {
      console.log('\n\nReceived shutdown signal...');
      strategyEngine.stop();
      console.log('Keeper bot stopped. Goodbye!');
      process.exit(0);
    };

    process.on('SIGINT', shutdown);
    process.on('SIGTERM', shutdown);

    // Keep process alive
    console.log('Keeper bot is now running. Press Ctrl+C to stop.\n');

  } catch (error) {
    console.error('\n❌ Fatal error:', error);
    process.exit(1);
  }
}

// Run the keeper bot
main().catch(error => {
  console.error('Unhandled error:', error);
  process.exit(1);
});
