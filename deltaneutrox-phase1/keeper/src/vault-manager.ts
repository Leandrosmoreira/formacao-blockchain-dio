import { Connection, PublicKey, Keypair, SystemProgram, SYSVAR_CLOCK_PUBKEY, SYSVAR_RENT_PUBKEY } from '@solana/web3.js';
import { Program, AnchorProvider, Wallet, BN } from '@coral-xyz/anchor';
import { TOKEN_PROGRAM_ID } from '@solana/spl-token';
import * as fs from 'fs';
import { KeeperConfig } from './config';
import { IDL, DeltaneutroxVault } from './idl';
import {
  deriveVaultAuthority,
  deriveTickArray,
  getTickArrayStartIndex,
  deriveAssociatedTokenAddress,
  WHIRLPOOL_PROGRAM_ID,
  JUPITER_PROGRAM_ID,
  ASSOCIATED_TOKEN_PROGRAM_ID
} from './pda';
import { JupiterClient } from './jupiter-api';

/**
 * Vault Manager
 *
 * Handles interactions with the DeltaNeutroX vault program
 */

export enum VaultStatus {
  Idle = 0,
  PositionOpen = 1,
  ExitedToUSDC = 2,
  Reentering = 3,
}

export interface VaultConfig {
  deadbandBps: number;
  twapWindowSecs: number;
  cooldownMs: BN;
  slippageBps: number;
  forceSwapToUsdc: boolean;
}

export interface VaultState {
  authority: PublicKey;
  poolId: PublicKey;
  positionKey: PublicKey;
  tokenAMint: PublicKey;
  usdcMint: PublicKey;
  sharesMint: PublicKey;
  vaultTokenA: PublicKey;
  vaultUsdc: PublicKey;
  tickLower: number;
  tickUpper: number;
  status: VaultStatus;
  operationInProgress: boolean;
  totalShares: BN;
  lastExitTimestamp: BN;
  totalDeposits: BN;
  totalWithdrawals: BN;
  keeperAuthority: PublicKey;
  config: VaultConfig;
  bump: number;
}

export class VaultManager {
  private connection: Connection;
  private program: Program<DeltaneutroxVault>;
  private vaultPubkey: PublicKey;
  private keeper: Keypair;
  private config: KeeperConfig;
  private jupiterClient: JupiterClient;
  private vaultAuthority: PublicKey;
  private vaultAuthorityBump: number;

  constructor(config: KeeperConfig) {
    this.config = config;
    this.connection = new Connection(config.solanaRpcUrl, 'confirmed');
    this.vaultPubkey = config.vaultPubkey;

    // Load keeper keypair
    const keypairData = JSON.parse(fs.readFileSync(config.keeperKeypairPath, 'utf-8'));
    this.keeper = Keypair.fromSecretKey(new Uint8Array(keypairData));

    // Initialize Anchor provider and program
    const wallet = new Wallet(this.keeper);
    const provider = new AnchorProvider(this.connection, wallet, {
      commitment: 'confirmed',
    });

    // Initialize program with IDL
    this.program = new Program<DeltaneutroxVault>(
      IDL,
      config.programId,
      provider
    );

    // Derive vault authority PDA
    const [vaultAuthority, bump] = deriveVaultAuthority(
      this.vaultPubkey,
      config.programId
    );
    this.vaultAuthority = vaultAuthority;
    this.vaultAuthorityBump = bump;

    // Initialize Jupiter client
    this.jupiterClient = new JupiterClient(config.jupiterApiUrl);

    console.log('VaultManager initialized');
    console.log(`Program ID: ${config.programId.toString()}`);
    console.log(`Keeper: ${this.keeper.publicKey.toString()}`);
    console.log(`Vault: ${this.vaultPubkey.toString()}`);
    console.log(`Vault Authority: ${this.vaultAuthority.toString()}`);
  }

