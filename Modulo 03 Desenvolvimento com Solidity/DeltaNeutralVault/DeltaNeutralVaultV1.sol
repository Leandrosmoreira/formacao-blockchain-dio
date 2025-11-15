// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC4626.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/Pausable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@chainlink/contracts/src/v0.8/interfaces/AggregatorV3Interface.sol";

/**
 * @title DeltaNeutralVaultV1
 * @notice Vault ERC-4626 para estratégia delta-neutral com Uniswap v3
 * @dev Etapa 1: Implementação base com stubs para integração Uniswap v3
 */
contract DeltaNeutralVaultV1 is ERC20, ERC4626, Ownable, Pausable, ReentrancyGuard {

    // ============================================
    // ENUMS
    // ============================================

    enum ExitReason {
        ManualExit,
        RangeExit,
        EmergencyExit,
        Rebalance
    }

    // ============================================
    // ROLES
    // ============================================

    address public keeper;
    address public treasury;

    // ============================================
    // FEES (basis points - 10000 = 100%)
    // ============================================

    uint16 public performanceFeeBps;
    uint16 public managementFeeBps;
    uint16 public entryFeeBps;
    uint16 public exitFeeBps;
    uint16 public swapFeeBps;
    uint16 public keeperFeeBps;

    // ============================================
    // ORACLES
    // ============================================

    AggregatorV3Interface public chainlinkPriceFeed;
    uint256 public maxOracleDeviationBps;
    uint256 public maxOracleDelay;

    // ============================================
    // UNISWAP V3 PLACEHOLDERS
    // ============================================

    address public uniswapPool;
    int24 public tickLower;
    int24 public tickUpper;

    // ============================================
    // ACCOUNTING
    // ============================================

    uint256 public lastManagementFeeTimestamp;
    uint256 public highWaterMark;

    // ============================================
    // SLIPPAGE & OTHER PARAMS
    // ============================================

    uint256 public maxSlippageBps;

    // ============================================
    // EVENTS
    // ============================================

    event KeeperUpdated(address indexed oldKeeper, address indexed newKeeper);
    event TreasuryUpdated(address indexed oldTreasury, address indexed newTreasury);
    event FeesUpdated(
        uint16 performanceFeeBps,
        uint16 managementFeeBps,
        uint16 entryFeeBps,
        uint16 exitFeeBps,
        uint16 swapFeeBps,
        uint16 keeperFeeBps
    );
    event OracleUpdated(
        address indexed priceFeed,
        uint256 maxDeviationBps,
        uint256 maxDelay
    );
    event UniswapPoolUpdated(address indexed pool);
    event RangeUpdated(int24 tickLower, int24 tickUpper);
    event SlippageParamsUpdated(uint256 maxSlippageBps);
    event EntryFeeCharged(uint256 assets, uint256 fee);
    event ExitFeeCharged(uint256 assets, uint256 fee);
    event ManagementFeeCharged(uint256 fee, uint256 shares);
    event PerformanceFeeCharged(uint256 profit, uint256 fee);
    event SwapFeeApplied(uint256 amountIn, uint256 fee);
    event AutoExitExecuted(
        uint256 indexed price,
        ExitReason indexed reason,
        uint256 totalAssets,
        uint256 profit
    );
    event AutoReenterExecuted(
        uint256 indexed price,
        int24 tickLower,
        int24 tickUpper,
        uint256 totalAssets
    );
    event HedgeStateRecorded(bytes32 indexed stateHash, uint64 timestamp);
    event AccountingUpdated(uint256 totalAssets, uint256 totalShares);
    event EmergencyExitExecuted(uint256 totalAssets);
    event SwapExecuted(
        address indexed tokenIn,
        address indexed tokenOut,
        uint256 amountIn,
        uint256 amountOut
    );

    // ============================================
    // MODIFIERS
    // ============================================

    modifier onlyKeeper() {
        require(msg.sender == keeper, "DeltaNeutralVault: caller is not keeper");
        _;
    }

    // ============================================
    // CONSTRUCTOR
    // ============================================

    /**
     * @notice Construtor do vault
     * @param _asset Endereço do token base (USDC)
     * @param _name Nome do token de shares
     * @param _symbol Símbolo do token de shares
     * @param _chainlinkFeed Endereço do price feed Chainlink
     * @param _treasury Endereço da treasury para receber fees
     */
    constructor(
        IERC20 _asset,
        string memory _name,
        string memory _symbol,
        address _chainlinkFeed,
        address _treasury
    )
        ERC20(_name, _symbol)
        ERC4626(_asset)
    {
        require(_treasury != address(0), "DeltaNeutralVault: treasury cannot be zero");
        require(_chainlinkFeed != address(0), "DeltaNeutralVault: chainlink feed cannot be zero");

        treasury = _treasury;
        chainlinkPriceFeed = AggregatorV3Interface(_chainlinkFeed);
        lastManagementFeeTimestamp = block.timestamp;

        // Defaults
        maxOracleDeviationBps = 500; // 5%
        maxOracleDelay = 3600; // 1 hour
        maxSlippageBps = 100; // 1%
    }

    // ============================================
    // CONFIGURAÇÃO (onlyOwner)
    // ============================================

    /**
     * @notice Define o endereço do pool Uniswap v3
     * @param _pool Endereço do pool
     */
    function setUniswapPool(address _pool) external onlyOwner {
        require(_pool != address(0), "DeltaNeutralVault: pool cannot be zero");
        uniswapPool = _pool;
        emit UniswapPoolUpdated(_pool);
    }

    /**
     * @notice Define o range de ticks da posição LP
     * @param _tickLower Tick inferior
     * @param _tickUpper Tick superior
     */
    function setRange(int24 _tickLower, int24 _tickUpper) external onlyOwner {
        require(_tickLower < _tickUpper, "DeltaNeutralVault: invalid tick range");
        tickLower = _tickLower;
        tickUpper = _tickUpper;
        emit RangeUpdated(_tickLower, _tickUpper);
    }

    /**
     * @notice Define o keeper autorizado
     * @param _keeper Endereço do keeper
     */
    function setKeeper(address _keeper) external onlyOwner {
        require(_keeper != address(0), "DeltaNeutralVault: keeper cannot be zero");
        address oldKeeper = keeper;
        keeper = _keeper;
        emit KeeperUpdated(oldKeeper, _keeper);
    }

    /**
     * @notice Define parâmetros do oracle
     * @param _priceFeed Endereço do price feed Chainlink
     * @param _maxDeviationBps Desvio máximo permitido em bps
     * @param _maxDelay Delay máximo permitido em segundos
     */
    function setOracles(
        address _priceFeed,
        uint256 _maxDeviationBps,
        uint256 _maxDelay
    ) external onlyOwner {
        require(_priceFeed != address(0), "DeltaNeutralVault: price feed cannot be zero");
        require(_maxDeviationBps <= 10000, "DeltaNeutralVault: max deviation too high");

        chainlinkPriceFeed = AggregatorV3Interface(_priceFeed);
        maxOracleDeviationBps = _maxDeviationBps;
        maxOracleDelay = _maxDelay;

        emit OracleUpdated(_priceFeed, _maxDeviationBps, _maxDelay);
    }

    /**
     * @notice Define parâmetros de slippage
     * @param _maxSlippageBps Slippage máximo em bps
     */
    function setSlippageParams(uint256 _maxSlippageBps) external onlyOwner {
        require(_maxSlippageBps <= 10000, "DeltaNeutralVault: slippage too high");
        maxSlippageBps = _maxSlippageBps;
        emit SlippageParamsUpdated(_maxSlippageBps);
    }

    /**
     * @notice Define o endereço da treasury
     * @param _treasury Nova treasury
     */
    function setTreasury(address _treasury) external onlyOwner {
        require(_treasury != address(0), "DeltaNeutralVault: treasury cannot be zero");
        address oldTreasury = treasury;
        treasury = _treasury;
        emit TreasuryUpdated(oldTreasury, _treasury);
    }

    /**
     * @notice Define todas as fees de uma vez
     * @param _performanceFeeBps Fee de performance
     * @param _managementFeeBps Fee de gestão anual
     * @param _entryFeeBps Fee de entrada
     * @param _exitFeeBps Fee de saída
     * @param _swapFeeBps Fee de swap
     * @param _keeperFeeBps Fee do keeper
     */
    function setFees(
        uint16 _performanceFeeBps,
        uint16 _managementFeeBps,
        uint16 _entryFeeBps,
        uint16 _exitFeeBps,
        uint16 _swapFeeBps,
        uint16 _keeperFeeBps
    ) external onlyOwner {
        require(_performanceFeeBps <= 5000, "DeltaNeutralVault: performance fee too high"); // max 50%
        require(_managementFeeBps <= 1000, "DeltaNeutralVault: management fee too high"); // max 10%
        require(_entryFeeBps <= 1000, "DeltaNeutralVault: entry fee too high"); // max 10%
        require(_exitFeeBps <= 1000, "DeltaNeutralVault: exit fee too high"); // max 10%
        require(_swapFeeBps <= 1000, "DeltaNeutralVault: swap fee too high"); // max 10%
        require(_keeperFeeBps <= 1000, "DeltaNeutralVault: keeper fee too high"); // max 10%

        performanceFeeBps = _performanceFeeBps;
        managementFeeBps = _managementFeeBps;
        entryFeeBps = _entryFeeBps;
        exitFeeBps = _exitFeeBps;
        swapFeeBps = _swapFeeBps;
        keeperFeeBps = _keeperFeeBps;

        emit FeesUpdated(
            _performanceFeeBps,
            _managementFeeBps,
            _entryFeeBps,
            _exitFeeBps,
            _swapFeeBps,
            _keeperFeeBps
        );
    }

    /**
     * @notice Pausa o contrato
     */
    function pause() external onlyOwner {
        _pause();
    }

    /**
     * @notice Despausa o contrato
     */
    function unpause() external onlyOwner {
        _unpause();
    }

    // ============================================
    // FUNÇÕES DE FEE
    // ============================================

    /**
     * @notice Cobra entry fee
     * @param assets Quantidade de assets depositados
     * @return netAssets Assets após a fee
     */
    function _chargeEntryFee(uint256 assets) internal returns (uint256 netAssets) {
        if (entryFeeBps == 0) {
            return assets;
        }

        uint256 fee = (assets * entryFeeBps) / 10000;
        netAssets = assets - fee;

        if (fee > 0) {
            IERC20(asset()).transfer(treasury, fee);
            emit EntryFeeCharged(assets, fee);
        }
    }

    /**
     * @notice Cobra exit fee
     * @param assets Quantidade de assets a sacar
     * @return netAssets Assets após a fee
     */
    function _chargeExitFee(uint256 assets) internal returns (uint256 netAssets) {
        if (exitFeeBps == 0) {
            return assets;
        }

        uint256 fee = (assets * exitFeeBps) / 10000;
        netAssets = assets - fee;

        if (fee > 0) {
            IERC20(asset()).transfer(treasury, fee);
            emit ExitFeeCharged(assets, fee);
        }
    }

    /**
     * @notice Cobra management fee (anualizada, calculada proporcionalmente ao tempo)
     */
    function _chargeManagementFee() internal {
        if (managementFeeBps == 0) {
            return;
        }

        uint256 timeElapsed = block.timestamp - lastManagementFeeTimestamp;
        if (timeElapsed == 0) {
            return;
        }

        uint256 totalAssets_ = totalAssets();
        if (totalAssets_ == 0) {
            lastManagementFeeTimestamp = block.timestamp;
            return;
        }

        // Fee anualizada: (totalAssets * managementFeeBps * timeElapsed) / (10000 * 365 days)
        uint256 feeAmount = (totalAssets_ * managementFeeBps * timeElapsed) / (10000 * 365 days);

        if (feeAmount > 0) {
            // Minta shares para a treasury equivalentes ao fee
            uint256 shares = convertToShares(feeAmount);
            _mint(treasury, shares);
            emit ManagementFeeCharged(feeAmount, shares);
        }

        lastManagementFeeTimestamp = block.timestamp;
    }

    /**
     * @notice Cobra performance fee sobre lucro realizado
     * @param profit Lucro realizado
     * @return netProfit Lucro após fee
     */
    function _chargePerformanceFee(uint256 profit) internal returns (uint256 netProfit) {
        if (performanceFeeBps == 0 || profit == 0) {
            return profit;
        }

        // Performance fee é cobrada apenas sobre lucro acima do high water mark
        uint256 totalAssets_ = totalAssets();

        if (totalAssets_ > highWaterMark) {
            uint256 profitAboveHWM = totalAssets_ - highWaterMark;
            if (profitAboveHWM > profit) {
                profitAboveHWM = profit;
            }

            uint256 fee = (profitAboveHWM * performanceFeeBps) / 10000;
            netProfit = profit - fee;

            if (fee > 0) {
                // Minta shares para a treasury equivalentes ao fee
                uint256 shares = convertToShares(fee);
                _mint(treasury, shares);
                emit PerformanceFeeCharged(profit, fee);
            }

            // Atualiza high water mark
            highWaterMark = totalAssets_;
        } else {
            netProfit = profit;
        }
    }

    /**
     * @notice Aplica swap fee ao valor do swap
     * @param amountIn Quantidade a ser swapada
     * @return netAmount Quantidade após fee
     */
    function _applySwapFee(uint256 amountIn) internal returns (uint256 netAmount) {
        if (swapFeeBps == 0) {
            return amountIn;
        }

        uint256 fee = (amountIn * swapFeeBps) / 10000;
        netAmount = amountIn - fee;

        if (fee > 0) {
            emit SwapFeeApplied(amountIn, fee);
        }
    }

    // ============================================
    // ORACLE (Chainlink)
    // ============================================

    /**
     * @notice Obtém preço do oracle Chainlink
     * @return price Preço atual
     * @return updatedAt Timestamp da última atualização
     */
    function _getOraclePrice() internal view returns (uint256 price, uint256 updatedAt) {
        (
            uint80 roundId,
            int256 answer,
            ,
            uint256 timestamp,
            uint80 answeredInRound
        ) = chainlinkPriceFeed.latestRoundData();

        require(answer > 0, "DeltaNeutralVault: invalid oracle price");
        require(answeredInRound >= roundId, "DeltaNeutralVault: stale oracle data");

        price = uint256(answer);
        updatedAt = timestamp;
    }

    /**
     * @notice Valida preço do keeper contra oracle
     * @param priceFromKeeper Preço fornecido pelo keeper
     */
    function _checkOracle(uint256 priceFromKeeper) internal view {
        (uint256 oraclePrice, uint256 updatedAt) = _getOraclePrice();

        // Verifica staleness
        require(
            block.timestamp - updatedAt <= maxOracleDelay,
            "DeltaNeutralVault: oracle data too old"
        );

        // Verifica desvio
        uint256 deviation;
        if (priceFromKeeper > oraclePrice) {
            deviation = ((priceFromKeeper - oraclePrice) * 10000) / oraclePrice;
        } else {
            deviation = ((oraclePrice - priceFromKeeper) * 10000) / oraclePrice;
        }

        require(
            deviation <= maxOracleDeviationBps,
            "DeltaNeutralVault: price deviation too high"
        );
    }

    // ============================================
    // FUNÇÕES DO KEEPER
    // ============================================

    /**
     * @notice Auto-exit da posição LP (chamado pelo keeper)
     * @param price Preço atual (para validação contra oracle)
     * @param reason Razão do exit
     */
    function autoExit(
        uint256 price,
        ExitReason reason
    ) external onlyKeeper whenNotPaused nonReentrant {
        // Valida oracle
        _checkOracle(price);

        // Cobra management fee
        _chargeManagementFee();

        uint256 totalAssetsBefore = totalAssets();

        // Fecha posição LP e converte tudo para USDC (stub)
        _closePositionAndConvertToUSDC();

        uint256 totalAssetsAfter = totalAssets();

        // Calcula lucro e cobra performance fee
        uint256 profit = 0;
        if (totalAssetsAfter > totalAssetsBefore) {
            profit = totalAssetsAfter - totalAssetsBefore;
            _chargePerformanceFee(profit);
        }

        emit AutoExitExecuted(price, reason, totalAssetsAfter, profit);
    }

    /**
     * @notice Auto-reenter em nova posição LP (chamado pelo keeper)
     * @param price Preço atual (para validação contra oracle)
     * @param _tickLower Novo tick inferior
     * @param _tickUpper Novo tick superior
     */
    function autoReenter(
        uint256 price,
        int24 _tickLower,
        int24 _tickUpper
    ) external onlyKeeper whenNotPaused nonReentrant {
        require(_tickLower < _tickUpper, "DeltaNeutralVault: invalid tick range");

        // Valida oracle
        _checkOracle(price);

        // Cobra management fee
        _chargeManagementFee();

        // Atualiza ticks
        tickLower = _tickLower;
        tickUpper = _tickUpper;

        uint256 totalAssets_ = totalAssets();

        // Abre nova posição LP (stub)
        _openPosition();

        emit AutoReenterExecuted(price, _tickLower, _tickUpper, totalAssets_);
    }

    /**
     * @notice Registra estado do hedge (para auditoria)
     * @param stateHash Hash do estado do hedge
     * @param timestamp Timestamp do estado
     */
    function recordHedgeState(
        bytes32 stateHash,
        uint64 timestamp
    ) external onlyKeeper {
        require(timestamp <= block.timestamp, "DeltaNeutralVault: future timestamp");
        emit HedgeStateRecorded(stateHash, timestamp);
    }

    /**
     * @notice Atualiza accounting (cobra management fee)
     */
    function updateAccounting() external onlyKeeper {
        _chargeManagementFee();
        emit AccountingUpdated(totalAssets(), totalSupply());
    }

    // ============================================
    // FUNÇÕES CORE (STUBS ETAPA 1)
    // ============================================

    /**
     * @notice Abre posição LP no Uniswap v3 (STUB - Etapa 2)
     * @dev Esta função será implementada completamente na Etapa 2
     */
    function _openPosition() internal {
        // STUB: Implementação completa virá na Etapa 2
        // Aqui será implementado:
        // 1. Cálculo da distribuição de assets entre token0 e token1
        // 2. Swaps necessários para balancear
        // 3. Approve dos tokens para o NonfungiblePositionManager
        // 4. Mint da posição LP
        // 5. Armazenamento do tokenId da posição
    }

    /**
     * @notice Fecha posição LP e converte tudo para USDC (STUB - Etapa 2)
     * @dev Esta função será implementada completamente na Etapa 2
     */
    function _closePositionAndConvertToUSDC() internal {
        // STUB: Implementação completa virá na Etapa 2
        // Aqui será implementado:
        // 1. Decrease liquidity da posição
        // 2. Collect fees e tokens
        // 3. Burn da posição NFT
        // 4. Swaps para converter tudo de volta para USDC
    }

    /**
     * @notice Executa swap via 1inch (STUB - Etapa 2)
     * @param tokenIn Token de entrada
     * @param tokenOut Token de saída
     * @param amountIn Quantidade a ser swapada
     * @return amountOut Quantidade recebida
     */
    function executeSwap(
        address tokenIn,
        address tokenOut,
        uint256 amountIn
    ) internal returns (uint256 amountOut) {
        // Aplica swap fee
        uint256 netAmountIn = _applySwapFee(amountIn);

        // STUB: Implementação completa virá na Etapa 2
        // Aqui será implementado:
        // 1. Preparação dos parâmetros para 1inch
        // 2. Chamada para o agregador 1inch
        // 3. Validação do slippage
        // 4. Retorno do amountOut real

        // Por enquanto, apenas retorna o valor de entrada (placeholder)
        amountOut = netAmountIn;

        emit SwapExecuted(tokenIn, tokenOut, amountIn, amountOut);
    }

    /**
     * @notice Emergency exit: fecha tudo e converte para USDC
     */
    function emergencyExitToUSDC() external onlyOwner whenPaused nonReentrant {
        // Fecha posição LP e converte para USDC
        _closePositionAndConvertToUSDC();

        uint256 totalAssets_ = totalAssets();
        emit EmergencyExitExecuted(totalAssets_);
    }

    // ============================================
    // OVERRIDES ERC4626
    // ============================================

    /**
     * @notice Override deposit para cobrar entry fee
     */
    function deposit(
        uint256 assets,
        address receiver
    ) public virtual override whenNotPaused nonReentrant returns (uint256) {
        // Cobra management fee antes do depósito
        _chargeManagementFee();

        // Transfer assets antes de cobrar fee
        IERC20(asset()).transferFrom(msg.sender, address(this), assets);

        // Cobra entry fee
        uint256 netAssets = _chargeEntryFee(assets);

        // Calcula shares baseado nos assets líquidos
        uint256 shares = previewDeposit(netAssets);

        // Minta shares para o receiver
        _mint(receiver, shares);

        emit Deposit(msg.sender, receiver, assets, shares);

        return shares;
    }

    /**
     * @notice Override withdraw para cobrar exit fee
     */
    function withdraw(
        uint256 assets,
        address receiver,
        address owner
    ) public virtual override whenNotPaused nonReentrant returns (uint256) {
        // Cobra management fee antes do saque
        _chargeManagementFee();

        uint256 shares = previewWithdraw(assets);

        if (msg.sender != owner) {
            _spendAllowance(owner, msg.sender, shares);
        }

        // Burn shares
        _burn(owner, shares);

        // Cobra exit fee
        uint256 netAssets = _chargeExitFee(assets);

        // Transfer assets para o receiver
        IERC20(asset()).transfer(receiver, netAssets);

        emit Withdraw(msg.sender, receiver, owner, assets, shares);

        return shares;
    }

    /**
     * @notice Override redeem para cobrar exit fee
     */
    function redeem(
        uint256 shares,
        address receiver,
        address owner
    ) public virtual override whenNotPaused nonReentrant returns (uint256) {
        // Cobra management fee antes do resgate
        _chargeManagementFee();

        if (msg.sender != owner) {
            _spendAllowance(owner, msg.sender, shares);
        }

        uint256 assets = previewRedeem(shares);

        // Burn shares
        _burn(owner, shares);

        // Cobra exit fee
        uint256 netAssets = _chargeExitFee(assets);

        // Transfer assets para o receiver
        IERC20(asset()).transfer(receiver, netAssets);

        emit Withdraw(msg.sender, receiver, owner, assets, shares);

        return assets;
    }

    /**
     * @notice Override totalAssets (por enquanto apenas retorna o saldo de USDC)
     * @dev Na Etapa 2, incluirá o valor da posição LP
     */
    function totalAssets() public view virtual override returns (uint256) {
        // STUB: Na Etapa 2, adicionar valor da posição LP
        return IERC20(asset()).balanceOf(address(this));
    }
}
