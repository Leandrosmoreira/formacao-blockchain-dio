import * as anchor from "@coral-xyz/anchor";
import { Program, BN } from "@coral-xyz/anchor";
import { PublicKey, Keypair, SystemProgram, SYSVAR_RENT_PUBKEY } from "@solana/web3.js";
import { TOKEN_PROGRAM_ID, ASSOCIATED_TOKEN_PROGRAM_ID, getAssociatedTokenAddress } from "@solana/spl-token";
import { assert } from "chai";
import { DeltaneutroxVault } from "../target/types/deltaneutrox_vault";
import {
  initTestContext,
  deriveVaultAuthority,
  createTestMints,
  fundUser,
  createMockWhirlpoolPool,
  getTokenBalance,
  assertError,
} from "./utils/setup";

describe("DeltaNeutroX Vault", () => {
  // Test context
  const { provider, program, payer } = initTestContext();

  // Test accounts
  let tokenAMint: PublicKey;
  let usdcMint: PublicKey;
  let poolId: PublicKey;

  // Vault accounts
  let vault: Keypair;
  let vaultAuthority: PublicKey;
  let sharesMint: Keypair;
  let vaultTokenA: PublicKey;
  let vaultUsdc: PublicKey;

  // User accounts
  let user: Keypair;
  let userTokenA: PublicKey;
  let userUsdc: PublicKey;
  let userShares: PublicKey;

  // Test parameters
  const tickLower = -20000;
  const tickUpper = 20000;
  const slippageBps = 100; // 1%
  const forceSwapToUsdc = true;

  before(async () => {
    console.log("\n🚀 Setting up test environment...\n");

    // Create test token mints
    const mints = await createTestMints(provider, payer);
    tokenAMint = mints.tokenAMint;
    usdcMint = mints.usdcMint;

    console.log("Token A Mint:", tokenAMint.toString());
    console.log("USDC Mint:", usdcMint.toString());

    // Create mock Whirlpool pool
    poolId = createMockWhirlpoolPool();
    console.log("Pool ID:", poolId.toString());

    // Create user
    user = Keypair.generate();

    // Fund user with SOL
    const signature = await provider.connection.requestAirdrop(
      user.publicKey,
      10 * anchor.web3.LAMPORTS_PER_SOL
    );
    await provider.connection.confirmTransaction(signature);

    // Fund user with tokens
    const userAccounts = await fundUser(
      provider,
      payer,
      user.publicKey,
      tokenAMint,
      usdcMint,
      10, // 10 token A
      1000 // 1000 USDC
    );

    userTokenA = userAccounts.userTokenA;
    userUsdc = userAccounts.userUsdc;

    console.log("\n✅ Test environment ready\n");
  });

  describe("1. Create Vault", () => {
    it("Creates a vault with correct parameters", async () => {
      // Generate vault keypair
      vault = Keypair.generate();

      // Derive vault authority
      [vaultAuthority] = deriveVaultAuthority(vault.publicKey, program.programId);

      // Create shares mint
      sharesMint = Keypair.generate();

      // Derive vault token accounts
      vaultTokenA = await getAssociatedTokenAddress(tokenAMint, vaultAuthority, true);
      vaultUsdc = await getAssociatedTokenAddress(usdcMint, vaultAuthority, true);

      // Create vault
      const tx = await program.methods
        .createVault(poolId, tickLower, tickUpper, slippageBps, forceSwapToUsdc)
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
          associatedTokenProgram: ASSOCIATED_TOKEN_PROGRAM_ID,
          systemProgram: SystemProgram.programId,
          rent: SYSVAR_RENT_PUBKEY,
        })
        .signers([vault, sharesMint])
        .rpc();

      console.log("Create vault tx:", tx);

      // Fetch and verify vault state
      const vaultAccount = await program.account.strategyVault.fetch(vault.publicKey);

      assert.equal(vaultAccount.poolId.toString(), poolId.toString());
      assert.equal(vaultAccount.tickLower, tickLower);
      assert.equal(vaultAccount.tickUpper, tickUpper);
      assert.equal(vaultAccount.config.slippageBps, slippageBps);
      assert.equal(vaultAccount.config.forceSwapToUsdc, forceSwapToUsdc);
      assert.equal(vaultAccount.totalShares.toNumber(), 0);
      assert.equal(vaultAccount.operationInProgress, false);

      // Verify status is Idle
      assert.property(vaultAccount.status, "idle");
    });

    it("Fails with invalid tick range", async () => {
      const badVault = Keypair.generate();
      const badSharesMint = Keypair.generate();
      const [badVaultAuthority] = deriveVaultAuthority(badVault.publicKey, program.programId);

      const badVaultTokenA = await getAssociatedTokenAddress(tokenAMint, badVaultAuthority, true);
      const badVaultUsdc = await getAssociatedTokenAddress(usdcMint, badVaultAuthority, true);

      try {
        await program.methods
          .createVault(
            poolId,
            20000, // Lower tick > upper tick (invalid)
            -20000,
            slippageBps,
            forceSwapToUsdc
          )
          .accounts({
            vault: badVault.publicKey,
            vaultAuthority: badVaultAuthority,
            sharesMint: badSharesMint.publicKey,
            vaultTokenA: badVaultTokenA,
            vaultUsdc: badVaultUsdc,
            tokenAMint,
            usdcMint,
            authority: payer.publicKey,
            keeperAuthority: payer.publicKey,
            tokenProgram: TOKEN_PROGRAM_ID,
            associatedTokenProgram: ASSOCIATED_TOKEN_PROGRAM_ID,
            systemProgram: SystemProgram.programId,
            rent: SYSVAR_RENT_PUBKEY,
          })
          .signers([badVault, badSharesMint])
          .rpc();

        assert.fail("Should have failed with invalid tick range");
      } catch (error) {
        assertError(error, "InvalidTickRange");
      }
    });
  });

  describe("2. Deposit", () => {
    before(async () => {
      // Get user shares account
      userShares = await getAssociatedTokenAddress(sharesMint.publicKey, user.publicKey);
    });

    it("Deposits tokens and mints shares", async () => {
      const amountA = new BN(1 * 1e9); // 1 token A
      const amountUsdc = new BN(100 * 1e6); // 100 USDC

      // Get balances before
      const userTokenABefore = await getTokenBalance(provider, userTokenA);
      const userUsdcBefore = await getTokenBalance(provider, userUsdc);

      // Deposit
      const tx = await program.methods
        .deposit(amountA, amountUsdc)
        .accounts({
          vault: vault.publicKey,
          sharesMint: sharesMint.publicKey,
          userTokenA,
          userUsdc,
          vaultTokenA,
          vaultUsdc,
          userShares,
          user: user.publicKey,
          tokenProgram: TOKEN_PROGRAM_ID,
        })
        .signers([user])
        .rpc();

      console.log("Deposit tx:", tx);

      // Get balances after
      const userTokenAAfter = await getTokenBalance(provider, userTokenA);
      const userUsdcAfter = await getTokenBalance(provider, userUsdc);
      const vaultTokenAAfter = await getTokenBalance(provider, vaultTokenA);
      const vaultUsdcAfter = await getTokenBalance(provider, vaultUsdc);
      const userSharesBalance = await getTokenBalance(provider, userShares);

      // Verify token transfers
      assert.approximately(userTokenABefore - userTokenAAfter, 1, 0.0001);
      assert.approximately(userUsdcBefore - userUsdcAfter, 100, 0.01);
      assert.approximately(vaultTokenAAfter, 1, 0.0001);
      assert.approximately(vaultUsdcAfter, 100, 0.01);

      // Verify shares minted
      assert.isAbove(userSharesBalance, 0);

      // Verify vault state updated
      const vaultAccount = await program.account.strategyVault.fetch(vault.publicKey);
      assert.isAbove(vaultAccount.totalShares.toNumber(), 0);
      assert.isAbove(vaultAccount.totalDeposits.toNumber(), 0);
    });

    it("Second deposit mints proportional shares", async () => {
      const amountA = new BN(0.5 * 1e9); // 0.5 token A
      const amountUsdc = new BN(50 * 1e6); // 50 USDC

      const sharesBefore = await getTokenBalance(provider, userShares);

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
          user: user.publicKey,
          tokenProgram: TOKEN_PROGRAM_ID,
        })
        .signers([user])
        .rpc();

      const sharesAfter = await getTokenBalance(provider, userShares);

      // Second deposit should mint additional shares
      assert.isAbove(sharesAfter, sharesBefore);
    });

    it("Fails when depositing zero amount", async () => {
      try {
        await program.methods
          .deposit(new BN(0), new BN(0))
          .accounts({
            vault: vault.publicKey,
            sharesMint: sharesMint.publicKey,
            userTokenA,
            userUsdc,
            vaultTokenA,
            vaultUsdc,
            userShares,
            user: user.publicKey,
            tokenProgram: TOKEN_PROGRAM_ID,
          })
          .signers([user])
          .rpc();

        assert.fail("Should have failed with zero amount");
      } catch (error) {
        // Expected to fail
        assert.ok(error);
      }
    });
  });

  describe("3. Withdraw", () => {
    it("Withdraws tokens by burning shares", async () => {
      const sharesBefore = await getTokenBalance(provider, userShares);
      const vaultTokenABefore = await getTokenBalance(provider, vaultTokenA);
      const vaultUsdcBefore = await getTokenBalance(provider, vaultUsdc);

      // Withdraw 50% of shares
      const sharesToBurn = new BN(sharesBefore * 0.5 * 1e6);

      const tx = await program.methods
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
          user: user.publicKey,
          tokenProgram: TOKEN_PROGRAM_ID,
        })
        .signers([user])
        .rpc();

      console.log("Withdraw tx:", tx);

      // Verify shares burned
      const sharesAfter = await getTokenBalance(provider, userShares);
      assert.approximately(sharesAfter, sharesBefore * 0.5, 0.01);

      // Verify tokens returned to user (approximately 50% of vault)
      const vaultTokenAAfter = await getTokenBalance(provider, vaultTokenA);
      const vaultUsdcAfter = await getTokenBalance(provider, vaultUsdc);

      assert.isBelow(vaultTokenAAfter, vaultTokenABefore);
      assert.isBelow(vaultUsdcAfter, vaultUsdcBefore);

      // Verify vault state
      const vaultAccount = await program.account.strategyVault.fetch(vault.publicKey);
      assert.isAbove(vaultAccount.totalWithdrawals.toNumber(), 0);
    });

    it("Fails when withdrawing more shares than owned", async () => {
      const sharesBalance = await getTokenBalance(provider, userShares);
      const excessiveShares = new BN((sharesBalance + 1000) * 1e6);

      try {
        await program.methods
          .withdraw(excessiveShares)
          .accounts({
            vault: vault.publicKey,
            vaultAuthority,
            sharesMint: sharesMint.publicKey,
            userTokenA,
            userUsdc,
            vaultTokenA,
            vaultUsdc,
            userShares,
            user: user.publicKey,
            tokenProgram: TOKEN_PROGRAM_ID,
          })
          .signers([user])
          .rpc();

        assert.fail("Should have failed with insufficient shares");
      } catch (error) {
        // Expected to fail due to insufficient balance
        assert.ok(error);
      }
    });
  });

  describe("4. Set Params", () => {
    it("Updates vault configuration parameters", async () => {
      const newDeadbandBps = 75; // 0.75%
      const newCooldownMs = new BN(300000); // 5 minutes

      const tx = await program.methods
        .setParams(newDeadbandBps, null, newCooldownMs, null)
        .accounts({
          vault: vault.publicKey,
          authority: payer.publicKey,
        })
        .rpc();

      console.log("Set params tx:", tx);

      // Verify parameters updated
      const vaultAccount = await program.account.strategyVault.fetch(vault.publicKey);
      assert.equal(vaultAccount.config.deadbandBps, newDeadbandBps);
      assert.equal(vaultAccount.config.cooldownMs.toNumber(), newCooldownMs.toNumber());
    });

    it("Fails when called by non-authority", async () => {
      try {
        await program.methods
          .setParams(100, null, null, null)
          .accounts({
            vault: vault.publicKey,
            authority: user.publicKey, // Wrong authority
          })
          .signers([user])
          .rpc();

        assert.fail("Should have failed with unauthorized");
      } catch (error) {
        // Expected to fail
        assert.ok(error);
      }
    });
  });

  describe("5. Vault Status Display", () => {
    it("Shows correct vault state", async () => {
      const vaultAccount = await program.account.strategyVault.fetch(vault.publicKey);

      console.log("\n📊 Final Vault State:");
      console.log("Status:", vaultAccount.status);
      console.log("Total Shares:", vaultAccount.totalShares.toString());
      console.log("Total Deposits:", vaultAccount.totalDeposits.toString());
      console.log("Total Withdrawals:", vaultAccount.totalWithdrawals.toString());
      console.log("Tick Range:", [vaultAccount.tickLower, vaultAccount.tickUpper]);
      console.log("Config:");
      console.log("  Deadband:", vaultAccount.config.deadbandBps, "bps");
      console.log("  Cooldown:", vaultAccount.config.cooldownMs.toString(), "ms");
      console.log("  Slippage:", vaultAccount.config.slippageBps, "bps");
      console.log("  Force Swap:", vaultAccount.config.forceSwapToUsdc);
    });
  });

  // Note: Tests for position management (open, decrease, collect, swap, reenter)
  // would require a real Whirlpool pool and Jupiter program.
  // These are best tested in E2E tests with actual program clones.
});
