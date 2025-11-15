# DeltaNeutralVaultV1 - Etapa 1

## Visão Geral

O **DeltaNeutralVaultV1** é um vault ERC-4626 projetado para executar estratégias delta-neutral utilizando posições de liquidez no Uniswap v3. Esta é a **Etapa 1** da implementação, que estabelece a base do contrato com todas as estruturas necessárias.

## Status da Implementação

✅ **COMPLETO - Etapa 1**

Esta versão implementa:
- Estrutura base ERC-4626 completa
- Sistema de roles (owner + keeper)
- Sistema completo de fees (6 tipos)
- Integração com Chainlink (price feeds + validação)
- Stubs para integração futura com Uniswap v3
- Funções de gestão e emergência

⏳ **Pendente - Etapa 2**

A próxima etapa implementará:
- Integração real com Uniswap v3 (mint/burn de posições LP)
- Swaps via 1inch
- Keeper off-chain automatizado
- Testes completos

## Arquitetura do Contrato

### Heranças

```solidity
ERC20           // Token de shares
ERC4626         // Padrão de vault tokenizado
Ownable         // Controle de acesso do owner
Pausable        // Capacidade de pausar operações
ReentrancyGuard // Proteção contra reentrância
```

### Componentes Principais

#### 1. Sistema de Roles

- **Owner**: Administrador do contrato (configurações, fees, pause)
- **Keeper**: Bot autorizado para executar operações automáticas
- **Treasury**: Endereço que recebe todas as fees

#### 2. Sistema de Fees (6 tipos)

| Fee | Descrição | Quando é cobrada | Máximo |
|-----|-----------|------------------|--------|
| `entryFeeBps` | Fee de entrada | No `deposit()` | 10% |
| `exitFeeBps` | Fee de saída | No `withdraw()`/`redeem()` | 10% |
| `managementFeeBps` | Fee de gestão anual | Periodicamente (anualizada) | 10% |
| `performanceFeeBps` | Fee sobre lucro | No `autoExit()` quando há profit | 50% |
| `swapFeeBps` | Fee sobre swaps | Nos swaps internos | 10% |
| `keeperFeeBps` | Fee do keeper | Operações do keeper | 10% |

**Nota**: Todos os valores são em basis points (10000 = 100%)

#### 3. Integração com Chainlink

O contrato utiliza Chainlink Price Feeds para:
- Validar preços fornecidos pelo keeper
- Proteger contra manipulação de preços
- Garantir dados atualizados (validação de staleness)

**Parâmetros de Segurança**:
- `maxOracleDeviationBps`: Desvio máximo permitido (padrão: 5%)
- `maxOracleDelay`: Idade máxima dos dados (padrão: 1 hora)

#### 4. Placeholders Uniswap v3 (Etapa 1)

Variáveis preparadas para integração futura:
```solidity
address public uniswapPool;   // Endereço do pool
int24 public tickLower;       // Tick inferior da posição
int24 public tickUpper;       // Tick superior da posição
```

## Funções Principais

### Configuração (onlyOwner)

```solidity
setUniswapPool(address _pool)
setRange(int24 _tickLower, int24 _tickUpper)
setKeeper(address _keeper)
setOracles(address _priceFeed, uint256 _maxDeviationBps, uint256 _maxDelay)
setSlippageParams(uint256 _maxSlippageBps)
setTreasury(address _treasury)
setFees(...)  // Define todas as fees de uma vez
pause() / unpause()
```

### Funções do Keeper (onlyKeeper)

```solidity
autoExit(uint256 price, ExitReason reason)
// Fecha posição LP, cobra fees, valida oracle

autoReenter(uint256 price, int24 _tickLower, int24 _tickUpper)
// Reabre posição LP com novos parâmetros

recordHedgeState(bytes32 stateHash, uint64 timestamp)
// Registra estado do hedge para auditoria

updateAccounting()
// Atualiza contabilidade e cobra management fee
```

### Funções do Usuário (ERC-4626)

```solidity
deposit(uint256 assets, address receiver) returns (uint256 shares)
// Deposita USDC, cobra entry fee, recebe shares

withdraw(uint256 assets, address receiver, address owner) returns (uint256 shares)
// Saca USDC, cobra exit fee, queima shares

redeem(uint256 shares, address receiver, address owner) returns (uint256 assets)
// Resgata shares, cobra exit fee, recebe USDC
```

### Emergência (onlyOwner, whenPaused)

```solidity
emergencyExitToUSDC()
// Fecha todas as posições e converte tudo para USDC
```

## Fluxo de Fees

