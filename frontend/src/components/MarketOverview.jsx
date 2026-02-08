import React, { useEffect, useState, useRef } from 'react';
import ApiService from '../services/api';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  AreaChart,
  Area,
} from 'recharts';
import { TrendingUp, TrendingDown, Activity, AlertTriangle, BarChart3, Clock, RefreshCw, ExternalLink, Newspaper } from 'lucide-react';

/**
 * MarketOverview Component
 * 
 * Displays overall market data including TUNINDEX, sentiment, top movers, and alerts.
 * 
 * DATA SOURCES (via API endpoints → Backend CRUD → CSV files):
 * ──────────────────────────────────────────────────────────────
 * 1. TUNINDEX Chart:
 *    - API: GET /market-overview/tunindex?days=60&index_type=tunindex|tunindex20
 *    - Source: data/historical_data.csv (columns: TUNINDEX_INDICE_JOUR, TUNINDEX20_INDICE_JOUR)
 * 
 * 2. Market Sentiment Gauge:
 *    - API: GET /market-overview/sentiment
 *    - Source: data/historical_data.csv (columns: MarketMood, DirectionScore, IntensityScore, etc.)
 * 
 * 3. Top Gainers & Losers:
 *    - API: GET /market-overview/movers
 *    - Source: data/historical_data.csv (columns: VALEUR, CLOTURE, VARIATION)
 * 
 * 4. Market Alerts:
 *    - API: GET /market-overview/alerts
 *    - Source: data/historical_data.csv (columns: VOLUME_Anomaly, VARIATION_ANOMALY)
 */

// Animated Semi-Circle Gauge Component
const SentimentGauge = ({ value = 50, maxValue = 100 }) => {
  const [animatedValue, setAnimatedValue] = useState(0);

  useEffect(() => {
    // Animate the value
    const duration = 1500;
    const startTime = Date.now();
    const startValue = 0;

    const animate = () => {
      const elapsed = Date.now() - startTime;
      const progress = Math.min(elapsed / duration, 1);
      
      // Easing function (ease out cubic)
      const easeOut = 1 - Math.pow(1 - progress, 3);
      const currentValue = startValue + (value - startValue) * easeOut;
      
      setAnimatedValue(currentValue);

      if (progress < 1) {
        requestAnimationFrame(animate);
      }
    };

    requestAnimationFrame(animate);
  }, [value]);

  const percentage = (animatedValue / maxValue) * 100;
  const rotation = (percentage / 100) * 180; // 180 degrees for semi-circle

  const getSentimentColor = (val) => {
    if (val >= 70) return '#10b981'; // Green
    if (val >= 40) return '#f59e0b'; // Yellow/Amber
    return '#ef4444'; // Red
  };

  const getSentimentLabel = (val) => {
    if (val >= 70) return 'Bullish';
    if (val >= 40) return 'Neutral';
    return 'Bearish';
  };

  const color = getSentimentColor(animatedValue);

  return (
    <div className="flex flex-col items-center">
      <div className="relative w-64 h-32 overflow-hidden">
        {/* Background arc */}
        <svg viewBox="0 0 200 100" className="w-full h-full">
          {/* Background semi-circle */}
          <path
            d="M 10 100 A 90 90 0 0 1 190 100"
            fill="none"
            stroke="#1e293b"
            strokeWidth="16"
            strokeLinecap="round"
          />
          {/* Animated progress arc */}
          <path
            d="M 10 100 A 90 90 0 0 1 190 100"
            fill="none"
            stroke={color}
            strokeWidth="16"
            strokeLinecap="round"
            strokeDasharray={`${(rotation / 180) * 283} 283`}
            style={{
              filter: `drop-shadow(0 0 8px ${color}40)`,
              transition: 'stroke 0.3s ease',
            }}
          />
          {/* Center point */}
          <circle cx="100" cy="100" r="8" fill={color} />
          {/* Needle */}
          <line
            x1="100"
            y1="100"
            x2={100 + 70 * Math.cos((Math.PI * (180 - rotation)) / 180)}
            y2={100 - 70 * Math.sin((Math.PI * (180 - rotation)) / 180)}
            stroke={color}
            strokeWidth="3"
            strokeLinecap="round"
            style={{
              filter: `drop-shadow(0 0 4px ${color}60)`,
            }}
          />
        </svg>
      </div>
      
      <div className="text-center mt-2">
        <div className="text-4xl font-bold text-slate-100" style={{ color }}>
          {Math.round(animatedValue)}
          <span className="text-lg text-slate-400">/{maxValue}</span>
        </div>
        <div className="text-lg font-medium mt-1" style={{ color }}>
          {getSentimentLabel(animatedValue)}
        </div>
        <div className="text-sm text-slate-500 mt-1">Market Sentiment Score</div>
      </div>
    </div>
  );
};

