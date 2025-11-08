use anchor_lang::prelude::*;

pub mod constants;
pub mod cpi;
pub mod errors;
pub mod events;
pub mod instructions;
pub mod state;

use instructions::*;

declare_id!("Fg6PaFpoGXkYsidMpWTK6W2BeZ7FEfcYkg476zPFsLnS");

#[program]
pub mod deltaneutrox_vault {
    use super::*;

    /// Creates a new strategy vault for Orca Whirlpool LP management
    pub fn create_vault(
        ctx: Context<CreateVault>,
        pool_id: Pubkey,
        tick_lower: i32,
        tick_upper: i32,
        slippage_bps: u16,
        force_swap_to_usdc: bool,
    ) -> Result<()> {
        instructions::create_vault::handler(
            ctx,
            pool_id,
            tick_lower,
            tick_upper,
            slippage_bps,
            force_swap_to_usdc,
        )
    }

    /// Deposits tokens into the vault and mints shares
    pub fn deposit(ctx: Context<Deposit>, amount_a: u64, amount_usdc: u64) -> Result<()> {
        instructions::deposit::handler(ctx, amount_a, amount_usdc)
    }

    /// Withdraws tokens by burning shares
    pub fn withdraw(ctx: Context<Withdraw>, shares_amount: u64) -> Result<()> {
        instructions::withdraw::handler(ctx, shares_amount)
    }

    /// Opens a new LP position in Orca Whirlpool (called once)
    pub fn open_position_once(ctx: Context<OpenPosition>, liquidity: u128) -> Result<()> {
        instructions::open_position::handler(ctx, liquidity)
    }

    /// Decreases liquidity to 100% (exit from position)
    pub fn decrease_liquidity_all(ctx: Context<DecreaseLiquidity>) -> Result<()> {
        instructions::decrease_liquidity::handler(ctx)
    }

    /// Collects fees from the Whirlpool position
    pub fn collect_fees(ctx: Context<CollectFees>) -> Result<()> {
        instructions::collect_fees::handler(ctx)
    }

    /// Swaps all token_a to USDC
    pub fn swap_all_to_usdc(ctx: Context<SwapToUSDC>) -> Result<()> {
        instructions::swap_to_usdc::handler(ctx)
    }

    /// Marks vault as exited to USDC after decrease + collect + swap
    pub fn mark_exited_to_usdc(ctx: Context<MarkExited>) -> Result<()> {
        instructions::mark_exited::handler(ctx)
    }

    /// Re-enters position after cooldown with TWAP validation
    pub fn reenter_with_liquidity(ctx: Context<Reenter>, target_liquidity: u128) -> Result<()> {
        instructions::reenter::handler(ctx, target_liquidity)
    }

    /// Updates vault configuration parameters
    pub fn set_params(
        ctx: Context<SetParams>,
        deadband_bps: Option<u16>,
        twap_window_secs: Option<u32>,
        cooldown_ms: Option<u64>,
        slippage_bps: Option<u16>,
    ) -> Result<()> {
        instructions::set_params::handler(ctx, deadband_bps, twap_window_secs, cooldown_ms, slippage_bps)
    }
}
