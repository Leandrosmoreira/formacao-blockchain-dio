use anchor_lang::prelude::*;
use anchor_lang::solana_program::program::invoke_signed;
use anchor_lang::solana_program::instruction::Instruction;

/// Whirlpool program ID
pub const WHIRLPOOL_PROGRAM_ID: Pubkey = anchor_lang::solana_program::pubkey!(
    "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc"
);

/// Open position with metadata (Whirlpool instruction)
/// This creates a new position NFT and opens a position in the pool
pub fn open_position_with_metadata<'info>(
    whirlpool_program: AccountInfo<'info>,
    funder: AccountInfo<'info>,
    owner: AccountInfo<'info>,
    position: AccountInfo<'info>,
    position_mint: AccountInfo<'info>,
    position_token_account: AccountInfo<'info>,
    whirlpool: AccountInfo<'info>,
    token_program: AccountInfo<'info>,
    system_program: AccountInfo<'info>,
    rent: AccountInfo<'info>,
    associated_token_program: AccountInfo<'info>,
    metadata_program: AccountInfo<'info>,
    metadata_update_auth: AccountInfo<'info>,
    tick_lower_index: i32,
    tick_upper_index: i32,
    signer_seeds: &[&[&[u8]]],
) -> Result<()> {
    // Instruction discriminator for open_position_with_metadata
    // This is the first 8 bytes of SHA256("global:open_position_with_metadata")
    let mut data = vec![0x7d, 0x4f, 0x35, 0x5c, 0x5c, 0x6f, 0x0c, 0x8e];

    // Serialize tick bounds
    data.extend_from_slice(&tick_lower_index.to_le_bytes());
    data.extend_from_slice(&tick_upper_index.to_le_bytes());

    let accounts = vec![
        AccountMeta::new(funder.key(), true),
        AccountMeta::new_readonly(owner.key(), false),
        AccountMeta::new(position.key(), false),
        AccountMeta::new(position_mint.key(), false),
        AccountMeta::new(position_token_account.key(), false),
        AccountMeta::new(whirlpool.key(), false),
        AccountMeta::new_readonly(token_program.key(), false),
        AccountMeta::new_readonly(system_program.key(), false),
        AccountMeta::new_readonly(rent.key(), false),
        AccountMeta::new_readonly(associated_token_program.key(), false),
        AccountMeta::new_readonly(metadata_program.key(), false),
        AccountMeta::new(metadata_update_auth.key(), false),
    ];

    let ix = Instruction {
        program_id: whirlpool_program.key(),
        accounts,
        data,
    };

    invoke_signed(
        &ix,
        &[
            whirlpool_program,
            funder,
            owner,
            position,
            position_mint,
            position_token_account,
            whirlpool,
            token_program,
            system_program,
            rent,
            associated_token_program,
            metadata_program,
            metadata_update_auth,
        ],
        signer_seeds,
    )?;

    Ok(())
}

