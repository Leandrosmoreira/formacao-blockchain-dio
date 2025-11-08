export type DeltaneutroxVault = {
  "version": "0.1.0",
  "name": "deltaneutrox_vault",
  "instructions": [
    {
      "name": "createVault",
      "accounts": [
        {
          "name": "vault",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "vaultAuthority",
          "isMut": false,
          "isSigner": false
        },
        {
          "name": "sharesMint",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "vaultTokenA",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "vaultUsdc",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "tokenAMint",
          "isMut": false,
          "isSigner": false
        },
        {
          "name": "usdcMint",
          "isMut": false,
          "isSigner": false
        },
        {
          "name": "authority",
          "isMut": true,
          "isSigner": true
        },
        {
          "name": "keeperAuthority",
          "isMut": false,
          "isSigner": false
        },
        {
          "name": "tokenProgram",
          "isMut": false,
          "isSigner": false
        },
        {
          "name": "associatedTokenProgram",
          "isMut": false,
          "isSigner": false
        },
        {
          "name": "systemProgram",
          "isMut": false,
          "isSigner": false
        },
        {
          "name": "rent",
          "isMut": false,
          "isSigner": false
        }
      ],
      "args": [
        {
          "name": "poolId",
          "type": "publicKey"
        },
        {
          "name": "tickLower",
          "type": "i32"
        },
        {
          "name": "tickUpper",
          "type": "i32"
        },
        {
          "name": "slippageBps",
          "type": "u16"
        },
        {
          "name": "forceSwapToUsdc",
          "type": "bool"
        }
      ]
    },
    {
      "name": "deposit",
      "accounts": [
        {
          "name": "vault",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "sharesMint",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "userTokenA",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "userUsdc",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "vaultTokenA",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "vaultUsdc",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "userShares",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "user",
          "isMut": false,
          "isSigner": true
        },
        {
          "name": "tokenProgram",
          "isMut": false,
          "isSigner": false
        }
      ],
      "args": [
        {
          "name": "amountA",
          "type": "u64"
        },
        {
          "name": "amountUsdc",
          "type": "u64"
        }
      ]
    },
    {
      "name": "withdraw",
      "accounts": [
        {
          "name": "vault",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "vaultAuthority",
          "isMut": false,
          "isSigner": false
        },
        {
          "name": "sharesMint",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "userTokenA",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "userUsdc",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "vaultTokenA",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "vaultUsdc",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "userShares",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "user",
          "isMut": false,
          "isSigner": true
        },
        {
          "name": "tokenProgram",
          "isMut": false,
          "isSigner": false
        }
      ],
      "args": [
        {
          "name": "sharesAmount",
          "type": "u64"
        }
      ]
    },
    {
      "name": "openPositionOnce",
      "accounts": [
        {
          "name": "vault",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "vaultAuthority",
          "isMut": false,
          "isSigner": false
        },
        {
          "name": "whirlpoolProgram",
          "isMut": false,
          "isSigner": false
        },
        {
          "name": "whirlpool",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "position",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "positionMint",
          "isMut": true,
          "isSigner": true
        },
        {
          "name": "positionTokenAccount",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "vaultTokenA",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "vaultUsdc",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "tokenVaultA",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "tokenVaultB",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "tickArrayLower",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "tickArrayUpper",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "keeper",
          "isMut": true,
          "isSigner": true
        },
        {
          "name": "tokenProgram",
          "isMut": false,
          "isSigner": false
        },
        {
          "name": "systemProgram",
          "isMut": false,
          "isSigner": false
        },
        {
          "name": "rent",
          "isMut": false,
          "isSigner": false
        },
        {
          "name": "associatedTokenProgram",
          "isMut": false,
          "isSigner": false
        },
        {
          "name": "metadataProgram",
          "isMut": false,
          "isSigner": false
        },
        {
          "name": "metadataUpdateAuth",
          "isMut": false,
          "isSigner": false
        }
      ],
      "args": [
        {
          "name": "liquidity",
          "type": "u128"
        }
      ]
    },
    {
      "name": "decreaseLiquidityAll",
      "accounts": [
        {
          "name": "vault",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "vaultAuthority",
          "isMut": false,
          "isSigner": false
        },
        {
          "name": "whirlpoolProgram",
          "isMut": false,
          "isSigner": false
        },
        {
          "name": "whirlpool",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "position",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "positionTokenAccount",
          "isMut": false,
          "isSigner": false
        },
        {
          "name": "vaultTokenA",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "vaultUsdc",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "tokenVaultA",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "tokenVaultB",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "tickArrayLower",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "tickArrayUpper",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "keeper",
          "isMut": false,
          "isSigner": true
        },
        {
          "name": "tokenProgram",
          "isMut": false,
          "isSigner": false
        }
      ],
      "args": []
    },
    {
      "name": "collectFees",
      "accounts": [
        {
          "name": "vault",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "vaultAuthority",
          "isMut": false,
          "isSigner": false
        },
        {
          "name": "whirlpoolProgram",
          "isMut": false,
          "isSigner": false
        },
        {
          "name": "whirlpool",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "position",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "positionTokenAccount",
          "isMut": false,
          "isSigner": false
        },
        {
          "name": "vaultTokenA",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "vaultUsdc",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "tokenVaultA",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "tokenVaultB",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "keeper",
          "isMut": false,
          "isSigner": true
        },
        {
          "name": "tokenProgram",
          "isMut": false,
          "isSigner": false
        }
      ],
      "args": []
    },
    {
      "name": "swapAllToUsdc",
      "accounts": [
        {
          "name": "vault",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "vaultAuthority",
          "isMut": false,
          "isSigner": false
        },
        {
          "name": "jupiterProgram",
          "isMut": false,
          "isSigner": false
        },
        {
          "name": "tokenAMint",
          "isMut": false,
          "isSigner": false
        },
        {
          "name": "usdcMint",
          "isMut": false,
          "isSigner": false
        },
        {
          "name": "vaultTokenA",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "vaultUsdc",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "keeper",
          "isMut": false,
          "isSigner": true
        },
        {
          "name": "tokenProgram",
          "isMut": false,
          "isSigner": false
        }
      ],
      "args": []
    },
    {
      "name": "markExitedToUsdc",
      "accounts": [
        {
          "name": "vault",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "keeper",
          "isMut": false,
          "isSigner": true
        },
        {
          "name": "clock",
          "isMut": false,
          "isSigner": false
        }
      ],
      "args": []
    },
    {
      "name": "reenterWithLiquidity",
      "accounts": [
        {
          "name": "vault",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "vaultAuthority",
          "isMut": false,
          "isSigner": false
        },
        {
          "name": "whirlpoolProgram",
          "isMut": false,
          "isSigner": false
        },
        {
          "name": "whirlpool",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "position",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "positionTokenAccount",
          "isMut": false,
          "isSigner": false
        },
        {
          "name": "vaultTokenA",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "vaultUsdc",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "tokenVaultA",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "tokenVaultB",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "tickArrayLower",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "tickArrayUpper",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "keeper",
          "isMut": false,
          "isSigner": true
        },
        {
          "name": "clock",
          "isMut": false,
          "isSigner": false
        },
        {
          "name": "tokenProgram",
          "isMut": false,
          "isSigner": false
        }
      ],
      "args": [
        {
          "name": "targetLiquidity",
          "type": "u128"
        }
      ]
    },
    {
      "name": "setParams",
      "accounts": [
        {
          "name": "vault",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "authority",
          "isMut": false,
          "isSigner": true
        }
      ],
      "args": [
        {
          "name": "deadbandBps",
          "type": {
            "option": "u16"
          }
        },
        {
          "name": "twapWindowSecs",
          "type": {
            "option": "u32"
          }
        },
        {
          "name": "cooldownMs",
          "type": {
            "option": "u64"
          }
        },
        {
          "name": "slippageBps",
          "type": {
            "option": "u16"
          }
        }
      ]
    }
  ],
  "accounts": [
    {
      "name": "strategyVault",
      "type": {
        "kind": "struct",
        "fields": [
          {
            "name": "authority",
            "type": "publicKey"
          },
          {
            "name": "poolId",
            "type": "publicKey"
          },
          {
            "name": "positionKey",
            "type": "publicKey"
          },
          {
            "name": "tokenAMint",
            "type": "publicKey"
          },
          {
            "name": "usdcMint",
            "type": "publicKey"
          },
          {
            "name": "sharesMint",
            "type": "publicKey"
          },
          {
            "name": "vaultTokenA",
            "type": "publicKey"
          },
          {
            "name": "vaultUsdc",
            "type": "publicKey"
          },
          {
            "name": "tickLower",
            "type": "i32"
          },
          {
            "name": "tickUpper",
            "type": "i32"
          },
          {
            "name": "status",
            "type": {
              "defined": "VaultStatus"
            }
          },
          {
            "name": "operationInProgress",
            "type": "bool"
          },
          {
            "name": "config",
            "type": {
              "defined": "VaultConfig"
            }
          },
          {
            "name": "totalShares",
            "type": "u64"
          },
          {
            "name": "lastExitTimestamp",
            "type": "i64"
          },
          {
            "name": "totalDeposits",
            "type": "u64"
          },
          {
            "name": "totalWithdrawals",
            "type": "u64"
          },
          {
            "name": "keeperAuthority",
            "type": "publicKey"
          },
          {
            "name": "bump",
            "type": "u8"
          }
        ]
      }
    }
  ],
  "types": [
    {
      "name": "VaultConfig",
      "type": {
        "kind": "struct",
        "fields": [
          {
            "name": "deadbandBps",
            "type": "u16"
          },
          {
            "name": "twapWindowSecs",
            "type": "u32"
          },
          {
            "name": "cooldownMs",
            "type": "u64"
          },
          {
            "name": "slippageBps",
            "type": "u16"
          },
          {
            "name": "forceSwapToUsdc",
            "type": "bool"
          }
        ]
      }
    },
    {
      "name": "VaultStatus",
      "type": {
        "kind": "enum",
        "variants": [
          {
            "name": "Idle"
          },
          {
            "name": "PositionOpen"
          },
          {
            "name": "ExitedToUSDC"
          },
          {
            "name": "Reentering"
          }
        ]
      }
    }
  ],
  "errors": [
    {
      "code": 6000,
      "name": "InvalidVaultStatus",
      "msg": "Invalid vault status for this operation"
    },
    {
      "code": 6001,
      "name": "OperationInProgress",
      "msg": "Operation already in progress - reentrancy blocked"
    },
    {
      "code": 6002,
      "name": "UnauthorizedKeeper",
      "msg": "Unauthorized keeper - not in whitelist"
    },
    {
      "code": 6003,
      "name": "CooldownNotMet",
      "msg": "Cooldown period not met - wait before re-entry"
    },
    {
      "code": 6004,
      "name": "InvalidTickRange",
      "msg": "Invalid tick range - tick_lower must be < tick_upper"
    },
    {
      "code": 6005,
      "name": "SlippageExceeded",
      "msg": "Slippage exceeds maximum allowed"
    },
    {
      "code": 6006,
      "name": "DeadbandExceeded",
      "msg": "Deadband exceeds maximum allowed"
    },
    {
      "code": 6007,
      "name": "InvalidCooldown",
      "msg": "Cooldown value out of allowed range"
    },
    {
      "code": 6008,
      "name": "InvalidTwapWindow",
      "msg": "TWAP window out of allowed range"
    },
    {
      "code": 6009,
      "name": "InvalidPoolId",
      "msg": "Invalid pool ID - not whitelisted"
    },
    {
      "code": 6010,
      "name": "InvalidTokenMint",
      "msg": "Invalid token mint - does not match vault configuration"
    },
    {
      "code": 6011,
      "name": "InsufficientLiquidity",
      "msg": "Insufficient liquidity in vault"
    },
    {
      "code": 6012,
      "name": "InsufficientShares",
      "msg": "Insufficient shares to withdraw"
    },
    {
      "code": 6013,
      "name": "NoActivePosition",
      "msg": "No active position to decrease"
    },
    {
      "code": 6014,
      "name": "MathOverflow",
      "msg": "Math overflow occurred"
    },
    {
      "code": 6015,
      "name": "DivisionByZero",
      "msg": "Division by zero"
    },
    {
      "code": 6016,
      "name": "InvalidProgramId",
      "msg": "Invalid program ID for CPI"
    },
    {
      "code": 6017,
      "name": "PositionKeyMismatch",
      "msg": "Position key mismatch"
    },
    {
      "code": 6018,
      "name": "NotProperlyExited",
      "msg": "Vault not properly exited - complete exit flow first"
    },
    {
      "code": 6019,
      "name": "CannotWithdrawDuringOperation",
      "msg": "Cannot withdraw while operation in progress"
    }
  ]
};