  /**
   * Fetch the current vault state
   */
  async fetchVaultState(): Promise<VaultState> {
    try {
      const vaultAccount = await this.program.account.strategyVault.fetch(this.vaultPubkey);

      // Map enum variant to number
      let status: VaultStatus;
      if ('idle' in vaultAccount.status) {
        status = VaultStatus.Idle;
      } else if ('positionOpen' in vaultAccount.status) {
        status = VaultStatus.PositionOpen;
      } else if ('exitedToUSDC' in vaultAccount.status) {
        status = VaultStatus.ExitedToUSDC;
      } else if ('reentering' in vaultAccount.status) {
        status = VaultStatus.Reentering;
      } else {
        status = VaultStatus.Idle;
      }

      return {
        authority: vaultAccount.authority,
        poolId: vaultAccount.poolId,
        positionKey: vaultAccount.positionKey,
        tokenAMint: vaultAccount.tokenAMint,
        usdcMint: vaultAccount.usdcMint,
        sharesMint: vaultAccount.sharesMint,
        vaultTokenA: vaultAccount.vaultTokenA,
        vaultUsdc: vaultAccount.vaultUsdc,
        tickLower: vaultAccount.tickLower,
        tickUpper: vaultAccount.tickUpper,
        status,
        operationInProgress: vaultAccount.operationInProgress,
        totalShares: vaultAccount.totalShares,
        lastExitTimestamp: vaultAccount.lastExitTimestamp,
        totalDeposits: vaultAccount.totalDeposits,
        totalWithdrawals: vaultAccount.totalWithdrawals,
        keeperAuthority: vaultAccount.keeperAuthority,
        config: {
          deadbandBps: vaultAccount.config.deadbandBps,
          twapWindowSecs: vaultAccount.config.twapWindowSecs,
          cooldownMs: new BN(vaultAccount.config.cooldownMs),
          slippageBps: vaultAccount.config.slippageBps,
          forceSwapToUsdc: vaultAccount.config.forceSwapToUsdc,
        },
        bump: vaultAccount.bump,
      };
    } catch (error) {
      console.error('Error fetching vault state:', error);
      throw error;
    }
  }

  /**
   * Check if vault can exit (is in PositionOpen status)
   */
  async canExit(): Promise<boolean> {
    const state = await this.fetchVaultState();
    return state.status === VaultStatus.PositionOpen && !state.operationInProgress;
  }

  /**
   * Check if vault can reenter (is in ExitedToUSDC status and cooldown has passed)
   */
  async canReenter(): Promise<{ canReenter: boolean; cooldownRemaining: number }> {
    const state = await this.fetchVaultState();

    if (state.status !== VaultStatus.ExitedToUSDC || state.operationInProgress) {
      return { canReenter: false, cooldownRemaining: 0 };
    }

    const now = Date.now();
    const lastExitMs = state.lastExitTimestamp.toNumber() * 1000;
    const cooldownMs = state.config.cooldownMs.toNumber();
    const elapsed = now - lastExitMs;
    const remaining = Math.max(0, cooldownMs - elapsed);

    return {
      canReenter: remaining === 0,
      cooldownRemaining: remaining,
    };
  }

  /**
   * Execute exit operation (decrease liquidity + collect fees + swap to USDC + mark exited)
   */
  async executeExit(twapPrice: number): Promise<string> {
    console.log(`\n=== Executing Exit Strategy ===`);
    console.log(`TWAP Price: $${twapPrice.toFixed(4)}`);

    try {
      const state = await this.fetchVaultState();

      // Validate state
      if (state.status !== VaultStatus.PositionOpen) {
        throw new Error(`Cannot exit: vault status is ${VaultStatus[state.status]}, expected PositionOpen`);
      }

      if (state.operationInProgress) {
        throw new Error('Cannot exit: operation already in progress');
      }

      // Fetch whirlpool data to get token vaults and tick spacing
      const whirlpoolData = await this.fetchWhirlpoolData(state.poolId);

      // Derive tick arrays
      const tickArrayLowerStart = getTickArrayStartIndex(state.tickLower, whirlpoolData.tickSpacing);
      const tickArrayUpperStart = getTickArrayStartIndex(state.tickUpper, whirlpoolData.tickSpacing);
      const [tickArrayLower] = deriveTickArray(state.poolId, tickArrayLowerStart);
      const [tickArrayUpper] = deriveTickArray(state.poolId, tickArrayUpperStart);

      // Get position token account
      const positionTokenAccount = deriveAssociatedTokenAddress(
        this.vaultAuthority,
        state.positionKey
      );

      console.log('Step 1: Decreasing liquidity to 100%...');
      // Step 1: Decrease liquidity to 100%
      const decreaseTx = await this.program.methods
        .decreaseLiquidityAll()
        .accounts({
          vault: this.vaultPubkey,
          vaultAuthority: this.vaultAuthority,
          whirlpoolProgram: WHIRLPOOL_PROGRAM_ID,
          whirlpool: state.poolId,
          position: state.positionKey,
          positionTokenAccount,
          vaultTokenA: state.vaultTokenA,
          vaultUsdc: state.vaultUsdc,
          tokenVaultA: whirlpoolData.tokenVaultA,
          tokenVaultB: whirlpoolData.tokenVaultB,
          tickArrayLower,
          tickArrayUpper,
          keeper: this.keeper.publicKey,
          tokenProgram: TOKEN_PROGRAM_ID,
        })
        .rpc();
      console.log(`✓ Decrease liquidity TX: ${decreaseTx}`);

      console.log('Step 2: Collecting fees...');
      // Step 2: Collect fees
      const collectTx = await this.program.methods
        .collectFees()
        .accounts({
          vault: this.vaultPubkey,
          vaultAuthority: this.vaultAuthority,
          whirlpoolProgram: WHIRLPOOL_PROGRAM_ID,
          whirlpool: state.poolId,
          position: state.positionKey,
          positionTokenAccount,
          vaultTokenA: state.vaultTokenA,
          vaultUsdc: state.vaultUsdc,
          tokenVaultA: whirlpoolData.tokenVaultA,
          tokenVaultB: whirlpoolData.tokenVaultB,
          keeper: this.keeper.publicKey,
          tokenProgram: TOKEN_PROGRAM_ID,
        })
        .rpc();
      console.log(`✓ Collect fees TX: ${collectTx}`);

      // Step 3: Swap token_a to USDC (if configured)
      if (state.config.forceSwapToUsdc) {
        console.log('Step 3: Swapping token_a to USDC...');
        const swapTx = await this.executeSwapToUSDC(state);
        console.log(`✓ Swap TX: ${swapTx}`);
      } else {
        console.log('Step 3: Skipping swap (force_swap_to_usdc = false)');
      }

      console.log('Step 4: Marking vault as exited...');
      // Step 4: Mark as exited
      const markTx = await this.program.methods
        .markExitedToUsdc()
        .accounts({
          vault: this.vaultPubkey,
          keeper: this.keeper.publicKey,
          clock: SYSVAR_CLOCK_PUBKEY,
        })
        .rpc();
      console.log(`✓ Mark exited TX: ${markTx}`);

      console.log(`\n✅ Exit strategy completed successfully!`);
      return markTx;
    } catch (error) {
      console.error('Error executing exit:', error);
      throw error;
    }
  }

