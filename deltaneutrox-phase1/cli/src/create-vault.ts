#!/usr/bin/env ts-node

import { Command } from 'commander';
import { PublicKey, Keypair, SystemProgram, SYSVAR_RENT_PUBKEY } from '@solana/web3.js';
import { TOKEN_PROGRAM_ID, ASSOCIATED_TOKEN_PROGRAM_ID, getAssociatedTokenAddress } from '@solana/spl-token';
import chalk from 'chalk';
import ora from 'ora';
import {
  loadConfig,
  initProgram,
  deriveVaultAuthority,
  confirmTx,
  getBalance,
  displayError,
} from './utils';

const program = new Command();

program
  .name('create-vault')
  .description('Create a new DeltaNeutroX vault')
  .requiredOption('-p, --pool <address>', 'Whirlpool pool address')
  .requiredOption('-a, --token-a <address>', 'Token A mint address')
  .requiredOption('-u, --usdc <address>', 'USDC mint address')
  .requiredOption('-l, --tick-lower <number>', 'Lower tick boundary', parseInt)
  .requiredOption('-U, --tick-upper <number>', 'Upper tick boundary', parseInt)
  .option('-s, --slippage <bps>', 'Slippage tolerance in basis points', '100')
  .option('-f, --force-swap', 'Force swap to USDC on exit', true)
  .option('-k, --keeper <address>', 'Keeper authority (defaults to wallet)')
  .parse(process.argv);

const opts = program.opts();

async function main() {
  console.log(chalk.bold.cyan('\n🚀 DeltaNeutroX Vault Creation\n'));

  try {
    // Load configuration
    const config = loadConfig();
    console.log(chalk.gray(`RPC: ${config.rpcUrl}`));
    console.log(chalk.gray(`Program: ${config.programId.toString()}`));

    // Initialize program
    const { program: anchorProgram, provider, wallet } = initProgram(config);

    console.log(chalk.gray(`Wallet: ${wallet.publicKey.toString()}`));

    // Check balance
    const balance = await getBalance(provider.connection, wallet.publicKey);
    console.log(chalk.gray(`Balance: ${balance.toFixed(4)} SOL\n`));

    if (balance < 0.5) {
      console.log(chalk.yellow('⚠️  Low SOL balance. You may need to airdrop:'));
      console.log(chalk.gray(`   solana airdrop 2 ${wallet.publicKey.toString()}\n`));
    }

    // Parse inputs
    const poolId = new PublicKey(opts.pool);
    const tokenAMint = new PublicKey(opts.tokenA);
    const usdcMint = new PublicKey(opts.usdc);
    const tickLower = opts.tickLower;
    const tickUpper = opts.tickUpper;
    const slippageBps = parseInt(opts.slippage);
    const forceSwapToUsdc = opts.forceSwap;
    const keeperAuthority = opts.keeper ? new PublicKey(opts.keeper) : wallet.publicKey;

    // Validate ticks
    if (tickLower >= tickUpper) {
      throw new Error('tick-lower must be less than tick-upper');
    }

    // Generate vault keypair
    const vault = Keypair.generate();

    console.log(chalk.bold('📋 Vault Configuration:'));
    console.log(chalk.gray(`Vault Address: ${chalk.white(vault.publicKey.toString())}`));
    console.log(chalk.gray(`Pool: ${poolId.toString()}`));
    console.log(chalk.gray(`Token A: ${tokenAMint.toString()}`));
    console.log(chalk.gray(`USDC: ${usdcMint.toString()}`));
    console.log(chalk.gray(`Tick Range: [${tickLower}, ${tickUpper}]`));
    console.log(chalk.gray(`Slippage: ${slippageBps} bps (${(slippageBps / 100).toFixed(2)}%)`));
    console.log(chalk.gray(`Force Swap to USDC: ${forceSwapToUsdc}`));
    console.log(chalk.gray(`Keeper: ${keeperAuthority.toString()}\n`));

    // Derive PDAs
    const [vaultAuthority] = deriveVaultAuthority(vault.publicKey, config.programId);

    // Create shares mint
    const sharesMint = Keypair.generate();

    // Derive token accounts
    const vaultTokenA = await getAssociatedTokenAddress(tokenAMint, vaultAuthority, true);
    const vaultUsdc = await getAssociatedTokenAddress(usdcMint, vaultAuthority, true);

    const spinner = ora('Creating vault...').start();

    try {
      // Create vault instruction
      const tx = await anchorProgram.methods
        .createVault(
          poolId,
          tickLower,
          tickUpper,
          slippageBps,
          forceSwapToUsdc
        )
        .accounts({
          vault: vault.publicKey,
          vaultAuthority,
          sharesMint: sharesMint.publicKey,
          vaultTokenA,
          vaultUsdc,
          tokenAMint,
          usdcMint,
          authority: wallet.publicKey,
          keeperAuthority,
          tokenProgram: TOKEN_PROGRAM_ID,
          associatedTokenProgram: ASSOCIATED_TOKEN_PROGRAM_ID,
          systemProgram: SystemProgram.programId,
          rent: SYSVAR_RENT_PUBKEY,
        })
        .signers([vault, sharesMint])
        .rpc();

      spinner.succeed('Vault created successfully!');

      console.log(chalk.green('\n✅ Transaction confirmed'));
      console.log(chalk.gray(`Signature: ${tx}`));
      console.log(chalk.gray(`Explorer: https://explorer.solana.com/tx/${tx}?cluster=devnet`));

      console.log(chalk.bold.green('\n🎉 Vault Created!\n'));
      console.log(chalk.bold('Save these addresses:'));
      console.log(chalk.cyan(`Vault:       ${vault.publicKey.toString()}`));
      console.log(chalk.cyan(`Shares Mint: ${sharesMint.publicKey.toString()}`));
      console.log(chalk.cyan(`Authority:   ${vaultAuthority.toString()}`));

      console.log(chalk.gray('\nAdd to your .env:'));
      console.log(chalk.white(`VAULT_PUBKEY=${vault.publicKey.toString()}`));

      console.log(chalk.gray('\nNext steps:'));
      console.log(chalk.gray('1. Fund the vault: npm run deposit'));
      console.log(chalk.gray('2. Open position: Use keeper or manual'));
      console.log(chalk.gray('3. View vault: npm run view-vault'));

    } catch (error) {
      spinner.fail('Vault creation failed');
      throw error;
    }

  } catch (error) {
    console.error(chalk.red('\n❌ Error:'));
    displayError(error);
    process.exit(1);
  }
}

main();
