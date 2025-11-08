use anchor_lang::prelude::*;
use anchor_spl::token::{self, Mint, Token, TokenAccount, Burn, Transfer};
use crate::state::StrategyVault;
use crate::errors::VaultError;
use crate::events::Withdrawn;

#[derive(Accounts)]
pub struct Withdraw<'info> {
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
    ctx: Context<Withdraw>,
    shares_amount: u64,
) -> Result<()> {
    let vault = &mut ctx.accounts.vault;
    let clock = Clock::get()?;

    // Check not in operation
    require!(
        !vault.operation_in_progress,
        VaultError::CannotWithdrawDuringOperation
    );

    // Check sufficient shares
    require!(
        ctx.accounts.user_shares.amount >= shares_amount,
        VaultError::InsufficientShares
    );

    require!(shares_amount > 0, VaultError::InsufficientShares);

    // Calculate pro-rata amounts
    let balance_a = ctx.accounts.vault_token_a.amount;
    let balance_usdc = ctx.accounts.vault_usdc.amount;

    let amount_a = (shares_amount as u128)
        .checked_mul(balance_a as u128)
        .ok_or(VaultError::MathOverflow)?
        .checked_div(vault.total_shares as u128)
        .ok_or(VaultError::DivisionByZero)? as u64;

    let amount_usdc = (shares_amount as u128)
        .checked_mul(balance_usdc as u128)
        .ok_or(VaultError::MathOverflow)?
        .checked_div(vault.total_shares as u128)
        .ok_or(VaultError::DivisionByZero)? as u64;

    // Burn shares
    token::burn(
        CpiContext::new(
            ctx.accounts.token_program.to_account_info(),
            Burn {
                mint: ctx.accounts.shares_mint.to_account_info(),
                from: ctx.accounts.user_shares.to_account_info(),
                authority: ctx.accounts.user.to_account_info(),
            },
        ),
        shares_amount,
    )?;

    // Transfer tokens from vault to user
    let seeds = &[
        crate::constants::VAULT_AUTHORITY_SEED,
        vault.key().as_ref(),
        &[ctx.bumps.vault_authority],
    ];
    let signer = &[&seeds[..]];

    if amount_a > 0 {
        token::transfer(
            CpiContext::new_with_signer(
                ctx.accounts.token_program.to_account_info(),
                Transfer {
                    from: ctx.accounts.vault_token_a.to_account_info(),
                    to: ctx.accounts.user_token_a.to_account_info(),
                    authority: ctx.accounts.vault_authority.to_account_info(),
                },
                signer,
            ),
            amount_a,
        )?;
    }

    if amount_usdc > 0 {
        token::transfer(
            CpiContext::new_with_signer(
                ctx.accounts.token_program.to_account_info(),
                Transfer {
                    from: ctx.accounts.vault_usdc.to_account_info(),
                    to: ctx.accounts.user_usdc.to_account_info(),
                    authority: ctx.accounts.vault_authority.to_account_info(),
                },
                signer,
            ),
            amount_usdc,
        )?;
    }

    // Update vault state
    vault.total_shares = vault
        .total_shares
        .checked_sub(shares_amount)
        .ok_or(VaultError::MathOverflow)?;

    vault.total_withdrawals = vault
        .total_withdrawals
        .checked_add(amount_a.checked_add(amount_usdc).ok_or(VaultError::MathOverflow)?)
        .ok_or(VaultError::MathOverflow)?;

    // Emit event
    emit!(Withdrawn {
        vault: vault.key(),
        user: ctx.accounts.user.key(),
        shares_burned: shares_amount,
        amount_a,
        amount_usdc,
        total_shares: vault.total_shares,
        timestamp: clock.unix_timestamp,
    });

    msg!("Withdrawn: {} shares burned", shares_amount);
    msg!("Received: {} token_a, {} USDC", amount_a, amount_usdc);

    Ok(())
}
