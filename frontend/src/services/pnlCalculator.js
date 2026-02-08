/**
 * P&L Calculator Utility
 * 
 * This module handles all Profit & Loss calculations for the portfolio.
 * It computes realized P&L (from completed trades) and unrealized P&L (from open positions)
 * based on transaction history without requiring backend model changes.
 * 
 * Definitions:
 * - Realized P&L: The actual profit/loss locked in when shares are sold
 *   Formula: (Sell Price - Average Purchase Price) × Shares Sold
 * 
 * - Unrealized P&L: The potential profit/loss on shares still held
 *   Formula: (Current Price - Average Purchase Price) × Current Shares
 */

/**
 * Calculate P&L metrics from transactions and holdings
 * @param {Array} transactions - Array of transaction objects
 * @param {Array} holdings - Array of holding objects with current prices
 * @param {Object} currentPrices - Optional map of stock_code -> current_price for real-time pricing
 * @returns {Object} P&L metrics including realized, unrealized, and per-stock breakdown
 */
export function calculatePnLFromTransactions(transactions = [], holdings = [], currentPrices = {}) {
  // Build a tracker for each stock's cost basis and realized P&L
  const stockTracker = {};

  // Sort transactions by date (oldest first) to process in order
  const sortedTransactions = [...transactions].sort((a, b) => {
    const dateA = new Date(a.transaction_date || a.date || 0);
    const dateB = new Date(b.transaction_date || b.date || 0);
    return dateA - dateB;
  });

  // Process each transaction to track cost basis and calculate realized P&L
  sortedTransactions.forEach(tx => {
    const stockCode = tx.stock_code;
    const stockName = tx.stock_name || stockCode;
    const shares = Number(tx.shares || 0);
    const pricePerShare = Number(tx.price_per_share || 0);
    const transactionType = (tx.transaction_type || '').toUpperCase();
    const fees = Number(tx.fees || 0);

    if (!stockTracker[stockCode]) {
      stockTracker[stockCode] = {
        stockCode,
        stockName,
        totalSharesBought: 0,
        totalCostBasis: 0,
        currentShares: 0,
        avgPurchasePrice: 0,
        realizedPnL: 0,
        sellTransactions: []
      };
    }

    const tracker = stockTracker[stockCode];

    if (transactionType === 'BUY') {
      // Add to total shares and cost basis
      tracker.totalSharesBought += shares;
      tracker.totalCostBasis += (shares * pricePerShare) + fees;
      tracker.currentShares += shares;

      // Recalculate weighted average purchase price
      if (tracker.currentShares > 0) {
        tracker.avgPurchasePrice = tracker.totalCostBasis / tracker.totalSharesBought;
      }
    } else if (transactionType === 'SELL') {
      if (tracker.currentShares > 0 && shares > 0) {
        // Calculate realized P&L for this sale
        // Use the average purchase price at the time of sale
        const costBasisOfSold = shares * tracker.avgPurchasePrice;
        const sellProceeds = (shares * pricePerShare) - fees;
        const realizedPnLThisSale = sellProceeds - costBasisOfSold;

        tracker.realizedPnL += realizedPnLThisSale;
        tracker.currentShares -= shares;

        // Track individual sell transactions for detailed reporting
        tracker.sellTransactions.push({
          date: tx.transaction_date || tx.date,
          shares,
          sellPrice: pricePerShare,
          avgCostAtSale: tracker.avgPurchasePrice,
          realizedPnL: realizedPnLThisSale,
          fees
        });

        // Note: We don't adjust totalCostBasis or totalSharesBought here
        // because we use them to track the average price paid across all buys
      }
    }
  });

  // Calculate unrealized P&L using current holdings and prices
  let totalRealizedPnL = 0;
  let totalUnrealizedPnL = 0;
  const stockBreakdown = [];

  // First, aggregate realized P&L from the tracker (covers stocks fully sold)
  Object.values(stockTracker).forEach(tracker => {
    totalRealizedPnL += tracker.realizedPnL;
  });

  // Process current holdings for unrealized P&L
  holdings.forEach(holding => {
    const stockCode = holding.stock_code;
    const shares = Number(holding.shares || 0);
    const avgPrice = Number(holding.avg_purchase_price || 0);
    
    // Get current price: from passed prices, from holding, or fallback to avg
    const currentPrice = Number(
      currentPrices[stockCode] ||
      holding.current_price ||
      holding.currentPrice ||
      avgPrice
    );

    if (shares > 0) {
      const marketValue = shares * currentPrice;
      const costBasis = shares * avgPrice;
      const unrealizedPnL = marketValue - costBasis;
      const unrealizedPnLPercent = costBasis > 0 ? (unrealizedPnL / costBasis) * 100 : 0;

      // Get realized P&L for this stock from tracker
      const trackerData = stockTracker[stockCode] || {};
      const realizedPnL = trackerData.realizedPnL || 0;

      totalUnrealizedPnL += unrealizedPnL;

      stockBreakdown.push({
        stockCode,
        stockName: holding.stock_name || stockCode,
        shares,
        avgPurchasePrice: avgPrice,
        currentPrice,
        marketValue,
        costBasis,
        unrealizedPnL,
        unrealizedPnLPercent,
        realizedPnL,
        totalPnL: unrealizedPnL + realizedPnL
      });
    } else if (shares === 0) {
      // Stock fully sold - only has realized P&L
      const trackerData = stockTracker[stockCode];
      if (trackerData && trackerData.realizedPnL !== 0) {
        stockBreakdown.push({
          stockCode,
          stockName: holding.stock_name || trackerData.stockName || stockCode,
          shares: 0,
          avgPurchasePrice: trackerData.avgPurchasePrice,
          currentPrice: 0,
          marketValue: 0,
          costBasis: 0,
          unrealizedPnL: 0,
          unrealizedPnLPercent: 0,
          realizedPnL: trackerData.realizedPnL,
          totalPnL: trackerData.realizedPnL
        });
      }
    }
  });

  // Also include stocks that were fully sold but not in holdings array
  Object.values(stockTracker).forEach(tracker => {
    if (tracker.currentShares === 0 && tracker.realizedPnL !== 0) {
      // Check if already in breakdown
      const exists = stockBreakdown.some(s => s.stockCode === tracker.stockCode);
      if (!exists) {
        stockBreakdown.push({
          stockCode: tracker.stockCode,
          stockName: tracker.stockName,
          shares: 0,
          avgPurchasePrice: tracker.avgPurchasePrice,
          currentPrice: 0,
          marketValue: 0,
          costBasis: 0,
          unrealizedPnL: 0,
          unrealizedPnLPercent: 0,
          realizedPnL: tracker.realizedPnL,
          totalPnL: tracker.realizedPnL
        });
      }
    }
  });

  const totalPnL = totalRealizedPnL + totalUnrealizedPnL;

  return {
    totalRealizedPnL,
    totalUnrealizedPnL,
    totalPnL,
    stockBreakdown,
    // Provide the tracker for detailed analysis if needed
    stockTracker
  };
}

