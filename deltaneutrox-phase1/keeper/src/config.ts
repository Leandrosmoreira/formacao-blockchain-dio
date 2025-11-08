import dotenv from 'dotenv';
import { PublicKey } from '@solana/web3.js';
import * as fs from 'fs';

dotenv.config();

export interface KeeperConfig {
  // Solana Configuration
  solanaRpcUrl: string;
  solanaWssUrl: string;

  // Keeper Wallet
  keeperKeypairPath: string;

  // Vault Configuration
  vaultPubkey: PublicKey;
  programId: PublicKey;

  // Pyth Configuration
  pythPriceFeedId: PublicKey;

  // Strategy Parameters
  deadbandBps: number;        // e.g., 50 = 0.5%
  twapWindowSecs: number;     // e.g., 60 = 1 minute
  cooldownMs: number;         // e.g., 180000 = 3 minutes
  checkIntervalMs: number;    // e.g., 5000 = 5 seconds

  // Jupiter Configuration
  jupiterApiUrl: string;
}

export function loadConfig(): KeeperConfig {
  const requiredEnvVars = [
    'SOLANA_RPC_URL',
    'SOLANA_WSS_URL',
    'KEEPER_KEYPAIR_PATH',
    'VAULT_PUBKEY',
    'PROGRAM_ID',
    'PYTH_PRICE_FEED_ID',
  ];

  // Validate required env vars
  for (const envVar of requiredEnvVars) {
    if (!process.env[envVar]) {
      throw new Error(`Missing required environment variable: ${envVar}`);
    }
  }

  // Validate keypair file exists
  const keypairPath = process.env.KEEPER_KEYPAIR_PATH!;
  if (!fs.existsSync(keypairPath)) {
    throw new Error(`Keeper keypair file not found: ${keypairPath}`);
  }

  return {
    solanaRpcUrl: process.env.SOLANA_RPC_URL!,
    solanaWssUrl: process.env.SOLANA_WSS_URL!,
    keeperKeypairPath: keypairPath,
    vaultPubkey: new PublicKey(process.env.VAULT_PUBKEY!),
    programId: new PublicKey(process.env.PROGRAM_ID!),
    pythPriceFeedId: new PublicKey(process.env.PYTH_PRICE_FEED_ID!),
    deadbandBps: parseInt(process.env.DEADBAND_BPS || '50'),
    twapWindowSecs: parseInt(process.env.TWAP_WINDOW_SECS || '60'),
    cooldownMs: parseInt(process.env.COOLDOWN_MS || '180000'),
    checkIntervalMs: parseInt(process.env.CHECK_INTERVAL_MS || '5000'),
    jupiterApiUrl: process.env.JUPITER_API_URL || 'https://quote-api.jup.ag/v6',
  };
}

export function validateConfig(config: KeeperConfig): void {
  if (config.deadbandBps < 0 || config.deadbandBps > 10000) {
    throw new Error('deadbandBps must be between 0 and 10000');
  }

  if (config.twapWindowSecs < 10) {
    throw new Error('twapWindowSecs must be at least 10 seconds');
  }

  if (config.cooldownMs < 60000) {
    console.warn('WARNING: cooldownMs is less than 1 minute. This may cause excessive transactions.');
  }

  if (config.checkIntervalMs < 1000) {
    throw new Error('checkIntervalMs must be at least 1 second');
  }
}
