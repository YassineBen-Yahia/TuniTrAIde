import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../contexts/AuthContext';
import ApiService from '../services/api';
import { 
  ShoppingCart, MinusCircle, AlertTriangle, CheckCircle2, Info, ChevronDown, Search
} from 'lucide-react';

/**
 * TradingSimulation Component
 * 
 * Simulated trading interface for buying/selling stocks.
 * 
 * DATA SOURCES (via API endpoints → Backend):
 * ──────────────────────────────────────────────────────────────
 * 1. Stock Search:
 *    - API: GET /stocks/search?q={query}
 *    - Source: data/historical_data.csv (CODE, VALEUR, CLOTURE)
 * 
 * 2. Current Stock Prices:
 *    - API: GET /market-data/{symbol}
 *    - Source: data/historical_data.csv (latest CLOTURE, VARIATION)
 * 
 * 3. Portfolio & Holdings:
 *    - API: GET /portfolios, GET /portfolios/{id}/holdings
 *    - Source: SQLite Database (portfolios, holdings tables)
 * 
 * 4. Transactions:
 *    - API: POST /portfolios/{id}/transactions
 *    - Source: SQLite Database (transactions table)
 */

const TradingSimulation = () => {
  const { user } = useAuth();
  const [portfolios, setPortfolios] = useState([]);
  const [selectedPortfolio, setSelectedPortfolio] = useState(null);
  const [loading, setLoading] = useState(true);
  
  // Trading state
  const [searchSymbol, setSearchSymbol] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [allStocks, setAllStocks] = useState([]);
  const [showStockDropdown, setShowStockDropdown] = useState(false);
  const [tradeType, setTradeType] = useState('BUY');
  const [quantity, setQuantity] = useState('');
  const [price, setPrice] = useState('');
  const [selectedStock, setSelectedStock] = useState(null);
  const [isTrading, setIsTrading] = useState(false);
  const [toast, setToast] = useState(null);
  const toastTimerRef = useRef(null);
  const stockDropdownRef = useRef(null);

  useEffect(() => {
    if (user && user.id) {
      fetchData();
      fetchAllStocks();
    }
  }, [user]);

  useEffect(() => {
    // Close dropdown when clicking outside
    const handleClickOutside = (e) => {
      if (stockDropdownRef.current && !stockDropdownRef.current.contains(e.target)) {
        setShowStockDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  useEffect(() => {
    if (!toast) {
      return undefined;
    }
    if (toastTimerRef.current) {
      clearTimeout(toastTimerRef.current);
    }
    toastTimerRef.current = setTimeout(() => {
      setToast(null);
    }, 3500);
    return () => {
      if (toastTimerRef.current) {
        clearTimeout(toastTimerRef.current);
      }
    };
  }, [toast]);

  const showToast = ({ type = 'info', title, message }) => {
    setToast({ type, title, message });
  };

  const fetchAllStocks = async () => {
    try {
      const resp = await ApiService.getAllStocks(200);
      let arr = [];
      if (Array.isArray(resp)) arr = resp;
      else if (resp && Array.isArray(resp.stocks)) arr = resp.stocks;
      else if (resp && Array.isArray(resp.data)) arr = resp.data;
      setAllStocks(arr || []);
    } catch (err) {
      console.error('Failed to fetch all stocks:', err);
      setAllStocks([]);
    }
  };

  const fetchData = async () => {
    try {
      setLoading(true);
      const portfoliosRes = await ApiService.getUserPortfolios();
      
      setPortfolios(portfoliosRes);
      
      if (portfoliosRes.length > 0) {
        // Fetch detailed portfolio with holdings
        try {
          const detailedPortfolio = await ApiService.getPortfolio(portfoliosRes[0].id);
          setSelectedPortfolio(detailedPortfolio);
        } catch (err) {
          console.warn('Could not fetch detailed portfolio:', err);
          setSelectedPortfolio(portfoliosRes[0]);
        }
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
    // Get the code and name, handling different response structures
    const code = stock.stock_code || stock.symbol || stock.code || '';
    const name = stock.stock_name || stock.name || '';
    
    // Keep the stock object as base (it includes close_price from search results)
    setSelectedStock(stock);
    setSearchSymbol(name || code);
    setPrice(stock.close_price?.toString() || stock.price?.toString() || '');
    setSearchResults([]);
    setShowStockDropdown(false);

    // Try to enrich with detailed market data (historical series)
    try {
      const marketData = await ApiService.getMarketData(code);

      // marketData is { history: [...], snapshot: {...} } when available
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
      showToast({
        type: 'error',
        title: 'Missing information',
        message: 'Please fill in all required fields before executing a trade.'
      });
      return;
    }

    // For SELL orders, check if user owns enough shares
    if (tradeType === 'SELL') {
      const holdings = selectedPortfolio.holdings || [];
      const stockHolding = holdings.find(
        h => h.stock_code === selectedStock.stock_code || h.stock_code === selectedStock.code
      );
      
      if (!stockHolding || stockHolding.shares <= 0) {
        showToast({
          type: 'error',
          title: 'No shares to sell',
          message: `You do not own any shares of ${selectedStock.stock_name || selectedStock.stock_code}. You can only sell stocks that you currently hold.`
        });
        return;
      }
      
      if (stockHolding.shares < parseInt(quantity)) {
        showToast({
          type: 'error',
          title: 'Insufficient shares',
          message: `You only own ${Math.floor(stockHolding.shares)} shares of ${selectedStock.stock_name || selectedStock.stock_code}. Cannot sell ${parseInt(quantity)} shares.`
        });
        return;
      }
    }

    try {
      setIsTrading(true);
      const transactionData = {
        stock_code: selectedStock.stock_code,
        stock_name: selectedStock.stock_name,
        transaction_type: tradeType,
        shares: parseInt(quantity),
        price_per_share: parseFloat(price),
        fees: 0,
        notes: `${tradeType} order executed via trading platform`,
        recommended_by_ai: false
      };

      await ApiService.createTransaction(selectedPortfolio.id, transactionData);
      showToast({
        type: 'success',
        title: `${tradeType} order executed`,
        message: `${selectedStock.stock_code} - ${parseInt(quantity)} shares at ${parseFloat(price).toFixed(2)} TND`
      });
      
      // Reset form
      setQuantity('');
      setSearchSymbol('');
      setSelectedStock(null);
      setPrice('');
      setSearchResults([]);
      
      // Refresh data
      fetchData();
    } catch (error) {
      console.error('Error executing trade:', error);
      const errorMessage = error.message || 'Error executing trade. Please try again.';
      showToast({
        type: 'error',
        title: 'Trade failed',
        message: errorMessage
      });
    } finally {
      setIsTrading(false);
    }
  };

  const handleCreateSimulation = async () => {
    try {
      const simulation = await ApiService.createSimulation({
        ...newSimulation,
        start_date: new Date(newSimulation.start_date),
        end_date: new Date(newSimulation.end_date)
      });
      
      setSimulations([...simulations, simulation]);
      setCurrentSimulation(simulation);
      showToast({
        type: 'success',
        title: 'Simulation created',
        message: 'Your portfolio simulation was created successfully.'
      });
      
      // Reset form
      setNewSimulation({
        name: '',
        description: '',
        initial_capital: 10000,
        start_date: new Date().toISOString().split('T')[0],
        end_date: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
      });
    } catch (error) {
      console.error('Error creating simulation:', error);
      showToast({
        type: 'error',
        title: 'Simulation failed',
        message: 'Error creating simulation. Please try again.'
      });
    }
  };

  const handleRunSimulation = async (simulationId) => {
    try {
      await ApiService.runSimulation(simulationId);
      showToast({
        type: 'success',
        title: 'Simulation started',
        message: 'Check back later for results.'
      });
      fetchData(); // Refresh simulations
    } catch (error) {
      console.error('Error running simulation:', error);
      showToast({
        type: 'error',
        title: 'Simulation failed',
        message: 'Error running simulation. Please try again.'
      });
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
      {toast && (
        <div className="fixed top-6 right-6 z-50">
          <div
            className={`panel p-4 w-80 border ${
              toast.type === 'success'
                ? 'border-emerald-400/30 bg-emerald-500/10'
                : toast.type === 'error'
                ? 'border-rose-400/30 bg-rose-500/10'
                : 'border-cyan-400/30 bg-cyan-500/10'
            } shadow-[0_18px_40px_rgba(2,6,23,0.55)]`}
          >
            <div className="flex items-start gap-3">
              <div
                className={`mt-0.5 ${
                  toast.type === 'success'
                    ? 'text-emerald-300'
                    : toast.type === 'error'
                    ? 'text-rose-300'
                    : 'text-cyan-200'
                }`}
              >
                {toast.type === 'success' && <CheckCircle2 className="h-5 w-5" />}
                {toast.type === 'error' && <AlertTriangle className="h-5 w-5" />}
                {toast.type === 'info' && <Info className="h-5 w-5" />}
              </div>
              <div className="flex-1">
                <p className="text-sm font-semibold text-slate-100">{toast.title}</p>
                <p className="text-sm text-slate-300 mt-1">{toast.message}</p>
              </div>
              <button
                onClick={() => setToast(null)}
                className="text-slate-400 hover:text-slate-200 transition-colors"
                aria-label="Dismiss notification"
              >
                X
              </button>
            </div>
          </div>
        </div>
      )}
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

                    {/* Stock Symbol Search - Enhanced Dropdown */}
                    <div ref={stockDropdownRef}>
                      <label className="block text-sm font-medium text-slate-300 mb-2">
                        <Search className="inline w-4 h-4 mr-1" />
                        Select Stock
                      </label>
                      <div className="relative">
                        <div 
                          className="input-field flex items-center justify-between cursor-pointer min-h-[48px]"
                          onClick={() => setShowStockDropdown(!showStockDropdown)}
                        >
                          <input
                            type="text"
                            value={searchSymbol}
                            onChange={(e) => {
                              setSearchSymbol(e.target.value);
                              handleSearchStock(e.target.value);
                              setShowStockDropdown(true);
                            }}
                            onFocus={() => setShowStockDropdown(true)}
                            placeholder="Search by name or code..."
                            className="bg-transparent border-none outline-none flex-1 text-slate-100 placeholder-slate-500"
                          />
                          <ChevronDown className={`w-5 h-5 text-slate-400 transition-transform ${showStockDropdown ? 'rotate-180' : ''}`} />
                        </div>
                        
                        {/* Enhanced Stock Dropdown */}
                        {showStockDropdown && (
                          <div className="absolute z-10 w-full mt-1 bg-slate-900 border border-slate-700 rounded-xl shadow-2xl max-h-72 overflow-auto">
                            {(() => {
                              // Determine which list to show
                              const displayList = searchSymbol.trim() 
                                ? searchResults 
                                : allStocks.filter(s => {
                                    const code = s.stock_code || s.symbol || s.code || '';
                                    const name = s.stock_name || s.name || '';
                                    return code.toLowerCase() !== 'stocks' && name.toLowerCase() !== 'stocks';
                                  });
                              
                              if (displayList.length === 0) {
                                return <div className="px-4 py-6 text-center text-slate-500">No companies found</div>;
                              }
                              
                              return displayList.slice(0, 50).map((stock, index) => {
                                const code = stock.stock_code || stock.symbol || stock.code || '';
                                const name = stock.stock_name || stock.name || '';
                                const closePrice = stock.close_price ?? stock.price ?? null;
                                const isSelected = selectedStock && (selectedStock.stock_code === code || selectedStock.code === code);
                                
                                return (
                                  <button
                                    key={code || index}
                                    type="button"
                                    onClick={() => handleSelectStock(stock)}
                                    className={`w-full flex items-center justify-between px-4 py-3 text-left transition-colors
                                      hover:bg-slate-800
                                      ${isSelected ? 'bg-cyan-500/10 border-l-4 border-cyan-400' : 'border-l-4 border-transparent'}
                                    `}
                                  >
                                    <div>
                                      <div className="text-base font-medium text-slate-100">
                                        {name || code} {name && code && <span className="text-slate-500">({code})</span>}
                                      </div>
                                      {closePrice != null && (
                                        <div className="text-sm text-cyan-200">{Number(closePrice).toFixed(2)} TND</div>
                                      )}
                                    </div>
                                    {isSelected && <span className="text-xs text-cyan-400 font-medium">Selected</span>}
                                  </button>
                                );
                              });
                            })()}
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Trade Type */}
                    <div>
                      <label className="block text-sm font-medium text-slate-300 mb-2">Order Type</label>
                      <div className="flex space-x-4">
                        <button
                          onClick={() => setTradeType('BUY')}
                          className={`flex-1 py-2 px-4 rounded-md font-medium ${
                            tradeType === 'BUY'
                              ? 'bg-emerald-400 text-slate-900'
                              : 'bg-slate-800/60 text-slate-300 hover:bg-slate-700/60'
                          }`}
                        >
                          <ShoppingCart className="h-4 w-4 inline mr-2" />
                          BUY
                        </button>
                        <button
                          onClick={() => setTradeType('SELL')}
                          className={`flex-1 py-2 px-4 rounded-md font-medium ${
                            tradeType === 'SELL'
                              ? 'bg-rose-400 text-slate-900'
                              : 'bg-slate-800/60 text-slate-300 hover:bg-slate-700/60'
                          }`}
                        >
                          <MinusCircle className="h-4 w-4 inline mr-2" />
                          SELL
                        </button>
                      </div>
                    </div>

                    {/* Quantity and Price */}
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-slate-300 mb-2">Quantity</label>
                        <input
                          type="number"
                          step="1"
                          min="1"
                          value={quantity}
                          onChange={(e) => setQuantity(e.target.value)}
                          placeholder="0"
                          className="input-field"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-slate-300 mb-2">Price per Share (TND)</label>
                        <input
                          type="number"
                          step="0.01"
                          value={price}
                          onChange={(e) => setPrice(e.target.value)}
                          placeholder="0.00"
                          className="input-field"
                        />
                      </div>
                    </div>

                    {/* Total Value */}
                    {quantity && price && (
                      <div className="panel-muted p-4">
                        <div className="flex justify-between items-center">
                          <span className="font-medium text-slate-300">Total Value:</span>
                          <span className="font-bold text-lg text-slate-100">
                            {calculateTradeValue().toFixed(2)} TND
                          </span>
                        </div>
                      </div>
                    )}

                    {/* Execute Trade Button */}
                    <button
                      onClick={handleExecuteTrade}
                      disabled={isTrading || !selectedPortfolio || !selectedStock || !quantity || !price}
                      className="btn-primary w-full disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {isTrading ? 'Executing...' : `Execute ${tradeType} Order`}
                    </button>
                  </div>
                </div>

            {/* Market Data Panel */}
            <div>
              <h3 className="text-lg font-semibold mb-4">Market Data</h3>
              {selectedStock ? (
                <div className="panel-muted p-4">
                  <h4 className="font-medium text-slate-100 mb-2">
                    {selectedStock.stock_name} ({selectedStock.stock_code})
                  </h4>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-slate-400">Close Price:</span>
                      <span className="font-medium">{selectedStock.close_price != null ? `${Number(selectedStock.close_price).toFixed(2)} TND` : '—'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Open Price:</span>
                      <span className="font-medium">{selectedStock.open_price != null ? `${Number(selectedStock.open_price).toFixed(2)} TND` : '—'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">High:</span>
                      <span className="font-medium">{selectedStock.high_price != null ? `${Number(selectedStock.high_price).toFixed(2)} TND` : '—'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Low:</span>
                      <span className="font-medium">{selectedStock.low_price != null ? `${Number(selectedStock.low_price).toFixed(2)} TND` : '—'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Volume:</span>
                      <span className="font-medium">{selectedStock.volume != null ? Number(selectedStock.volume).toLocaleString() : '—'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Daily Return:</span>
                      <span className={`font-medium ${selectedStock.daily_return_pct >= 0 ? 'text-emerald-300' : 'text-rose-300'}`}>
                        {selectedStock.daily_return_pct != null ? `${Number(selectedStock.daily_return_pct).toFixed(2)}%` : '—'}
                      </span>
                    </div>
                    {selectedStock.anomaly && (
                      <div className="flex justify-between">
                        <span className="text-slate-400">Anomaly Score:</span>
                        <span className="font-medium text-amber-300">{selectedStock.anomaly_score?.toFixed(2)}</span>
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

export default TradingSimulation;