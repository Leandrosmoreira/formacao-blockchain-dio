use anchor_lang::prelude::*;
use anchor_spl::token::{Token, TokenAccount, Mint};
use crate::state::{StrategyVault, VaultStatus};
use crate::errors::VaultError;
use crate::events::PositionOpened;
use crate::cpi::whirlpool;

#[derive(Accounts)]
pub struct OpenPosition<'info> {
    #[account(mut)]
    pub vault: Account<'info, StrategyVault>,

    /// CHECK: Vault authority PDA
    #[account(
        seeds = [crate::constants::VAULT_AUTHORITY_SEED, vault.key().as_ref()],
        bump
    )]
    pub vault_authority: UncheckedAccount<'info>,

    /// CHECK: Whirlpool program
    #[account(
        constraint = whirlpool_program.key() == whirlpool::WHIRLPOOL_PROGRAM_ID @ VaultError::InvalidProgramId
    )]
    pub whirlpool_program: UncheckedAccount<'info>,

    /// CHECK: Whirlpool pool (validated against vault.pool_id)
    #[account(
        mut,
        constraint = whirlpool.key() == vault.pool_id @ VaultError::InvalidPoolId
    )]
    pub whirlpool: UncheckedAccount<'info>,

    /// CHECK: Position PDA (will be created)
    #[account(mut)]
    pub position: UncheckedAccount<'info>,

    /// CHECK: Position mint (NFT, will be created)
    #[account(mut)]
    pub position_mint: UncheckedAccount<'info>,

    /// CHECK: Position token account (ATA, will be created)
    #[account(mut)]
    pub position_token_account: UncheckedAccount<'info>,

    /// Vault's token A account
    #[account(
        mut,
        constraint = vault_token_a.key() == vault.vault_token_a @ VaultError::InvalidTokenMint
    )]
    pub vault_token_a: Account<'info, TokenAccount>,

    /// Vault's USDC account
    #[account(
        mut,
        constraint = vault_usdc.key() == vault.vault_usdc @ VaultError::InvalidTokenMint
    )]
    pub vault_usdc: Account<'info, TokenAccount>,

    /// CHECK: Pool's token A vault
    #[account(mut)]
    pub token_vault_a: UncheckedAccount<'info>,

    /// CHECK: Pool's token B (USDC) vault
    #[account(mut)]
    pub token_vault_b: UncheckedAccount<'info>,

    /// CHECK: Tick array lower
    #[account(mut)]
    pub tick_array_lower: UncheckedAccount<'info>,

    /// CHECK: Tick array upper
    #[account(mut)]
    pub tick_array_upper: UncheckedAccount<'info>,

    /// Token program
    pub token_program: Program<'info, Token>,

    /// System program
    pub system_program: Program<'info, System>,

    /// Rent sysvar
    pub rent: Sysvar<'info, Rent>,

    /// CHECK: Associated token program
    pub associated_token_program: UncheckedAccount<'info>,

    /// CHECK: Metaplex Token Metadata program
    pub metadata_program: UncheckedAccount<'info>,

    /// CHECK: Metadata update authority
    #[account(mut)]
    pub metadata_update_auth: UncheckedAccount<'info>,

    /// Keeper (funder and signer)
    #[account(mut)]
    pub keeper: Signer<'info>,
}