// Stock Card Component
const StockCard = ({ symbol, name, price, change, changePercent, isGainer }) => {
  const isPositive = change >= 0;
  
  return (
    <div className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg hover:bg-slate-800 transition-colors">
      <div>
        <div className="font-medium text-slate-100">{symbol}</div>
        <div className="text-sm text-slate-400 truncate max-w-32">{name}</div>
      </div>
      <div className="text-right">
        <div className="font-medium text-slate-100">{price?.toFixed(2)} TND</div>
        <div className={`text-sm flex items-center justify-end gap-1 ${isPositive ? 'text-emerald-400' : 'text-rose-400'}`}>
          {isPositive ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
          {isPositive ? '+' : ''}{changePercent?.toFixed(2)}%
        </div>
      </div>
    </div>
  );
};

// Alert Card Component
const AlertCard = ({ alert }) => {
  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'high': return 'border-rose-500/50 bg-rose-500/10';
      case 'medium': return 'border-amber-500/50 bg-amber-500/10';
      default: return 'border-blue-500/50 bg-blue-500/10';
    }
  };

  const getSeverityIcon = (severity) => {
    switch (severity) {
      case 'high': return <AlertTriangle className="w-4 h-4 text-rose-400" />;
      case 'medium': return <AlertTriangle className="w-4 h-4 text-amber-400" />;
      default: return <Activity className="w-4 h-4 text-blue-400" />;
    }
  };

  return (
    <div className={`p-3 rounded-lg border ${getSeverityColor(alert.severity)}`}>
      <div className="flex items-start gap-2">
        {getSeverityIcon(alert.severity)}
        <div className="flex-1">
          <div className="flex items-center justify-between">
            <span className="font-medium text-slate-100">{alert.symbol}</span>
            <span className="text-xs text-slate-500">{alert.time}</span>
          </div>
          <p className="text-sm text-slate-300 mt-1">{alert.message}</p>
        </div>
      </div>
    </div>
  );
};

