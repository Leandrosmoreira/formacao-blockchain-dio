use anchor_lang::prelude::*;
use anchor_spl::token::{Mint, Token, TokenAccount};
use crate::state::{StrategyVault, VaultConfig};
use crate::constants::*;
use crate::errors::VaultError;
use crate::events::VaultCreated;

#[derive(Accounts)]
#[instruction(pool_id: Pubkey)]
pub struct CreateVault<'info> {
    #[account(
        init,
        payer = payer,
        space = StrategyVault::LEN,
        seeds = [b"strategy_vault", pool_id.as_ref()],
        bump
    )]
    pub vault: Account<'info, StrategyVault>,

    /// CHECK: PDA authority for vault operations
    #[account(
        seeds = [VAULT_AUTHORITY_SEED, vault.key().as_ref()],
        bump
    )]
    pub vault_authority: UncheckedAccount<'info>,

    /// Shares mint (vault LP token)
    #[account(
        init,
        payer = payer,
        seeds = [SHARES_MINT_SEED, vault.key().as_ref()],
        bump,
        mint::decimals = 6,
        mint::authority = vault_authority,
    )]
    pub shares_mint: Account<'info, Mint>,

    /// Token A mint (volatile token)
    pub token_a_mint: Account<'info, Mint>,

    /// USDC mint
    pub usdc_mint: Account<'info, Mint>,

    /// Vault's token A account
    #[account(
        init,
        payer = payer,
        associated_token::mint = token_a_mint,
        associated_token::authority = vault_authority,
    )]
    pub vault_token_a: Account<'info, TokenAccount>,

    /// Vault's USDC account
    #[account(
        init,
        payer = payer,
        associated_token::mint = usdc_mint,
        associated_token::authority = vault_authority,
    )]
    pub vault_usdc: Account<'info, TokenAccount>,

    /// Payer and initial admin
    #[account(mut)]
    pub payer: Signer<'info>,

    /// System program
    pub system_program: Program<'info, System>,

    /// Token program
    pub token_program: Program<'info, Token>,

    /// Associated token program
    pub associated_token_program: Program<'info, anchor_spl::associated_token::AssociatedToken>,

    /// Rent sysvar
    pub rent: Sysvar<'info, Rent>,
}

pub fn handler(
    ctx: Context<CreateVault>,
    pool_id: Pubkey,
    tick_lower: i32,
    tick_upper: i32,
    slippage_bps: u16,
    force_swap_to_usdc: bool,
) -> Result<()> {
    let vault = &mut ctx.accounts.vault;
    let clock = Clock::get()?;

    // Validate tick range
    require!(
        tick_lower < tick_upper,
        VaultError::InvalidTickRange
    );

    // Create config
    let config = VaultConfig {
        deadband_bps: 50,      // Default 0.5%
        twap_window_secs: 60,  // Default 60 seconds
        cooldown_ms: 180_000,  // Default 3 minutes
        slippage_bps,
        force_swap_to_usdc,
    };

    // Validate config
    config.validate()?;

    // Initialize vault
    vault.authority = ctx.accounts.vault_authority.key();
    vault.pool_id = pool_id;
    vault.position_key = Pubkey::default(); // Will be set when position is opened
    vault.token_a_mint = ctx.accounts.token_a_mint.key();
    vault.usdc_mint = ctx.accounts.usdc_mint.key();
    vault.shares_mint = ctx.accounts.shares_mint.key();
    vault.vault_token_a = ctx.accounts.vault_token_a.key();
    vault.vault_usdc = ctx.accounts.vault_usdc.key();
    vault.tick_lower = tick_lower;
    vault.tick_upper = tick_upper;
    vault.status = crate::state::VaultStatus::Idle;
    vault.operation_in_progress = false;
    vault.config = config;
    vault.total_shares = 0;
    vault.last_exit_timestamp = 0;
    vault.total_deposits = 0;
    vault.total_withdrawals = 0;
    vault.keeper_authority = ctx.accounts.payer.key(); // Initial keeper is creator
    vault.bump = ctx.bumps.vault;

    // Emit event
    emit!(VaultCreated {
        vault: vault.key(),
        authority: vault.authority,
        pool_id,
        token_a_mint: vault.token_a_mint,
        usdc_mint: vault.usdc_mint,
        tick_lower,
        tick_upper,
        timestamp: clock.unix_timestamp,
    });

    msg!("Vault created successfully!");
    msg!("Vault: {}", vault.key());
    msg!("Authority: {}", vault.authority);
    msg!("Shares Mint: {}", vault.shares_mint);

    Ok(())
}