/// Increase liquidity in a position
pub fn increase_liquidity<'info>(
    whirlpool_program: AccountInfo<'info>,
    whirlpool: AccountInfo<'info>,
    token_program: AccountInfo<'info>,
    position_authority: AccountInfo<'info>,
    position: AccountInfo<'info>,
    position_token_account: AccountInfo<'info>,
    token_owner_account_a: AccountInfo<'info>,
    token_owner_account_b: AccountInfo<'info>,
    token_vault_a: AccountInfo<'info>,
    token_vault_b: AccountInfo<'info>,
    tick_array_lower: AccountInfo<'info>,
    tick_array_upper: AccountInfo<'info>,
    liquidity_amount: u128,
    token_max_a: u64,
    token_max_b: u64,
    signer_seeds: &[&[&[u8]]],
) -> Result<()> {
    // Instruction discriminator for increase_liquidity
    let mut data = vec![0x2e, 0x88, 0x9c, 0x0a, 0x84, 0x5c, 0x6c, 0x4e];

    // Serialize parameters
    data.extend_from_slice(&liquidity_amount.to_le_bytes());
    data.extend_from_slice(&token_max_a.to_le_bytes());
    data.extend_from_slice(&token_max_b.to_le_bytes());

    let accounts = vec![
        AccountMeta::new(whirlpool.key(), false),
        AccountMeta::new_readonly(token_program.key(), false),
        AccountMeta::new_readonly(position_authority.key(), true),
        AccountMeta::new(position.key(), false),
        AccountMeta::new_readonly(position_token_account.key(), false),
        AccountMeta::new(token_owner_account_a.key(), false),
        AccountMeta::new(token_owner_account_b.key(), false),
        AccountMeta::new(token_vault_a.key(), false),
        AccountMeta::new(token_vault_b.key(), false),
        AccountMeta::new(tick_array_lower.key(), false),
        AccountMeta::new(tick_array_upper.key(), false),
    ];

    let ix = Instruction {
        program_id: whirlpool_program.key(),
        accounts,
        data,
    };

    invoke_signed(
        &ix,
        &[
            whirlpool_program,
            whirlpool,
            token_program,
            position_authority,
            position,
            position_token_account,
            token_owner_account_a,
            token_owner_account_b,
            token_vault_a,
            token_vault_b,
            tick_array_lower,
            tick_array_upper,
        ],
        signer_seeds,
    )?;

    Ok(())
}

/// Decrease liquidity from a position
pub fn decrease_liquidity<'info>(
    whirlpool_program: AccountInfo<'info>,
    whirlpool: AccountInfo<'info>,
    token_program: AccountInfo<'info>,
    position_authority: AccountInfo<'info>,
    position: AccountInfo<'info>,
    position_token_account: AccountInfo<'info>,
    token_owner_account_a: AccountInfo<'info>,
    token_owner_account_b: AccountInfo<'info>,
    token_vault_a: AccountInfo<'info>,
    token_vault_b: AccountInfo<'info>,
    tick_array_lower: AccountInfo<'info>,
    tick_array_upper: AccountInfo<'info>,
    liquidity_amount: u128,
    token_min_a: u64,
    token_min_b: u64,
    signer_seeds: &[&[&[u8]]],
) -> Result<()> {
    // Instruction discriminator for decrease_liquidity
    let mut data = vec![0xa0, 0x2a, 0x19, 0xfb, 0xdc, 0x9b, 0xa5, 0x9d];

    // Serialize parameters
    data.extend_from_slice(&liquidity_amount.to_le_bytes());
    data.extend_from_slice(&token_min_a.to_le_bytes());
    data.extend_from_slice(&token_min_b.to_le_bytes());

    let accounts = vec![
        AccountMeta::new(whirlpool.key(), false),
        AccountMeta::new_readonly(token_program.key(), false),
        AccountMeta::new_readonly(position_authority.key(), true),
        AccountMeta::new(position.key(), false),
        AccountMeta::new_readonly(position_token_account.key(), false),
        AccountMeta::new(token_owner_account_a.key(), false),
        AccountMeta::new(token_owner_account_b.key(), false),
        AccountMeta::new(token_vault_a.key(), false),
        AccountMeta::new(token_vault_b.key(), false),
        AccountMeta::new(tick_array_lower.key(), false),
        AccountMeta::new(tick_array_upper.key(), false),
    ];

    let ix = Instruction {
        program_id: whirlpool_program.key(),
        accounts,
        data,
    };

    invoke_signed(
        &ix,
        &[
            whirlpool_program,
            whirlpool,
            token_program,
            position_authority,
            position,
            position_token_account,
            token_owner_account_a,
            token_owner_account_b,
            token_vault_a,
            token_vault_b,
            tick_array_lower,
            tick_array_upper,
        ],
        signer_seeds,
    )?;

    Ok(())
}

