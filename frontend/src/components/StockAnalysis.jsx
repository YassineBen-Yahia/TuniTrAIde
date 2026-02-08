import React, { useEffect, useState, useRef } from 'react';
import {  Sparkles } from "lucide-react";

import ApiService from '../services/api';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Legend,
  AreaChart,
  Area,
  ComposedChart,
  Bar,
  ReferenceDot,
  Scatter,
  ScatterChart,
  Cell,
} from 'recharts';
import { TrendingUp, TrendingDown, Minus, ChevronDown, Search, Calendar, BarChart2, Activity, Brain, Eye, EyeOff, Filter, AlertTriangle } from 'lucide-react';

/**
 * StockAnalysis Component
 * 
 * Detailed analysis view for individual stocks including price charts, 
 * volume, anomalies, forecasts, and sentiment.
 * 
 * DATA SOURCES (via API endpoints → Backend CRUD → CSV files):
 * ──────────────────────────────────────────────────────────────
 * 1. Stock List (Dropdown):
 *    - API: GET /stocks/all
 *    - Source: data/historical_data.csv (unique CODE, VALEUR pairs)
 * 
 * 2. Price & Volume Chart (Historical + Forecast):
 *    - API: GET /market-data/{symbol}/history-forecast
 *    - Historical: data/historical_data.csv (OHLCV, VARIATION, anomaly flags)
 *    - Forecast: data/forecast_next_5_days.csv (5-day predictions)
 * 
 * 3. Anomaly Markers (3 types for Price & Volume):
 *    - Source: data/historical_data.csv
 *    - Price anomalies: VARIATION_ANOMALY, VARIATION_ANOMALY_POST_NEWS, VARIATION_ANOMALY_PRE_NEWS
 *    - Volume anomalies: VOLUME_Anomaly, VOLUME_ANOMALY_POST_NEWS, VOLUME_ANOMALY_PRE_NEWS
 *    - Legend: ▲ Green = News Reaction | ▼ Red = Possible Leakage | ● Yellow = Unexplained
 * 
 * 4. Sentiment Analysis Chart:
 *    - API: GET /sentiment/{symbol}
 *    - Source: data/sentiment_features.csv (Mean_Weighted_Sentiment, Article_Count, Sentiment_Intensity)
 * 
 * 5. 5-Day Forecast Cards:
 *    - API: GET /market-data/{symbol}/history-forecast (forecast array)
 *    - Source: data/forecast_next_5_days.csv (CLOTURE, VOLUME, VAR_CLOTURE, PROB_LIQUIDITY)
 */

const timePresets = [
  { id: '1d', label: '1D', days: 1 },
  { id: '1w', label: '1W', days: 7 },
  { id: '1m', label: '1M', days: 30 },
  { id: '3m', label: '3M', days: 90 },
  { id: '6m', label: '6M', days: 180 },
  { id: '1y', label: '1Y', days: 365 },
  { id: 'ytd', label: 'YTD', days: null },
  { id: 'all', label: 'ALL', days: null },
  { id: 'custom', label: 'Custom', days: null },
];

// RSI calculation helper
const calculateRSI = (data, period = 14) => {
  if (!data || data.length < period + 1) return data?.map(() => null) || [];
  
  const rsiValues = [];
  let gains = 0;
  let losses = 0;

  for (let i = 1; i <= period; i++) {
    const change = data[i].price - data[i - 1].price;
    if (change > 0) gains += change;
    else losses -= change;
  }

  let avgGain = gains / period;
  let avgLoss = losses / period;

  for (let i = 0; i < data.length; i++) {
    if (i < period) {
      rsiValues.push(null);
    } else if (i === period) {
      const rs = avgLoss === 0 ? 100 : avgGain / avgLoss;
      rsiValues.push(100 - (100 / (1 + rs)));
    } else {
      const change = data[i].price - data[i - 1].price;
      const currentGain = change > 0 ? change : 0;
      const currentLoss = change < 0 ? -change : 0;
      
      avgGain = (avgGain * (period - 1) + currentGain) / period;
      avgLoss = (avgLoss * (period - 1) + currentLoss) / period;
      
      const rs = avgLoss === 0 ? 100 : avgGain / avgLoss;
      rsiValues.push(100 - (100 / (1 + rs)));
    }
  }
  
  return rsiValues;
};

// EMA calculation helper
const calculateEMA = (data, period) => {
  if (!data || data.length === 0) return [];
  const k = 2 / (period + 1);
  const emaValues = [data[0].price];
  
  for (let i = 1; i < data.length; i++) {
    emaValues.push(data[i].price * k + emaValues[i - 1] * (1 - k));
  }
  
  return emaValues;
};

// MACD calculation helper
const calculateMACD = (data, fastPeriod = 12, slowPeriod = 26, signalPeriod = 9) => {
  if (!data || data.length < slowPeriod) return { macd: [], signal: [], histogram: [] };
  
  const fastEMA = calculateEMA(data, fastPeriod);
  const slowEMA = calculateEMA(data, slowPeriod);
  
  const macdLine = fastEMA.map((fast, i) => fast - slowEMA[i]);
  
  // Calculate signal line (EMA of MACD)
  const signalData = macdLine.map((v, i) => ({ price: v }));
  const signalLine = calculateEMA(signalData, signalPeriod);
  
  const histogram = macdLine.map((m, i) => m - signalLine[i]);
  
  return { macd: macdLine, signal: signalLine, histogram };
};

