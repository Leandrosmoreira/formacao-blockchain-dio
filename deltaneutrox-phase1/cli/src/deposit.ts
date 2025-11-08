#!/usr/bin/env ts-node

import { Command } from 'commander';
import { PublicKey } from '@solana/web3.js';
import { TOKEN_PROGRAM_ID, getAssociatedTokenAddress, createAssociatedTokenAccountInstruction } from '@solana/spl-token';
import chalk from 'chalk';
import ora from 'ora';
import {
  loadConfig,
  initProgram,
  getAssociatedTokenAddresses,
  formatAmount,
  confirmTx,
  accountExists,
  displayError,
} from './utils';

const program = new Command();

program
  .name('deposit')
  .description('Deposit tokens into a DeltaNeutroX vault')
  .requiredOption('-v, --vault <address>', 'Vault address')
  .requiredOption('-a, --amount-a <number>', 'Amount of token A to deposit', parseFloat)
  .requiredOption('-u, --amount-usdc <number>', 'Amount of USDC to deposit', parseFloat)
  .option('-d, --decimals-a <number>', 'Token A decimals', '9')
  .option('-D, --decimals-usdc <number>', 'USDC decimals', '6')
  .parse(process.argv);

const opts = program.opts();

async function main() {
  console.log(chalk.bold.cyan('\n💰 Deposit to DeltaNeutroX Vault\n'));

  try {
    // Load configuration
    const config = loadConfig();
    const { program: anchorProgram, provider, wallet } = initProgram(config);

    console.log(chalk.gray(`Wallet: ${wallet.publicKey.toString()}`));
    console.log(chalk.gray(`Vault: ${opts.vault}\n`));

    // Parse inputs
    const vaultPubkey = new PublicKey(opts.vault);
    const decimalsA = parseInt(opts.decimalsA);
    const decimalsUsdc = parseInt(opts.decimalsUsdc);
    const amountA = Math.floor(opts.amountA * Math.pow(10, decimalsA));
    const amountUsdc = Math.floor(opts.amountUsdc * Math.pow(10, decimalsUsdc));

    console.log(chalk.bold('📋 Deposit Details:'));
    console.log(chalk.gray(`Token A: ${formatAmount(amountA, decimalsA)}`));
    console.log(chalk.gray(`USDC: ${formatAmount(amountUsdc, decimalsUsdc)}\n`));

    const spinner = ora('Fetching vault...').start();

    try {
      // Fetch vault state
      const vaultState = await anchorProgram.account.strategyVault.fetch(vaultPubkey);
      spinner.succeed('Vault fetched');

      const tokenAMint = vaultState.tokenAMint;
      const usdcMint = vaultState.usdcMint;
      const sharesMint = vaultState.sharesMint;

      console.log(chalk.gray(`Token A Mint: ${tokenAMint.toString()}`));
      console.log(chalk.gray(`USDC Mint: ${usdcMint.toString()}`));
      console.log(chalk.gray(`Shares Mint: ${sharesMint.toString()}\n`));

      // Get user token accounts
      const userAccounts = await getAssociatedTokenAddresses(
        wallet.publicKey,
        tokenAMint,
        usdcMint,
        sharesMint
      );

      // Get vault token accounts
      const vaultAccounts = await getAssociatedTokenAddresses(
        vaultState.authority,
        tokenAMint,
        usdcMint,
        sharesMint
      );

      // Check if user shares account exists, create if not
      const sharesExists = await accountExists(provider.connection, userAccounts.shares);

      spinner.start('Depositing tokens...');

      // Build transaction
      const tx = anchorProgram.methods
        .deposit(amountA, amountUsdc)
        .accounts({
          vault: vaultPubkey,
          sharesMint,
          userTokenA: userAccounts.tokenA,
          userUsdc: userAccounts.usdc,
          vaultTokenA: vaultAccounts.tokenA,
          vaultUsdc: vaultAccounts.usdc,
          userShares: userAccounts.shares,
          user: wallet.publicKey,
          tokenProgram: TOKEN_PROGRAM_ID,
        });

      // Add create ATA instruction if needed
      if (!sharesExists) {
        const createAtaIx = createAssociatedTokenAccountInstruction(
          wallet.publicKey,
          userAccounts.shares,
          wallet.publicKey,
          sharesMint
        );
        tx.preInstructions([createAtaIx]);
      }

      const signature = await tx.rpc();

      spinner.succeed('Deposit successful!');

      console.log(chalk.green('\n✅ Transaction confirmed'));
      console.log(chalk.gray(`Signature: ${signature}`));
      console.log(chalk.gray(`Explorer: https://explorer.solana.com/tx/${signature}?cluster=devnet`));

      // Fetch updated shares balance
      const sharesAccount = await provider.connection.getTokenAccountBalance(userAccounts.shares);
      const sharesBalance = sharesAccount.value.uiAmount || 0;

      console.log(chalk.bold.green('\n🎉 Deposit Complete!\n'));
      console.log(chalk.cyan(`Your Shares: ${sharesBalance.toFixed(6)}`));

      console.log(chalk.gray('\nNext steps:'));
      console.log(chalk.gray('- View vault: npm run view-vault -- -v ' + opts.vault));
      console.log(chalk.gray('- Withdraw: npm run withdraw -- -v ' + opts.vault + ' -s <shares>'));

    } catch (error) {
      spinner.fail('Deposit failed');
      throw error;
    }

  } catch (error) {
    console.error(chalk.red('\n❌ Error:'));
    displayError(error);
    process.exit(1);
  }
}

main();