  /**
   * Execute swap to USDC using Jupiter
   */
  private async executeSwapToUSDC(state: VaultState): Promise<string> {
    // Get token_a balance
    const tokenAAccount = await this.connection.getTokenAccountBalance(state.vaultTokenA);
    const amountIn = tokenAAccount.value.uiAmount;

    if (!amountIn || amountIn === 0) {
      console.log('No token_a to swap, skipping...');
      return 'skipped';
    }

    console.log(`Getting Jupiter quote for ${amountIn} token_a...`);

    // Get Jupiter quote
    const quote = await this.jupiterClient.getQuote(
      state.tokenAMint,
      state.usdcMint,
      Number(tokenAAccount.value.amount),
      state.config.slippageBps
    );

    // Check price impact
    if (!this.jupiterClient.isQuoteAcceptable(quote, 5.0)) {
      console.warn(`Warning: High price impact (${quote.priceImpactPct}%)`);
    }

    // Get swap instructions from Jupiter
    const swapInstructions = await this.jupiterClient.getSwapInstructions(
      quote,
      this.vaultAuthority
    );

    // Build remaining accounts from Jupiter instructions
    const remainingAccounts = swapInstructions.swapInstruction.accounts.map(acc => ({
      pubkey: new PublicKey(acc.pubkey),
      isWritable: acc.isWritable,
      isSigner: acc.isSigner,
    }));

    // Execute swap instruction
    const swapTx = await this.program.methods
      .swapAllToUsdc()
      .accounts({
        vault: this.vaultPubkey,
        vaultAuthority: this.vaultAuthority,
        jupiterProgram: JUPITER_PROGRAM_ID,
        tokenAMint: state.tokenAMint,
        usdcMint: state.usdcMint,
        vaultTokenA: state.vaultTokenA,
        vaultUsdc: state.vaultUsdc,
        keeper: this.keeper.publicKey,
        tokenProgram: TOKEN_PROGRAM_ID,
      })
      .remainingAccounts(remainingAccounts)
      .rpc();

    return swapTx;
  }

