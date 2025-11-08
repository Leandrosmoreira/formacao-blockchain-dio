use anchor_lang::prelude::*;
use crate::state::StrategyVault;
use crate::events::ParamsUpdated;

#[derive(Accounts)]
pub struct SetParams<'info> {
    #[account(
        mut,
        has_one = keeper_authority
    )]
    pub vault: Account<'info, StrategyVault>,

    pub keeper_authority: Signer<'info>,
}

pub fn handler(
    ctx: Context<SetParams>,
    deadband_bps: Option<u16>,
    twap_window_secs: Option<u32>,
    cooldown_ms: Option<u64>,
    slippage_bps: Option<u16>,
) -> Result<()> {
    let vault = &mut ctx.accounts.vault;
    let clock = Clock::get()?;

    // Update config if values provided
    if let Some(db) = deadband_bps {
        vault.config.deadband_bps = db;
    }

    if let Some(tw) = twap_window_secs {
        vault.config.twap_window_secs = tw;
    }

    if let Some(cd) = cooldown_ms {
        vault.config.cooldown_ms = cd;
    }

    if let Some(sl) = slippage_bps {
        vault.config.slippage_bps = sl;
    }

    // Validate updated config
    vault.config.validate()?;

    emit!(ParamsUpdated {
        vault: vault.key(),
        deadband_bps: vault.config.deadband_bps,
        twap_window_secs: vault.config.twap_window_secs,
        cooldown_ms: vault.config.cooldown_ms,
        slippage_bps: vault.config.slippage_bps,
        timestamp: clock.unix_timestamp,
    });

    msg!("Vault parameters updated");

    Ok(())
}