const StockAnalysis = () => {
  const [symbols, setSymbols] = useState([]);
  const [symbolQuery, setSymbolQuery] = useState('');
  const [selectedSymbol, setSelectedSymbol] = useState(null);
  const [selectedCompanyName, setSelectedCompanyName] = useState('');
  const [period, setPeriod] = useState('1m');
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState([]);
  const [error, setError] = useState(null);
  const [showDropdown, setShowDropdown] = useState(false);
  const [suggestions, setSuggestions] = useState([]);
  const [activeSuggestion, setActiveSuggestion] = useState(-1);
  
  // Technical indicators state
  const [showRSI, setShowRSI] = useState(true);
  const [showMACD, setShowMACD] = useState(true);
  const [technicalData, setTechnicalData] = useState({ rsi: [], macd: [], signal: [], histogram: [] });
  
  // Market Analysis state - rule-based analysis of last 5 days + next 5 days forecast
  const [marketAnalysis, setMarketAnalysis] = useState(null);

  // Sentiment data from API
  const [sentimentData, setSentimentData] = useState([]);
  
  // Stock name for sentiment lookup (from API response)
  const [stockNameForSentiment, setStockNameForSentiment] = useState(null);
  
  // Track last historical date for forecast visualization
  const [lastHistoricalDate, setLastHistoricalDate] = useState(null);
  
  // Track last historical price and variation
  const [lastHistoricalPrice, setLastHistoricalPrice] = useState(null);
  const [lastHistoricalVariation, setLastHistoricalVariation] = useState(null);
  
  // Forecast data for prediction cards
  const [forecastData, setForecastData] = useState([]);
  
  // Anomaly display state
  const [showPriceAnomalies, setShowPriceAnomalies] = useState(false);
  const [showVolumeAnomalies, setShowVolumeAnomalies] = useState(false);
  const [priceAnomalyFilter, setPriceAnomalyFilter] = useState('all'); // 'all', 'news', 'leakage', 'unexplained'
  const [volumeAnomalyFilter, setVolumeAnomalyFilter] = useState('all'); // 'all', 'reaction', 'anticipation', 'unexplained'

  // Custom date range state
  const [customStartDate, setCustomStartDate] = useState('');
  const [customEndDate, setCustomEndDate] = useState('');
  const [customDateError, setCustomDateError] = useState('');

  const searchTimeoutRef = useRef(null);
  const dropdownRef = useRef(null);

  useEffect(() => {
    fetchSymbols();
    
    // Close dropdown when clicking outside
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      if (searchTimeoutRef.current) clearTimeout(searchTimeoutRef.current);
    };
  }, []);

  // Calculate technical indicators when data changes
  useEffect(() => {
    if (data && data.length > 0) {
      const rsiValues = calculateRSI(data);
      const { macd, signal, histogram } = calculateMACD(data);
      setTechnicalData({ rsi: rsiValues, macd, signal, histogram });
    }
  }, [data]);

  // Debounced search
  useEffect(() => {
    if (!symbolQuery || symbolQuery.trim() === '') {
      setSuggestions([]);
      return;
    }

    if (searchTimeoutRef.current) clearTimeout(searchTimeoutRef.current);
    searchTimeoutRef.current = setTimeout(async () => {
      try {
        const resp = await ApiService.searchStocks(symbolQuery, 20);
        let arr = [];
        if (Array.isArray(resp)) arr = resp;
        else if (resp && Array.isArray(resp.data)) arr = resp.data;
        else if (resp && Array.isArray(resp.results)) arr = resp.results;
        setSuggestions(arr);
        setActiveSuggestion(-1);
      } catch (err) {
        console.error('searchStocks failed', err);
        setSuggestions([]);
      }
    }, 300);
  }, [symbolQuery]);

  const fetchSymbols = async () => {
    try {
      const resp = await ApiService.getAllStocks(200);
      let arr = [];
      if (Array.isArray(resp)) arr = resp;
      else if (resp && Array.isArray(resp.stocks)) arr = resp.stocks;
      else if (resp && Array.isArray(resp.data)) arr = resp.data;
      else if (resp && Array.isArray(resp.results)) arr = resp.results;
      else if (resp && typeof resp === 'object') {
        arr = Object.keys(resp).map((k) => {
          const val = resp[k];
          if (typeof val === 'string') return { symbol: k, name: val };
          if (val && typeof val === 'object') return { symbol: k, name: val.name || '' };
          return { symbol: k, name: '' };
        });
      }
      setSymbols(arr || []);
    } catch (err) {
      console.error('Failed to fetch symbols', err);
      setSymbols([]);
    }
  };

  const getDateRange = () => {
    const preset = timePresets.find((p) => p.id === period);
    const end = new Date();
    let start = new Date();

    if (period === 'custom' && customStartDate && customEndDate) {
      return { start: customStartDate, end: customEndDate };
    } else if (period === 'ytd') {
      start = new Date(end.getFullYear(), 0, 1);
    } else if (period === 'all') {
      start.setFullYear(start.getFullYear() - 10);
    } else {
      start.setDate(end.getDate() - (preset?.days || 30));
    }

    const format = (d) => d.toISOString().slice(0, 10);
    return { start: format(start), end: format(end) };
  };

  const fetchMarketHistory = async (symbolArg) => {
    const symbol = (symbolArg || selectedSymbol || '').toString();
    if (!symbol) return;

    // Validate custom date range
    if (period === 'custom') {
      if (!customStartDate && !customEndDate) {
        setCustomDateError('Please select both start and end dates');
        return;
      }
      if (!customStartDate) {
        setCustomDateError('Please select a start date');
        return;
      }
      if (!customEndDate) {
        setCustomDateError('Please select an end date');
        return;
      }
      // Clear error if both dates are valid
      setCustomDateError('');
    }

    setLoading(true);
    setError(null);

    // Fetch full range first; we'll anchor client-side to last historical date
    const start = null;
    const end = null;

    try {
      // Use the new API endpoint that includes forecast data
      const resp = await ApiService.getMarketDataWithForecast(symbol, start, end);

      if (resp && resp.combined && resp.combined.length > 0) {
        // Use combined data (history + forecast)
        let chartData = resp.combined.map((row) => ({
          date: row?.date || '',
          price: row?.price != null ? Number(row.price) : Number(row?.close ?? 0),
          close: Number(row?.close ?? row?.price ?? 0),
          open: Number(row?.open ?? 0),
          high: Number(row?.high ?? 0),
          low: Number(row?.low ?? 0),
          volume: Number(row?.volume ?? 0),
          variation: Number(row?.variation ?? 0),
          isPrediction: Boolean(row?.isPrediction),
          // Price/Variation Anomaly data - 3 types
          variationAnomaly: Boolean(row?.variationAnomaly),
          variationAnomalyPostNews: Boolean(row?.variationAnomalyPostNews),
          variationAnomalyPreNews: Boolean(row?.variationAnomalyPreNews),
          // Volume Anomaly data - 3 types
          volumeAnomaly: Boolean(row?.volumeAnomaly),
          volumeAnomalyPostNews: Boolean(row?.volumeAnomalyPostNews),
          volumeAnomalyPreNews: Boolean(row?.volumeAnomalyPreNews),
          // Z-scores
          volumeZScore: Number(row?.volumeZScore ?? 0),
          variationZScore: Number(row?.variationZScore ?? 0),
          newsScore: Number(row?.newsScore ?? 0),
          articleCount: Number(row?.articleCount ?? 0),
          probLiquidity: Number(row?.probLiquidity ?? 0),
        }));

        // Anchor date range to the last historical date
        const baseEndStr = resp.lastHistoricalDate
          || (chartData.filter(d => !d.isPrediction).slice(-1)[0]?.date)
          || (chartData.slice(-1)[0]?.date);
        const baseEnd = baseEndStr ? new Date(baseEndStr) : new Date();

        // Compute anchored start/end based on selected period
        let anchoredStart = new Date(baseEnd);
        let anchoredEnd = new Date(baseEnd);
        // Determine if we should show forecast:
        // - Hide forecast when custom date range is selected (both start AND end dates)
        // - Show forecast for all other periods
        const isCustomRange = period === 'custom' && customStartDate && customEndDate;
        const showForecast = !isCustomRange;
        
        if (isCustomRange) {
          anchoredStart = new Date(customStartDate);
          anchoredEnd = new Date(customEndDate);
        } else if (period === 'ytd') {
          anchoredStart = new Date(baseEnd.getFullYear(), 0, 1);
        } else if (period === 'all') {
          anchoredStart.setFullYear(anchoredStart.getFullYear() - 10);
        } else {
          const preset = timePresets.find((p) => p.id === period);
          anchoredStart.setDate(anchoredStart.getDate() - (preset?.days || 30));
        }

        // Get the last historical point before filtering
        const lastHistoricalPoint = chartData.filter(d => !d.isPrediction).slice(-1)[0];
        
        // Filter data based on date range
        chartData = chartData.filter(d => {
          // Only include predictions when showForecast is true
          if (d.isPrediction) return showForecast;
          const dt = d.date ? new Date(d.date) : null;
          return dt && dt >= anchoredStart && dt <= anchoredEnd;
        });
        
        // If showing forecast, ensure first forecast point connects to last historical point
        // by inserting the last historical point's price as a bridge point if there's a gap
        if (showForecast && lastHistoricalPoint) {
          const forecastPoints = chartData.filter(d => d.isPrediction);
          const historicalPoints = chartData.filter(d => !d.isPrediction);
          const lastHistInFiltered = historicalPoints.slice(-1)[0];
          const firstForecast = forecastPoints[0];
          
          // Check if there's a date gap between last historical and first forecast
          if (firstForecast && lastHistInFiltered) {
            const lastHistDate = new Date(lastHistInFiltered.date);
            const firstForecastDate = new Date(firstForecast.date);
            const daysDiff = Math.floor((firstForecastDate - lastHistDate) / (1000 * 60 * 60 * 24));
            
            // If gap is more than 1 day, create a bridge point
            if (daysDiff > 1) {
              // Modify the first forecast point to use last historical price as starting reference
              // This creates visual continuity
              const bridgeDate = new Date(lastHistDate);
              bridgeDate.setDate(bridgeDate.getDate() + 1);
              
              // Insert bridge point with interpolated values
              const bridgePoint = {
                ...lastHistInFiltered,
                date: bridgeDate.toISOString().slice(0, 10),
                isPrediction: true,
                price: lastHistInFiltered.price,
                volume: lastHistInFiltered.volume,
              };
              
              // Find the index where forecast starts and insert bridge
              const forecastStartIdx = chartData.findIndex(d => d.isPrediction);
              if (forecastStartIdx > 0) {
                chartData.splice(forecastStartIdx, 0, bridgePoint);
              }
            }
          }
        }

        setData(chartData);
        
        // Store the last historical date for visual separation
        if (resp.lastHistoricalDate) {
          setLastHistoricalDate(resp.lastHistoricalDate);
        }
        
        // Store last historical price and variation
        if (resp.lastHistoricalPrice != null) {
          setLastHistoricalPrice(resp.lastHistoricalPrice);
        }
        if (resp.lastHistoricalVariation != null) {
          setLastHistoricalVariation(resp.lastHistoricalVariation);
        }
        
        // Store forecast data for prediction cards
        if (resp.forecast && resp.forecast.length > 0) {
          setForecastData(resp.forecast);
        } else {
          setForecastData([]);
        }
        
        // Generate rule-based market analysis
        generateMarketAnalysis(chartData, resp.forecast || []);
        
        // Store stock name for sentiment lookup
        const sentimentName = resp.name || selectedCompanyName || symbol;
        setStockNameForSentiment(sentimentName);
        
        // Fetch real sentiment data using the stock name
        // Use anchored dates for sentiment as well
        const fmt = (d) => (d instanceof Date ? d.toISOString().slice(0,10) : d);
        fetchSentimentData(sentimentName, fmt(anchoredStart), fmt(anchoredEnd));
      } else if (resp && resp.history && resp.history.length > 0) {
        // Fallback to just history if combined is empty
        let chartData = resp.history.map((row) => ({
          date: row?.date || '',
          price: row?.price != null ? Number(row.price) : Number(row?.close ?? 0),
          close: Number(row?.close ?? row?.price ?? 0),
          open: Number(row?.open ?? 0),
          high: Number(row?.high ?? 0),
          low: Number(row?.low ?? 0),
          volume: Number(row?.volume ?? 0),
          variation: Number(row?.variation ?? 0),
          isPrediction: false,
          // Price/Variation Anomaly data - 3 types
          variationAnomaly: Boolean(row?.variationAnomaly),
          variationAnomalyPostNews: Boolean(row?.variationAnomalyPostNews),
          variationAnomalyPreNews: Boolean(row?.variationAnomalyPreNews),
          // Volume Anomaly data - 3 types
          volumeAnomaly: Boolean(row?.volumeAnomaly),
          volumeAnomalyPostNews: Boolean(row?.volumeAnomalyPostNews),
          volumeAnomalyPreNews: Boolean(row?.volumeAnomalyPreNews),
        }));
        // Anchor to last historical date from history
        const baseEndStr = chartData.slice(-1)[0]?.date;
        const baseEnd = baseEndStr ? new Date(baseEndStr) : new Date();
        let anchoredStart = new Date(baseEnd);
        let anchoredEnd = new Date(baseEnd);
        
        // Determine if we should show forecast (hide for custom date range)
        const isCustomRange = period === 'custom' && customStartDate && customEndDate;
        const showForecast = !isCustomRange;
        
        if (isCustomRange) {
          anchoredStart = new Date(customStartDate);
          anchoredEnd = new Date(customEndDate);
        } else if (period === 'ytd') {
          anchoredStart = new Date(baseEnd.getFullYear(), 0, 1);
        } else if (period === 'all') {
          anchoredStart.setFullYear(anchoredStart.getFullYear() - 10);
        } else {
          const preset = timePresets.find((p) => p.id === period);
          anchoredStart.setDate(anchoredStart.getDate() - (preset?.days || 30));
        }
        
        chartData = chartData.filter(d => {
          // Only include predictions when showForecast is true
          if (d.isPrediction) return showForecast;
          const dt = d.date ? new Date(d.date) : null;
          return dt && dt >= anchoredStart && dt <= anchoredEnd;
        });

        setData(chartData);
        setForecastData([]);
        const fmt = (d) => (d instanceof Date ? d.toISOString().slice(0,10) : d);
        fetchSentimentData(symbol, fmt(anchoredStart), fmt(anchoredEnd));
      } else {
        // Fallback to old API
        const fallbackResp = await ApiService.request(`/market-data/${encodeURIComponent(symbol)}`, { method: 'GET' });
        
        let series = [];
        if (fallbackResp && Array.isArray(fallbackResp.history)) series = fallbackResp.history;
        else if (Array.isArray(fallbackResp)) series = fallbackResp;

        let chartData = series.map((row) => ({
          date: row?.date || '',
          price: row?.close != null ? Number(row.close) : Number(row?.price ?? 0),
          isPrediction: false,
        }));
        if (chartData.length) {
          const baseEndStr = chartData.slice(-1)[0]?.date;
          const baseEnd = baseEndStr ? new Date(baseEndStr) : new Date();
          let anchoredStart = new Date(baseEnd);
          let anchoredEnd = new Date(baseEnd);
          
          // Determine if we should show forecast (hide for custom date range)
          const isCustomRange = period === 'custom' && customStartDate && customEndDate;
          const showForecast = !isCustomRange;
          
          if (isCustomRange) {
            anchoredStart = new Date(customStartDate);
            anchoredEnd = new Date(customEndDate);
          } else if (period === 'ytd') {
            anchoredStart = new Date(baseEnd.getFullYear(), 0, 1);
          } else if (period === 'all') {
            anchoredStart.setFullYear(anchoredStart.getFullYear() - 10);
          } else {
            const preset = timePresets.find((p) => p.id === period);
            anchoredStart.setDate(anchoredStart.getDate() - (preset?.days || 30));
          }
          
          chartData = chartData.filter(d => {
            // Only include predictions when showForecast is true
            if (d.isPrediction) return showForecast;
            const dt = d.date ? new Date(d.date) : null;
            return dt && dt >= anchoredStart && dt <= anchoredEnd;
          });

          setData(chartData);
          const fmt = (d) => (d instanceof Date ? d.toISOString().slice(0,10) : d);
          fetchSentimentData(symbol, fmt(anchoredStart), fmt(anchoredEnd));
        } else {
          setError('No market data available');
          setData([]);
        }
      }
    } catch (err) {
      console.error('Failed to fetch market data', err);
      setError(err.message || 'Failed to fetch market data');
      setData([]);
    } finally {
      setLoading(false);
    }
  };

  // Fetch real sentiment data from API
  const fetchSentimentData = async (symbol, start, end) => {
    try {
      const resp = await ApiService.getStockSentiment(symbol, start, end);
      if (resp && resp.data && resp.data.length > 0) {
        setSentimentData(resp.data.map(d => ({
          date: d.date,
          sentiment: d.sentiment,
          articleCount: d.articleCount,
          intensity: d.intensity,
        })));
      } else {
        // No sentiment data available, clear it
        setSentimentData([]);
      }
    } catch (err) {
      console.error('Failed to fetch sentiment data', err);
      setSentimentData([]);
    }
  };

  const selectSymbol = (item) => {
    const code = typeof item === 'string' ? item : (item.stock_code || item.symbol || item.code || '');
    const name = typeof item === 'string' ? item : (item.stock_name || item.name || code);
    setSelectedSymbol(code);
    setSelectedCompanyName(name);
    setSymbolQuery(name);
    setShowDropdown(false);
    setSuggestions([]);
    fetchMarketHistory(code);
  };

  const handleKeyDown = (e) => {
    const list = suggestions.length > 0 ? suggestions : symbols;
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActiveSuggestion((i) => Math.min(i + 1, list.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActiveSuggestion((i) => Math.max(i - 1, 0));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      const picked = list[activeSuggestion] || list[0];
      if (picked) selectSymbol(picked);
    } else if (e.key === 'Escape') {
      setShowDropdown(false);
    }
  };

  const filteredSymbols = symbols.filter((s) => {
    const text = typeof s === 'string' ? s : `${s.symbol} ${s.name || ''}`;
    return text.toLowerCase().includes(symbolQuery.toLowerCase());
  });

  // Filter out items that are just "stocks" (case insensitive)
  const filterOutStocks = (list) => list.filter((s) => {
    const code = typeof s === 'string' ? s : (s.stock_code || s.symbol || s.code || '');
    const name = typeof s === 'string' ? '' : (s.stock_name || s.name || '');
    return code.toLowerCase() !== 'stocks' && name.toLowerCase() !== 'stocks';
  });

  // Always filter out "stocks" from all lists
  const filteredAllSymbols = filterOutStocks(symbols);
  const displayList = filterOutStocks(suggestions.length > 0 ? suggestions : (symbolQuery ? filteredSymbols : filteredAllSymbols));

  // Prepare chart data with technical indicators
  const chartDataWithIndicators = data.map((d, i) => ({
    ...d,
    rsi: technicalData.rsi[i],
    macd: technicalData.macd[i],
    signal: technicalData.signal[i],
    histogram: technicalData.histogram[i],
  }));

  // Generate rule-based market analysis from last 5 historical days + next 5 forecast days
  const generateMarketAnalysis = (historicalData, forecastData) => {
    if (!historicalData || historicalData.length === 0) {
      setMarketAnalysis(null);
      return;
    }

    // Get last 5 historical days (non-prediction)
    const last5Historical = historicalData.filter(d => !d.isPrediction).slice(-5);
    
    if (last5Historical.length === 0) {
      setMarketAnalysis(null);
      return;
    }

    // Calculate metrics for last 5 days
    const historicalPrices = last5Historical.map(d => d.price || d.close);
    const historicalVolumes = last5Historical.map(d => d.volume || 0);
    const historicalVariations = last5Historical.map(d => d.variation || 0);
    
    const avgHistPrice = historicalPrices.reduce((a, b) => a + b, 0) / historicalPrices.length;
    const avgHistVolume = historicalVolumes.reduce((a, b) => a + b, 0) / historicalVolumes.length;
    const totalHistVariation = historicalVariations.reduce((a, b) => a + b, 0);
    const priceRange = Math.max(...historicalPrices) - Math.min(...historicalPrices);
    const volatility = (priceRange / avgHistPrice) * 100;
    
    // Trend analysis
    const isUptrend = historicalPrices[historicalPrices.length - 1] > historicalPrices[0];
    const trendStrength = Math.abs(totalHistVariation);
    
    // Calculate metrics for next 5 days forecast
    let forecastPrices = [];
    let forecastVariations = [];
    let avgForecastPrice = 0;
    let totalForecastVariation = 0;
    let forecastTrend = 'neutral';
    
    if (forecastData && forecastData.length > 0) {
      forecastPrices = forecastData.map(d => d.price || d.close || 0);
      forecastVariations = forecastData.map(d => d.variation || 0);
      avgForecastPrice = forecastPrices.reduce((a, b) => a + b, 0) / forecastPrices.length;
      totalForecastVariation = forecastVariations.reduce((a, b) => a + b, 0);
      
      if (totalForecastVariation > 2) forecastTrend = 'bullish';
      else if (totalForecastVariation < -2) forecastTrend = 'bearish';
      else forecastTrend = 'neutral';
    }

    // Generate insights
    const insights = [];
    
    // Historical trend insight
    if (isUptrend && trendStrength > 3) {
      insights.push(`📈 Strong upward momentum in last 5 days (+${totalHistVariation.toFixed(2)}%)`);
    } else if (!isUptrend && trendStrength > 3) {
      insights.push(`📉 Downward pressure in last 5 days (${totalHistVariation.toFixed(2)}%)`);
    } else {
      insights.push(`➡️ Sideways movement in last 5 days (${totalHistVariation.toFixed(2)}%)`);
    }
    
    // Volatility insight
    if (volatility > 5) {
      insights.push(`⚠️ High volatility detected (${volatility.toFixed(1)}% price range)`);
    } else if (volatility < 2) {
      insights.push(`✓ Low volatility - stable price action (${volatility.toFixed(1)}%)`);
    }
    
    // Volume insight
    const lastVolume = historicalVolumes[historicalVolumes.length - 1];
    if (lastVolume > avgHistVolume * 1.5) {
      insights.push(`📊 Above-average volume detected (${((lastVolume / avgHistVolume - 1) * 100).toFixed(0)}% above avg)`);
    } else if (lastVolume < avgHistVolume * 0.5) {
      insights.push(`📊 Below-average volume (${((1 - lastVolume / avgHistVolume) * 100).toFixed(0)}% below avg)`);
    }
    
    // Forecast insight
    if (forecastData && forecastData.length > 0) {
      if (forecastTrend === 'bullish') {
        insights.push(`🔮 Forecast: Positive outlook for next 5 days (+${totalForecastVariation.toFixed(2)}% expected)`);
      } else if (forecastTrend === 'bearish') {
        insights.push(`🔮 Forecast: Negative outlook for next 5 days (${totalForecastVariation.toFixed(2)}% expected)`);
      } else {
        insights.push(`🔮 Forecast: Neutral outlook for next 5 days (${totalForecastVariation.toFixed(2)}% expected)`);
      }
    }

    setMarketAnalysis({
      last5Days: {
        avgPrice: avgHistPrice,
        totalVariation: totalHistVariation,
        volatility: volatility,
        trend: isUptrend ? 'up' : 'down',
        trendStrength: trendStrength,
        avgVolume: avgHistVolume,
      },
      next5Days: forecastData && forecastData.length > 0 ? {
        avgPrice: avgForecastPrice,
        totalVariation: totalForecastVariation,
        trend: forecastTrend,
      } : null,
      insights: insights,
    });
  };

  const getRecommendationColor = (action) => {
    switch (action) {
      case 'buy': return 'text-emerald-400';
      case 'sell': return 'text-rose-400';
      default: return 'text-amber-400';
    }
  };

  const getRecommendationIcon = (action) => {
    switch (action) {
      case 'buy': return <TrendingUp className="w-8 h-8 text-emerald-400" />;
      case 'sell': return <TrendingDown className="w-8 h-8 text-rose-400" />;
      default: return <Minus className="w-8 h-8 text-amber-400" />;
    }
  };

  const getRecommendationBg = (action) => {
    switch (action) {
      case 'buy': return 'bg-emerald-500/10 border-emerald-500/30';
      case 'sell': return 'bg-rose-500/10 border-rose-500/30';
      default: return 'bg-amber-500/10 border-amber-500/30';
    }
  };

  return (
    <div className="min-h-screen app-shell py-6">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-slate-100">Stock Analysis</h1>
          <p className="text-slate-400 mt-1">Analyze individual stock performance with technical indicators</p>
        </div>

        {/* Controls Panel */}
        <div className="panel p-6 mb-6">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Company Selector - Larger Dropdown */}
            <div className="lg:col-span-5" ref={dropdownRef}>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                <Search className="inline w-4 h-4 mr-1" />
                Select Company
              </label>
              <div className="relative">
                <div 
                  className="input-field flex items-center justify-between cursor-pointer min-h-[48px] text-base"
                  onClick={() => setShowDropdown(!showDropdown)}
                >
                  <input
                    type="text"
                    placeholder="Search by name or symbol..."
                    value={symbolQuery}
                    onChange={(e) => {
                      setSymbolQuery(e.target.value);
                      setShowDropdown(true);
                    }}
                    onKeyDown={handleKeyDown}
                    onFocus={() => setShowDropdown(true)}
                    className="bg-transparent border-none outline-none flex-1 text-slate-100 placeholder-slate-500"
                  />
                  <ChevronDown className={`w-5 h-5 text-slate-400 transition-transform ${showDropdown ? 'rotate-180' : ''}`} />
                </div>

                {showDropdown && (
                  <div className="absolute left-0 right-0 mt-2 z-50 bg-slate-900 border border-slate-700 rounded-xl shadow-2xl max-h-80 overflow-auto">
                    {(symbolQuery.trim() === '' ? filteredAllSymbols : displayList).length === 0 ? (
                      <div className="px-4 py-6 text-center text-slate-500">No companies found</div>
                    ) : (
                      (symbolQuery.trim() === '' ? filteredAllSymbols : displayList).slice(0, 50).map((s, idx) => {
                        const code = typeof s === 'string' ? s : (s.stock_code || s.symbol || s.code || '');
                        const name = typeof s === 'string' ? '' : (s.stock_name || s.name || '');
                        const isActive = idx === activeSuggestion;
                        const isSelected = code === selectedSymbol;
                        
                        return (
                          <button
                            key={code || idx}
                            type="button"
                            onClick={() => selectSymbol(s)}
                            className={`w-full flex items-center justify-between px-4 py-3 text-left transition-colors
                              ${isActive ? 'bg-cyan-500/20' : 'hover:bg-slate-800'}
                              ${isSelected ? 'bg-cyan-500/10 border-l-4 border-cyan-400' : 'border-l-4 border-transparent'}
                            `}
                          >
                            <div>
                              <div className="text-base font-medium text-slate-100">{name || code}</div>
                              {name && <div className="text-sm text-slate-500">{code}</div>}
                            </div>
                            {isSelected && <span className="text-xs text-cyan-400 font-medium">Selected</span>}
                          </button>
                        );
                      })
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Time Period Selector - Modern Button Group */}
            <div className="lg:col-span-5">
              <label className="block text-sm font-medium text-slate-300 mb-2">
                <Calendar className="inline w-4 h-4 mr-1" />
                Time Period
              </label>
              <div className="flex flex-wrap gap-1 bg-slate-900/50 p-1 rounded-lg border border-slate-700/50">
                {timePresets.map((p) => (
                  <button
                    key={p.id}
                    onClick={() => {
                      setPeriod(p.id);
                      setCustomDateError('');
                      if (p.id !== 'custom' && selectedSymbol) fetchMarketHistory(selectedSymbol);
                    }}
                    className={`px-3 py-2 rounded-md text-sm font-medium transition-all
                      ${period === p.id 
                        ? 'bg-cyan-500 text-slate-900 shadow-lg shadow-cyan-500/25' 
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                      }
                    `}
                  >
                    {p.label}
                  </button>
                ))}
              </div>
              
              {/* Custom Date Range Inputs */}
              {period === 'custom' && (
                <div className="mt-3">
                  <div className="flex flex-wrap gap-3">
                    <div className="flex items-center gap-2">
                      <label className="text-sm text-slate-400">From:</label>
                      <input
                        type="date"
                        value={customStartDate}
                        onChange={(e) => {
                          setCustomStartDate(e.target.value);
                          setCustomDateError('');
                        }}
                        className={`input-field py-1.5 px-3 text-sm ${!customStartDate && customDateError ? 'border-rose-500' : ''}`}
                      />
                    </div>
                    <div className="flex items-center gap-2">
                      <label className="text-sm text-slate-400">To:</label>
                      <input
                        type="date"
                        value={customEndDate}
                        onChange={(e) => {
                          setCustomEndDate(e.target.value);
                          setCustomDateError('');
                        }}
                        className={`input-field py-1.5 px-3 text-sm ${!customEndDate && customDateError ? 'border-rose-500' : ''}`}
                      />
                    </div>
                  </div>
                  {customDateError && (
                    <div className="mt-2 text-sm text-rose-400 flex items-center gap-1">
                      <AlertTriangle className="w-4 h-4" />
                      {customDateError}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Apply Button */}
            <div className="lg:col-span-2 flex items-end">
              <button
                onClick={() => selectedSymbol && fetchMarketHistory(selectedSymbol)}
                disabled={loading || !selectedSymbol}
                className="btn-primary w-full h-12 text-base disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <span className="flex items-center justify-center">
                    <svg className="animate-spin h-5 w-5 mr-2" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    Loading
                  </span>
                ) : 'Apply'}
              </button>
            </div>
          </div>
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Price Chart - 2 columns */}
          <div className="lg:col-span-2 panel p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-lg font-semibold text-slate-100">
                  {selectedSymbol ? `${selectedCompanyName || selectedSymbol}` : 'Select a stock'}
                </h3>
                {selectedSymbol && data.length > 0 && (
                  <div className="text-sm text-slate-500">
                    <span>{data.filter(d => !d.isPrediction).length} historical + {data.filter(d => d.isPrediction).length} forecast points</span>
                    {lastHistoricalDate && (
                      <span className="ml-2">• History ends: {lastHistoricalDate}</span>
                    )}
                  </div>
                )}
              </div>
              {data.length > 0 && (
                <div className="text-right">
                  <div className="text-2xl font-bold text-slate-100">
                    {lastHistoricalPrice != null ? lastHistoricalPrice.toFixed(2) : data.filter(d => !d.isPrediction).slice(-1)[0]?.price?.toFixed(2)} TND
                    <span className="text-xs text-slate-400 ml-2">(Last Historical)</span>
                  </div>
                  <div className={`text-sm ${(lastHistoricalVariation ?? 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {(lastHistoricalVariation ?? 0) >= 0 ? '+' : ''}{(lastHistoricalVariation ?? 0).toFixed(2)}%
                  </div>
                </div>
              )}
            </div>

            {/* Price Chart Title and Anomaly Controls - Upper Left */}
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-2">
                  <BarChart2 className="w-5 h-5 text-cyan-400" />
                  <h4 className="text-md font-semibold text-slate-200">Price</h4>
                </div>
                <button
                  onClick={() => setShowPriceAnomalies(!showPriceAnomalies)}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors ${
                    showPriceAnomalies 
                      ? 'bg-rose-500/20 text-rose-400 border border-rose-500/50' 
                      : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
                  }`}
                >
                  {showPriceAnomalies ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  {showPriceAnomalies ? 'Hide Price Anomalies' : 'Show Price Anomalies'}
                </button>
                
                {showPriceAnomalies && (
                  <div className="flex items-center gap-2">
                    <Filter className="w-4 h-4 text-slate-400" />
                    <select
                      value={priceAnomalyFilter}
                      onChange={(e) => setPriceAnomalyFilter(e.target.value)}
                      className="bg-slate-800 text-slate-300 text-sm rounded-lg px-2 py-1 border border-slate-700"
                    >
                      <option value="all">All Anomalies</option>
                      <option value="news">Reaction to News</option>
                      <option value="leakage">Possible Leakage</option>
                      <option value="unexplained">Unexplained</option>
                    </select>
                  </div>
                )}
              </div>
            </div>

            {error && <div className="text-rose-400 mb-4 p-3 bg-rose-500/10 rounded-lg">{error}</div>}

            {data.length > 0 ? (
              <>
                <div style={{ height: 320 }}>
                  <ResponsiveContainer>
                    <ComposedChart data={chartDataWithIndicators} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                      <defs>
                        <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#22d3ee" stopOpacity={0.3}/>
                          <stop offset="95%" stopColor="#22d3ee" stopOpacity={0}/>
                        </linearGradient>
                        <linearGradient id="colorPrediction" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.3}/>
                          <stop offset="95%" stopColor="#f59e0b" stopOpacity={0}/>
                        </linearGradient>
                        {/* Gradient for transition from historical to forecast */}
                        <linearGradient id="colorTransition" x1="0" y1="0" x2="1" y2="0">
                          <stop offset="0%" stopColor="#22d3ee"/>
                          <stop offset="100%" stopColor="#f59e0b"/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                      <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 12 }} tickLine={{ stroke: '#334155' }} />
                      <YAxis domain={['auto', 'auto']} tick={{ fill: '#64748b', fontSize: 12 }} tickLine={{ stroke: '#334155' }} />
                      <Tooltip 
                        contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #334155', borderRadius: '8px' }}
                        labelStyle={{ color: '#e2e8f0' }}
                        content={({ active, payload, label }) => {
                          if (!active || !payload || !payload.length) return null;
                          const d = payload[0]?.payload;
                          const hasAnomaly = d?.variationAnomaly || d?.variationAnomalyPostNews || d?.variationAnomalyPreNews;
                        return (
                          <div className="bg-slate-900 border border-slate-700 rounded-lg p-3 shadow-xl">
                            <p className="text-slate-300 text-sm mb-1">{label}</p>
                            <p className="text-slate-100 font-semibold">
                              {d?.price?.toFixed(2)} TND 
                              {d?.isPrediction && <span className="text-amber-400 text-xs ml-1">(Forecast)</span>}
                            </p>
                            {d?.variation !== 0 && (
                              <p className={`text-sm ${d?.variation >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                                {d?.variation >= 0 ? '+' : ''}{d?.variation?.toFixed(2)}%
                              </p>
                            )}
                            {showPriceAnomalies && hasAnomaly && !d?.isPrediction && (
                              <div className="mt-2 pt-2 border-t border-slate-700">
                                {d?.variationAnomalyPostNews && (
                                  <p className="text-green-400 text-xs flex items-center gap-1">
                                    <span>▲</span> Reaction to News
                                  </p>
                                )}
                                {d?.variationAnomalyPreNews && (
                                  <p className="text-red-400 text-xs flex items-center gap-1">
                                    <span>▼</span> Possible Leakage
                                  </p>
                                )}
                                {d?.variationAnomaly && !d?.variationAnomalyPostNews && !d?.variationAnomalyPreNews && (
                                  <p className="text-yellow-400 text-xs flex items-center gap-1">
                                    <span>●</span> Unexplained Anomaly
                                  </p>
                                )}
                              </div>
                            )}
                          </div>
                        );
                      }}
                    />

                    {/* Historical data - cyan - stops at last historical point */}
                    <Area 
                      type="monotone" 
                      dataKey={(d) => {
                        // Only include historical points (blue fill stops at last historical)
                        if (!d.isPrediction) return d.price;
                        return null;
                      }} 
                      name="historical"
                      stroke="#22d3ee" 
                      fillOpacity={1} 
                      fill="url(#colorPrice)" 
                      strokeWidth={2.5}
                      connectNulls={true}
                    />
                    {/* Prediction data - amber/orange - starts from last historical for continuous fill */}
                    <Area 
                      type="monotone" 
                      dataKey={(d, index) => {
                        // Include all forecast points
                        if (d.isPrediction) return d.price;
                        // Also include the last historical point so orange fill extends back to it
                        // This ensures the transition zone is filled with orange
                        const nextPoint = chartDataWithIndicators[index + 1];
                        if (nextPoint && nextPoint.isPrediction) return d.price;
                        return null;
                      }} 
                      name="forecast"
                      stroke="#f59e0b" 
                      fillOpacity={1} 
                      fill="url(#colorPrediction)" 
                      strokeWidth={2.5}
                      strokeDasharray="6 4"
                      connectNulls={true}
                    />
                    {/* Transition marker at junction point */}
                    <Line 
                      type="monotone"
                      dataKey={(d, index) => {
                        // Only show for the transition point (last historical and first forecast)
                        const nextPoint = chartDataWithIndicators[index + 1];
                        const prevPoint = chartDataWithIndicators[index - 1];
                        if (!d.isPrediction && nextPoint?.isPrediction) return d.price;
                        if (d.isPrediction && prevPoint && !prevPoint.isPrediction) return d.price;
                        return null;
                      }}
                      stroke="url(#colorTransition)"
                      strokeWidth={3}
                      dot={false}
                      connectNulls={true}
                    />
                    {/* Anomaly markers on price chart */}
                    {showPriceAnomalies && (
                      <Line
                        type="monotone"
                        dataKey={(d) => {
                          if (!d.isPrediction) {
                            const hasAnomaly = d.variationAnomaly || d.variationAnomalyPostNews || d.variationAnomalyPreNews;
                            if (priceAnomalyFilter === 'all' && hasAnomaly) return d.price;
                            if (priceAnomalyFilter === 'news' && d.variationAnomalyPostNews) return d.price;
                            if (priceAnomalyFilter === 'leakage' && d.variationAnomalyPreNews) return d.price;
                            if (priceAnomalyFilter === 'unexplained' && d.variationAnomaly && !d.variationAnomalyPostNews && !d.variationAnomalyPreNews) return d.price;
                          }
                          return null;
                        }}
                        stroke="transparent"
                        dot={(props) => {
                          const { cx, cy, payload } = props;
                          if (!payload || payload.isPrediction) return null;
                          
                          const isPostNews = payload.variationAnomalyPostNews;
                          const isPreNews = payload.variationAnomalyPreNews;
                          const isUnexplained = payload.variationAnomaly && !isPostNews && !isPreNews;
                          
                          if (!isPostNews && !isPreNews && !isUnexplained) return null;
                          
                          // Post-news (reaction): green up arrow
                          if (isPostNews) {
                            return (
                              <g key={`anomaly-post-${payload.date}`}>
                                <polygon
                                  points={`${cx},${cy - 10} ${cx - 6},${cy + 2} ${cx + 6},${cy + 2}`}
                                  fill="#22c55e"
                                  stroke="#fff"
                                  strokeWidth={1.5}
                                  style={{ filter: 'drop-shadow(0 0 4px #22c55e)' }}
                                />
                              </g>
                            );
                          }
                          
                          // Pre-news (leakage): red down arrow
                          if (isPreNews) {
                            return (
                              <g key={`anomaly-pre-${payload.date}`}>
                                <polygon
                                  points={`${cx},${cy + 10} ${cx - 6},${cy - 2} ${cx + 6},${cy - 2}`}
                                  fill="#ef4444"
                                  stroke="#fff"
                                  strokeWidth={1.5}
                                  style={{ filter: 'drop-shadow(0 0 4px #ef4444)' }}
                                />
                              </g>
                            );
                          }
                          
                          // Unexplained: yellow circle
                          return (
                            <circle
                              key={`anomaly-unexplained-${payload.date}`}
                              cx={cx}
                              cy={cy}
                              r={6}
                              fill="#eab308"
                              stroke="#fff"
                              strokeWidth={2}
                              style={{ filter: 'drop-shadow(0 0 4px #eab308)' }}
                            />
                          );
                        }}
                      />
                    )}
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
              {/* Price Chart Legend - Below Graph */}
              <div className="flex justify-center gap-6 mt-3 text-xs">
                <span className="flex items-center gap-1"><span className="text-cyan-400">■</span> Historical</span>
                <span className="flex items-center gap-1"><span className="text-amber-400">■</span> Forecast (5 days)</span>
                {showPriceAnomalies && (
                  <React.Fragment>
                    <span className="flex items-center gap-1 text-green-400">▲ Reaction to News</span>
                    <span className="flex items-center gap-1 text-red-400">▼ Possible Leakage</span>
                    <span className="flex items-center gap-1 text-yellow-400">● Unexplained</span>
                  </React.Fragment>
                )}
              </div>
            </>
            ) : (
              <div className="flex items-center justify-center h-64 text-slate-500">
                <div className="text-center">
                  <BarChart2 className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p>Select a company to view price chart</p>
                </div>
              </div>
            )}

            {/* Volume Chart */}
            {data.length > 0 && (
              <div className="mt-6">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className="flex items-center gap-2">
                      <BarChart2 className="w-5 h-5 text-cyan-400" />
                      <h4 className="text-md font-semibold text-slate-200">Volume</h4>
                    </div>
                    <button
                      onClick={() => setShowVolumeAnomalies(!showVolumeAnomalies)}
                      className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors ${
                        showVolumeAnomalies 
                          ? 'bg-amber-500/20 text-amber-400 border border-amber-500/50' 
                          : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
                      }`}
                    >
                      {showVolumeAnomalies ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      {showVolumeAnomalies ? 'Hide Volume Anomalies' : 'Show Volume Anomalies'}
                    </button>
                    
                    {showVolumeAnomalies && (
                      <div className="flex items-center gap-2">
                        <Filter className="w-4 h-4 text-slate-400" />
                        <select
                          value={volumeAnomalyFilter}
                          onChange={(e) => setVolumeAnomalyFilter(e.target.value)}
                          className="bg-slate-800 text-slate-300 text-sm rounded-lg px-2 py-1 border border-slate-700"
                        >
                          <option value="all">All Anomalies</option>
                          <option value="reaction">Reaction Volume</option>
                          <option value="anticipation">Anticipation Volume</option>
                          <option value="unexplained">Unexplained</option>
                        </select>
                      </div>
                    )}
                  </div>
                </div>
                <div style={{ height: 150 }}>
                  <ResponsiveContainer>
                    <ComposedChart data={chartDataWithIndicators} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                      <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 10 }} tickLine={{ stroke: '#334155' }} />
                      <YAxis tick={{ fill: '#64748b', fontSize: 10 }} tickLine={{ stroke: '#334155' }} tickFormatter={(v) => v >= 1000000 ? `${(v/1000000).toFixed(1)}M` : v >= 1000 ? `${(v/1000).toFixed(0)}K` : v} />
                      <Tooltip 
                        contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #334155', borderRadius: '8px' }}
                        content={({ active, payload, label }) => {
                          if (!active || !payload || !payload.length) return null;
                          const d = payload[0]?.payload;
                          const hasVolumeAnomaly = d?.volumeAnomaly || d?.volumeAnomalyPostNews || d?.volumeAnomalyPreNews;
                          return (
                            <div className="bg-slate-900 border border-slate-700 rounded-lg p-3 shadow-xl">
                              <p className="text-slate-300 text-sm mb-1">{label}</p>
                              <p className="text-slate-100 font-semibold">
                                Volume: {d?.volume?.toLocaleString()}
                                {d?.isPrediction && <span className="text-amber-400 text-xs ml-1">(Forecast)</span>}
                              </p>
                              {showVolumeAnomalies && hasVolumeAnomaly && !d?.isPrediction && (
                                <div className="mt-2 pt-2 border-t border-slate-700">
                                  {d?.volumeAnomalyPostNews && (
                                    <p className="text-green-400 text-xs flex items-center gap-1">
                                      <span>▲</span> Reaction to News
                                    </p>
                                  )}
                                  {d?.volumeAnomalyPreNews && (
                                    <p className="text-red-400 text-xs flex items-center gap-1">
                                      <span>▼</span> Possible Leakage
                                    </p>
                                  )}
                                  {d?.volumeAnomaly && !d?.volumeAnomalyPostNews && !d?.volumeAnomalyPreNews && (
                                    <p className="text-yellow-400 text-xs flex items-center gap-1">
                                      <span>●</span> Unexplained Anomaly
                                    </p>
                                  )}
                                </div>
                              )}
                            </div>
                          );
                        }}
                      />
                      <Bar 
                        dataKey="volume" 
                        radius={[2, 2, 0, 0]}
                        shape={(props) => {
                          const { x, y, width, height, payload } = props;
                          const fill = payload?.isPrediction ? '#f59e0b' : '#22d3ee';
                          const opacity = payload?.isPrediction ? 0.7 : 0.6;
                          return (
                            <rect
                              x={x}
                              y={y}
                              width={width}
                              height={height}
                              fill={fill}
                              opacity={opacity}
                              rx={2}
                              ry={2}
                            />
                          );
                        }}
                      />
                      {/* Volume anomaly markers */}
                      {showVolumeAnomalies && (
                        <Line
                          type="monotone"
                          dataKey={(d) => {
                            const hasVolumeAnomaly = d.volumeAnomaly || d.volumeAnomalyPostNews || d.volumeAnomalyPreNews;
                            if (volumeAnomalyFilter === 'all' && hasVolumeAnomaly) return d.volume;
                            if (volumeAnomalyFilter === 'reaction' && d.volumeAnomalyPostNews) return d.volume;
                            if (volumeAnomalyFilter === 'anticipation' && d.volumeAnomalyPreNews) return d.volume;
                            if (volumeAnomalyFilter === 'unexplained' && d.volumeAnomaly && !d.volumeAnomalyPostNews && !d.volumeAnomalyPreNews) return d.volume;
                            return null;
                          }}
                          stroke="transparent"
                          dot={(props) => {
                            const { cx, cy, payload } = props;
                            if (!payload || payload.isPrediction) return null;

                            const isPostNews = payload.volumeAnomalyPostNews;
                            const isPreNews = payload.volumeAnomalyPreNews;
                            const isUnexplained = payload.volumeAnomaly && !isPostNews && !isPreNews;

                            // Respect selected filter
                            const matchesFilter = (() => {
                              if (volumeAnomalyFilter === 'all') return (isPostNews || isPreNews || isUnexplained);
                              if (volumeAnomalyFilter === 'reaction') return isPostNews;
                              if (volumeAnomalyFilter === 'anticipation') return isPreNews;
                              if (volumeAnomalyFilter === 'unexplained') return isUnexplained;
                              return false;
                            })();

                            if (!matchesFilter) return null;

                            // Post-news (reaction): green up arrow
                            if (isPostNews) {
                              return (
                                <g key={`vol-anomaly-post-${payload.date}`}>
                                  <polygon
                                    points={`${cx},${cy - 8} ${cx - 5},${cy + 1} ${cx + 5},${cy + 1}`}
                                    fill="#22c55e"
                                    stroke="#fff"
                                    strokeWidth={1.5}
                                    style={{ filter: 'drop-shadow(0 0 4px #22c55e)' }}
                                  />
                                </g>
                              );
                            }

                            // Pre-news (leakage): red down arrow
                            if (isPreNews) {
                              return (
                                <g key={`vol-anomaly-pre-${payload.date}`}>
                                  <polygon
                                    points={`${cx},${cy + 8} ${cx - 5},${cy - 1} ${cx + 5},${cy - 1}`}
                                    fill="#ef4444"
                                    stroke="#fff"
                                    strokeWidth={1.5}
                                    style={{ filter: 'drop-shadow(0 0 4px #ef4444)' }}
                                  />
                                </g>
                              );
                            }

                            // Unexplained: yellow circle
                            return (
                              <circle
                                key={`vol-anomaly-unexplained-${payload.date}`}
                                cx={cx}
                                cy={cy}
                                r={5}
                                fill="#eab308"
                                stroke="#fff"
                                strokeWidth={2}
                                style={{ filter: 'drop-shadow(0 0 4px #eab308)' }}
                              />
                            );
                          }}
                        />
                      )}
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
                {/* Volume Chart Legend - Below Graph */}
                <div className="flex justify-center gap-6 mt-3 text-xs">
                  <span className="flex items-center gap-1"><span className="text-cyan-400">■</span> Historical</span>
                  <span className="flex items-center gap-1"><span className="text-amber-400">■</span> Forecast</span>
                  {showVolumeAnomalies && (
                    <React.Fragment>
                      <span className="flex items-center gap-1 text-green-400">▲ Reaction Volume</span>
                      <span className="flex items-center gap-1 text-red-400">▼ Anticipation Volume</span>
                      <span className="flex items-center gap-1 text-yellow-400">● Unexplained</span>
                    </React.Fragment>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Market Analysis Panel - Rule-based */}
          <div className="panel p-6">
            <div className="flex items-center gap-2 mb-4">
              <Activity className="w-5 h-5 text-cyan-400" />
              <h3 className="text-lg font-semibold text-slate-100">Market Analysis</h3>
            </div>

            {selectedSymbol && marketAnalysis ? (
              <div className="space-y-4">
                {/* Last 5 Days Summary */}
                <div className="rounded-xl border border-slate-700 bg-slate-800/30 p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <BarChart2 className="w-4 h-4 text-blue-400" />
                    <h4 className="text-sm font-semibold text-slate-200">Last 5 Days</h4>
                  </div>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-slate-400">Avg Price:</span>
                      <span className="text-slate-200 font-medium">{marketAnalysis.last5Days.avgPrice.toFixed(2)} TND</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Total Change:</span>
                      <span className={marketAnalysis.last5Days.totalVariation >= 0 ? 'text-emerald-400 font-medium' : 'text-rose-400 font-medium'}>
                        {marketAnalysis.last5Days.totalVariation >= 0 ? '+' : ''}{marketAnalysis.last5Days.totalVariation.toFixed(2)}%
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Volatility:</span>
                      <span className={`font-medium ${
                        marketAnalysis.last5Days.volatility > 5 ? 'text-rose-400' : 
                        marketAnalysis.last5Days.volatility < 2 ? 'text-emerald-400' : 'text-amber-400'
                      }`}>
                        {marketAnalysis.last5Days.volatility.toFixed(1)}%
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Trend:</span>
                      <span className="text-slate-200 font-medium flex items-center gap-1">
                        {marketAnalysis.last5Days.trend === 'up' ? <TrendingUp className="w-4 h-4 text-emerald-400" /> : <TrendingDown className="w-4 h-4 text-rose-400" />}
                        {marketAnalysis.last5Days.trend === 'up' ? 'Upward' : 'Downward'}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Next 5 Days Forecast */}
                {marketAnalysis.next5Days && (
                  <div className="rounded-xl border border-slate-700 bg-slate-800/30 p-4">
                    <div className="flex items-center gap-2 mb-3">
                      <TrendingUp className="w-4 h-4 text-amber-400" />
                      <h4 className="text-sm font-semibold text-slate-200">Next 5 Days Forecast</h4>
                    </div>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-slate-400">Avg Forecast:</span>
                        <span className="text-slate-200 font-medium">{marketAnalysis.next5Days.avgPrice.toFixed(2)} TND</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Expected Change:</span>
                        <span className={marketAnalysis.next5Days.totalVariation >= 0 ? 'text-emerald-400 font-medium' : 'text-rose-400 font-medium'}>
                          {marketAnalysis.next5Days.totalVariation >= 0 ? '+' : ''}{marketAnalysis.next5Days.totalVariation.toFixed(2)}%
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Outlook:</span>
                        <span className={`font-medium ${
                          marketAnalysis.next5Days.trend === 'bullish' ? 'text-emerald-400' : 
                          marketAnalysis.next5Days.trend === 'bearish' ? 'text-rose-400' : 'text-amber-400'
                        }`}>
                          {marketAnalysis.next5Days.trend === 'bullish' ? '📈 Bullish' : 
                           marketAnalysis.next5Days.trend === 'bearish' ? '📉 Bearish' : '➡️ Neutral'}
                        </span>
                      </div>
                    </div>
                  </div>
                )}

                {/* Key Insights */}
                <div className="rounded-xl border border-cyan-500/30 bg-cyan-500/10 p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <Sparkles className="w-4 h-4 text-cyan-400" />
                    <h4 className="text-sm font-semibold text-cyan-300">Key Insights</h4>
                  </div>
                  <div className="space-y-2">
                    {marketAnalysis.insights.map((insight, idx) => (
                      <div key={idx} className="text-sm text-slate-300 leading-relaxed">
                        {insight}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-center h-48 text-slate-500 text-center">
                <div>
                  <Activity className="w-10 h-10 mx-auto mb-2 opacity-50" />
                  <p>Select a stock to see market analysis</p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* 5-Day Forecast Prediction Cards */}
        {forecastData.length > 0 && (
          <div className="mt-6 panel p-6">
            <div className="flex items-center gap-2 mb-4">
              <TrendingUp className="w-5 h-5 text-amber-400" />
              <h3 className="text-lg font-semibold text-slate-100">5-Day Price Forecast</h3>
              <span className="text-xs text-slate-500 ml-auto">Predicted values based on ML model</span>
            </div>
            
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
              {forecastData.map((forecast, idx) => {
                const isPositive = forecast.variation >= 0;
                return (
                  <div 
                    key={forecast.date || idx}
                    className={`rounded-xl p-4 border transition-all hover:scale-105 ${
                      isPositive 
                        ? 'bg-emerald-500/10 border-emerald-500/30 hover:border-emerald-500/50' 
                        : 'bg-rose-500/10 border-rose-500/30 hover:border-rose-500/50'
                    }`}
                  >
                    <div className="text-center">
                      {/* Date */}
                      <div className="text-sm font-medium text-slate-300 mb-2">
                        {new Date(forecast.date).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}
                      </div>
                      
                      {/* Predicted Price */}
                      <div className="text-2xl font-bold text-slate-100 mb-1">
                        {forecast.price?.toFixed(2)}
                        <span className="text-sm text-slate-400 ml-1">TND</span>
                      </div>
                      
                      {/* Variation */}
                      <div className={`text-sm font-semibold ${isPositive ? 'text-emerald-400' : 'text-rose-400'}`}>
                        {isPositive ? '↑' : '↓'} {isPositive ? '+' : ''}{forecast.variation?.toFixed(2)}%
                      </div>
                      
                      {/* Volume */}
                      <div className="mt-3 pt-3 border-t border-slate-700/50">
                        <div className="flex justify-between text-xs">
                          <span className="text-slate-500">Volume</span>
                          <span className="text-slate-300">{forecast.volume?.toLocaleString()}</span>
                        </div>
                        
                        {/* Probability Liquidity */}
                        <div className="flex justify-between text-xs mt-1">
                          <span className="text-slate-500">Liquidity</span>
                          <span className={`${forecast.probLiquidity >= 0.7 ? 'text-emerald-400' : forecast.probLiquidity >= 0.4 ? 'text-amber-400' : 'text-rose-400'}`}>
                            {(forecast.probLiquidity * 100)?.toFixed(0)}%
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
            
            {/* Legend */}
            <div className="flex items-center justify-center gap-6 mt-4 text-xs text-slate-500">
              <span className="flex items-center gap-1">
                <span className="w-3 h-3 rounded-full bg-emerald-500/30 border border-emerald-500/50"></span>
                Positive forecast
              </span>
              <span className="flex items-center gap-1">
                <span className="w-3 h-3 rounded-full bg-rose-500/30 border border-rose-500/50"></span>
                Negative forecast
              </span>
              <span className="flex items-center gap-1">
                <span className="text-emerald-400">●</span> High liquidity (&gt;70%)
              </span>
            </div>
          </div>
        )}

        {/* Technical Indicators Section */}
        {data.length > 0 && (
          <div className="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* RSI Chart */}
            {showRSI && (
              <div className="panel p-6">
                <div className="flex items-center gap-2 mb-4">
                  <Activity className="w-5 h-5 text-purple-400" />
                  <h3 className="text-lg font-semibold text-slate-100">RSI (14)</h3>
                  <span className="text-xs text-slate-500 ml-auto">Relative Strength Index</span>
                </div>
                <div style={{ height: 200 }}>
                  <ResponsiveContainer>
                    <LineChart data={chartDataWithIndicators} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                      <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 10 }} />
                      <YAxis domain={[0, 100]} ticks={[30, 50, 70]} tick={{ fill: '#64748b', fontSize: 10 }} />
                      <Tooltip contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #334155', borderRadius: '8px' }} />
                      {/* Overbought/Oversold zones */}
                      <Line type="monotone" dataKey={() => 70} stroke="#ef4444" strokeDasharray="5 5" dot={false} strokeWidth={1} />
                      <Line type="monotone" dataKey={() => 30} stroke="#22c55e" strokeDasharray="5 5" dot={false} strokeWidth={1} />
                      <Line type="monotone" dataKey="rsi" stroke="#a855f7" dot={false} strokeWidth={2} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
                <div className="flex justify-center gap-6 mt-3 text-xs">
                  <span className="text-rose-400">● Overbought (70+)</span>
                  <span className="text-emerald-400">● Oversold (30-)</span>
                </div>
              </div>
            )}

            {/* MACD Chart */}
            {showMACD && (
              <div className="panel p-6">
                <div className="flex items-center gap-2 mb-4">
                  <Activity className="w-5 h-5 text-blue-400" />
                  <h3 className="text-lg font-semibold text-slate-100">MACD</h3>
                  <span className="text-xs text-slate-500 ml-auto">12, 26, 9</span>
                </div>
                <div style={{ height: 200 }}>
                  <ResponsiveContainer>
                    <ComposedChart data={chartDataWithIndicators} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                      <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 10 }} />
                      <YAxis tick={{ fill: '#64748b', fontSize: 10 }} />
                      <Tooltip contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #334155', borderRadius: '8px' }} />
                      <Bar dataKey="histogram" fill="#3b82f6" opacity={0.5} />
                      <Line type="monotone" dataKey="macd" stroke="#22d3ee" dot={false} strokeWidth={2} />
                      <Line type="monotone" dataKey="signal" stroke="#f97316" dot={false} strokeWidth={2} />
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
                <div className="flex justify-center gap-6 mt-3 text-xs">
                  <span className="text-cyan-400">● MACD Line</span>
                  <span className="text-orange-400">● Signal Line</span>
                  <span className="text-blue-400">● Histogram</span>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Sentiment Analysis Section */}
        {data.length > 0 && (
          <div className="mt-6 panel p-6">
            <div className="flex items-center gap-2 mb-4">
              <TrendingUp className="w-5 h-5 text-emerald-400" />
              <h3 className="text-lg font-semibold text-slate-100">Sentiment Analysis</h3>
              <span className="text-xs text-slate-500 ml-auto">News & Social Media Sentiment for {selectedCompanyName || selectedSymbol}</span>
            </div>
            
            {sentimentData.length > 0 ? (
              <>
                <div style={{ height: 200 }}>
                  <ResponsiveContainer>
                    <AreaChart data={sentimentData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                      <defs>
                        <linearGradient id="colorSentiment" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                          <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                      <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 10 }} />
                      <YAxis domain={[0, 100]} tick={{ fill: '#64748b', fontSize: 10 }} />
                      <Tooltip 
                        contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #334155', borderRadius: '8px' }}
                        content={({ active, payload, label }) => {
                          if (!active || !payload || !payload.length) return null;
                          const d = payload[0]?.payload;
                          return (
                            <div className="bg-slate-900 border border-slate-700 rounded-lg p-3 shadow-xl">
                              <p className="text-slate-300 text-sm mb-1">{label}</p>
                              <p className="text-emerald-400 font-semibold">
                                Sentiment: {d?.sentiment?.toFixed(1)}%
                              </p>
                              {d?.intensity !== undefined && (
                                <p className="text-slate-400 text-xs">
                                  Intensity: {d.intensity?.toFixed(2)}
                                </p>
                              )}
                            </div>
                          );
                        }}
                      />
                      <Area type="monotone" dataKey="sentiment" stroke="#10b981" fillOpacity={1} fill="url(#colorSentiment)" strokeWidth={2} name="Sentiment Score" />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
                <div className="flex justify-center gap-6 mt-3 text-xs">
                  <span className="text-emerald-400">● Sentiment Score (0-100)</span>
                  <span className="text-slate-500">• 50 = Neutral, &gt;50 = Positive, &lt;50 = Negative</span>
                </div>
              </>
            ) : (
              <div className="flex items-center justify-center h-48 text-slate-500">
                <div className="text-center">
                  <Activity className="w-10 h-10 mx-auto mb-2 opacity-50" />
                  <p>No sentiment data available for this stock</p>
                  <p className="text-xs mt-1">Sentiment data requires news articles in the database</p>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default StockAnalysis;