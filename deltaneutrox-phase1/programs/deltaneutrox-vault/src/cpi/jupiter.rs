use anchor_lang::prelude::*;
use anchor_lang::solana_program::program::invoke_signed;
use anchor_lang::solana_program::instruction::Instruction;

/// Jupiter V6 program ID
pub const JUPITER_PROGRAM_ID: Pubkey = anchor_lang::solana_program::pubkey!(
    "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4"
);

/// Simplified Jupiter swap using shared accounts
/// For production, you should use Jupiter API to get the best route
/// and pass remaining accounts dynamically
#[allow(clippy::too_many_arguments)]
pub fn swap_with_route<'info>(
    jupiter_program: AccountInfo<'info>,
    token_program: AccountInfo<'info>,
    user_transfer_authority: AccountInfo<'info>,
    user_source_token_account: AccountInfo<'info>,
    user_destination_token_account: AccountInfo<'info>,
    destination_token_account: AccountInfo<'info>,
    source_mint: AccountInfo<'info>,
    destination_mint: AccountInfo<'info>,
    platform_fee_account: AccountInfo<'info>,
    amount_in: u64,
    minimum_amount_out: u64,
    platform_fee_bps: u8,
    remaining_accounts: &[AccountInfo<'info>],
    signer_seeds: &[&[&[u8]]],
) -> Result<()> {
    // Jupiter V6 instruction discriminator for shared_accounts_route
    // This is the Anchor discriminator for the route swap instruction
    let mut data = vec![0xe4, 0x45, 0xa5, 0x2e, 0x51, 0xcb, 0x9a, 0x1d];

    // Serialize route parameters
    // Route ID (u8) - 0 for simple swap
    data.push(0);

    // Amount in (u64)
    data.extend_from_slice(&amount_in.to_le_bytes());

    // Minimum amount out (u64)
    data.extend_from_slice(&minimum_amount_out.to_le_bytes());

    // Platform fee bps (u8)
    data.push(platform_fee_bps);

    // Build account metas
    let mut accounts = vec![
        AccountMeta::new_readonly(token_program.key(), false),
        AccountMeta::new_readonly(user_transfer_authority.key(), true),
        AccountMeta::new(user_source_token_account.key(), false),
        AccountMeta::new(user_destination_token_account.key(), false),
        AccountMeta::new(destination_token_account.key(), false),
        AccountMeta::new_readonly(source_mint.key(), false),
        AccountMeta::new_readonly(destination_mint.key(), false),
        AccountMeta::new(platform_fee_account.key(), false),
    ];

    // Add remaining accounts for the swap route
    for account in remaining_accounts {
        accounts.push(AccountMeta::new(account.key(), false));
    }

    let ix = Instruction {
        program_id: jupiter_program.key(),
        accounts,
        data,
    };

    // Build account infos vec
    let mut account_infos = vec![
        jupiter_program.clone(),
        token_program.clone(),
        user_transfer_authority.clone(),
        user_source_token_account.clone(),
        user_destination_token_account.clone(),
        destination_token_account.clone(),
        source_mint.clone(),
        destination_mint.clone(),
        platform_fee_account.clone(),
    ];

    // Add remaining accounts
    for account in remaining_accounts {
        account_infos.push(account.clone());
    }

    invoke_signed(&ix, &account_infos, signer_seeds)?;

    Ok(())
}

/// Simplified direct swap for common pairs
/// This uses a simpler route that doesn't require fetching from Jupiter API
/// Suitable for devnet testing with direct pools
pub fn swap_exact_in<'info>(
    jupiter_program: AccountInfo<'info>,
    token_program: AccountInfo<'info>,
    user_transfer_authority: AccountInfo<'info>,
    user_source_token_account: AccountInfo<'info>,
    user_destination_token_account: AccountInfo<'info>,
    swap_program: AccountInfo<'info>,
    swap_state: AccountInfo<'info>,
    authority: AccountInfo<'info>,
    source_vault: AccountInfo<'info>,
    destination_vault: AccountInfo<'info>,
    amount_in: u64,
    minimum_amount_out: u64,
    signer_seeds: &[&[&[u8]]],
) -> Result<()> {
    // Simple exact-in swap instruction
    let mut data = vec![0x09]; // Swap discriminator
    data.extend_from_slice(&amount_in.to_le_bytes());
    data.extend_from_slice(&minimum_amount_out.to_le_bytes());

    let accounts = vec![
        AccountMeta::new_readonly(token_program.key(), false),
        AccountMeta::new_readonly(user_transfer_authority.key(), true),
        AccountMeta::new(user_source_token_account.key(), false),
        AccountMeta::new(user_destination_token_account.key(), false),
        AccountMeta::new_readonly(swap_program.key(), false),
        AccountMeta::new(swap_state.key(), false),
        AccountMeta::new_readonly(authority.key(), false),
        AccountMeta::new(source_vault.key(), false),
        AccountMeta::new(destination_vault.key(), false),
    ];

    let ix = Instruction {
        program_id: jupiter_program.key(),
        accounts,
        data,
    };

    invoke_signed(
        &ix,
        &[
            jupiter_program,
            token_program,
            user_transfer_authority,
            user_source_token_account,
            user_destination_token_account,
            swap_program,
            swap_state,
            authority,
            source_vault,
            destination_vault,
        ],
        signer_seeds,
    )?;

    Ok(())
}

/// Calculate minimum amount out with slippage
pub fn calculate_min_amount_out(amount_out: u64, slippage_bps: u16) -> u64 {
    let slippage_multiplier = 10000u128
        .checked_sub(slippage_bps as u128)
        .unwrap_or(9900); // Default to 1% if overflow

    ((amount_out as u128)
        .checked_mul(slippage_multiplier)
        .unwrap_or(0)
        / 10000) as u64
}

/// Helper to estimate output amount (simplified)
/// In production, use Jupiter API quote endpoint
pub fn estimate_swap_output(
    amount_in: u64,
    reserve_in: u64,
    reserve_out: u64,
    fee_bps: u16,
) -> u64 {
    if reserve_in == 0 || reserve_out == 0 {
        return 0;
    }

    // Constant product formula with fees
    // amount_out = (amount_in * (10000 - fee_bps) * reserve_out) / ((reserve_in * 10000) + (amount_in * (10000 - fee_bps)))

    let amount_in_with_fee = (amount_in as u128)
        .checked_mul((10000u128).checked_sub(fee_bps as u128).unwrap_or(9900))
        .unwrap_or(0);

    let numerator = amount_in_with_fee
        .checked_mul(reserve_out as u128)
        .unwrap_or(0);

    let denominator = ((reserve_in as u128)
        .checked_mul(10000)
        .unwrap_or(0))
        .checked_add(amount_in_with_fee)
        .unwrap_or(1);

    (numerator / denominator) as u64
}