/// Collect fees and rewards from a position
pub fn collect_fees<'info>(
    whirlpool_program: AccountInfo<'info>,
    whirlpool: AccountInfo<'info>,
    position_authority: AccountInfo<'info>,
    position: AccountInfo<'info>,
    position_token_account: AccountInfo<'info>,
    token_owner_account_a: AccountInfo<'info>,
    token_owner_account_b: AccountInfo<'info>,
    token_vault_a: AccountInfo<'info>,
    token_vault_b: AccountInfo<'info>,
    token_program: AccountInfo<'info>,
    signer_seeds: &[&[&[u8]]],
) -> Result<()> {
    // Instruction discriminator for collect_fees
    let data = vec![0xa5, 0x9b, 0x8a, 0x48, 0x23, 0x97, 0x62, 0x10];

    let accounts = vec![
        AccountMeta::new_readonly(whirlpool.key(), false),
        AccountMeta::new_readonly(position_authority.key(), true),
        AccountMeta::new(position.key(), false),
        AccountMeta::new_readonly(position_token_account.key(), false),
        AccountMeta::new(token_owner_account_a.key(), false),
        AccountMeta::new(token_vault_a.key(), false),
        AccountMeta::new(token_owner_account_b.key(), false),
        AccountMeta::new(token_vault_b.key(), false),
        AccountMeta::new_readonly(token_program.key(), false),
    ];

    let ix = Instruction {
        program_id: whirlpool_program.key(),
        accounts,
        data,
    };

    invoke_signed(
        &ix,
        &[
            whirlpool_program,
            whirlpool,
            position_authority,
            position,
            position_token_account,
            token_owner_account_a,
            token_vault_a,
            token_owner_account_b,
            token_vault_b,
            token_program,
        ],
        signer_seeds,
    )?;

    Ok(())
}

/// Close a position
pub fn close_position<'info>(
    whirlpool_program: AccountInfo<'info>,
    position_authority: AccountInfo<'info>,
    receiver: AccountInfo<'info>,
    position: AccountInfo<'info>,
    position_mint: AccountInfo<'info>,
    position_token_account: AccountInfo<'info>,
    token_program: AccountInfo<'info>,
    signer_seeds: &[&[&[u8]]],
) -> Result<()> {
    // Instruction discriminator for close_position
    let data = vec![0x7b, 0x4e, 0x16, 0x3a, 0x5c, 0xd6, 0x8a, 0x91];

    let accounts = vec![
        AccountMeta::new_readonly(position_authority.key(), true),
        AccountMeta::new(receiver.key(), false),
        AccountMeta::new(position.key(), false),
        AccountMeta::new(position_mint.key(), false),
        AccountMeta::new(position_token_account.key(), false),
        AccountMeta::new_readonly(token_program.key(), false),
    ];

    let ix = Instruction {
        program_id: whirlpool_program.key(),
        accounts,
        data,
    };

    invoke_signed(
        &ix,
        &[
            whirlpool_program,
            position_authority,
            receiver,
            position,
            position_mint,
            position_token_account,
            token_program,
        ],
        signer_seeds,
    )?;

    Ok(())
}

/// Helper: Calculate tick array start index
pub fn get_tick_array_start_index(tick_index: i32, tick_spacing: u16) -> i32 {
    let ticks_in_array = 88; // Whirlpool constant
    let real_index = tick_index / tick_spacing as i32;
    let start_array_index = real_index / ticks_in_array;
    start_array_index * ticks_in_array * tick_spacing as i32
}

/// Helper: Derive tick array PDA
pub fn derive_tick_array_pda(
    whirlpool: &Pubkey,
    start_tick: i32,
) -> (Pubkey, u8) {
    Pubkey::find_program_address(
        &[
            b"tick_array",
            whirlpool.as_ref(),
            &start_tick.to_string().as_bytes(),
        ],
        &WHIRLPOOL_PROGRAM_ID,
    )
}
