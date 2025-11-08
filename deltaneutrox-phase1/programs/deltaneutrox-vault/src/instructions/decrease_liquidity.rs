use anchor_lang::prelude::*;
use anchor_spl::token::{Token, TokenAccount};
use crate::state::{StrategyVault, VaultStatus};
use crate::errors::VaultError;
use crate::events::LiquidityDecreased;
use crate::cpi::whirlpool;

// Whirlpool Position account structure (simplified for reading liquidity)
// We only need the liquidity field at offset 65
#[derive(AnchorDeserialize, AnchorSerialize)]
pub struct WhirlpoolPosition {
    pub whirlpool: Pubkey,        // 32
    pub position_mint: Pubkey,    // 32
    pub liquidity: u128,          // 16 (offset 64)
    // ... other fields we don't need
}

#[derive(Accounts)]
pub struct DecreaseLiquidity<'info> {
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

    /// CHECK: Whirlpool pool
    #[account(
        mut,
        constraint = whirlpool.key() == vault.pool_id @ VaultError::InvalidPoolId
    )]
    pub whirlpool: UncheckedAccount<'info>,

    /// CHECK: Position account (contains liquidity data)
    #[account(
        mut,
        constraint = position.key() == vault.position_key @ VaultError::PositionKeyMismatch
    )]
    pub position: UncheckedAccount<'info>,

    /// CHECK: Position token account (NFT)
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

    /// Keeper
    #[account(mut)]
    pub keeper: Signer<'info>,
}

pub fn handler(ctx: Context<DecreaseLiquidity>) -> Result<()> {
    let vault = &mut ctx.accounts.vault;
    let clock = Clock::get()?;

    // Validate status
    require!(
        vault.status == VaultStatus::PositionOpen,
        VaultError::NoActivePosition
    );

    // Validate keeper
    require!(
        ctx.accounts.keeper.key() == vault.keeper_authority,
        VaultError::UnauthorizedKeeper
    );

    vault.operation_in_progress = true;

    // Read position account to get current liquidity
    let position_data = ctx.accounts.position.try_borrow_data()?;

    // Liquidity is u128 at bytes 64-79 (after 2 Pubkeys)
    let mut liquidity_bytes = [0u8; 16];
    liquidity_bytes.copy_from_slice(&position_data[64..80]);
    let current_liquidity = u128::from_le_bytes(liquidity_bytes);

    require!(
        current_liquidity > 0,
        VaultError::InsufficientLiquidity
    );

    msg!("Decreasing liquidity: {} (100%)", current_liquidity);

    // Get balances before
    let balance_a_before = ctx.accounts.vault_token_a.amount;
    let balance_usdc_before = ctx.accounts.vault_usdc.amount;

    // Calculate minimum tokens to receive with slippage
    // For decrease, we expect to receive tokens back, so we apply minimum
    // Set to 0 for now (accept any amount) - in production, estimate from liquidity
    let token_min_a = 0u64;
    let token_min_b = 0u64;

    // Prepare PDA signer seeds
    let vault_key = vault.key();
    let seeds = &[
        crate::constants::VAULT_AUTHORITY_SEED,
        vault_key.as_ref(),
        &[ctx.bumps.vault_authority],
    ];
    let signer_seeds = &[&seeds[..]];

    // CPI: Decrease liquidity 100%
    whirlpool::decrease_liquidity(
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
        current_liquidity, // Decrease 100%
        token_min_a,
        token_min_b,
        signer_seeds,
    )?;

    // Reload to get amounts received
    ctx.accounts.vault_token_a.reload()?;
    ctx.accounts.vault_usdc.reload()?;

    let amount_a_received = ctx.accounts.vault_token_a.amount - balance_a_before;
    let amount_usdc_received = ctx.accounts.vault_usdc.amount - balance_usdc_before;

    vault.operation_in_progress = false;

    emit!(LiquidityDecreased {
        vault: vault.key(),
        liquidity_removed: current_liquidity,
        amount_a: amount_a_received,
        amount_usdc: amount_usdc_received,
        timestamp: clock.unix_timestamp,
    });

    msg!("Liquidity decreased to 0%");
    msg!("Liquidity removed: {}", current_liquidity);
    msg!("Amount A received: {}", amount_a_received);
    msg!("Amount USDC received: {}", amount_usdc_received);

    Ok(())
}
