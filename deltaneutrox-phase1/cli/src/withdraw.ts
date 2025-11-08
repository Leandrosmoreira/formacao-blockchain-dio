#!/usr/bin/env ts-node

import { Command } from 'commander';
import { PublicKey } from '@solana/web3.js';
import { TOKEN_PROGRAM_ID } from '@solana/spl-token';
import chalk from 'chalk';
import ora from 'ora';
import {
  loadConfig,
  initProgram,
  getAssociatedTokenAddresses,
  deriveVaultAuthority,
  formatAmount,
  displayError,
} from './utils';

const program = new Command();

program
  .name('withdraw')
  .description('Withdraw tokens from a DeltaNeutroX vault')
  .requiredOption('-v, --vault <address>', 'Vault address')
  .requiredOption('-s, --shares <number>', 'Amount of shares to burn', parseFloat)
  .option('-d, --decimals <number>', 'Shares decimals', '6')
  .parse(process.argv);

const opts = program.opts();

async function main() {
  console.log(chalk.bold.cyan('\n💸 Withdraw from DeltaNeutroX Vault\n'));

  try {
    // Load configuration
    const config = loadConfig();
    const { program: anchorProgram, provider, wallet } = initProgram(config);

    console.log(chalk.gray(`Wallet: ${wallet.publicKey.toString()}`));
    console.log(chalk.gray(`Vault: ${opts.vault}\n`));

    // Parse inputs
    const vaultPubkey = new PublicKey(opts.vault);
    const decimals = parseInt(opts.decimals);
    const sharesAmount = Math.floor(opts.shares * Math.pow(10, decimals));

    console.log(chalk.bold('📋 Withdrawal Details:'));
    console.log(chalk.gray(`Shares to Burn: ${formatAmount(sharesAmount, decimals)}\n`));

    const spinner = ora('Fetching vault...').start();

    try {
      // Fetch vault state
      const vaultState = await anchorProgram.account.strategyVault.fetch(vaultPubkey);
      spinner.succeed('Vault fetched');

      // Check vault status
      const status = vaultState.status;
      const statusStr = 'idle' in status ? 'Idle' :
                       'positionOpen' in status ? 'PositionOpen' :
                       'exitedToUSDC' in status ? 'ExitedToUSDC' :
                       'reentering' in status ? 'Reentering' : 'Unknown';

      console.log(chalk.gray(`Vault Status: ${statusStr}`));

      if (vaultState.operationInProgress) {
        throw new Error('Cannot withdraw: operation in progress');
      }

      const tokenAMint = vaultState.tokenAMint;
      const usdcMint = vaultState.usdcMint;
      const sharesMint = vaultState.sharesMint;
      const [vaultAuthority] = deriveVaultAuthority(vaultPubkey, config.programId);

      // Get user token accounts
      const userAccounts = await getAssociatedTokenAddresses(
        wallet.publicKey,
        tokenAMint,
        usdcMint,
        sharesMint
      );

      // Get vault token accounts
      const vaultAccounts = await getAssociatedTokenAddresses(
        vaultAuthority,
        tokenAMint,
        usdcMint,
        sharesMint
      );

      // Check user shares balance
      const userSharesAccount = await provider.connection.getTokenAccountBalance(userAccounts.shares);
      const userSharesBalance = userSharesAccount.value.uiAmount || 0;
      const requestedShares = sharesAmount / Math.pow(10, decimals);

      console.log(chalk.gray(`Your Shares: ${userSharesBalance.toFixed(6)}`));

      if (userSharesBalance < requestedShares) {
        throw new Error(`Insufficient shares. You have ${userSharesBalance}, requested ${requestedShares}`);
      }

      // Get vault token balances (to show what user will receive)
      const vaultTokenA = await provider.connection.getTokenAccountBalance(vaultAccounts.tokenA);
      const vaultUsdc = await provider.connection.getTokenAccountBalance(vaultAccounts.usdc);

      const totalShares = Number(vaultState.totalShares) / Math.pow(10, decimals);
      const shareRatio = requestedShares / totalShares;

      const expectedTokenA = (vaultTokenA.value.uiAmount || 0) * shareRatio;
      const expectedUsdc = (vaultUsdc.value.uiAmount || 0) * shareRatio;

      console.log(chalk.gray(`\nExpected Withdrawal (approximate):`));
      console.log(chalk.gray(`  Token A: ${expectedTokenA.toFixed(6)}`));
      console.log(chalk.gray(`  USDC: ${expectedUsdc.toFixed(6)}\n`));

      spinner.start('Withdrawing...');

      // Execute withdrawal
      const signature = await anchorProgram.methods
        .withdraw(sharesAmount)
        .accounts({
          vault: vaultPubkey,
          vaultAuthority,
          sharesMint,
          userTokenA: userAccounts.tokenA,
          userUsdc: userAccounts.usdc,
          vaultTokenA: vaultAccounts.tokenA,
          vaultUsdc: vaultAccounts.usdc,
          userShares: userAccounts.shares,
          user: wallet.publicKey,
          tokenProgram: TOKEN_PROGRAM_ID,
        })
        .rpc();

      spinner.succeed('Withdrawal successful!');

      console.log(chalk.green('\n✅ Transaction confirmed'));
      console.log(chalk.gray(`Signature: ${signature}`));
      console.log(chalk.gray(`Explorer: https://explorer.solana.com/tx/${signature}?cluster=devnet`));

      // Fetch updated balances
      const updatedShares = await provider.connection.getTokenAccountBalance(userAccounts.shares);
      const updatedTokenA = await provider.connection.getTokenAccountBalance(userAccounts.tokenA);
      const updatedUsdc = await provider.connection.getTokenAccountBalance(userAccounts.usdc);

      console.log(chalk.bold.green('\n🎉 Withdrawal Complete!\n'));
      console.log(chalk.cyan(`Remaining Shares: ${(updatedShares.value.uiAmount || 0).toFixed(6)}`));
      console.log(chalk.cyan(`Token A Balance: ${(updatedTokenA.value.uiAmount || 0).toFixed(6)}`));
      console.log(chalk.cyan(`USDC Balance: ${(updatedUsdc.value.uiAmount || 0).toFixed(6)}`));

      console.log(chalk.gray('\nNext steps:'));
      console.log(chalk.gray('- View vault: npm run view-vault -- -v ' + opts.vault));
      console.log(chalk.gray('- Deposit more: npm run deposit -- -v ' + opts.vault));

    } catch (error) {
      spinner.fail('Withdrawal failed');
      throw error;
    }

  } catch (error) {
    console.error(chalk.red('\n❌ Error:'));
    displayError(error);
    process.exit(1);
  }
}

main();
