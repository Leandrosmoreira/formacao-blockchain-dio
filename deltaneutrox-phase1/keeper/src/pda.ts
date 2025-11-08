import { PublicKey } from '@solana/web3.js';
import { utils } from '@coral-xyz/anchor';

/**
 * PDA (Program Derived Address) Helpers
 *
 * Utilities for deriving PDAs used by the DeltaNeutroX vault program
 */

// Program constants
export const VAULT_AUTHORITY_SEED = Buffer.from('vault_authority');
export const WHIRLPOOL_PROGRAM_ID = new PublicKey('whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc');
export const JUPITER_PROGRAM_ID = new PublicKey('JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4');
export const TOKEN_PROGRAM_ID = new PublicKey('TokenkegQfeZyiNwAJbNbGKPFXCo');
export const ASSOCIATED_TOKEN_PROGRAM_ID = new PublicKey('ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL');
export const METADATA_PROGRAM_ID = new PublicKey('metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s');

/**
 * Derive the vault authority PDA
 *
 * Seeds: ["vault_authority", vault_pubkey]
 */
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
 * Derive a Whirlpool position PDA
 *
 * Seeds: ["position", position_mint]
 */
export function deriveWhirlpoolPosition(
  positionMint: PublicKey
): [PublicKey, number] {
  return PublicKey.findProgramAddressSync(
    [Buffer.from('position'), positionMint.toBuffer()],
    WHIRLPOOL_PROGRAM_ID
  );
}

/**
 * Derive a Whirlpool tick array PDA
 *
 * Seeds: ["tick_array", whirlpool, start_tick_index.to_string()]
 */
export function deriveTickArray(
  whirlpoolPubkey: PublicKey,
  startTickIndex: number
): [PublicKey, number] {
  return PublicKey.findProgramAddressSync(
    [
      Buffer.from('tick_array'),
      whirlpoolPubkey.toBuffer(),
      Buffer.from(startTickIndex.toString()),
    ],
    WHIRLPOOL_PROGRAM_ID
  );
}

/**
 * Calculate tick array start index from a tick
 *
 * Tick arrays in Whirlpool group ticks by tick_spacing
 */
export function getTickArrayStartIndex(tick: number, tickSpacing: number): number {
  const ticksPerArray = tickSpacing * 88; // Whirlpool uses 88 ticks per array
  const arrayIndex = Math.floor(tick / ticksPerArray);
  return arrayIndex * ticksPerArray;
}

/**
 * Derive the metadata PDA for a position NFT
 *
 * Seeds: ["metadata", metadata_program, mint]
 */
export function deriveMetadata(mint: PublicKey): [PublicKey, number] {
  return PublicKey.findProgramAddressSync(
    [
      Buffer.from('metadata'),
      METADATA_PROGRAM_ID.toBuffer(),
      mint.toBuffer(),
    ],
    METADATA_PROGRAM_ID
  );
}

/**
 * Derive associated token account address
 */
export function deriveAssociatedTokenAddress(
  owner: PublicKey,
  mint: PublicKey
): PublicKey {
  return utils.token.associatedAddress({
    mint,
    owner,
  });
}

/**
 * Get the Whirlpool token vaults from pool data
 * These are typically stored in the whirlpool account
 *
 * For now, these need to be fetched from the whirlpool account
 */
export interface WhirlpoolData {
  tokenMintA: PublicKey;
  tokenMintB: PublicKey;
  tokenVaultA: PublicKey;
  tokenVaultB: PublicKey;
  tickSpacing: number;
  tickCurrentIndex: number;
}

/**
 * Helper to build signer seeds for vault authority
 */
export function getVaultAuthoritySeeds(
  vaultPubkey: PublicKey,
  bump: number
): Buffer[] {
  return [
    VAULT_AUTHORITY_SEED,
    vaultPubkey.toBuffer(),
    Buffer.from([bump]),
  ];
}
