// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./interfaces/IUniswapV2Router.sol";
import "./interfaces/IERC20.sol";

/**
 * @title SandwichBot
 * @notice Contrato para executar sandwich attacks de forma atômica
 * @dev APENAS PARA FINS EDUCACIONAIS
 */
contract SandwichBot {
    address public immutable owner;

    // Eventos
    event SandwichExecuted(
        address indexed token,
        uint256 frontrunAmount,
        uint256 backrunAmount,
        uint256 profit
    );

    event EmergencyWithdraw(
        address indexed token,
        uint256 amount
    );

    // Modifiers
    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    /**
     * @notice Executa um sandwich attack
     * @param router Endereço do router DEX
     * @param tokenIn Token de entrada
     * @param tokenOut Token de saída
     * @param frontrunAmount Quantidade para o frontrun
     * @param minProfitAmount Lucro mínimo aceitável
     * @param deadline Deadline da transação
     */
    function executeSandwich(
        address router,
        address tokenIn,
        address tokenOut,
        uint256 frontrunAmount,
        uint256 minProfitAmount,
        uint256 deadline
    ) external onlyOwner returns (uint256 profit) {
        require(frontrunAmount > 0, "Invalid amount");
        require(deadline >= block.timestamp, "Deadline passed");

        IERC20 inputToken = IERC20(tokenIn);
        IERC20 outputToken = IERC20(tokenOut);
        IUniswapV2Router dexRouter = IUniswapV2Router(router);

        // Verificar saldo inicial
        uint256 initialBalance = inputToken.balanceOf(address(this));
        require(initialBalance >= frontrunAmount, "Insufficient balance");

        // Aprovar router para gastar tokens
        inputToken.approve(router, frontrunAmount);

        // Path para o swap
        address[] memory path = new address[](2);
        path[0] = tokenIn;
        path[1] = tokenOut;

        // 1. FRONTRUN: Comprar tokenOut com tokenIn
        uint256[] memory frontrunAmounts = dexRouter.swapExactTokensForTokens(
            frontrunAmount,
            0, // Aceitar qualquer quantidade (calculamos off-chain)
            path,
            address(this),
            deadline
        );

        uint256 acquiredTokens = frontrunAmounts[1];

        // Agora a vítima executa seu swap (acontece entre este bloco e o próximo)
        // O preço do tokenOut aumenta

        // 2. BACKRUN: Vender os tokens adquiridos
        // Preparar path reverso
        address[] memory reversePath = new address[](2);
        reversePath[0] = tokenOut;
        reversePath[1] = tokenIn;

        // Aprovar router para gastar os tokens adquiridos
        outputToken.approve(router, acquiredTokens);

        // Executar backrun
        uint256[] memory backrunAmounts = dexRouter.swapExactTokensForTokens(
            acquiredTokens,
            frontrunAmount, // Mínimo: recuperar o que gastamos
            reversePath,
            address(this),
            deadline
        );

        uint256 finalAmount = backrunAmounts[1];

        // Calcular lucro
        profit = finalAmount > frontrunAmount ? finalAmount - frontrunAmount : 0;

        // Verificar lucro mínimo
        require(profit >= minProfitAmount, "Insufficient profit");

        emit SandwichExecuted(tokenIn, frontrunAmount, acquiredTokens, profit);

        return profit;
    }

    /**
     * @notice Executa apenas o frontrun (usado em bundle com Flashbots)
     * @param router Endereço do router DEX
     * @param tokenIn Token de entrada
     * @param tokenOut Token de saída
     * @param amount Quantidade para swap
     * @param minAmountOut Quantidade mínima de saída
     * @param deadline Deadline
     */
    function executeFrontrun(
        address router,
        address tokenIn,
        address tokenOut,
        uint256 amount,
        uint256 minAmountOut,
        uint256 deadline
    ) external onlyOwner returns (uint256 amountOut) {
        IERC20 inputToken = IERC20(tokenIn);
        IUniswapV2Router dexRouter = IUniswapV2Router(router);

        require(inputToken.balanceOf(address(this)) >= amount, "Insufficient balance");

        inputToken.approve(router, amount);

        address[] memory path = new address[](2);
        path[0] = tokenIn;
        path[1] = tokenOut;

        uint256[] memory amounts = dexRouter.swapExactTokensForTokens(
            amount,
            minAmountOut,
            path,
            address(this),
            deadline
        );

        return amounts[1];
    }

    /**
     * @notice Executa apenas o backrun (usado em bundle com Flashbots)
     * @param router Endereço do router DEX
     * @param tokenIn Token de entrada
     * @param tokenOut Token de saída
     * @param amount Quantidade para swap
     * @param minAmountOut Quantidade mínima de saída
     * @param deadline Deadline
     */
    function executeBackrun(
        address router,
        address tokenIn,
        address tokenOut,
        uint256 amount,
        uint256 minAmountOut,
        uint256 deadline
    ) external onlyOwner returns (uint256 amountOut) {
        IERC20 inputToken = IERC20(tokenIn);
        IUniswapV2Router dexRouter = IUniswapV2Router(router);

        require(inputToken.balanceOf(address(this)) >= amount, "Insufficient balance");

        inputToken.approve(router, amount);

        address[] memory path = new address[](2);
        path[0] = tokenIn;
        path[1] = tokenOut;

        uint256[] memory amounts = dexRouter.swapExactTokensForTokens(
            amount,
            minAmountOut,
            path,
            address(this),
            deadline
        );

        return amounts[1];
    }

    /**
     * @notice Retira tokens do contrato (emergência)
     * @param token Endereço do token (address(0) para ETH)
     * @param amount Quantidade a retirar (0 para tudo)
     */
    function emergencyWithdraw(address token, uint256 amount) external onlyOwner {
        if (token == address(0)) {
            // Retirar ETH
            uint256 balance = address(this).balance;
            uint256 withdrawAmount = amount == 0 ? balance : amount;
            require(withdrawAmount <= balance, "Insufficient ETH balance");

            payable(owner).transfer(withdrawAmount);
            emit EmergencyWithdraw(address(0), withdrawAmount);
        } else {
            // Retirar ERC20
            IERC20 erc20 = IERC20(token);
            uint256 balance = erc20.balanceOf(address(this));
            uint256 withdrawAmount = amount == 0 ? balance : amount;
            require(withdrawAmount <= balance, "Insufficient token balance");

            require(erc20.transfer(owner, withdrawAmount), "Transfer failed");
            emit EmergencyWithdraw(token, withdrawAmount);
        }
    }

    /**
     * @notice Retira lucros para o owner
     * @param token Token a retirar
     */
    function withdrawProfits(address token) external onlyOwner {
        IERC20 erc20 = IERC20(token);
        uint256 balance = erc20.balanceOf(address(this));
        require(balance > 0, "No profits to withdraw");
        require(erc20.transfer(owner, balance), "Transfer failed");
    }

    /**
     * @notice Verifica saldo de um token
     * @param token Endereço do token
     */
    function getTokenBalance(address token) external view returns (uint256) {
        return IERC20(token).balanceOf(address(this));
    }

    /**
     * @notice Permite receber ETH
     */
    receive() external payable {}
}
