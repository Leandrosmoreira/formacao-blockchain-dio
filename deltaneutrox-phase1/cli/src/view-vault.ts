#!/usr/bin/env ts-node

import { Command } from 'commander';
import { PublicKey } from '@solana/web3.js';
import chalk from 'chalk';
import ora from 'ora';
import {
  loadConfig,
  initProgram,
  deriveVaultAuthority,
  getAssociatedTokenAddresses,
  formatAmount,
  formatPercentage,
  formatTimestamp,
  vaultStatusToString,
  displayError,
} from './utils';

const program = new Command();

program
  .name('view-vault')
  .description('View DeltaNeutroX vault details')
  .requiredOption('-v, --vault <address>', 'Vault address')
  .option('-d, --detailed', 'Show detailed information', false)
  .parse(process.argv);

const opts = program.opts();

async function main() {
  console.log(chalk.bold.cyan('\n📊 DeltaNeutroX Vault Information\n'));

  try {
    // Load configuration
    const config = loadConfig();
    const { program: anchorProgram, provider } = initProgram(config);

    const vaultPubkey = new PublicKey(opts.vault);

    const spinner = ora('Fetching vault...').start();

    try {
      // Fetch vault state
      const vaultState = await anchorProgram.account.strategyVault.fetch(vaultPubkey);
      spinner.succeed('Vault data loaded');

      // Derive vault authority
      const [vaultAuthority] = deriveVaultAuthority(vaultPubkey, config.programId);

      // Get vault token accounts
      const vaultAccounts = await getAssociatedTokenAddresses(
        vaultAuthority,
        vaultState.tokenAMint,
        vaultState.usdcMint,
        vaultState.sharesMint
      );

      // Fetch token balances
      const tokenABalance = await provider.connection.getTokenAccountBalance(vaultAccounts.tokenA);
      const usdcBalance = await provider.connection.getTokenAccountBalance(vaultAccounts.usdc);

      // Display vault information
      console.log(chalk.bold('🏦 Vault Overview\n'));

      console.log(chalk.white('Address:'), chalk.cyan(vaultPubkey.toString()));
      console.log(chalk.white('Authority:'), chalk.gray(vaultAuthority.toString()));
      console.log(chalk.white('Status:'), getStatusColor(vaultStatusToString(vaultState.status)));
      console.log(chalk.white('Operation in Progress:'), vaultState.operationInProgress ? chalk.yellow('Yes') : chalk.green('No'));

      console.log(chalk.bold('\n💰 Balances\n'));

      console.log(chalk.white('Token A:'), chalk.cyan((tokenABalance.value.uiAmount || 0).toFixed(6)));
      console.log(chalk.white('USDC:'), chalk.cyan((usdcBalance.value.uiAmount || 0).toFixed(6)));
      console.log(chalk.white('Total Shares:'), chalk.cyan(formatAmount(vaultState.totalShares, 6)));

      console.log(chalk.bold('\n📈 Pool Configuration\n'));

      console.log(chalk.white('Pool ID:'), chalk.gray(vaultState.poolId.toString()));
      console.log(chalk.white('Position Key:'), chalk.gray(vaultState.positionKey.toString()));
      console.log(chalk.white('Tick Range:'), chalk.cyan(`[${vaultState.tickLower}, ${vaultState.tickUpper}]`));

      console.log(chalk.bold('\n⚙️  Strategy Parameters\n'));

      console.log(chalk.white('Deadband:'), chalk.cyan(formatPercentage(vaultState.config.deadbandBps)));
      console.log(chalk.white('TWAP Window:'), chalk.cyan(`${vaultState.config.twapWindowSecs} seconds`));
      console.log(chalk.white('Cooldown:'), chalk.cyan(`${Number(vaultState.config.cooldownMs) / 1000} seconds`));
      console.log(chalk.white('Slippage:'), chalk.cyan(formatPercentage(vaultState.config.slippageBps)));
      console.log(chalk.white('Force Swap to USDC:'), vaultState.config.forceSwapToUsdc ? chalk.green('Yes') : chalk.yellow('No'));

      console.log(chalk.bold('\n👤 Authorities\n'));

      console.log(chalk.white('Keeper:'), chalk.gray(vaultState.keeperAuthority.toString()));

      console.log(chalk.bold('\n📊 Statistics\n'));

      console.log(chalk.white('Total Deposits:'), chalk.cyan(formatAmount(vaultState.totalDeposits, 6)));
      console.log(chalk.white('Total Withdrawals:'), chalk.cyan(formatAmount(vaultState.totalWithdrawals, 6)));

      if (Number(vaultState.lastExitTimestamp) > 0) {
        console.log(chalk.white('Last Exit:'), chalk.gray(formatTimestamp(vaultState.lastExitTimestamp)));
      } else {
        console.log(chalk.white('Last Exit:'), chalk.gray('Never'));
      }

      // Detailed information
      if (opts.detailed) {
        console.log(chalk.bold('\n🔍 Detailed Information\n'));

        console.log(chalk.white('Token A Mint:'), chalk.gray(vaultState.tokenAMint.toString()));
        console.log(chalk.white('USDC Mint:'), chalk.gray(vaultState.usdcMint.toString()));
        console.log(chalk.white('Shares Mint:'), chalk.gray(vaultState.sharesMint.toString()));

        console.log(chalk.white('\nVault Token Accounts:'));
        console.log(chalk.gray(`  Token A: ${vaultAccounts.tokenA.toString()}`));
        console.log(chalk.gray(`  USDC: ${vaultAccounts.usdc.toString()}`));

        console.log(chalk.white('\nPDA Bump:'), chalk.gray(vaultState.bump.toString()));
      }

      // Show cooldown status if exited
      const status = vaultStatusToString(vaultState.status);
      if (status === 'ExitedToUSDC') {
        const now = Math.floor(Date.now() / 1000);
        const lastExit = Number(vaultState.lastExitTimestamp);
        const cooldownSecs = Number(vaultState.config.cooldownMs) / 1000;
        const elapsed = now - lastExit;
        const remaining = Math.max(0, cooldownSecs - elapsed);

        console.log(chalk.bold('\n⏱️  Cooldown Status\n'));

        if (remaining > 0) {
          console.log(chalk.yellow(`Cooldown active: ${remaining.toFixed(0)} seconds remaining`));
          console.log(chalk.gray(`Can reenter at: ${new Date((lastExit + cooldownSecs) * 1000).toISOString()}`));
        } else {
          console.log(chalk.green('✓ Cooldown complete - Can reenter'));
        }
      }

      console.log(chalk.bold.green('\n✅ Vault information displayed successfully\n'));

      console.log(chalk.gray('Commands:'));
      console.log(chalk.gray('  Deposit: npm run deposit -- -v ' + opts.vault + ' -a <amount> -u <amount>'));
      console.log(chalk.gray('  Withdraw: npm run withdraw -- -v ' + opts.vault + ' -s <shares>'));

    } catch (error) {
      spinner.fail('Failed to load vault');
      throw error;
    }

  } catch (error) {
    console.error(chalk.red('\n❌ Error:'));
    displayError(error);
    process.exit(1);
  }
}

function getStatusColor(status: string): string {
  switch (status) {
    case 'Idle':
      return chalk.gray(status);
    case 'PositionOpen':
      return chalk.green(status);
    case 'ExitedToUSDC':
      return chalk.yellow(status);
    case 'Reentering':
      return chalk.blue(status);
    default:
      return chalk.white(status);
  }
}

main();