export const IDL: DeltaneutroxVault = {
  "version": "0.1.0",
  "name": "deltaneutrox_vault",
  "instructions": [
    {
      "name": "createVault",
      "accounts": [
        {
          "name": "vault",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "vaultAuthority",
          "isMut": false,
          "isSigner": false
        },
        {
          "name": "sharesMint",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "vaultTokenA",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "vaultUsdc",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "tokenAMint",
          "isMut": false,
          "isSigner": false
        },
        {
          "name": "usdcMint",
          "isMut": false,
          "isSigner": false
        },
        {
          "name": "authority",
          "isMut": true,
          "isSigner": true
        },
        {
          "name": "keeperAuthority",
          "isMut": false,
          "isSigner": false
        },
        {
          "name": "tokenProgram",
          "isMut": false,
          "isSigner": false
        },
        {
          "name": "associatedTokenProgram",
          "isMut": false,
          "isSigner": false
        },
        {
          "name": "systemProgram",
          "isMut": false,
          "isSigner": false
        },
        {
          "name": "rent",
          "isMut": false,
          "isSigner": false
        }
      ],
      "args": [
        {
          "name": "poolId",
          "type": "publicKey"
        },
        {
          "name": "tickLower",
          "type": "i32"
        },
        {
          "name": "tickUpper",
          "type": "i32"
        },
        {
          "name": "slippageBps",
          "type": "u16"
        },
        {
          "name": "forceSwapToUsdc",
          "type": "bool"
        }
      ]
    },
    {
      "name": "deposit",
      "accounts": [
        {
          "name": "vault",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "sharesMint",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "userTokenA",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "userUsdc",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "vaultTokenA",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "vaultUsdc",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "userShares",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "user",
          "isMut": false,
          "isSigner": true
        },
        {
          "name": "tokenProgram",
          "isMut": false,
          "isSigner": false
        }
      ],
      "args": [
        {
          "name": "amountA",
          "type": "u64"
        },
        {
          "name": "amountUsdc",
          "type": "u64"
        }
      ]
    },
    {
      "name": "withdraw",
      "accounts": [
        {
          "name": "vault",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "vaultAuthority",
          "isMut": false,
          "isSigner": false
        },
        {
          "name": "sharesMint",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "userTokenA",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "userUsdc",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "vaultTokenA",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "vaultUsdc",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "userShares",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "user",
          "isMut": false,
          "isSigner": true
        },
        {
          "name": "tokenProgram",
          "isMut": false,
          "isSigner": false
        }
      ],
      "args": [
        {
          "name": "sharesAmount",
          "type": "u64"
        }
      ]
    },
    {
      "name": "openPositionOnce",
      "accounts": [
        {
          "name": "vault",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "vaultAuthority",
          "isMut": false,
          "isSigner": false
        },
        {
          "name": "whirlpoolProgram",
          "isMut": false,
          "isSigner": false
        },
        {
          "name": "whirlpool",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "position",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "positionMint",
          "isMut": true,
          "isSigner": true
        },
        {
          "name": "positionTokenAccount",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "vaultTokenA",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "vaultUsdc",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "tokenVaultA",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "tokenVaultB",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "tickArrayLower",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "tickArrayUpper",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "keeper",
          "isMut": true,
          "isSigner": true
        },
        {
          "name": "tokenProgram",
          "isMut": false,
          "isSigner": false
        },
        {
          "name": "systemProgram",
          "isMut": false,
          "isSigner": false
        },
        {
          "name": "rent",
          "isMut": false,
          "isSigner": false
        },
        {
          "name": "associatedTokenProgram",
          "isMut": false,
          "isSigner": false
        },
        {
          "name": "metadataProgram",
          "isMut": false,
          "isSigner": false
        },
        {
          "name": "metadataUpdateAuth",
          "isMut": false,
          "isSigner": false
        }
      ],
      "args": [
        {
          "name": "liquidity",
          "type": "u128"
        }
      ]
    },
    {
      "name": "decreaseLiquidityAll",
      "accounts": [
        {
          "name": "vault",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "vaultAuthority",
          "isMut": false,
          "isSigner": false
        },
        {
          "name": "whirlpoolProgram",
          "isMut": false,
          "isSigner": false
        },
        {
          "name": "whirlpool",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "position",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "positionTokenAccount",
          "isMut": false,
          "isSigner": false
        },
        {
          "name": "vaultTokenA",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "vaultUsdc",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "tokenVaultA",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "tokenVaultB",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "tickArrayLower",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "tickArrayUpper",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "keeper",
          "isMut": false,
          "isSigner": true
        },
        {
          "name": "tokenProgram",
          "isMut": false,
          "isSigner": false
        }
      ],
      "args": []
    },
    {
      "name": "collectFees",
      "accounts": [
        {
          "name": "vault",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "vaultAuthority",
          "isMut": false,
          "isSigner": false
        },
        {
          "name": "whirlpoolProgram",
          "isMut": false,
          "isSigner": false
        },
        {
          "name": "whirlpool",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "position",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "positionTokenAccount",
          "isMut": false,
          "isSigner": false
        },
        {
          "name": "vaultTokenA",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "vaultUsdc",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "tokenVaultA",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "tokenVaultB",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "keeper",
          "isMut": false,
          "isSigner": true
        },
        {
          "name": "tokenProgram",
          "isMut": false,
          "isSigner": false
        }
      ],
      "args": []
    },
    {
      "name": "swapAllToUsdc",
      "accounts": [
        {
          "name": "vault",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "vaultAuthority",
          "isMut": false,
          "isSigner": false
        },
        {
          "name": "jupiterProgram",
          "isMut": false,
          "isSigner": false
        },
        {
          "name": "tokenAMint",
          "isMut": false,
          "isSigner": false
        },
        {
          "name": "usdcMint",
          "isMut": false,
          "isSigner": false
        },
        {
          "name": "vaultTokenA",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "vaultUsdc",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "keeper",
          "isMut": false,
          "isSigner": true
        },
        {
          "name": "tokenProgram",
          "isMut": false,
          "isSigner": false
        }
      ],
      "args": []
    },
    {
      "name": "markExitedToUsdc",
      "accounts": [
        {
          "name": "vault",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "keeper",
          "isMut": false,
          "isSigner": true
        },
        {
          "name": "clock",
          "isMut": false,
          "isSigner": false
        }
      ],
      "args": []
    },
    {
      "name": "reenterWithLiquidity",
      "accounts": [
        {
          "name": "vault",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "vaultAuthority",
          "isMut": false,
          "isSigner": false
        },
        {
          "name": "whirlpoolProgram",
          "isMut": false,
          "isSigner": false
        },
        {
          "name": "whirlpool",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "position",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "positionTokenAccount",
          "isMut": false,
          "isSigner": false
        },
        {
          "name": "vaultTokenA",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "vaultUsdc",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "tokenVaultA",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "tokenVaultB",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "tickArrayLower",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "tickArrayUpper",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "keeper",
          "isMut": false,
          "isSigner": true
        },
        {
          "name": "clock",
          "isMut": false,
          "isSigner": false
        },
        {
          "name": "tokenProgram",
          "isMut": false,
          "isSigner": false
        }
      ],
      "args": [
        {
          "name": "targetLiquidity",
          "type": "u128"
        }
      ]
    },
    {
      "name": "setParams",
      "accounts": [
        {
          "name": "vault",
          "isMut": true,
          "isSigner": false
        },
        {
          "name": "authority",
          "isMut": false,
          "isSigner": true
        }
      ],
      "args": [
        {
          "name": "deadbandBps",
          "type": {
            "option": "u16"
          }
        },
        {
          "name": "twapWindowSecs",
          "type": {
            "option": "u32"
          }
        },
        {
          "name": "cooldownMs",
          "type": {
            "option": "u64"
          }
        },
        {
          "name": "slippageBps",
          "type": {
            "option": "u16"
          }
        }
      ]
    }
  ],
  "accounts": [
    {
      "name": "strategyVault",
      "type": {
        "kind": "struct",
        "fields": [
          {
            "name": "authority",
            "type": "publicKey"
          },
          {
            "name": "poolId",
            "type": "publicKey"
          },
          {
            "name": "positionKey",
            "type": "publicKey"
          },
          {
            "name": "tokenAMint",
            "type": "publicKey"
          },
          {
            "name": "usdcMint",
            "type": "publicKey"
          },
          {
            "name": "sharesMint",
            "type": "publicKey"
          },
          {
            "name": "vaultTokenA",
            "type": "publicKey"
          },
          {
            "name": "vaultUsdc",
            "type": "publicKey"
          },
          {
            "name": "tickLower",
            "type": "i32"
          },
          {
            "name": "tickUpper",
            "type": "i32"
          },
          {
            "name": "status",
            "type": {
              "defined": "VaultStatus"
            }
          },
          {
            "name": "operationInProgress",
            "type": "bool"
          },
          {
            "name": "config",
            "type": {
              "defined": "VaultConfig"
            }
          },
          {
            "name": "totalShares",
            "type": "u64"
          },
          {
            "name": "lastExitTimestamp",
            "type": "i64"
          },
          {
            "name": "totalDeposits",
            "type": "u64"
          },
          {
            "name": "totalWithdrawals",
            "type": "u64"
          },
          {
            "name": "keeperAuthority",
            "type": "publicKey"
          },
          {
            "name": "bump",
            "type": "u8"
          }
        ]
      }
    }
  ],
  "types": [
    {
      "name": "VaultConfig",
      "type": {
        "kind": "struct",
        "fields": [
          {
            "name": "deadbandBps",
            "type": "u16"
          },
          {
            "name": "twapWindowSecs",
            "type": "u32"
          },
          {
            "name": "cooldownMs",
            "type": "u64"
          },
          {
            "name": "slippageBps",
            "type": "u16"
          },
          {
            "name": "forceSwapToUsdc",
            "type": "bool"
          }
        ]
      }
    },
    {
      "name": "VaultStatus",
      "type": {
        "kind": "enum",
        "variants": [
          {
            "name": "Idle"
          },
          {
            "name": "PositionOpen"
          },
          {
            "name": "ExitedToUSDC"
          },
          {
            "name": "Reentering"
          }
        ]
      }
    }
  ],
  "errors": [
    {
      "code": 6000,
      "name": "InvalidVaultStatus",
      "msg": "Invalid vault status for this operation"
    },
    {
      "code": 6001,
      "name": "OperationInProgress",
      "msg": "Operation already in progress - reentrancy blocked"
    },
    {
      "code": 6002,
      "name": "UnauthorizedKeeper",
      "msg": "Unauthorized keeper - not in whitelist"
    },
    {
      "code": 6003,
      "name": "CooldownNotMet",
      "msg": "Cooldown period not met - wait before re-entry"
    },
    {
      "code": 6004,
      "name": "InvalidTickRange",
      "msg": "Invalid tick range - tick_lower must be < tick_upper"
    },
    {
      "code": 6005,
      "name": "SlippageExceeded",
      "msg": "Slippage exceeds maximum allowed"
    },
    {
      "code": 6006,
      "name": "DeadbandExceeded",
      "msg": "Deadband exceeds maximum allowed"
    },
    {
      "code": 6007,
      "name": "InvalidCooldown",
      "msg": "Cooldown value out of allowed range"
    },
    {
      "code": 6008,
      "name": "InvalidTwapWindow",
      "msg": "TWAP window out of allowed range"
    },
    {
      "code": 6009,
      "name": "InvalidPoolId",
      "msg": "Invalid pool ID - not whitelisted"
    },
    {
      "code": 6010,
      "name": "InvalidTokenMint",
      "msg": "Invalid token mint - does not match vault configuration"
    },
    {
      "code": 6011,
      "name": "InsufficientLiquidity",
      "msg": "Insufficient liquidity in vault"
    },
    {
      "code": 6012,
      "name": "InsufficientShares",
      "msg": "Insufficient shares to withdraw"
    },
    {
      "code": 6013,
      "name": "NoActivePosition",
      "msg": "No active position to decrease"
    },
    {
      "code": 6014,
      "name": "MathOverflow",
      "msg": "Math overflow occurred"
    },
    {
      "code": 6015,
      "name": "DivisionByZero",
      "msg": "Division by zero"
    },
    {
      "code": 6016,
      "name": "InvalidProgramId",
      "msg": "Invalid program ID for CPI"
    },
    {
      "code": 6017,
      "name": "PositionKeyMismatch",
      "msg": "Position key mismatch"
    },
    {
      "code": 6018,
      "name": "NotProperlyExited",
      "msg": "Vault not properly exited - complete exit flow first"
    },
    {
      "code": 6019,
      "name": "CannotWithdrawDuringOperation",
      "msg": "Cannot withdraw while operation in progress"
    }
  ]
};
