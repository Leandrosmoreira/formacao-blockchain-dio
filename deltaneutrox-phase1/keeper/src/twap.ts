/**
 * Time-Weighted Average Price (TWAP) Calculator
 *
 * Maintains a sliding window of price observations and calculates
 * the time-weighted average price over that window.
 */

export interface PriceObservation {
  price: number;
  timestamp: number; // Unix timestamp in seconds
  confidence: number;
}

export class TWAPCalculator {
  private observations: PriceObservation[] = [];
  private windowSecs: number;

  constructor(windowSecs: number) {
    if (windowSecs < 10) {
      throw new Error('TWAP window must be at least 10 seconds');
    }
    this.windowSecs = windowSecs;
  }

  /**
   * Add a new price observation
   */
  addObservation(price: number, timestamp: number, confidence: number): void {
    // Validate inputs
    if (price <= 0) {
      throw new Error('Price must be positive');
    }
    if (confidence <= 0) {
      throw new Error('Confidence must be positive');
    }

    // Add observation
    this.observations.push({ price, timestamp, confidence });

    // Clean old observations outside the window
    this.cleanOldObservations(timestamp);
  }

  /**
   * Remove observations older than the TWAP window
   */
  private cleanOldObservations(currentTimestamp: number): void {
    const cutoffTime = currentTimestamp - this.windowSecs;
    this.observations = this.observations.filter(
      obs => obs.timestamp > cutoffTime
    );
  }

  /**
   * Calculate the TWAP over the current window
   *
   * Returns null if there are not enough observations
   */
  calculateTWAP(): number | null {
    if (this.observations.length < 2) {
      return null; // Need at least 2 observations for time weighting
    }

    // Sort observations by timestamp (should already be sorted, but ensure it)
    const sorted = [...this.observations].sort((a, b) => a.timestamp - b.timestamp);

    let weightedSum = 0;
    let totalWeight = 0;

    // Calculate time-weighted average
    // Each price is weighted by the time duration until the next price
    for (let i = 0; i < sorted.length - 1; i++) {
      const currentObs = sorted[i];
      const nextObs = sorted[i + 1];

      const timeDelta = nextObs.timestamp - currentObs.timestamp;

      // Weight by time delta and confidence
      const weight = timeDelta / currentObs.confidence;
      weightedSum += currentObs.price * weight;
      totalWeight += weight;
    }

    // Add the last observation (weighted by time since it was added)
    const lastObs = sorted[sorted.length - 1];
    const currentTime = Math.floor(Date.now() / 1000);
    const lastTimeDelta = Math.max(1, currentTime - lastObs.timestamp);
    const lastWeight = lastTimeDelta / lastObs.confidence;
    weightedSum += lastObs.price * lastWeight;
    totalWeight += lastWeight;

    if (totalWeight === 0) {
      return null;
    }

    return weightedSum / totalWeight;
  }

  /**
   * Get simple average price (non-time-weighted)
   * Useful for comparison or when TWAP window is not filled yet
   */
  getSimpleAverage(): number | null {
    if (this.observations.length === 0) {
      return null;
    }

    const sum = this.observations.reduce((acc, obs) => acc + obs.price, 0);
    return sum / this.observations.length;
  }

  /**
   * Get the latest price observation
   */
  getLatestPrice(): number | null {
    if (this.observations.length === 0) {
      return null;
    }
    return this.observations[this.observations.length - 1].price;
  }

  /**
   * Get the number of observations in the window
   */
  getObservationCount(): number {
    return this.observations.length;
  }

  /**
   * Check if the TWAP window is sufficiently filled
   * Returns true if we have observations spanning at least 80% of the window
   */
  isWindowFilled(): boolean {
    if (this.observations.length < 2) {
      return false;
    }

    const sorted = [...this.observations].sort((a, b) => a.timestamp - b.timestamp);
    const oldestTimestamp = sorted[0].timestamp;
    const newestTimestamp = sorted[sorted.length - 1].timestamp;
    const timeSpan = newestTimestamp - oldestTimestamp;

    // Consider filled if we have 80% of the window covered
    return timeSpan >= (this.windowSecs * 0.8);
  }

  /**
   * Get statistics about the current price window
   */
  getStatistics(): {
    count: number;
    latest: number | null;
    twap: number | null;
    simpleAvg: number | null;
    windowFilled: boolean;
    timeSpanSecs: number;
  } {
    const twap = this.calculateTWAP();
    const simpleAvg = this.getSimpleAverage();
    const latest = this.getLatestPrice();

    let timeSpanSecs = 0;
    if (this.observations.length >= 2) {
      const sorted = [...this.observations].sort((a, b) => a.timestamp - b.timestamp);
      timeSpanSecs = sorted[sorted.length - 1].timestamp - sorted[0].timestamp;
    }

    return {
      count: this.observations.length,
      latest,
      twap,
      simpleAvg,
      windowFilled: this.isWindowFilled(),
      timeSpanSecs,
    };
  }

  /**
   * Reset the calculator (clear all observations)
   */
  reset(): void {
    this.observations = [];
  }
}
