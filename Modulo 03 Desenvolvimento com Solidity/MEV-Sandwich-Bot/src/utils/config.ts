import * as dotenv from "dotenv";
import { BotConfig } from "../types";
import { DEFAULTS } from "./constants";
import logger from "./logger";

dotenv.config();

/**
 * Carrega e valida configuração do bot
 */
export function loadConfig(): BotConfig {
  const requiredEnvVars = [
    "MAINNET_RPC_URL",
    "MAINNET_WSS_URL",
    "PRIVATE_KEY",
  ];

  // Verificar variáveis obrigatórias
  for (const envVar of requiredEnvVars) {
    if (!process.env[envVar]) {
      throw new Error(`Missing required environment variable: ${envVar}`);
    }
  }

  // Validar private key
  const privateKey = process.env.PRIVATE_KEY!;
  if (!privateKey.startsWith("0x")) {
    throw new Error("PRIVATE_KEY must start with 0x");
  }
  if (privateKey.length !== 66) {
    throw new Error("PRIVATE_KEY must be 64 characters (plus 0x prefix)");
  }

  const config: BotConfig = {
    rpcUrl: process.env.MAINNET_RPC_URL!,
    wssUrl: process.env.MAINNET_WSS_URL!,
    privateKey: privateKey,
    flashbotsRelayUrl:
      process.env.FLASHBOTS_RELAY_URL || "https://relay.flashbots.net",
    minProfitWei: process.env.MIN_PROFIT_WEI
      ? BigInt(process.env.MIN_PROFIT_WEI)
      : DEFAULTS.MIN_PROFIT_WEI,
    maxGasPriceGwei: process.env.MAX_GAS_PRICE_GWEI
      ? Number(process.env.MAX_GAS_PRICE_GWEI)
      : DEFAULTS.MAX_GAS_PRICE_GWEI,
    slippageTolerance: process.env.SLIPPAGE_TOLERANCE
      ? Number(process.env.SLIPPAGE_TOLERANCE)
      : DEFAULTS.SLIPPAGE_TOLERANCE,
    network: process.env.NETWORK || "mainnet",
  };

  logger.info("Configuration loaded successfully");
  logger.info(`Network: ${config.network}`);
  logger.info(`Min profit: ${config.minProfitWei.toString()} wei`);
  logger.info(`Max gas price: ${config.maxGasPriceGwei} gwei`);

  return config;
}

/**
 * Valida se o ambiente está configurado corretamente
 */
export function validateEnvironment(): boolean {
  try {
    loadConfig();
    return true;
  } catch (error) {
    logger.error("Environment validation failed:", error);
    return false;
  }
}