  /**
   * Execute reentry operation (increase liquidity on existing position)
   */
  async executeReentry(twapPrice: number, targetLiquidity: BN): Promise<string> {
    console.log(`\n=== Executing Reentry Strategy ===`);
    console.log(`TWAP Price: $${twapPrice.toFixed(4)}`);
    console.log(`Target Liquidity: ${targetLiquidity.toString()}`);

    try {
      const state = await this.fetchVaultState();

      // Validate state
      if (state.status !== VaultStatus.ExitedToUSDC) {
        throw new Error(`Cannot reenter: vault status is ${VaultStatus[state.status]}, expected ExitedToUSDC`);
      }

      if (state.operationInProgress) {
        throw new Error('Cannot reenter: operation already in progress');
      }

      // Check cooldown
      const { canReenter, cooldownRemaining } = await this.canReenter();
      if (!canReenter) {
        throw new Error(`Cooldown not met: ${cooldownRemaining}ms remaining`);
      }

      // Fetch whirlpool data
      const whirlpoolData = await this.fetchWhirlpoolData(state.poolId);

      // Derive tick arrays
      const tickArrayLowerStart = getTickArrayStartIndex(state.tickLower, whirlpoolData.tickSpacing);
      const tickArrayUpperStart = getTickArrayStartIndex(state.tickUpper, whirlpoolData.tickSpacing);
      const [tickArrayLower] = deriveTickArray(state.poolId, tickArrayLowerStart);
      const [tickArrayUpper] = deriveTickArray(state.poolId, tickArrayUpperStart);

      // Get position token account
      const positionTokenAccount = deriveAssociatedTokenAddress(
        this.vaultAuthority,
        state.positionKey
      );

      console.log('Increasing liquidity on existing position...');

      // Execute reentry
      const tx = await this.program.methods
        .reenterWithLiquidity(targetLiquidity)
        .accounts({
          vault: this.vaultPubkey,
          vaultAuthority: this.vaultAuthority,
          whirlpoolProgram: WHIRLPOOL_PROGRAM_ID,
          whirlpool: state.poolId,
          position: state.positionKey,
          positionTokenAccount,
          vaultTokenA: state.vaultTokenA,
          vaultUsdc: state.vaultUsdc,
          tokenVaultA: whirlpoolData.tokenVaultA,
          tokenVaultB: whirlpoolData.tokenVaultB,
          tickArrayLower,
          tickArrayUpper,
          keeper: this.keeper.publicKey,
          clock: SYSVAR_CLOCK_PUBKEY,
          tokenProgram: TOKEN_PROGRAM_ID,
        })
        .rpc();

      console.log(`✅ Reentry completed successfully!`);
      console.log(`TX: ${tx}`);

      return tx;
    } catch (error) {
      console.error('Error executing reentry:', error);
      throw error;
    }
  }

  /**
   * Fetch whirlpool account data
   * This is a simplified version - in production you'd use the Whirlpool SDK
   */
  private async fetchWhirlpoolData(whirlpoolPubkey: PublicKey): Promise<{
    tokenMintA: PublicKey;
    tokenMintB: PublicKey;
    tokenVaultA: PublicKey;
    tokenVaultB: PublicKey;
    tickSpacing: number;
  }> {
    try {
      const accountInfo = await this.connection.getAccountInfo(whirlpoolPubkey);

      if (!accountInfo) {
        throw new Error('Whirlpool account not found');
      }

      const data = accountInfo.data;

      // Parse whirlpool account data (simplified)
      // Actual layout: discriminator(8) + whirlpools_config(32) + whirlpool_bump(1) +
      // tick_spacing(2) + tick_spacing_seed(2) + fee_rate(2) + protocol_fee_rate(2) +
      // liquidity(16) + sqrt_price(16) + tick_current_index(4) + protocol_fee_owed_a(8) +
      // protocol_fee_owed_b(8) + token_mint_a(32) + token_vault_a(32) +
      // fee_growth_global_a(16) + token_mint_b(32) + token_vault_b(32) + ...

      const tokenMintA = new PublicKey(data.slice(101, 133));
      const tokenVaultA = new PublicKey(data.slice(133, 165));
      const tokenMintB = new PublicKey(data.slice(181, 213));
      const tokenVaultB = new PublicKey(data.slice(213, 245));
      const tickSpacing = data.readUInt16LE(41);

      return {
        tokenMintA,
        tokenMintB,
        tokenVaultA,
        tokenVaultB,
        tickSpacing,
      };
    } catch (error) {
      console.error('Error fetching whirlpool data:', error);
      throw error;
    }
  }

  /**
   * Get the keeper's public key
   */
  getKeeperPublicKey(): PublicKey {
    return this.keeper.publicKey;
  }

  /**
   * Get the vault public key
   */
  getVaultPublicKey(): PublicKey {
    return this.vaultPubkey;
  }

  /**
   * Get the program
   */
  getProgram(): Program<DeltaneutroxVault> {
    return this.program;
  }
}
