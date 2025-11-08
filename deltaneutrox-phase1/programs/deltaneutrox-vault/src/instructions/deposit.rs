use anchor_lang::prelude::*;
use anchor_spl::token::{self, Mint, Token, TokenAccount, MintTo, Transfer};
use crate::state::StrategyVault;
use crate::errors::VaultError;
use crate::events::Deposited;

#[derive(Accounts)]
pub struct Deposit<'info> {
    #[account(mut)]
    pub vault: Account<'info, StrategyVault>,

    /// CHECK: Vault authority PDA
    #[account(
        seeds = [crate::constants::VAULT_AUTHORITY_SEED, vault.key().as_ref()],
        bump
    )]
    pub vault_authority: UncheckedAccount<'info>,

    #[account(mut)]
    pub shares_mint: Account<'info, Mint>,

    #[account(mut)]
    pub vault_token_a: Account<'info, TokenAccount>,

    #[account(mut)]
    pub vault_usdc: Account<'info, TokenAccount>,

    #[account(mut)]
    pub user_token_a: Account<'info, TokenAccount>,

    #[account(mut)]
    pub user_usdc: Account<'info, TokenAccount>,

    #[account(mut)]
    pub user_shares: Account<'info, TokenAccount>,

    #[account(mut)]
    pub user: Signer<'info>,

    pub token_program: Program<'info, Token>,
}

pub fn handler(
    ctx: Context<Deposit>,
    amount_a: u64,
    amount_usdc: u64,
) -> Result<()> {
    let vault = &mut ctx.accounts.vault;
    let clock = Clock::get()?;

    // Check not in progress
    require!(
        !vault.operation_in_progress,
        VaultError::OperationInProgress
    );

    // Calculate shares to mint
    // First deposit: shares = sqrt(amount_a * amount_usdc)
    // Subsequent: shares = min(amount_a/total_a, amount_usdc/total_usdc) * total_shares
    let shares_to_mint = if vault.total_shares == 0 {
        // First deposit - use geometric mean
        ((amount_a as u128)
            .checked_mul(amount_usdc as u128)
            .ok_or(VaultError::MathOverflow)?
            as f64)
            .sqrt() as u64
    } else {
        // Pro-rata based on existing balances
        let balance_a = ctx.accounts.vault_token_a.amount;
        let balance_usdc = ctx.accounts.vault_usdc.amount;

        let shares_from_a = (amount_a as u128)
            .checked_mul(vault.total_shares as u128)
            .ok_or(VaultError::MathOverflow)?
            .checked_div(balance_a as u128)
            .ok_or(VaultError::DivisionByZero)? as u64;

        let shares_from_usdc = (amount_usdc as u128)
            .checked_mul(vault.total_shares as u128)
            .ok_or(VaultError::MathOverflow)?
            .checked_div(balance_usdc as u128)
            .ok_or(VaultError::DivisionByZero)? as u64;

        shares_from_a.min(shares_from_usdc)
    };

    require!(shares_to_mint > 0, VaultError::InsufficientLiquidity);

    // Transfer token A from user to vault
    if amount_a > 0 {
        token::transfer(
            CpiContext::new(
                ctx.accounts.token_program.to_account_info(),
                Transfer {
                    from: ctx.accounts.user_token_a.to_account_info(),
                    to: ctx.accounts.vault_token_a.to_account_info(),
                    authority: ctx.accounts.user.to_account_info(),
                },
            ),
            amount_a,
        )?;
    }

    // Transfer USDC from user to vault
    if amount_usdc > 0 {
        token::transfer(
            CpiContext::new(
                ctx.accounts.token_program.to_account_info(),
                Transfer {
                    from: ctx.accounts.user_usdc.to_account_info(),
                    to: ctx.accounts.vault_usdc.to_account_info(),
                    authority: ctx.accounts.user.to_account_info(),
                },
            ),
            amount_usdc,
        )?;
    }

    // Mint shares to user
    let seeds = &[
        crate::constants::VAULT_AUTHORITY_SEED,
        vault.key().as_ref(),
        &[ctx.bumps.vault_authority],
    ];
    let signer = &[&seeds[..]];

    token::mint_to(
        CpiContext::new_with_signer(
            ctx.accounts.token_program.to_account_info(),
            MintTo {
                mint: ctx.accounts.shares_mint.to_account_info(),
                to: ctx.accounts.user_shares.to_account_info(),
                authority: ctx.accounts.vault_authority.to_account_info(),
            },
            signer,
        ),
        shares_to_mint,
    )?;

    // Update vault state
    vault.total_shares = vault
        .total_shares
        .checked_add(shares_to_mint)
        .ok_or(VaultError::MathOverflow)?;

    vault.total_deposits = vault
        .total_deposits
        .checked_add(amount_a.checked_add(amount_usdc).ok_or(VaultError::MathOverflow)?)
        .ok_or(VaultError::MathOverflow)?;

    // Emit event
    emit!(Deposited {
        vault: vault.key(),
        user: ctx.accounts.user.key(),
        amount_a,
        amount_usdc,
        shares_minted: shares_to_mint,
        total_shares: vault.total_shares,
        timestamp: clock.unix_timestamp,
    });

    msg!("Deposited: {} token_a, {} USDC", amount_a, amount_usdc);
    msg!("Shares minted: {}", shares_to_mint);

    Ok(())
}