### Entry Fee (Depósito)
```
Usuário deposita 1000 USDC
↓
Entry fee 1% = 10 USDC → Treasury
↓
990 USDC entram no vault
↓
Shares mintadas baseadas em 990 USDC
```

### Management Fee (Periódica)
```
Calculada proporcionalmente ao tempo: (totalAssets * feeBps * timeElapsed) / (10000 * 365 days)
↓
Shares mintadas para Treasury
```

### Performance Fee (Lucro)
```
Apenas sobre lucro acima do High Water Mark
↓
Fee calculada sobre o lucro
↓
Shares mintadas para Treasury
↓
High Water Mark atualizado
```

### Exit Fee (Saque)
```
Usuário resgata 1000 USDC
↓
Exit fee 1% = 10 USDC → Treasury
↓
990 USDC transferidos ao usuário
```

## Segurança

### Proteções Implementadas

1. **ReentrancyGuard**: Todas as funções públicas críticas
2. **Pausable**: Capacidade de pausar em emergência
3. **Oracle Validation**: Proteção contra manipulação de preços
4. **Access Control**: Owner e Keeper separados
5. **Fee Limits**: Limites máximos para todas as fees

### Validações do Oracle

A função `_checkOracle()` verifica:
- ✅ Preço válido (> 0)
- ✅ Dados não-stale (roundId consistency)
- ✅ Timestamp recente (< maxOracleDelay)
- ✅ Desvio aceitável (< maxOracleDeviationBps)

## Eventos

Todos os eventos importantes estão implementados:

```solidity
event KeeperUpdated(address indexed oldKeeper, address indexed newKeeper)
event TreasuryUpdated(address indexed oldTreasury, address indexed newTreasury)
event FeesUpdated(...)
event OracleUpdated(...)
event EntryFeeCharged(uint256 assets, uint256 fee)
event ExitFeeCharged(uint256 assets, uint256 fee)
event ManagementFeeCharged(uint256 fee, uint256 shares)
event PerformanceFeeCharged(uint256 profit, uint256 fee)
event AutoExitExecuted(...)
event AutoReenterExecuted(...)
event HedgeStateRecorded(...)
event EmergencyExitExecuted(...)
// ... e outros
```

## Estrutura de Arquivos

```
DeltaNeutralVault/
├── DeltaNeutralVaultV1.sol    # Contrato principal (Etapa 1)
└── README.md                   # Esta documentação
```

## Dependências

O contrato requer as seguintes bibliotecas:

```json
{
  "@openzeppelin/contracts": "^5.0.0",
  "@chainlink/contracts": "^0.8.0"
}
```

### Imports Utilizados

```solidity
import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC4626.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/Pausable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@chainlink/contracts/src/v0.8/interfaces/AggregatorV3Interface.sol";
```

## Próximos Passos (Etapa 2)

1. **Integração Uniswap v3**
   - Implementar `_openPosition()` real
   - Implementar `_closePositionAndConvertToUSDC()` real
   - Gestão de posições NFT
   - Cálculo de liquidez e ranges

2. **Swaps via 1inch**
   - Implementar `executeSwap()` real
   - Integração com 1inch Aggregator
   - Validação de slippage

3. **Keeper Off-chain**
   - Bot para monitorar posições
   - Lógica de rebalanceamento
   - Integração com oracles

4. **Testes Completos**
   - Testes unitários
   - Testes de integração
   - Testes de cenários extremos
   - Auditoria de segurança

## Exemplo de Deploy

```solidity
// Parâmetros de exemplo (mainnet)
IERC20 usdc = IERC20(0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48);
string memory name = "Delta Neutral Vault Shares";
string memory symbol = "dnvUSDC";
address chainlinkFeed = 0x986b5E1e1755e3C2440e960477f25201B0a8bbD4; // ETH/USD
address treasury = 0x...; // Sua treasury

DeltaNeutralVaultV1 vault = new DeltaNeutralVaultV1(
    usdc,
    name,
    symbol,
    chainlinkFeed,
    treasury
);

// Configurar keeper
vault.setKeeper(0x...);

// Configurar fees
vault.setFees(
    2000,  // 20% performance fee
    200,   // 2% management fee
    50,    // 0.5% entry fee
    50,    // 0.5% exit fee
    30,    // 0.3% swap fee
    10     // 0.1% keeper fee
);
```

## Licença

MIT

## Versão

- **Etapa**: 1
- **Versão**: 1.0.0
- **Solidity**: ^0.8.20
- **Status**: Base implementada, aguardando Etapa 2 para integração completa