/**
 * Calculate portfolio metrics combining holdings, transactions, and P&L
 * @param {Object} portfolio - Portfolio object with holdings and cash_balance
 * @param {Array} transactions - Transaction history
 * @param {Object} analyticsData - Optional analytics data from API
 * @param {Object} currentPrices - Optional real-time prices
 * @returns {Object} Complete portfolio metrics
 */
export function calculatePortfolioMetricsWithPnL(portfolio, transactions = [], analyticsData = {}, currentPrices = {}) {
  if (!portfolio) return null;

  const cashBalance = Number(portfolio.cash_balance || 0);
  const holdings = portfolio.holdings || [];
  
  // Calculate P&L from transactions
  const pnlData = calculatePnLFromTransactions(transactions, holdings, currentPrices);

  // Calculate holdings data with P&L
  let totalMarketValue = 0;
  let totalCostBasis = 0;

  const holdingsData = holdings
    .filter(h => Number(h.shares || 0) > 0) // Only active holdings
    .map(holding => {
      const stockCode = holding.stock_code;
      const shares = Number(holding.shares || 0);
      const avgPrice = Number(holding.avg_purchase_price || 0);
      const currentPrice = Number(
        currentPrices[stockCode] ||
        holding.current_price ||
        holding.currentPrice ||
        avgPrice
      );

      const marketValue = shares * currentPrice;
      const costBasis = shares * avgPrice;
      const unrealizedPnL = marketValue - costBasis;
      const unrealizedPnLPercent = costBasis > 0 ? (unrealizedPnL / costBasis) * 100 : 0;

      // Get realized P&L for this stock from calculated data
      const stockPnL = pnlData.stockBreakdown.find(s => s.stockCode === stockCode);
      const realizedPnL = stockPnL?.realizedPnL || 0;

      totalMarketValue += marketValue;
      totalCostBasis += costBasis;

      return {
        name: holding.stock_name || stockCode,
        stockCode,
        value: marketValue,
        shares,
        avgPrice,
        currentPrice,
        pnl: unrealizedPnL,
        pnlPercentage: unrealizedPnLPercent,
        realized: realizedPnL
      };
    });

  // Add stocks with only realized P&L (fully sold) 
  pnlData.stockBreakdown
    .filter(s => s.shares === 0 && s.realizedPnL !== 0)
    .forEach(stock => {
      // Check if not already included
      const exists = holdingsData.some(h => h.stockCode === stock.stockCode);
      if (!exists) {
        holdingsData.push({
          name: stock.stockName,
          stockCode: stock.stockCode,
          value: 0,
          shares: 0,
          avgPrice: stock.avgPurchasePrice,
          currentPrice: 0,
          pnl: 0,
          pnlPercentage: 0,
          realized: stock.realizedPnL,
          isSoldOut: true
        });
      }
    });

  // Calculate totals
  const totalValue = cashBalance + totalMarketValue;
  const investedAmount = totalCostBasis;

  // P&L values
  const realizedPnL = pnlData.totalRealizedPnL;
  const unrealizedPnL = pnlData.totalUnrealizedPnL;
  const totalPnL = pnlData.totalPnL;

  // ROI calculation
  const investedForRoi = investedAmount > 0 
    ? investedAmount 
    : Number(analyticsData.total_invested || 0);
  const roiPercentage = investedForRoi > 0 ? (totalPnL / investedForRoi) * 100 : 0;
  const roiDisplay = investedForRoi > 0 ? `${roiPercentage.toFixed(2)}%` : '--';

  // Add cash to holdings for pie chart
  if (cashBalance > 0) {
    holdingsData.push({
      name: 'Cash',
      stockCode: 'CASH',
      value: cashBalance,
      shares: 1,
      avgPrice: cashBalance,
      currentPrice: cashBalance,
      pnl: 0,
      pnlPercentage: 0,
      realized: 0
    });
  }

  return {
    totalValue,
    cashBalance,
    investedAmount,
    positionsValue: totalMarketValue,
    holdingsData,
    totalPnL,
    totalPnLPercentage: roiPercentage,
    realizedPnL,
    unrealizedPnL,
    roiPercentage,
    roiDisplay,
    totalInvested: investedForRoi,
    // Include the detailed breakdown for debugging/analysis
    pnlBreakdown: pnlData.stockBreakdown
  };
}

/**
 * Format P&L value for display
 * @param {number} value - P&L value
 * @param {string} currency - Currency code (default: TND)
 * @returns {string} Formatted P&L string
 */
export function formatPnL(value, currency = 'TND') {
  if (value === undefined || value === null || isNaN(value)) {
    return '--';
  }
  const formatted = Math.abs(value).toFixed(2);
  const sign = value >= 0 ? '+' : '-';
  return `${sign}${formatted} ${currency}`;
}

/**
 * Get color class for P&L value
 * @param {number} value - P&L value
 * @returns {string} Tailwind CSS color class
 */
export function getPnLColorClass(value) {
  if (value === undefined || value === null || isNaN(value)) {
    return 'text-slate-500';
  }
  return value >= 0 ? 'text-emerald-300' : 'text-rose-300';
}

export default {
  calculatePnLFromTransactions,
  calculatePortfolioMetricsWithPnL,
  formatPnL,
  getPnLColorClass
};