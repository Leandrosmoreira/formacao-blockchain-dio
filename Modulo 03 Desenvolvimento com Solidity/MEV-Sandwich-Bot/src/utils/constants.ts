/**
 * Constantes do projeto
 */

// Endereços Ethereum Mainnet
export const ADDRESSES = {
  // Uniswap V2
  UNISWAP_V2_ROUTER: "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D",
  UNISWAP_V2_FACTORY: "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f",

  // Uniswap V3
  UNISWAP_V3_ROUTER: "0xE592427A0AEce92De3Edee1F18E0157C05861564",
  UNISWAP_V3_FACTORY: "0x1F98431c8aD98523631AE4a59f267346ea31F984",

  // SushiSwap
  SUSHISWAP_ROUTER: "0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F",
  SUSHISWAP_FACTORY: "0xC0AEe478e3658e2610c5F7A4A2E1777cE9e4f2Ac",

  // Tokens
  WETH: "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
  USDC: "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
  USDT: "0xdAC17F958D2ee523a2206206994597C13D831ec7",
  DAI: "0x6B175474E89094C44Da98b954EedeAC495271d0F",
};

// ABIs necessárias
export const ABIS = {
  ERC20: [
    "function decimals() view returns (uint8)",
    "function symbol() view returns (string)",
    "function balanceOf(address) view returns (uint256)",
    "function approve(address spender, uint256 amount) returns (bool)",
    "function allowance(address owner, address spender) view returns (uint256)",
  ],

  UNISWAP_V2_ROUTER: [
    "function swapExactTokensForTokens(uint amountIn, uint amountOutMin, address[] calldata path, address to, uint deadline) external returns (uint[] memory amounts)",
    "function swapTokensForExactTokens(uint amountOut, uint amountInMax, address[] calldata path, address to, uint deadline) external returns (uint[] memory amounts)",
    "function getAmountsOut(uint amountIn, address[] calldata path) external view returns (uint[] memory amounts)",
    "function getAmountsIn(uint amountOut, address[] calldata path) external view returns (uint[] memory amounts)",
  ],

  UNISWAP_V2_PAIR: [
    "function getReserves() external view returns (uint112 reserve0, uint112 reserve1, uint32 blockTimestampLast)",
    "function token0() external view returns (address)",
    "function token1() external view returns (address)",
  ],

  UNISWAP_V2_FACTORY: [
    "function getPair(address tokenA, address tokenB) external view returns (address pair)",
  ],
};

// Configurações padrão
export const DEFAULTS = {
  MIN_PROFIT_WEI: BigInt("100000000000000000"), // 0.1 ETH
  MAX_GAS_PRICE_GWEI: 300,
  SLIPPAGE_TOLERANCE: 0.5, // 0.5%
  DEADLINE_SECONDS: 300, // 5 minutos
  MIN_LIQUIDITY_USD: 100000, // $100k
  MAX_POSITION_SIZE_ETH: 50, // 50 ETH
  GAS_LIMIT_SANDWICH: 500000,
};

// Taxas dos DEXs (em basis points, 1 bp = 0.01%)
export const DEX_FEES = {
  UNISWAP_V2: 30, // 0.3%
  UNISWAP_V3_LOW: 5, // 0.05%
  UNISWAP_V3_MEDIUM: 30, // 0.3%
  UNISWAP_V3_HIGH: 100, // 1%
  SUSHISWAP: 30, // 0.3%
};

// Thresholds para análise
export const THRESHOLDS = {
  MIN_PRICE_IMPACT: 1, // 1% de impacto mínimo
  MIN_SWAP_SIZE_ETH: 10, // 10 ETH mínimo para considerar
  MAX_SLIPPAGE: 5, // 5% máximo de slippage aceitável
};

// Configurações de retry
export const RETRY_CONFIG = {
  MAX_RETRIES: 3,
  RETRY_DELAY_MS: 1000,
  BACKOFF_MULTIPLIER: 2,
};

// Tempos em milissegundos
export const TIMINGS = {
  MEMPOOL_POLL_INTERVAL: 100,
  PRICE_UPDATE_INTERVAL: 5000,
  METRICS_LOG_INTERVAL: 60000,
  WEBSOCKET_RECONNECT_DELAY: 5000,
};
