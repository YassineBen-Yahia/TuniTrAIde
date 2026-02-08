import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import ApiService from '../services/api';
import { 
  TrendingUp, TrendingDown, DollarSign, Search, ShoppingCart, MinusCircle, 
  Activity, AlertTriangle, CheckCircle2, Info
} from 'lucide-react';

const SimpleTradingComponent = () => {
  const { user } = useAuth();
  const [portfolios, setPortfolios] = useState([]);
  const [selectedPortfolio, setSelectedPortfolio] = useState(null);
  const [loading, setLoading] = useState(true);
  
  // Trading state
  const [searchSymbol, setSearchSymbol] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [tradeType, setTradeType] = useState('BUY');
  const [quantity, setQuantity] = useState('');
  const [price, setPrice] = useState('');
  const [selectedStock, setSelectedStock] = useState(null);
  const [isTrading, setIsTrading] = useState(false);

  useEffect(() => {
    if (user && user.id) {
      fetchData();
    }
  }, [user]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const portfoliosRes = await ApiService.getUserPortfolios();
      setPortfolios(portfoliosRes);
      
      if (portfoliosRes.length > 0) {
        setSelectedPortfolio(portfoliosRes[0]);
      }
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSearchStock = async (query) => {
    if (!query.trim()) {
      setSearchResults([]);
      return;
    }
    
    try {
      const response = await ApiService.searchStocks(query, 10);
      setSearchResults(response.results || []);
    } catch (error) {
      console.error('Error searching stocks:', error);
      setSearchResults([]);
    }
  };

  const handleSelectStock = async (stock) => {
    // Use stock object from search results as the base
    setSelectedStock(stock);
    setSearchSymbol(stock.stock_code);
    setPrice(stock.close_price?.toString() || '');
    setSearchResults([]);

    try {
      const marketData = await ApiService.getMarketData(stock.stock_code);

      let latestPoint = null;
      if (marketData && marketData.snapshot) {
        latestPoint = marketData.snapshot;
      } else if (Array.isArray(marketData) && marketData.length > 0) {
        latestPoint = marketData[marketData.length - 1];
      } else if (Array.isArray(marketData?.history) && marketData.history.length > 0) {
        latestPoint = marketData.history[marketData.history.length - 1];
      }

      const merged = {
        ...stock,
        close_price: latestPoint?.close ?? latestPoint?.close_price ?? stock.close_price,
        open_price: latestPoint?.open ?? latestPoint?.open_price ?? stock.open_price,
        high_price: latestPoint?.high ?? latestPoint?.high_price ?? stock.high_price,
        low_price: latestPoint?.low ?? latestPoint?.low_price ?? stock.low_price,
        volume: latestPoint?.volume ?? latestPoint?.QUANTITE_NEGOCIEE ?? stock.volume,
        daily_return_pct: latestPoint?.daily_return_pct ?? stock.daily_return_pct,
        anomaly: latestPoint?.anomaly ?? stock.anomaly ?? false,
        anomaly_score: latestPoint?.anomaly_score ?? stock.anomaly_score
      };

      setSelectedStock(merged);
      setPrice(merged.close_price?.toString() || '');
    } catch (error) {
      console.error('Error fetching detailed market data:', error);
    }
  };

  const handleExecuteTrade = async () => {
    if (!selectedPortfolio || !selectedStock || !quantity || !price) {
      alert('Please fill in all required fields');
      return;
    }

    try {
      setIsTrading(true);
      
      const transactionData = {
        stock_code: selectedStock.stock_code,
        stock_name: selectedStock.stock_name || selectedStock.stock_code,
        transaction_type: tradeType,
        shares: parseInt(quantity),
        price_per_share: parseFloat(price),
        fees: 0,
        notes: `${tradeType} order executed via trading platform`
      };

      await ApiService.createTransaction(selectedPortfolio.id, transactionData);
      
      alert(`${tradeType} order executed successfully!`);
      
      // Reset form
      setQuantity('');
      setSelectedStock(null);
      setSearchSymbol('');
      setPrice('');
      
      // Refresh portfolio data
      fetchData();
      
    } catch (error) {
      console.error('Error executing trade:', error);
      const errorMessage = error.message || 'Error executing trade. Please try again.';
      alert(errorMessage);
    } finally {
      setIsTrading(false);
    }
  };

  const calculateTradeValue = () => {
    const qty = parseFloat(quantity) || 0;
    const prc = parseFloat(price) || 0;
    return qty * prc;
  };

  if (loading) {
    return (
      <div className="min-h-screen app-shell flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-cyan-400 mx-auto mb-4"></div>
          <p className="text-slate-400">Loading trading platform...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen app-shell">
      <div className="container mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-slate-100">Trading Platform</h1>
          <p className="text-slate-400">Buy and sell stocks in real-time</p>
        </div>

        {/* Trading Interface */}
        <div className="panel p-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Trading Panel */}
            <div>
              <h3 className="text-lg font-semibold mb-4">Execute Trade</h3>
              <div className="space-y-4">
                {/* Portfolio Selection */}
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">Portfolio</label>
                  <select
                    value={selectedPortfolio?.id || ''}
                    onChange={(e) => setSelectedPortfolio(portfolios.find(p => p.id === parseInt(e.target.value)))}
                    className="select-field"
                  >
                    {portfolios.map(portfolio => (
                      <option key={portfolio.id} value={portfolio.id}>
                        {portfolio.name} ({(portfolio.cash_balance || 0).toFixed(2)} TND available)
                      </option>
                    ))}
                  </select>
                </div>

                {/* Stock Symbol Search */}
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">Stock Symbol</label>
                  <div className="relative">
                    <input
                      type="text"
                      value={searchSymbol}
                      onChange={(e) => {
                        setSearchSymbol(e.target.value);
                        handleSearchStock(e.target.value);
                      }}
                      placeholder="Search for stocks..."
                      className="input-field"
                    />
                    
                    {/* Search Results Dropdown */}
                    {searchResults.length > 0 && (
                      <div className="absolute z-10 w-full mt-1 panel border border-slate-700 rounded-md shadow-lg max-h-60 overflow-auto">
                        {searchResults.map((stock, index) => (
                          <div
                            key={index}
                            onClick={() => handleSelectStock(stock)}
                            className="p-3 hover:bg-slate-900/60 cursor-pointer border-b border-slate-800/60 last:border-b-0"
                          >
                            <div className="font-medium text-slate-100">{stock.stock_code}</div>
                            <div className="text-sm text-slate-400">{stock.stock_name}</div>
                            <div className="text-sm text-cyan-200">{stock.close_price} TND</div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                {/* Trade Type */}
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">Trade Type</label>
                  <div className="flex space-x-4">
                    <button
                      onClick={() => setTradeType('BUY')}
                      className={`flex-1 py-3 px-4 rounded-md font-medium transition-colors ${
                        tradeType === 'BUY'
                          ? 'bg-emerald-400 text-slate-900'
                          : 'bg-slate-900/60 text-slate-300 hover:bg-slate-800/60'
                      }`}
                    >
                      <ShoppingCart className="h-4 w-4 inline mr-2" />
                      Buy
                    </button>
                    <button
                      onClick={() => setTradeType('SELL')}
                      className={`flex-1 py-3 px-4 rounded-md font-medium transition-colors ${
                        tradeType === 'SELL'
                          ? 'bg-rose-400 text-slate-900'
                          : 'bg-slate-900/60 text-slate-300 hover:bg-slate-800/60'
                      }`}
                    >
                      <MinusCircle className="h-4 w-4 inline mr-2" />
                      Sell
                    </button>
                  </div>
                </div>

                {/* Quantity */}
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">Quantity</label>
                  <input
                    type="number"
                    value={quantity}
                    onChange={(e) => setQuantity(e.target.value)}
                    placeholder="Number of shares"
                    min="1"
                    step="1"
                    className="input-field"
                  />
                </div>

                {/* Price */}
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">Price per Share (TND)</label>
                  <input
                    type="number"
                    value={price}
                    onChange={(e) => setPrice(e.target.value)}
                    placeholder="Price per share"
                    min="0"
                    step="0.01"
                    className="input-field"
                  />
                </div>

                {/* Trade Summary */}
                {quantity && price && (
                  <div className="panel-muted p-4">
                    <h4 className="font-medium text-slate-100 mb-2">Trade Summary</h4>
                    <div className="space-y-1 text-sm">
                      <div className="flex justify-between">
                        <span>Total Value:</span>
                        <span className="font-medium">{calculateTradeValue().toFixed(2)} TND</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Fees:</span>
                        <span>0.00 TND</span>
                      </div>
                      <div className="flex justify-between border-t pt-1 mt-1">
                        <span className="font-medium">Total Cost:</span>
                        <span className="font-medium">{calculateTradeValue().toFixed(2)} TND</span>
                      </div>
                    </div>
                  </div>
                )}

                {/* Execute Trade Button */}
                <button
                  onClick={handleExecuteTrade}
                  disabled={!selectedPortfolio || !selectedStock || !quantity || !price || isTrading}
                  className={`w-full py-3 px-4 rounded-md font-medium transition-colors ${
                    tradeType === 'BUY'
                      ? 'bg-emerald-400 hover:bg-emerald-300 text-slate-900'
                      : 'bg-rose-400 hover:bg-rose-300 text-slate-900'
                  } disabled:opacity-50 disabled:cursor-not-allowed`}
                >
                  {isTrading ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white inline mr-2"></div>
                      Processing...
                    </>
                  ) : (
                    `${tradeType} ${quantity || 0} shares`
                  )}
                </button>
              </div>
            </div>

            {/* Market Data Panel */}
            <div>
              <h3 className="text-lg font-semibold mb-4">Market Data</h3>
              {selectedStock ? (
                <div className="space-y-4">
                  <div className="panel-muted p-4">
                    <h4 className="font-medium text-slate-100 mb-2">{selectedStock.stock_name || selectedStock.stock_code}</h4>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-slate-400">Symbol:</span>
                        <div className="font-medium">{selectedStock.stock_code}</div>
                      </div>
                      <div>
                        <span className="text-slate-400">Current Price:</span>
                        <div className="font-medium text-cyan-200">{selectedStock.close_price != null ? `${Number(selectedStock.close_price).toFixed(2)} TND` : '—'}</div>
                      </div>
                      <div>
                        <span className="text-slate-400">Open:</span>
                        <div className="font-medium">{selectedStock.open_price != null ? `${Number(selectedStock.open_price).toFixed(2)} TND` : '—'}</div>
                      </div>
                      <div>
                        <span className="text-slate-400">Volume:</span>
                        <div className="font-medium">{selectedStock.volume != null ? Number(selectedStock.volume).toLocaleString() : '—'}</div>
                      </div>
                    </div>
                    
                    {selectedStock.anomaly && (
                      <div className="mt-3 p-2 bg-amber-500/10 text-amber-200 border border-amber-400/30 rounded text-sm">
                        <AlertTriangle className="h-4 w-4 inline mr-1" />
                        Anomaly detected (Score: {selectedStock.anomaly_score?.toFixed(2)})
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div className="panel-muted p-8 text-center">
                  <Info className="h-12 w-12 text-slate-500 mx-auto mb-4" />
                  <p className="text-slate-500">Search and select a stock to view market data</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SimpleTradingComponent;