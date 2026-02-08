import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import ApiService from '../services/api';
import { calculatePortfolioMetricsWithPnL, getPnLColorClass } from '../services/pnlCalculator';
import { 
  PieChart, Pie, Cell, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar 
} from 'recharts';
import { 
  TrendingUp, TrendingDown, DollarSign, PieChart as PieChartIcon, 
  BarChart3, Eye, Plus, Minus, Activity, AlertCircle 
} from 'lucide-react';

const EnhancedDashboard = () => {
  const { user } = useAuth();
  const [portfolios, setPortfolios] = useState([]);
  const [selectedPortfolio, setSelectedPortfolio] = useState(null);
  const [portfolioTransactions, setPortfolioTransactions] = useState([]);
  const [portfolioAnalytics, setPortfolioAnalytics] = useState(null);
  const [portfolioPerformance, setPortfolioPerformance] = useState(null);
  const [userAnalytics, setUserAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    if (user && user.id) {
      fetchPortfolioData();
    }
  }, [user]);

  const fetchPortfolioData = async () => {
    try {
      setError(null);
      setLoading(true);
      
      // Debug: Check if analytics functions exist
      console.log('Analytics functions available:', {
        getPortfolioAnalytics: typeof ApiService.getPortfolioAnalytics,
        getUserAnalytics: typeof ApiService.getUserAnalytics
      });
      
      const portfoliosResponse = await ApiService.getUserPortfolios();
      setPortfolios(portfoliosResponse);
      
      if (portfoliosResponse.length > 0) {
        const firstPortfolio = portfoliosResponse[0];
        setSelectedPortfolio(firstPortfolio);
        
        // Fetch detailed portfolio data first
        const [detailedPortfolio, transactions] = await Promise.all([
          ApiService.getPortfolio(firstPortfolio.id),
          ApiService.getPortfolioTransactions(firstPortfolio.id)
        ]);
        
        setSelectedPortfolio(detailedPortfolio);
        setPortfolioTransactions(transactions);
        
        // Try to fetch analytics separately (optional)
        try {
          if (typeof ApiService.getPortfolioAnalytics === 'function' && 
              typeof ApiService.getUserAnalytics === 'function') {
            const [analytics, userAnalytics] = await Promise.all([
              ApiService.getPortfolioAnalytics(firstPortfolio.id),
              ApiService.getUserAnalytics()
            ]);
            setPortfolioAnalytics(analytics);
            setUserAnalytics(userAnalytics);

            // Try fetching performance (equity curve) - optional
            try {
              const perf = await ApiService.getPortfolioPerformance(firstPortfolio.id);
              setPortfolioPerformance(perf);
            } catch (perfErr) {
              console.warn('Portfolio performance not available:', perfErr.message);
            }
          } else {
            console.warn('Analytics functions not available');
            setPortfolioAnalytics({});
            setUserAnalytics({});
          }
        } catch (analyticsError) {
          console.warn('Analytics data not available:', analyticsError.message);
          // Set empty analytics data
          setPortfolioAnalytics({});
          setUserAnalytics({});
        }
      }
    } catch (error) {
      console.error('Error fetching portfolio data:', error);
      setError(error.message || 'Failed to load portfolio data. Please try refreshing the page.');
    } finally {
      setLoading(false);
    }
  };

  const calculatePortfolioMetrics = () => {
    if (!selectedPortfolio) return null;

    const analyticsData = portfolioAnalytics || {};
    const userAnalyticsData = userAnalytics || {};

    // Use the P&L calculator utility for accurate calculations from transactions
    const metrics = calculatePortfolioMetricsWithPnL(
      selectedPortfolio,
      portfolioTransactions,
      analyticsData
    );

    if (!metrics) return null;

    // Merge with user-level analytics
    return {
      ...metrics,
      // User-level analytics
      userTotalPnL: userAnalyticsData.total_pnl || 0,
      userROI: userAnalyticsData.roi_percentage || 0,
      userTotalInvested: userAnalyticsData.total_invested || 0
    };
  };

  const generateOptimizationSuggestions = () => {
    const suggestions = [];
    if (!selectedPortfolio || !metrics) return suggestions;

    const cashPct = metrics.totalValue > 0 ? (metrics.cashBalance / metrics.totalValue) * 100 : 0;
    if (cashPct >= 60) {
      suggestions.push(`Your cash is ${cashPct.toFixed(0)}% → consider diversifying (top 3 stable stocks)`);
    }

    // Per-holding rules (anomaly, predicted drop, concentration)
    const holdings = selectedPortfolio.holdings || [];
    holdings.forEach(h => {
      const name = h.stock_name || h.stock_code || 'Unknown';
      if (h.anomaly || (h.anomaly_score != null && h.anomaly_score >= 0.7)) {
        suggestions.push(`${name}: high anomaly score → consider reducing exposure / set an alert`);
      }
      const pred = h.predicted_return_5d ?? h.predicted_return ?? null;
      if (pred != null && Number(pred) < -2) {
        suggestions.push(`${name} predicted ${Number(pred).toFixed(1)}% in 5 days → consider a stop-loss`);
      }
    });

    // Concentration rule
    const invested = metrics.positionsValue || Math.max(metrics.totalValue - metrics.cashBalance, 1);
    metrics.holdingsData?.forEach(h => {
      const share = invested > 0 ? ((h.value || 0) / invested) : 0;
      if (share >= 0.3) {
        suggestions.push(`${h.name} represents ${(share * 100).toFixed(0)}% of invested assets → consider rebalancing`);
      }
    });

    // Deduplicate and limit
    return [...new Set(suggestions)].slice(0, 5);
  };

  const metrics = calculatePortfolioMetrics();

  const suggestions = generateOptimizationSuggestions();

  if (loading) {
    return (
      <div className="min-h-screen app-shell flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-cyan-400 mx-auto mb-4"></div>
          <p className="text-slate-400">Loading portfolio data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen app-shell flex items-center justify-center">
        <div className="text-center panel p-8">
          <AlertCircle className="h-12 w-12 text-rose-400 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-slate-100 mb-2">Error Loading Portfolio</h2>
          <p className="text-slate-400 mb-4">{error}</p>
          <button 
            onClick={fetchPortfolioData}
            className="btn-primary"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const COLORS = ['#22d3ee', '#34d399', '#fbbf24', '#f97316', '#38bdf8', '#fb7185'];

  return (
    <div className="min-h-screen app-shell">
      <div className="container mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-semibold text-slate-100">Portfolio Dashboard</h1>
          <p className="text-slate-400">Welcome back, {user?.username}</p>
        </div>

        {/* Portfolio Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6 mb-8">
          <div className="panel p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-slate-400">Total Value</p>
                <p className="text-2xl font-bold text-slate-100">
                  {metrics?.totalValue?.toFixed(2) || '0.00'} TND
                </p>
              </div>
              <DollarSign className="h-8 w-8 text-cyan-300" />
            </div>
          </div>

          <div className="panel p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-slate-400">Cash Balance</p>
                <p className="text-2xl font-bold text-slate-100">
                  {metrics?.cashBalance?.toFixed(2) || '0.00'} TND
                </p>
              </div>
              <Activity className="h-8 w-8 text-emerald-300" />
            </div>
          </div>

          <div className="panel p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-slate-400">Total P&L</p>
                <p className={`text-2xl font-bold ${metrics?.totalPnL >= 0 ? 'text-emerald-300' : 'text-rose-300'}`}>
                  {metrics?.totalPnL?.toFixed(2) || '0.00'} TND
                </p>
                <p className="text-xs text-slate-500">
                  Realized: {metrics?.realizedPnL?.toFixed(2) || '0.00'} TND | 
                  Unrealized: {metrics?.unrealizedPnL?.toFixed(2) || '0.00'} TND
                </p>
              </div>
              {metrics?.totalPnL >= 0 ? 
                <TrendingUp className="h-8 w-8 text-emerald-300" /> : 
                <TrendingDown className="h-8 w-8 text-rose-300" />
              }
            </div>
          </div>

          <div className="panel p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-slate-400">Portfolio ROI</p>
                <p className={`text-2xl font-bold ${metrics?.roiPercentage >= 0 ? 'text-emerald-300' : 'text-rose-300'}`}>
                  {metrics?.roiDisplay || '--'}
                </p>
                <p className="text-xs text-slate-500">
                  Invested: {metrics?.totalInvested?.toFixed(2) || '0.00'} TND
                </p>
              </div>
              {metrics?.roiPercentage >= 0 ? 
                <TrendingUp className="h-8 w-8 text-emerald-300" /> : 
                <TrendingDown className="h-8 w-8 text-rose-300" />
              }
            </div>
          </div>

          <div className="panel p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-slate-400">Total ROI</p>
                <p className={`text-2xl font-bold ${metrics?.userROI >= 0 ? 'text-emerald-300' : 'text-rose-300'}`}>
                  {metrics?.userROI?.toFixed(2) || '0.00'}%
                </p>
                <p className="text-xs text-slate-500">
                  All Portfolios: {metrics?.userTotalPnL?.toFixed(2) || '0.00'} TND
                </p>
              </div>
              <BarChart3 className="h-8 w-8 text-amber-300" />
            </div>
          </div>
        </div>

        {/* P&L Analytics Section */}
        <div className="panel p-6 mb-8">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold text-slate-100">P&L Analytics</h3>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="panel-muted p-4 bg-gradient-to-br from-emerald-500/15 via-slate-900/40 to-slate-900/20">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-300">Realized P&L</p>
                  <p className="text-xl font-bold text-emerald-300">
                    {metrics?.realizedPnL?.toFixed(2) || '0.00'} TND
                  </p>
                  <p className="text-xs text-slate-400">From completed trades</p>
                </div>
                <Plus className="h-6 w-6 text-emerald-300" />
              </div>
            </div>
            <div className="panel-muted p-4 bg-gradient-to-br from-cyan-500/15 via-slate-900/40 to-slate-900/20">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-300">Unrealized P&L</p>
                  <p className={`text-xl font-bold ${metrics?.unrealizedPnL >= 0 ? 'text-cyan-200' : 'text-rose-300'}`}>
                    {metrics?.unrealizedPnL?.toFixed(2) || '0.00'} TND
                  </p>
                  <p className="text-xs text-slate-400">Current holdings value</p>
                </div>
                <Activity className="h-6 w-6 text-cyan-200" />
              </div>
            </div>
            <div className="panel-muted p-4 bg-gradient-to-br from-amber-500/15 via-slate-900/40 to-slate-900/20">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-300">Total Investment</p>
                  <p className="text-xl font-bold text-amber-300">
                    {metrics?.totalInvested?.toFixed(2) || '0.00'} TND
                  </p>
                  <p className="text-xs text-slate-400">Net money in market</p>
                </div>
                <DollarSign className="h-6 w-6 text-amber-300" />
              </div>
            </div>
          </div>
        </div>

        {/* Tabs Navigation */}
        <div className="panel mb-6">
          <div className="border-b border-slate-800/70">
            <nav className="flex space-x-8 px-6">
              {[
                { id: 'overview', name: 'Overview', icon: Eye },
                { id: 'positions', name: 'Positions', icon: BarChart3 },
                { id: 'distribution', name: 'Distribution', icon: PieChartIcon },
                { id: 'performance', name: 'Performance', icon: TrendingUp }
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center py-4 px-1 border-b-2 font-medium text-sm ${
                    activeTab === tab.id
                      ? 'border-cyan-400 text-cyan-200'
                      : 'border-transparent text-slate-500 hover:text-slate-300 hover:border-slate-700'
                  }`}
                >
                  <tab.icon className="h-5 w-5 mr-2" />
                  {tab.name}
                </button>
              ))}
            </nav>
          </div>

          <div className="p-6">
            {activeTab === 'positions' && (
              <div>
                <h3 className="text-lg font-semibold mb-4">Current Positions</h3>
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-slate-800/70">
                    <thead className="table-head">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Symbol / Name</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Quantity</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Avg Buy Price</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Current Price</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Market Value</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Unrealized P&L</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Realized P&L</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">P&L %</th>
                      </tr>
                    </thead>
                    <tbody className="bg-slate-950/20 divide-y divide-slate-800/70">
                      {metrics?.holdingsData?.filter(h => h.name !== 'Cash').map((holding, index) => (
                        <tr key={index} className={`table-row hover:bg-slate-900/40 ${holding.isSoldOut ? 'opacity-60' : ''}`}>
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-slate-100">
                            {holding.name}
                            {holding.isSoldOut && <span className="ml-2 text-xs text-slate-500">(Sold)</span>}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500">
                            {Math.round(holding.shares || 0)}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500">
                            {holding.avgPrice?.toFixed(2)} TND
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500">
                            {holding.isSoldOut ? '--' : `${holding.currentPrice?.toFixed(2)} TND`}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500">
                            {holding.isSoldOut ? '--' : `${((holding.shares || 0) * (holding.currentPrice || holding.avgPrice || 0)).toFixed(2)} TND`}
                          </td>
                          <td className={`px-6 py-4 whitespace-nowrap text-sm font-medium ${
                            holding.isSoldOut ? 'text-slate-500' : (holding.pnl >= 0 ? 'text-emerald-300' : 'text-rose-300')
                          }`}>
                            {holding.isSoldOut ? '--' : `${holding.pnl?.toFixed(2)} TND`}
                          </td>
                          <td className={`px-6 py-4 whitespace-nowrap text-sm font-medium ${
                            holding.realized !== undefined && holding.realized !== 0
                              ? (holding.realized >= 0 ? 'text-emerald-300' : 'text-rose-300')
                              : 'text-slate-500'
                          }`}>
                            {holding.realized !== undefined && holding.realized !== 0 
                              ? `${holding.realized >= 0 ? '+' : ''}${holding.realized?.toFixed(2)} TND` 
                              : '--'}
                          </td>
                          <td className={`px-6 py-4 whitespace-nowrap text-sm font-medium ${
                            holding.isSoldOut ? 'text-slate-500' : (holding.pnlPercentage >= 0 ? 'text-emerald-300' : 'text-rose-300')
                          }`}>
                            {holding.isSoldOut ? '--' : `${holding.pnlPercentage?.toFixed(2)}%`}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {activeTab === 'distribution' && (
              <div>
                <h3 className="text-lg font-semibold mb-4">Portfolio Distribution</h3>
                <div className="h-96">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={(() => {
                          // Group holdings under 2% as "Others"
                          const holdings = metrics?.holdingsData || [];
                          const totalValue = holdings.reduce((sum, h) => sum + (h.value || 0), 0);
                          if (totalValue === 0) return holdings;
                          
                          const significant = [];
                          let othersValue = 0;
                          
                          holdings.forEach((h) => {
                            const percent = (h.value || 0) / totalValue;
                            if (percent >= 0.02) {
                              significant.push(h);
                            } else {
                              othersValue += (h.value || 0);
                            }
                          });
                          
                          if (othersValue > 0) {
                            significant.push({
                              name: 'Others',
                              value: othersValue,
                              shares: 0,
                              avgPrice: 0,
                              currentPrice: 0,
                              pnl: 0,
                              pnlPercentage: 0
                            });
                          }
                          
                          return significant;
                        })()}
                        cx="50%"
                        cy="50%"
                        labelLine={false}
                        label={({name, value, percent}) => `${name}: ${value?.toFixed(0)} TND (${(percent * 100).toFixed(1)}%)`}
                        outerRadius={120}
                        fill="#8884d8"
                        dataKey="value"
                      >
                        {(() => {
                          // Group holdings under 2% as "Others" for colors
                          const holdings = metrics?.holdingsData || [];
                          const totalValue = holdings.reduce((sum, h) => sum + (h.value || 0), 0);
                          if (totalValue === 0) return holdings.map((_, index) => (
                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                          ));
                          
                          const significant = [];
                          let hasOthers = false;
                          
                          holdings.forEach((h) => {
                            const percent = (h.value || 0) / totalValue;
                            if (percent >= 0.02) {
                              significant.push(h);
                            } else {
                              hasOthers = true;
                            }
                          });
                          
                          if (hasOthers) {
                            significant.push({ name: 'Others' });
                          }
                          
                          return significant.map((_, index) => (
                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                          ));
                        })()}
                      </Pie>
                      <Tooltip formatter={(value) => [`${value?.toFixed(2)} TND`, 'Value']} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}

            {activeTab === 'performance' && (
              <div>
                <h3 className="text-lg font-semibold mb-4">Performance</h3>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                  <div className="panel p-4">
                    <p className="text-sm text-slate-400">ROI</p>
                    <p className={`text-2xl font-bold ${portfolioPerformance?.roi >= 0 ? 'text-emerald-300' : 'text-rose-300'}`}>
                      {portfolioPerformance?.roi?.toFixed(2) || '0.00'}%
                    </p>
                  </div>

                  <div className="panel p-4">
                    <p className="text-sm text-slate-400">P&L (Realized / Unrealized)</p>
                    <p className="text-2xl font-bold text-slate-100">
                      {portfolioPerformance?.realized_pnl?.toFixed(2) || '0.00'} TND / {portfolioPerformance?.unrealized_pnl?.toFixed(2) || metrics?.unrealizedPnL?.toFixed(2) || '0.00'} TND
                    </p>
                  </div>

                  <div className="panel p-4">
                    <p className="text-sm text-slate-400">Max Drawdown</p>
                    <p className="text-2xl font-bold text-slate-100">{portfolioPerformance?.max_drawdown?.toFixed(2) || '0.00'}%</p>
                  </div>
                </div>

                <div className="panel p-6">
                  <h4 className="font-medium text-slate-100 mb-2">Capital Evolution (Évolution du capital)</h4>
                  {portfolioPerformance?.history?.length ? (
                    <div className="h-64">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={portfolioPerformance.history}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                          <XAxis dataKey="date" tickFormatter={(d)=>d} />
                          <YAxis domain={["auto","auto"]} tickFormatter={(v) => `${v} TND`} />
                          <Tooltip formatter={(value, name) => [`${Number(value).toFixed(2)} TND`, name]} />
                          <Line type="monotone" dataKey="value" stroke="#22d3ee" strokeWidth={2} dot={false} />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  ) : (
                    <div className="text-sm text-slate-500">No performance history available.</div>
                  )}
                </div>
              </div>
            )}

            {activeTab === 'overview' && (
              <div>
                <h3 className="text-lg font-semibold mb-4">Portfolio Overview</h3>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <div className="panel-muted p-4">
                    <h4 className="font-medium text-slate-100 mb-4">Top Holdings</h4>
                    <div className="space-y-3">
                      {metrics?.holdingsData?.filter(h => h.name !== 'Cash').slice(0, 5).map((holding, index) => (
                        <div key={index} className="flex justify-between items-center">
                          <span className="text-slate-100 font-medium">{holding.name}</span>
                          <div className="text-right">
                            <div className="text-slate-100">{holding.value?.toFixed(2)} TND</div>
                            <div className={`text-sm ${holding.pnl >= 0 ? 'text-emerald-300' : 'text-rose-300'}`}>
                              {holding.pnlPercentage?.toFixed(2)}%
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="panel-muted p-4">
                    <h4 className="font-medium text-slate-100 mb-4">Portfolio Allocation</h4>
                    <div className="space-y-3">
                      <div className="flex justify-between">
                        <span className="text-slate-400">Stocks:</span>
                        <span className="font-medium">
                          {metrics?.totalValue > 0 ? ((metrics?.positionsValue / metrics?.totalValue) * 100).toFixed(1) : 0}%
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Cash:</span>
                        <span className="font-medium">
                          {metrics?.totalValue > 0 ? ((metrics?.cashBalance / metrics?.totalValue) * 100).toFixed(1) : 100}%
                        </span>
                      </div>
                    </div>

                    {/* Optimization Suggestions */}
                    <div className="mt-4 panel p-4">
                      <div className="flex items-center justify-between mb-2">
                        <h5 className="font-medium text-slate-100">Suggestions d’optimisation</h5>
                        <AlertCircle className="h-5 w-5 text-amber-300" />
                      </div>
                      <div>
                        {suggestions && suggestions.length > 0 ? (
                          <ul className="list-disc ml-5 text-sm text-slate-300 space-y-2">
                            {suggestions.map((s, i) => (
                              <li key={i}>{s}</li>
                            ))}
                          </ul>
                        ) : (
                          <div className="text-sm text-slate-500">No suggestions at this time.</div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default EnhancedDashboard;