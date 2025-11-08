import { Connection, PublicKey, Keypair, SystemProgram, SYSVAR_RENT_PUBKEY } from '@solana/web3.js';
import { Program, AnchorProvider, Wallet } from '@coral-xyz/anchor';
import { TOKEN_PROGRAM_ID, ASSOCIATED_TOKEN_PROGRAM_ID, getAssociatedTokenAddress } from '@solana/spl-token';
import * as fs from 'fs';
import * as path from 'path';
import { IDL, DeltaneutroxVault } from './idl';

/**
 * Load configuration from environment
 */
export interface CLIConfig {
  rpcUrl: string;
  programId: PublicKey;
  walletPath: string;
}

export function loadConfig(): CLIConfig {
  const rpcUrl = process.env.SOLANA_RPC_URL || 'https://api.devnet.solana.com';
  const programIdStr = process.env.PROGRAM_ID || 'Fg6PaFpoGXkYsidMpWTK6W2BeZ7FEfcYkg476zPFsLnS';
  const walletPath = process.env.WALLET_PATH || path.join(process.env.HOME || '', '.config/solana/id.json');

  return {
    rpcUrl,
    programId: new PublicKey(programIdStr),
    walletPath,
  };
}

/**
 * Load wallet keypair from file
 */
export function loadWallet(walletPath: string): Keypair {
  if (!fs.existsSync(walletPath)) {
    throw new Error(`Wallet file not found: ${walletPath}`);
  }

  const keypairData = JSON.parse(fs.readFileSync(walletPath, 'utf-8'));
  return Keypair.fromSecretKey(new Uint8Array(keypairData));
}

/**
 * Initialize Anchor program
 */
export function initProgram(config: CLIConfig): { program: Program<DeltaneutroxVault>; provider: AnchorProvider; wallet: Keypair } {
  const connection = new Connection(config.rpcUrl, 'confirmed');
  const wallet = loadWallet(config.walletPath);
  const anchorWallet = new Wallet(wallet);

  const provider = new AnchorProvider(connection, anchorWallet, {
    commitment: 'confirmed',
  });

  const program = new Program<DeltaneutroxVault>(IDL, config.programId, provider);

  return { program, provider, wallet };
}

/**
 * PDA Derivation Utilities
 */

export const VAULT_AUTHORITY_SEED = Buffer.from('vault_authority');

export function deriveVaultAuthority(
  vaultPubkey: PublicKey,
  programId: PublicKey
): [PublicKey, number] {
  return PublicKey.findProgramAddressSync(
    [VAULT_AUTHORITY_SEED, vaultPubkey.toBuffer()],
    programId
  );
}

/**
 * Get associated token addresses
 */
export async function getAssociatedTokenAddresses(
  owner: PublicKey,
  tokenAMint: PublicKey,
  usdcMint: PublicKey,
  sharesMint: PublicKey
) {
  const [tokenA, usdc, shares] = await Promise.all([
    getAssociatedTokenAddress(tokenAMint, owner),
    getAssociatedTokenAddress(usdcMint, owner),
    getAssociatedTokenAddress(sharesMint, owner),
  ]);

  return { tokenA, usdc, shares };
}

/**
 * Format numbers for display
 */
export function formatAmount(amount: number | bigint, decimals: number = 6): string {
  const num = typeof amount === 'bigint' ? Number(amount) : amount;
  const divisor = Math.pow(10, decimals);
  return (num / divisor).toFixed(decimals);
}

export function formatPercentage(bps: number): string {
  return (bps / 100).toFixed(2) + '%';
}

export function formatTimestamp(timestamp: number | bigint): string {
  const ts = typeof timestamp === 'bigint' ? Number(timestamp) : timestamp;
  return new Date(ts * 1000).toISOString();
}

/**
 * Vault status enum to string
 */
export function vaultStatusToString(status: any): string {
  if ('idle' in status) return 'Idle';
  if ('positionOpen' in status) return 'PositionOpen';
  if ('exitedToUSDC' in status) return 'ExitedToUSDC';
  if ('reentering' in status) return 'Reentering';
  return 'Unknown';
}

/**
 * Confirm transaction with retries
 */
export async function confirmTx(
  connection: Connection,
  signature: string,
  maxRetries: number = 3
): Promise<void> {
  for (let i = 0; i < maxRetries; i++) {
    try {
      const confirmation = await connection.confirmTransaction(signature, 'confirmed');
      if (confirmation.value.err) {
        throw new Error(`Transaction failed: ${JSON.stringify(confirmation.value.err)}`);
      }
      return;
    } catch (error) {
      if (i === maxRetries - 1) throw error;
      await new Promise(resolve => setTimeout(resolve, 2000));
    }
  }
}

/**
 * Get SOL balance
 */
export async function getBalance(connection: Connection, pubkey: PublicKey): Promise<number> {
  const balance = await connection.getBalance(pubkey);
  return balance / 1e9; // Convert lamports to SOL
}

/**
 * Check if account exists
 */
export async function accountExists(connection: Connection, pubkey: PublicKey): Promise<boolean> {
  const accountInfo = await connection.getAccountInfo(pubkey);
  return accountInfo !== null;
}

/**
 * Display error
 */
export function displayError(error: any): void {
  if (error.message) {
    console.error('Error:', error.message);
  } else if (error.logs) {
    console.error('Transaction logs:');
    error.logs.forEach((log: string) => console.error('  ', log));
  } else {
    console.error('Error:', error);
  }
}