const MarketOverview = () => {
  // State for data from API
  const [tunindexData, setTunindexData] = useState([]);
  const [tunindexCurrent, setTunindexCurrent] = useState({
    value: 0,
    change: 0,
    changePercent: 0,
  });
  const [lastDataDate, setLastDataDate] = useState(null);
  const [topGainers, setTopGainers] = useState([]);
  const [topLosers, setTopLosers] = useState([]);
  const [marketSentiment, setMarketSentiment] = useState(50);
  const [sentimentScores, setSentimentScores] = useState({
    direction: 0,
    breadth: 0,
    liquidity: 0,
    intensity: 0,
    news: 0,
  });
  const [recentAlerts, setRecentAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // TUNINDEX/TUNINDEX20 toggle state
  const [selectedIndex, setSelectedIndex] = useState('tunindex'); // 'tunindex' or 'tunindex20'

  // Fetch all market overview data
  const fetchMarketData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Fetch all data in parallel
      const [tunindexResp, sentimentResp, moversResp, alertsResp] = await Promise.all([
        ApiService.getTunindexData(60, selectedIndex),
        ApiService.getMarketSentiment(),
        ApiService.getTopMovers(),
        ApiService.getMarketAlerts(10),
      ]);

      // Process TUNINDEX data
      if (tunindexResp && tunindexResp.history) {
        setTunindexData(tunindexResp.history);
        if (tunindexResp.current) {
          setTunindexCurrent(tunindexResp.current);
        }
        if (tunindexResp.lastDate) {
          setLastDataDate(tunindexResp.lastDate);
        }
      }

      // Process sentiment data
      if (sentimentResp && typeof sentimentResp.mood === 'number') {
        setMarketSentiment(sentimentResp.mood);
        // Store the subscores
        if (sentimentResp.scores) {
          setSentimentScores({
            direction: sentimentResp.scores.direction || 0,
            breadth: sentimentResp.scores.breadth || 0,
            liquidity: sentimentResp.scores.liquidity || 0,
            intensity: sentimentResp.scores.intensity || 0,
            news: sentimentResp.scores.news || 0,
          });
        }
      }

      // Process top movers
      if (moversResp) {
        if (moversResp.gainers && Array.isArray(moversResp.gainers)) {
          setTopGainers(moversResp.gainers.map(g => ({
            symbol: g.symbol,
            name: g.name,
            price: g.price,
            change: g.change,
            changePercent: g.changePercent,
          })));
        }
        if (moversResp.losers && Array.isArray(moversResp.losers)) {
          setTopLosers(moversResp.losers.map(l => ({
            symbol: l.symbol,
            name: l.name,
            price: l.price,
            change: l.change,
            changePercent: l.changePercent,
          })));
        }
      }

      // Process alerts
      if (alertsResp && Array.isArray(alertsResp)) {
        setRecentAlerts(alertsResp.map(a => ({
          id: a.id,
          symbol: a.symbol,
          message: a.message,
          severity: a.severity,
          time: a.date,
          type: a.type,
        })));
      }

    } catch (err) {
      console.error('Error fetching market data:', err);
      setError('Failed to load market data. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // Fetch index data when selectedIndex changes
  const fetchIndexData = async () => {
    try {
      const tunindexResp = await ApiService.getTunindexData(60, selectedIndex);
      if (tunindexResp && tunindexResp.history) {
        setTunindexData(tunindexResp.history);
        if (tunindexResp.current) {
          setTunindexCurrent(tunindexResp.current);
        }
        if (tunindexResp.lastDate) {
          setLastDataDate(tunindexResp.lastDate);
        }
      }
    } catch (err) {
      console.error('Error fetching index data:', err);
    }
  };

  useEffect(() => {
    fetchMarketData();
  }, []);

  useEffect(() => {
    if (!loading) {
      fetchIndexData();
    }
  }, [selectedIndex]);

  const isPositive = tunindexCurrent.change >= 0;

  if (loading) {
    return (
      <div className="min-h-screen app-shell py-6 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-cyan-400 mx-auto mb-4"></div>
          <p className="text-slate-400">Loading market data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen app-shell py-6">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-100">Market Overview</h1>
            <p className="text-slate-400 mt-1">
              Tunisian Stock Exchange at a glance
              {lastDataDate && <span className="text-slate-500"> • Data as of {lastDataDate}</span>}
            </p>
          </div>
          <button
            onClick={fetchMarketData}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-rose-500/10 border border-rose-500/50 rounded-lg text-rose-400">
            {error}
          </div>
        )}

        {/* Main Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* TUNINDEX Chart - Takes 2 columns */}
          <div className="lg:col-span-2 panel p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <BarChart3 className="w-6 h-6 text-cyan-400" />
                <div>
                  {/* Index Toggle Buttons */}
                  <div className="flex items-center gap-2 mb-1">
                    <button
                      onClick={() => setSelectedIndex('tunindex')}
                      className={`px-3 py-1 rounded-lg text-sm font-medium transition-all ${
                        selectedIndex === 'tunindex'
                          ? 'bg-cyan-500 text-slate-900 shadow-lg shadow-cyan-500/25'
                          : 'bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-slate-200'
                      }`}
                    >
                      TUNINDEX
                    </button>
                    <button
                      onClick={() => setSelectedIndex('tunindex20')}
                      className={`px-3 py-1 rounded-lg text-sm font-medium transition-all ${
                        selectedIndex === 'tunindex20'
                          ? 'bg-cyan-500 text-slate-900 shadow-lg shadow-cyan-500/25'
                          : 'bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-slate-200'
                      }`}
                    >
                      TUNINDEX20
                    </button>
                  </div>
                  <p className="text-sm text-slate-500">
                    {selectedIndex === 'tunindex' ? 'Tunisian Stock Market Index' : 'Top 20 Companies Index'}
                  </p>
                </div>
              </div>
              <div className="text-right">
                <div className="text-3xl font-bold text-slate-100">
                  {tunindexCurrent.value?.toLocaleString()}
                </div>
                <div className={`flex items-center justify-end gap-1 text-lg ${isPositive ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {isPositive ? <TrendingUp className="w-5 h-5" /> : <TrendingDown className="w-5 h-5" />}
                  <span>{isPositive ? '+' : ''}{tunindexCurrent.change?.toFixed(2)}</span>
                  <span className="text-sm">({isPositive ? '+' : ''}{tunindexCurrent.changePercent?.toFixed(2)}%)</span>
                </div>
              </div>
            </div>

            <div style={{ height: 280 }}>
              <ResponsiveContainer>
                <AreaChart data={tunindexData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorTunindex" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={isPositive ? '#10b981' : '#ef4444'} stopOpacity={0.3}/>
                      <stop offset="95%" stopColor={isPositive ? '#10b981' : '#ef4444'} stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis 
                    dataKey="date" 
                    tick={{ fill: '#64748b', fontSize: 11 }} 
                    tickLine={{ stroke: '#334155' }}
                    tickFormatter={(d) => new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                  />
                  <YAxis 
                    domain={['auto', 'auto']} 
                    tick={{ fill: '#64748b', fontSize: 11 }} 
                    tickLine={{ stroke: '#334155' }}
                    tickFormatter={(v) => v.toLocaleString()}
                  />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #334155', borderRadius: '8px' }}
                    labelStyle={{ color: '#e2e8f0' }}
                    formatter={(value) => [value?.toLocaleString(), 'TUNINDEX']}
                  />
                  <Area 
                    type="monotone" 
                    dataKey="value" 
                    stroke={isPositive ? '#10b981' : '#ef4444'} 
                    fillOpacity={1} 
                    fill="url(#colorTunindex)" 
                    strokeWidth={2} 
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            {/* Market Statistics - Below TUNINDEX Chart */}
            <div className="mt-6 pt-6 border-t border-slate-800/70">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-slate-800/40 rounded-lg p-3 text-center">
                  <div className="text-xs text-slate-400 uppercase mb-1">Trading Day</div>
                  <div className="text-sm font-medium text-slate-100">
                    {tunindexData[tunindexData.length - 1]?.date 
                      ? new Date(tunindexData[tunindexData.length - 1].date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
                      : '--'}
                  </div>
                </div>
                <div className="bg-slate-800/40 rounded-lg p-3 text-center">
                  <div className="text-xs text-slate-400 uppercase mb-1">Period High</div>
                  <div className="text-sm font-medium text-emerald-400">
                    {tunindexData.length > 0 
                      ? Math.max(...tunindexData.map(d => d.value || 0)).toLocaleString()
                      : '--'}
                  </div>
                </div>
                <div className="bg-slate-800/40 rounded-lg p-3 text-center">
                  <div className="text-xs text-slate-400 uppercase mb-1">Period Low</div>
                  <div className="text-sm font-medium text-rose-400">
                    {tunindexData.length > 0 
                      ? Math.min(...tunindexData.filter(d => d.value > 0).map(d => d.value)).toLocaleString()
                      : '--'}
                  </div>
                </div>
                <div className="bg-slate-800/40 rounded-lg p-3 text-center">
                  <div className="text-xs text-slate-400 uppercase mb-1">Active Stocks</div>
                  <div className="text-sm font-medium text-cyan-400">
                    {topGainers.length + topLosers.length > 0 ? `${topGainers.length + topLosers.length}+` : '--'}
                  </div>
                </div>
              </div>

              {/* Useful Links Section */}
              <div className="mt-4 pt-4 border-t border-slate-800/50">
                <div className="flex flex-wrap items-center justify-center gap-3">
                  <a
                    href="https://www.bvmt.com.tn/fr"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 px-4 py-2 bg-slate-800/60 hover:bg-slate-700/60 text-slate-300 hover:text-cyan-400 rounded-lg transition-colors text-sm"
                  >
                    <BarChart3 className="w-4 h-4" />
                    BVMT TUNINDEX
                    <ExternalLink className="w-3 h-3" />
                  </a>
                  <a
                    href="https://www.bvmt.com.tn/fr/entreprises/list"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 px-4 py-2 bg-slate-800/60 hover:bg-slate-700/60 text-slate-300 hover:text-cyan-400 rounded-lg transition-colors text-sm"
                  >
                    <TrendingUp className="w-4 h-4" />
                    Listed Companies
                    <ExternalLink className="w-3 h-3" />
                  </a>
                  <a
                    href="http://www.bvmt.com.tn/fr/actualites"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 px-4 py-2 bg-slate-800/60 hover:bg-slate-700/60 text-slate-300 hover:text-cyan-400 rounded-lg transition-colors text-sm"
                  >
                    <Newspaper className="w-4 h-4" />
                    BVMT News
                    <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
              </div>
            </div>
          </div>

          {/* Market Sentiment Gauge */}
          <div className="panel p-6">
            <div className="flex items-center gap-2 mb-6">
              <Activity className="w-5 h-5 text-emerald-400" />
              <h3 className="text-lg font-semibold text-slate-100">Market Sentiment</h3>
            </div>
            
            <SentimentGauge value={marketSentiment} maxValue={100} />
            
            {/* Sentiment Subscores */}
            <div className="mt-6 space-y-3">
              <div className="text-xs text-slate-400 uppercase tracking-wide mb-2">Sentiment Components</div>
              
              {/* Direction & Breadth Score */}
              <div className="flex items-center justify-between p-2 bg-slate-800/50 rounded-lg">
                <span className="text-sm text-slate-300">Direction & Breadth</span>
                <span className="text-sm font-medium text-cyan-400">{sentimentScores.direction?.toFixed(1) || '0.0'}</span>
              </div>
              
              {/* Breadth Score */}
              <div className="flex items-center justify-between p-2 bg-slate-800/50 rounded-lg">
                <span className="text-sm text-slate-300">Breadth Score</span>
                <span className="text-sm font-medium text-cyan-400">{sentimentScores.breadth?.toFixed(1) || '0.0'}</span>
              </div>
              
              {/* Liquidity Score */}
              <div className="flex items-center justify-between p-2 bg-slate-800/50 rounded-lg">
                <span className="text-sm text-slate-300">Liquidity Score</span>
                <span className="text-sm font-medium text-blue-400">{sentimentScores.liquidity?.toFixed(1) || '0.0'}</span>
              </div>
              
              {/* Intensity Score */}
              <div className="flex items-center justify-between p-2 bg-slate-800/50 rounded-lg">
                <span className="text-sm text-slate-300">Intensity Score</span>
                <span className="text-sm font-medium text-purple-400">{sentimentScores.intensity?.toFixed(1) || '0.0'}</span>
              </div>
              
              {/* News Score */}
              <div className="flex items-center justify-between p-2 bg-slate-800/50 rounded-lg">
                <span className="text-sm text-slate-300">News Score</span>
                <span className="text-sm font-medium text-amber-400">{sentimentScores.news?.toFixed(1) || '0.0'}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Second Row - Top Movers & Alerts */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-6">
          {/* Top Gainers */}
          <div className="panel p-6 flex flex-col">
            <div className="flex items-center gap-2 mb-4">
              <TrendingUp className="w-5 h-5 text-emerald-400" />
              <h3 className="text-lg font-semibold text-slate-100">Top 5 Gainers</h3>
            </div>
            <div className="space-y-2 flex-1">
              {topGainers.length > 0 ? (
                topGainers.map((stock, idx) => (
                  <StockCard key={stock.symbol || idx} {...stock} isGainer={true} />
                ))
              ) : (
                <div className="text-center text-slate-500 py-4">No gainers data available</div>
              )}
            </div>
          </div>

          {/* Top Losers */}
          <div className="panel p-6 flex flex-col">
            <div className="flex items-center gap-2 mb-4">
              <TrendingDown className="w-5 h-5 text-rose-400" />
              <h3 className="text-lg font-semibold text-slate-100">Top 5 Losers</h3>
            </div>
            <div className="space-y-2 flex-1">
              {topLosers.length > 0 ? (
                topLosers.map((stock, idx) => (
                  <StockCard key={stock.symbol || idx} {...stock} isGainer={false} />
                ))
              ) : (
                <div className="text-center text-slate-500 py-4">No losers data available</div>
              )}
            </div>
          </div>

          {/* Recent Alerts */}
          <div className="panel p-6 flex flex-col">
            <div className="flex items-center gap-2 mb-4">
              <AlertTriangle className="w-5 h-5 text-amber-400" />
              <h3 className="text-lg font-semibold text-slate-100">Recent Alerts</h3>
              <span className="ml-auto text-xs text-slate-500 flex items-center gap-1">
                <Clock className="w-3 h-3" />
                From Data
              </span>
            </div>
            <div className="space-y-2 flex-1 max-h-80 overflow-y-auto">
              {recentAlerts.length > 0 ? (
                recentAlerts.map((alert) => (
                  <AlertCard key={alert.id} alert={alert} />
                ))
              ) : (
                <div className="text-center text-slate-500 py-4">No alerts detected</div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MarketOverview;