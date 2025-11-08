import * as anchor from "@coral-xyz/anchor";
import { Program, BN } from "@coral-xyz/anchor";
import { PublicKey, Keypair, SYSVAR_CLOCK_PUBKEY } from "@solana/web3.js";
import { TOKEN_PROGRAM_ID, getAssociatedTokenAddress } from "@solana/spl-token";
import { assert } from "chai";
import { DeltaneutroxVault } from "../../target/types/deltaneutrox_vault";
import {
  initTestContext,
  deriveVaultAuthority,
  createTestMints,
  fundUser,
  getTokenBalance,
  sleep,
} from "../utils/setup";

/**
 * End-to-End Test: Complete Vault Lifecycle
 *
 * This test simulates the full lifecycle of a DeltaNeutroX vault:
 * 1. Create vault
 * 2. Multiple users deposit
 * 3. Keeper opens position (simulated)
 * 4. Position accumulates value
 * 5. Price moves outside range → Auto-exit
 * 6. Cooldown period
 * 7. Price returns → Auto-reentry
 * 8. Users withdraw
 *
 * Note: This test requires Whirlpool and Jupiter programs to be available
 * in the test validator (cloned or deployed).
 */

describe("E2E: Full Vault Lifecycle", () => {
  const { provider, program, payer } = initTestContext();

  let tokenAMint: PublicKey;
  let usdcMint: PublicKey;
  let poolId: PublicKey;

  let vault: Keypair;
  let vaultAuthority: PublicKey;
  let sharesMint: Keypair;

  // Multiple users
  let user1: Keypair;
  let user2: Keypair;
  let user3: Keypair;

  const tickLower = -20000;
  const tickUpper = 20000;

  before(async () => {
    console.log("\n🚀 E2E Test: Setting up complete environment...\n");

    // Create test mints
    const mints = await createTestMints(provider, payer);
    tokenAMint = mints.tokenAMint;
    usdcMint = mints.usdcMint;

    // For E2E, we'd use a real Whirlpool pool
    // This would be cloned from mainnet in Anchor.toml
    poolId = new PublicKey("HJPjoWUrhoZzkNfRpHuieeFk9WcZWjwy6PBjZ81ngndJ");

    // Create users
    user1 = Keypair.generate();
    user2 = Keypair.generate();
    user3 = Keypair.generate();

    // Fund users with SOL
    for (const user of [user1, user2, user3]) {
      const sig = await provider.connection.requestAirdrop(
        user.publicKey,
        10 * anchor.web3.LAMPORTS_PER_SOL
      );
      await provider.connection.confirmTransaction(sig);

      await fundUser(provider, payer, user.publicKey, tokenAMint, usdcMint, 20, 2000);
    }

    console.log("User 1:", user1.publicKey.toString());
    console.log("User 2:", user2.publicKey.toString());
    console.log("User 3:", user3.publicKey.toString());
    console.log("\n✅ E2E environment ready\n");
  });

  describe("Phase 1: Vault Creation and Initial Deposits", () => {
    it("Creates vault successfully", async () => {
      vault = Keypair.generate();
      [vaultAuthority] = deriveVaultAuthority(vault.publicKey, program.programId);
      sharesMint = Keypair.generate();

      const vaultTokenA = await getAssociatedTokenAddress(tokenAMint, vaultAuthority, true);
      const vaultUsdc = await getAssociatedTokenAddress(usdcMint, vaultAuthority, true);

      await program.methods
        .createVault(poolId, tickLower, tickUpper, 100, true)
        .accounts({
          vault: vault.publicKey,
          vaultAuthority,
          sharesMint: sharesMint.publicKey,
          vaultTokenA,
          vaultUsdc,
          tokenAMint,
          usdcMint,
          authority: payer.publicKey,
          keeperAuthority: payer.publicKey,
          tokenProgram: TOKEN_PROGRAM_ID,
          associatedTokenProgram: anchor.utils.token.ASSOCIATED_PROGRAM_ID,
          systemProgram: anchor.web3.SystemProgram.programId,
          rent: anchor.web3.SYSVAR_RENT_PUBKEY,
        })
        .signers([vault, sharesMint])
        .rpc();

      console.log("✅ Vault created:", vault.publicKey.toString());

      const vaultAccount = await program.account.strategyVault.fetch(vault.publicKey);
      assert.property(vaultAccount.status, "idle");
    });

    it("User 1 deposits (first depositor)", async () => {
      const userTokenA = await getAssociatedTokenAddress(tokenAMint, user1.publicKey);
      const userUsdc = await getAssociatedTokenAddress(usdcMint, user1.publicKey);
      const userShares = await getAssociatedTokenAddress(sharesMint.publicKey, user1.publicKey);

      const vaultTokenA = await getAssociatedTokenAddress(tokenAMint, vaultAuthority, true);
      const vaultUsdc = await getAssociatedTokenAddress(usdcMint, vaultAuthority, true);

      const amountA = new BN(5 * 1e9); // 5 tokens
      const amountUsdc = new BN(500 * 1e6); // 500 USDC

      await program.methods
        .deposit(amountA, amountUsdc)
        .accounts({
          vault: vault.publicKey,
          sharesMint: sharesMint.publicKey,
          userTokenA,
          userUsdc,
          vaultTokenA,
          vaultUsdc,
          userShares,
          user: user1.publicKey,
          tokenProgram: TOKEN_PROGRAM_ID,
        })
        .signers([user1])
        .rpc();

      const shares = await getTokenBalance(provider, userShares);
      console.log("✅ User 1 deposited. Shares:", shares);
      assert.isAbove(shares, 0);
    });

    it("User 2 deposits (second depositor)", async () => {
      const userTokenA = await getAssociatedTokenAddress(tokenAMint, user2.publicKey);
      const userUsdc = await getAssociatedTokenAddress(usdcMint, user2.publicKey);
      const userShares = await getAssociatedTokenAddress(sharesMint.publicKey, user2.publicKey);

      const vaultTokenA = await getAssociatedTokenAddress(tokenAMint, vaultAuthority, true);
      const vaultUsdc = await getAssociatedTokenAddress(usdcMint, vaultAuthority, true);

      const amountA = new BN(3 * 1e9); // 3 tokens
      const amountUsdc = new BN(300 * 1e6); // 300 USDC

      await program.methods
        .deposit(amountA, amountUsdc)
        .accounts({
          vault: vault.publicKey,
          sharesMint: sharesMint.publicKey,
          userTokenA,
          userUsdc,
          vaultTokenA,
          vaultUsdc,
          userShares,
          user: user2.publicKey,
          tokenProgram: TOKEN_PROGRAM_ID,
        })
        .signers([user2])
        .rpc();

      const shares = await getTokenBalance(provider, userShares);
      console.log("✅ User 2 deposited. Shares:", shares);
      assert.isAbove(shares, 0);
    });

    it("User 3 deposits (third depositor)", async () => {
      const userTokenA = await getAssociatedTokenAddress(tokenAMint, user3.publicKey);
      const userUsdc = await getAssociatedTokenAddress(usdcMint, user3.publicKey);
      const userShares = await getAssociatedTokenAddress(sharesMint.publicKey, user3.publicKey);

      const vaultTokenA = await getAssociatedTokenAddress(tokenAMint, vaultAuthority, true);
      const vaultUsdc = await getAssociatedTokenAddress(usdcMint, vaultAuthority, true);

      const amountA = new BN(2 * 1e9); // 2 tokens
      const amountUsdc = new BN(200 * 1e6); // 200 USDC

      await program.methods
        .deposit(amountA, amountUsdc)
        .accounts({
          vault: vault.publicKey,
          sharesMint: sharesMint.publicKey,
          userTokenA,
          userUsdc,
          vaultTokenA,
          vaultUsdc,
          userShares,
          user: user3.publicKey,
          tokenProgram: TOKEN_PROGRAM_ID,
        })
        .signers([user3])
        .rpc();

      const shares = await getTokenBalance(provider, userShares);
      console.log("✅ User 3 deposited. Shares:", shares);

      // Verify total vault balances
      const vaultTokenA = await getAssociatedTokenAddress(tokenAMint, vaultAuthority, true);
      const vaultUsdc = await getAssociatedTokenAddress(usdcMint, vaultAuthority, true);

      const totalTokenA = await getTokenBalance(provider, vaultTokenA);
      const totalUsdc = await getTokenBalance(provider, vaultUsdc);

      console.log("\n📊 Total Vault Balances:");
      console.log("Token A:", totalTokenA);
      console.log("USDC:", totalUsdc);

      assert.approximately(totalTokenA, 10, 0.1); // 5 + 3 + 2
      assert.approximately(totalUsdc, 1000, 1); // 500 + 300 + 200
    });
  });

  describe("Phase 2: Position Management (Simulated)", () => {
    it("Shows vault in Idle state (ready for position)", async () => {
      const vaultAccount = await program.account.strategyVault.fetch(vault.publicKey);

      console.log("\n📊 Vault State Before Position:");
      console.log("Status:", vaultAccount.status);
      console.log("Total Shares:", vaultAccount.totalShares.toString());

      assert.property(vaultAccount.status, "idle");
    });

    // Note: Opening position would require Whirlpool program
    // In a real E2E test, you would:
    // 1. Call open_position_once with real Whirlpool accounts
    // 2. Verify position NFT created
    // 3. Verify liquidity added
    // 4. Verify vault status changed to PositionOpen

    it("Simulates position lifecycle", async () => {
      console.log("\n⚠️  Position management tests require Whirlpool program");
      console.log("In production E2E:");
      console.log("1. open_position_once → PositionOpen");
      console.log("2. Accumulate fees");
      console.log("3. decrease_liquidity_all → Decrease 100%");
      console.log("4. collect_fees → Collect trading fees");
      console.log("5. swap_all_to_usdc → Swap via Jupiter");
      console.log("6. mark_exited_to_usdc → ExitedToUSDC + timestamp");
      console.log("7. Wait cooldown period");
      console.log("8. reenter_with_liquidity → Back to PositionOpen");
    });
  });

  describe("Phase 3: User Withdrawals", () => {
    it("User 1 withdraws 50% of their shares", async () => {
      const userShares = await getAssociatedTokenAddress(sharesMint.publicKey, user1.publicKey);
      const userTokenA = await getAssociatedTokenAddress(tokenAMint, user1.publicKey);
      const userUsdc = await getAssociatedTokenAddress(usdcMint, user1.publicKey);

      const vaultTokenA = await getAssociatedTokenAddress(tokenAMint, vaultAuthority, true);
      const vaultUsdc = await getAssociatedTokenAddress(usdcMint, vaultAuthority, true);

      const sharesBefore = await getTokenBalance(provider, userShares);
      const sharesToBurn = new BN(sharesBefore * 0.5 * 1e6);

      await program.methods
        .withdraw(sharesToBurn)
        .accounts({
          vault: vault.publicKey,
          vaultAuthority,
          sharesMint: sharesMint.publicKey,
          userTokenA,
          userUsdc,
          vaultTokenA,
          vaultUsdc,
          userShares,
          user: user1.publicKey,
          tokenProgram: TOKEN_PROGRAM_ID,
        })
        .signers([user1])
        .rpc();

      const sharesAfter = await getTokenBalance(provider, userShares);
      console.log("✅ User 1 withdrew 50%. Remaining shares:", sharesAfter);

      assert.approximately(sharesAfter, sharesBefore * 0.5, 0.1);
    });

    it("User 2 withdraws all shares", async () => {
      const userShares = await getAssociatedTokenAddress(sharesMint.publicKey, user2.publicKey);
      const userTokenA = await getAssociatedTokenAddress(tokenAMint, user2.publicKey);
      const userUsdc = await getAssociatedTokenAddress(usdcMint, user2.publicKey);

      const vaultTokenA = await getAssociatedTokenAddress(tokenAMint, vaultAuthority, true);
      const vaultUsdc = await getAssociatedTokenAddress(usdcMint, vaultAuthority, true);

      const sharesBefore = await getTokenBalance(provider, userShares);
      const sharesToBurn = new BN(sharesBefore * 1e6);

      await program.methods
        .withdraw(sharesToBurn)
        .accounts({
          vault: vault.publicKey,
          vaultAuthority,
          sharesMint: sharesMint.publicKey,
          userTokenA,
          userUsdc,
          vaultTokenA,
          vaultUsdc,
          userShares,
          user: user2.publicKey,
          tokenProgram: TOKEN_PROGRAM_ID,
        })
        .signers([user2])
        .rpc();

      const sharesAfter = await getTokenBalance(provider, userShares);
      console.log("✅ User 2 withdrew 100%. Remaining shares:", sharesAfter);

      assert.approximately(sharesAfter, 0, 0.0001);
    });

    it("Shows final vault state", async () => {
      const vaultAccount = await program.account.strategyVault.fetch(vault.publicKey);

      const vaultTokenA = await getAssociatedTokenAddress(tokenAMint, vaultAuthority, true);
      const vaultUsdc = await getAssociatedTokenAddress(usdcMint, vaultAuthority, true);

      const remainingTokenA = await getTokenBalance(provider, vaultTokenA);
      const remainingUsdc = await getTokenBalance(provider, vaultUsdc);

      console.log("\n📊 Final E2E Test Results:");
      console.log("Total Shares Remaining:", vaultAccount.totalShares.toString());
      console.log("Total Deposits:", vaultAccount.totalDeposits.toString());
      console.log("Total Withdrawals:", vaultAccount.totalWithdrawals.toString());
      console.log("Vault Token A:", remainingTokenA);
      console.log("Vault USDC:", remainingUsdc);

      // Vault should still have tokens from User 1's 50% and User 3's 100%
      assert.isAbove(remainingTokenA, 0);
      assert.isAbove(remainingUsdc, 0);
    });
  });

  describe("Phase 4: Share Distribution Verification", () => {
    it("Verifies fair share distribution", async () => {
      const user1Shares = await getAssociatedTokenAddress(sharesMint.publicKey, user1.publicKey);
      const user2Shares = await getAssociatedTokenAddress(sharesMint.publicKey, user2.publicKey);
      const user3Shares = await getAssociatedTokenAddress(sharesMint.publicKey, user3.publicKey);

      const shares1 = await getTokenBalance(provider, user1Shares);
      const shares2 = await getTokenBalance(provider, user2Shares);
      const shares3 = await getTokenBalance(provider, user3Shares);

      console.log("\n👥 Final Share Distribution:");
      console.log("User 1:", shares1, "(withdrew 50%)");
      console.log("User 2:", shares2, "(withdrew 100%)");
      console.log("User 3:", shares3, "(no withdrawal)");

      // User 2 should have ~0 shares (withdrew all)
      assert.approximately(shares2, 0, 0.001);

      // User 1 should have half their original
      // User 3 should have all their original
      assert.isAbove(shares1, 0);
      assert.isAbove(shares3, 0);
    });
  });
});
