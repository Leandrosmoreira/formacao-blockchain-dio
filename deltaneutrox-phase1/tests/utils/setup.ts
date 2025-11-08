import * as anchor from "@coral-xyz/anchor";
import { Program } from "@coral-xyz/anchor";
import { PublicKey, Keypair, SystemProgram, SYSVAR_RENT_PUBKEY } from "@solana/web3.js";
import { TOKEN_PROGRAM_ID, ASSOCIATED_TOKEN_PROGRAM_ID, createMint, mintTo, getOrCreateAssociatedTokenAccount } from "@solana/spl-token";
import { DeltaneutroxVault } from "../../target/types/deltaneutrox_vault";

export interface TestContext {
  provider: anchor.AnchorProvider;
  program: Program<DeltaneutroxVault>;
  payer: Keypair;
}

export interface VaultAccounts {
  vault: Keypair;
  vaultAuthority: PublicKey;
  sharesMint: Keypair;
  tokenAMint: PublicKey;
  usdcMint: PublicKey;
  poolId: PublicKey;
  vaultTokenA: PublicKey;
  vaultUsdc: PublicKey;
}

/**
 * Initialize test context
 */
export function initTestContext(): TestContext {
  const provider = anchor.AnchorProvider.env();
  anchor.setProvider(provider);

  const program = anchor.workspace.DeltaneutroxVault as Program<DeltaneutroxVault>;
  const payer = (provider.wallet as anchor.Wallet).payer;

  return { provider, program, payer };
}

/**
 * Derive vault authority PDA
 */
export function deriveVaultAuthority(
  vaultPubkey: PublicKey,
  programId: PublicKey
): [PublicKey, number] {
  return PublicKey.findProgramAddressSync(
    [Buffer.from("vault_authority"), vaultPubkey.toBuffer()],
    programId
  );
}

/**
 * Airdrop SOL to account
 */
export async function airdrop(
  provider: anchor.AnchorProvider,
  to: PublicKey,
  amount: number = 10
): Promise<void> {
  const signature = await provider.connection.requestAirdrop(
    to,
    amount * anchor.web3.LAMPORTS_PER_SOL
  );
  await provider.connection.confirmTransaction(signature);
}

/**
 * Create test token mints
 */
export async function createTestMints(
  provider: anchor.AnchorProvider,
  payer: Keypair
): Promise<{ tokenAMint: PublicKey; usdcMint: PublicKey }> {
  // Create Token A (9 decimals like SOL)
  const tokenAMint = await createMint(
    provider.connection,
    payer,
    payer.publicKey,
    null,
    9
  );

  // Create USDC (6 decimals)
  const usdcMint = await createMint(
    provider.connection,
    payer,
    payer.publicKey,
    null,
    6
  );

  return { tokenAMint, usdcMint };
}

/**
 * Fund user with tokens
 */
export async function fundUser(
  provider: anchor.AnchorProvider,
  payer: Keypair,
  user: PublicKey,
  tokenAMint: PublicKey,
  usdcMint: PublicKey,
  amountA: number = 10,
  amountUsdc: number = 1000
): Promise<{ userTokenA: PublicKey; userUsdc: PublicKey }> {
  // Create user token accounts
  const userTokenAAccount = await getOrCreateAssociatedTokenAccount(
    provider.connection,
    payer,
    tokenAMint,
    user
  );

  const userUsdcAccount = await getOrCreateAssociatedTokenAccount(
    provider.connection,
    payer,
    usdcMint,
    user
  );

  // Mint tokens to user
  await mintTo(
    provider.connection,
    payer,
    tokenAMint,
    userTokenAAccount.address,
    payer,
    amountA * 1e9 // 9 decimals
  );

  await mintTo(
    provider.connection,
    payer,
    usdcMint,
    userUsdcAccount.address,
    payer,
    amountUsdc * 1e6 // 6 decimals
  );

  return {
    userTokenA: userTokenAAccount.address,
    userUsdc: userUsdcAccount.address,
  };
}

/**
 * Create a mock Whirlpool pool
 * In real tests, you would clone actual Whirlpool from mainnet/devnet
 */
export function createMockWhirlpoolPool(): PublicKey {
  // For testing, we'll use a fake pool ID
  // In production, you'd use a real Whirlpool pool
  return new PublicKey("HJPjoWUrhoZzkNfRpHuieeFk9WcZWjwy6PBjZ81ngndJ");
}

/**
 * Wait for transaction confirmation
 */
export async function confirmTx(
  provider: anchor.AnchorProvider,
  signature: string
): Promise<void> {
  const latestBlockhash = await provider.connection.getLatestBlockhash();
  await provider.connection.confirmTransaction({
    signature,
    blockhash: latestBlockhash.blockhash,
    lastValidBlockHeight: latestBlockhash.lastValidBlockHeight,
  });
}

/**
 * Get token balance
 */
export async function getTokenBalance(
  provider: anchor.AnchorProvider,
  tokenAccount: PublicKey
): Promise<number> {
  const balance = await provider.connection.getTokenAccountBalance(tokenAccount);
  return balance.value.uiAmount || 0;
}

/**
 * Sleep helper
 */
export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Assert error message contains expected text
 */
export function assertError(error: any, expectedMessage: string): void {
  const errorMessage = error.toString();
  if (!errorMessage.includes(expectedMessage)) {
    throw new Error(
      `Expected error message to contain "${expectedMessage}", but got: "${errorMessage}"`
    );
  }
}