pub fn handler(
    ctx: Context<OpenPosition>,
    liquidity: u128,
) -> Result<()> {
    let vault = &mut ctx.accounts.vault;
    let clock = Clock::get()?;

    // Validate status
    require!(
        vault.status == VaultStatus::Idle || vault.status == VaultStatus::ExitedToUSDC,
        VaultError::InvalidVaultStatus
    );

    // Validate keeper
    require!(
        ctx.accounts.keeper.key() == vault.keeper_authority,
        VaultError::UnauthorizedKeeper
    );

    // Set reentrancy lock
    vault.operation_in_progress = true;

    msg!("Opening position in Whirlpool with ticks: {} to {}", vault.tick_lower, vault.tick_upper);

    // Prepare PDA signer seeds
    let vault_key = vault.key();
    let seeds = &[
        crate::constants::VAULT_AUTHORITY_SEED,
        vault_key.as_ref(),
        &[ctx.bumps.vault_authority],
    ];
    let signer_seeds = &[&seeds[..]];

    // Step 1: Open position with metadata (creates NFT)
    whirlpool::open_position_with_metadata(
        ctx.accounts.whirlpool_program.to_account_info(),
        ctx.accounts.keeper.to_account_info(), // funder
        ctx.accounts.vault_authority.to_account_info(), // owner (PDA)
        ctx.accounts.position.to_account_info(),
        ctx.accounts.position_mint.to_account_info(),
        ctx.accounts.position_token_account.to_account_info(),
        ctx.accounts.whirlpool.to_account_info(),
        ctx.accounts.token_program.to_account_info(),
        ctx.accounts.system_program.to_account_info(),
        ctx.accounts.rent.to_account_info(),
        ctx.accounts.associated_token_program.to_account_info(),
        ctx.accounts.metadata_program.to_account_info(),
        ctx.accounts.metadata_update_auth.to_account_info(),
        vault.tick_lower,
        vault.tick_upper,
        signer_seeds,
    )?;

    msg!("Position created, adding liquidity: {}", liquidity);

    // Get vault balances
    let balance_a = ctx.accounts.vault_token_a.amount;
    let balance_usdc = ctx.accounts.vault_usdc.amount;

    // Calculate token max with slippage (add 1% buffer)
    let slippage_multiplier = 10000u128 + vault.config.slippage_bps as u128;
    let token_max_a = ((balance_a as u128 * slippage_multiplier) / 10000) as u64;
    let token_max_b = ((balance_usdc as u128 * slippage_multiplier) / 10000) as u64;

    msg!("Token max A: {}, Token max B: {}", token_max_a, token_max_b);

    // Step 2: Increase liquidity
    whirlpool::increase_liquidity(
        ctx.accounts.whirlpool_program.to_account_info(),
        ctx.accounts.whirlpool.to_account_info(),
        ctx.accounts.token_program.to_account_info(),
        ctx.accounts.vault_authority.to_account_info(), // position authority
        ctx.accounts.position.to_account_info(),
        ctx.accounts.position_token_account.to_account_info(),
        ctx.accounts.vault_token_a.to_account_info(), // token owner account A
        ctx.accounts.vault_usdc.to_account_info(), // token owner account B
        ctx.accounts.token_vault_a.to_account_info(), // pool vault A
        ctx.accounts.token_vault_b.to_account_info(), // pool vault B
        ctx.accounts.tick_array_lower.to_account_info(),
        ctx.accounts.tick_array_upper.to_account_info(),
        liquidity,
        token_max_a,
        token_max_b,
        signer_seeds,
    )?;

    // Reload accounts to get actual amounts used
    ctx.accounts.vault_token_a.reload()?;
    ctx.accounts.vault_usdc.reload()?;

    let amount_a_used = balance_a - ctx.accounts.vault_token_a.amount;
    let amount_usdc_used = balance_usdc - ctx.accounts.vault_usdc.amount;

    // Save position key to vault
    vault.position_key = ctx.accounts.position.key();
    vault.status = VaultStatus::PositionOpen;
    vault.operation_in_progress = false;

    emit!(PositionOpened {
        vault: vault.key(),
        position_key: vault.position_key,
        liquidity,
        amount_a: amount_a_used,
        amount_usdc: amount_usdc_used,
        tick_lower: vault.tick_lower,
        tick_upper: vault.tick_upper,
        timestamp: clock.unix_timestamp,
    });

    msg!("Position opened successfully!");
    msg!("Position: {}", vault.position_key);
    msg!("Liquidity: {}", liquidity);
    msg!("Amount A used: {}", amount_a_used);
    msg!("Amount USDC used: {}", amount_usdc_used);

    Ok(())
}
