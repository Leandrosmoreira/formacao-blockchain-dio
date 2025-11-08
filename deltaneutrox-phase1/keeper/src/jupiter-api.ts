import axios from 'axios';
import { PublicKey } from '@solana/web3.js';

/**
 * Jupiter API Client
 *
 * Fetches optimal swap routes from Jupiter Aggregator V6
 */

export interface JupiterQuoteResponse {
  inputMint: string;
  inAmount: string;
  outputMint: string;
  outAmount: string;
  otherAmountThreshold: string;
  swapMode: string;
  slippageBps: number;
  platformFee: null | {
    amount: string;
    feeBps: number;
  };
  priceImpactPct: string;
  routePlan: Array<{
    swapInfo: {
      ammKey: string;
      label: string;
      inputMint: string;
      outputMint: string;
      inAmount: string;
      outAmount: string;
      feeAmount: string;
      feeMint: string;
    };
    percent: number;
  }>;
  contextSlot: number;
  timeTaken: number;
}

export interface JupiterSwapInstructions {
  tokenLedgerInstruction: null | any;
  computeBudgetInstructions: any[];
  setupInstructions: any[];
  swapInstruction: {
    programId: string;
    accounts: Array<{
      pubkey: string;
      isSigner: boolean;
      isWritable: boolean;
    }>;
    data: string;
  };
  cleanupInstruction: null | any;
  addressLookupTableAddresses: string[];
}

export class JupiterClient {
  private apiUrl: string;

  constructor(apiUrl: string = 'https://quote-api.jup.ag/v6') {
    this.apiUrl = apiUrl;
  }

  /**
   * Get a quote for swapping tokens
   *
   * @param inputMint - Input token mint address
   * @param outputMint - Output token mint address
   * @param amount - Amount to swap (in lamports/smallest unit)
   * @param slippageBps - Slippage tolerance in basis points (e.g., 50 = 0.5%)
   */
  async getQuote(
    inputMint: PublicKey,
    outputMint: PublicKey,
    amount: number,
    slippageBps: number = 50
  ): Promise<JupiterQuoteResponse> {
    try {
      const params = new URLSearchParams({
        inputMint: inputMint.toString(),
        outputMint: outputMint.toString(),
        amount: amount.toString(),
        slippageBps: slippageBps.toString(),
        onlyDirectRoutes: 'false',
        asLegacyTransaction: 'false',
      });

      const url = `${this.apiUrl}/quote?${params}`;
      console.log(`Fetching Jupiter quote: ${url}`);

      const response = await axios.get<JupiterQuoteResponse>(url, {
        timeout: 10000,
      });

      if (!response.data) {
        throw new Error('No quote data received from Jupiter');
      }

      console.log(`Jupiter quote received:`);
      console.log(`  Input: ${response.data.inAmount} ${inputMint.toString().slice(0, 8)}...`);
      console.log(`  Output: ${response.data.outAmount} ${outputMint.toString().slice(0, 8)}...`);
      console.log(`  Price Impact: ${response.data.priceImpactPct}%`);
      console.log(`  Routes: ${response.data.routePlan.length}`);

      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        console.error('Jupiter API error:', error.response?.data || error.message);
      } else {
        console.error('Error fetching Jupiter quote:', error);
      }
      throw error;
    }
  }

  /**
   * Get swap instructions from Jupiter
   *
   * Note: In the actual implementation, you would use the Jupiter SDK
   * or make a POST request to /swap-instructions endpoint with the quote.
   * This is a placeholder for the integration.
   */
  async getSwapInstructions(
    quote: JupiterQuoteResponse,
    userPublicKey: PublicKey
  ): Promise<JupiterSwapInstructions> {
    try {
      const url = `${this.apiUrl}/swap-instructions`;

      const response = await axios.post<JupiterSwapInstructions>(
        url,
        {
          quoteResponse: quote,
          userPublicKey: userPublicKey.toString(),
          wrapAndUnwrapSol: true,
          computeUnitPriceMicroLamports: 'auto',
        },
        {
          timeout: 10000,
        }
      );

      if (!response.data) {
        throw new Error('No swap instructions received from Jupiter');
      }

      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        console.error('Jupiter swap instructions error:', error.response?.data || error.message);
      } else {
        console.error('Error fetching Jupiter swap instructions:', error);
      }
      throw error;
    }
  }

  /**
   * Calculate minimum output amount with slippage
   */
  calculateMinimumOut(expectedOut: string, slippageBps: number): string {
    const outAmount = BigInt(expectedOut);
    const slippageMultiplier = BigInt(10000 - slippageBps);
    const minOut = (outAmount * slippageMultiplier) / BigInt(10000);
    return minOut.toString();
  }

  /**
   * Parse route plan into a human-readable format
   */
  parseRoutePlan(quote: JupiterQuoteResponse): string[] {
    return quote.routePlan.map((route, index) => {
      const swap = route.swapInfo;
      return `Route ${index + 1}: ${swap.label} (${swap.inputMint.slice(0, 8)}... → ${swap.outputMint.slice(0, 8)}...) - ${route.percent}%`;
    });
  }

  /**
   * Check if quote is acceptable based on price impact threshold
   */
  isQuoteAcceptable(quote: JupiterQuoteResponse, maxPriceImpactPct: number = 1.0): boolean {
    const priceImpact = parseFloat(quote.priceImpactPct);
    return priceImpact <= maxPriceImpactPct;
  }
}
