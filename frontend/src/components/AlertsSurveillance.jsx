import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';
import ApiService from '../services/api';
import { 
  Bell, 
  AlertTriangle, 
  TrendingUp, 
  TrendingDown, 
  Volume2, 
  Newspaper,
  Filter,
  Clock,
  RefreshCw,
  Sparkles,
  ChevronDown,
  ChevronRight,
  ChevronLeft,
  Search,
  Download,
  BarChart3,
  Activity,
  Eye,
  X
} from 'lucide-react';

/**
 * AlertsSurveillance Component
 * 
 * A comprehensive alerts and market surveillance page featuring:
 * - Real-time alerts feed with filtering by volume/news/price anomalies
 * - Google-style pagination (8 alerts per page)
 * - AI-powered alert explanations
 * - Export functionality
 * 
 * DATA SOURCES (from historical_data.csv):
 * - Volume anomalies: VOLUME_Anomaly column
 * - Price anomalies: VARIATION_ANOMALY column
 * - News anomalies: VARIATION_ANOMALY_POST_NEWS, VARIATION_ANOMALY_PRE_NEWS,
 *                   VOLUME_ANOMALY_POST_NEWS, VOLUME_ANOMALY_PRE_NEWS columns
 *
 */

const ALERTS_PER_PAGE = 8;

const AlertsSurveillance = () => {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [alerts, setAlerts] = useState([]);
  const [filteredAlerts, setFilteredAlerts] = useState([]);
  const [selectedFilter, setSelectedFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedAlert, setSelectedAlert] = useState(null);
  const [showExplanation, setShowExplanation] = useState(false);
  const [explanation, setExplanation] = useState('');
  const [loadingExplanation, setLoadingExplanation] = useState(false);
  const [error, setError] = useState(null);
  const [lastRefresh, setLastRefresh] = useState(new Date());
  
  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);

  // Fetch alerts data
  const fetchAlerts = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Fetch alerts directly from the alerts endpoint with higher limit
      const alertsResp = await ApiService.request('/market-overview/alerts?limit=500', { method: 'GET' });
      let allAlerts = [];
      
      // Process alerts from API
      if (alertsResp && Array.isArray(alertsResp)) {
        allAlerts = alertsResp.map((alert, idx) => ({
          id: alert.id || `alert-${idx}`,
          type: alert.type || 'price',
          subtype: alert.subtype || null,
          symbol: alert.symbol || alert.stock || '',
          code: alert.code || '',
          name: alert.symbol || alert.name || '',
          message: alert.message || '',
          severity: alert.severity || 'medium',
          timestamp: alert.timestamp || alert.date || new Date().toISOString(),
          date: alert.date || '',
          value: alert.value || null,
          change: alert.change || null,
          score: alert.score || null,
        }));
      }

      // Sort by timestamp (newest first)
      allAlerts.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
      
      setAlerts(allAlerts);
      setFilteredAlerts(allAlerts);
      setCurrentPage(1); // Reset to first page on refresh
      setLastRefresh(new Date());
    } catch (err) {
      console.error('Failed to fetch alerts:', err);
      setError('Failed to load alerts. Please try again.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (user) {
      fetchAlerts();
    }
  }, [user, fetchAlerts]);

  // Filter alerts based on selected filter and search query
  useEffect(() => {
    let filtered = alerts;
    
    // Apply type filter
    if (selectedFilter !== 'all') {
      filtered = filtered.filter(alert => alert.type === selectedFilter);
    }
    
    // Apply search query
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(alert => 
        alert.symbol.toLowerCase().includes(query) ||
        alert.name.toLowerCase().includes(query) ||
        alert.message.toLowerCase().includes(query) ||
        (alert.code && alert.code.toLowerCase().includes(query))
      );
    }
    
    setFilteredAlerts(filtered);
    setCurrentPage(1); // Reset to first page when filters change
  }, [alerts, selectedFilter, searchQuery]);

  // Pagination calculations
  const totalPages = Math.ceil(filteredAlerts.length / ALERTS_PER_PAGE);
  const startIndex = (currentPage - 1) * ALERTS_PER_PAGE;
  const endIndex = startIndex + ALERTS_PER_PAGE;
  const currentAlerts = filteredAlerts.slice(startIndex, endIndex);

  // Generate page numbers for pagination (Google-style)
  const getPageNumbers = () => {
    const pages = [];
    const maxVisiblePages = 7;
    
    if (totalPages <= maxVisiblePages) {
      for (let i = 1; i <= totalPages; i++) {
        pages.push(i);
      }
    } else {
      // Always show first page
      pages.push(1);
      
      if (currentPage > 4) {
        pages.push('...');
      }
      
      // Show pages around current page
      const start = Math.max(2, currentPage - 2);
      const end = Math.min(totalPages - 1, currentPage + 2);
      
      for (let i = start; i <= end; i++) {
        if (!pages.includes(i)) {
          pages.push(i);
        }
      }
      
      if (currentPage < totalPages - 3) {
        pages.push('...');
      }
      
      // Always show last page
      if (!pages.includes(totalPages)) {
        pages.push(totalPages);
      }
    }
    
    return pages;
  };

  // Get AI explanation for an alert
  const handleGetExplanation = async (alert) => {
    setSelectedAlert(alert);
    setShowExplanation(true);
    setLoadingExplanation(true);
    
    try {
      // Extract symbol and date
      const symbol = alert.symbol || alert.code;
      const dateStr = alert.date || (alert.timestamp ? alert.timestamp.split('T')[0] : '');
      
      console.log('Requesting explanation for:', { symbol, date: dateStr, alert });
      
      // Use the explain agent API endpoint
      const response = await ApiService.explainStock(symbol, dateStr);
      
      console.log('Explanation response:', response);
      
      // Extract explanation from response
      let explanationText = '';
      if (typeof response === 'string') {
        explanationText = response;
      } else if (response && response.explanation) {
        explanationText = response.explanation;
      } else if (response && response.message) {
        explanationText = response.message;
      } else if (response && response.data) {
        explanationText = typeof response.data === 'string' ? response.data : JSON.stringify(response.data, null, 2);
      } else {
        explanationText = JSON.stringify(response, null, 2);
      }
      
      setExplanation(explanationText || 'Unable to generate explanation at this time.');
    } catch (err) {
      console.error('Failed to get explanation:', err);
      console.error('Error details:', { message: err.message, stack: err.stack });
      // Provide a fallback explanation
      setExplanation(generateFallbackExplanation(alert));
    } finally {
      setLoadingExplanation(false);
    }
  };

  // Fallback explanation when AI is unavailable
  const generateFallbackExplanation = (alert) => {
    const explanations = {
      volume: `Volume anomaly detected for ${alert.symbol}. This could indicate:
• Increased institutional activity
• Breaking news or market rumors
• Technical breakout or breakdown
• Sector rotation or rebalancing

Consider monitoring news sources and checking related stocks for similar patterns.`,
      news: `News-related movement for ${alert.symbol}. ${alert.subtype === 'leakage' || alert.subtype === 'volume_leakage' ? 
`⚠️ POTENTIAL INFORMATION LEAKAGE DETECTED

This alert indicates unusual activity BEFORE news was released, which may suggest:
• Early access to information
• Insider trading concerns
• Rumor-driven speculation

This warrants closer regulatory attention.` :
`Possible causes:
• Corporate announcements or earnings
• Regulatory changes
• Industry developments
• Analyst upgrades/downgrades

Review recent news and consider the fundamental impact before making decisions.`}`,
      price: `Price anomaly detected for ${alert.symbol}. This may be due to:
• Market sentiment shift
• Technical pattern completion
• Liquidity conditions
• External market factors

Verify the movement with volume data and consider your risk tolerance.`,
    };
    
    return explanations[alert.type] || explanations.price;
  };

  // Export alerts to CSV
  const handleExportAlerts = () => {
    const csvContent = [
      ['Timestamp', 'Symbol', 'Code', 'Type', 'Subtype', 'Severity', 'Message', 'Value', 'Change', 'Score'].join(','),
      ...filteredAlerts.map(alert => [
        alert.timestamp,
        alert.symbol,
        alert.code || '',
        alert.type,
        alert.subtype || '',
        alert.severity,
        `"${alert.message.replace(/"/g, '""')}"`,
        alert.value || '',
        alert.change || '',
        alert.score || ''
      ].join(','))
    ].join('\n');
    
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `alerts_${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
  };

  // Get alert type icon
  const getAlertIcon = (type, subtype) => {
    switch (type) {
      case 'volume': return <Volume2 className="w-5 h-5" />;
      case 'news': 
        if (subtype === 'leakage' || subtype === 'volume_leakage') {
          return <AlertTriangle className="w-5 h-5" />;
        }
        return <Newspaper className="w-5 h-5" />;
      case 'price': return <Activity className="w-5 h-5" />;
      default: return <AlertTriangle className="w-5 h-5" />;
    }
  };

  // Get severity color
  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'high': return 'text-rose-400 bg-rose-500/20 border-rose-500/50';
      case 'medium': return 'text-amber-400 bg-amber-500/20 border-amber-500/50';
      case 'low': return 'text-emerald-400 bg-emerald-500/20 border-emerald-500/50';
      default: return 'text-slate-400 bg-slate-500/20 border-slate-500/50';
    }
  };

  // Get type color
  const getTypeColor = (type) => {
    switch (type) {
      case 'volume': return 'text-purple-400 bg-purple-500/20';
      case 'news': return 'text-blue-400 bg-blue-500/20';
      case 'price': return 'text-cyan-400 bg-cyan-500/20';
      default: return 'text-slate-400 bg-slate-500/20';
    }
  };

  // Get subtype badge
  const getSubtypeBadge = (subtype) => {
    if (!subtype) return null;
    
    const badges = {
      'reaction': { label: 'Reaction', color: 'text-emerald-400 bg-emerald-500/20' },
      'leakage': { label: '⚠️ Leakage', color: 'text-rose-400 bg-rose-500/20' },
      'volume_reaction': { label: 'Vol. Reaction', color: 'text-emerald-400 bg-emerald-500/20' },
      'volume_leakage': { label: '⚠️ Vol. Leakage', color: 'text-rose-400 bg-rose-500/20' },

    };
    
    const badge = badges[subtype];
    if (!badge) return null;
    
    return (
      <span className={`text-xs px-2 py-0.5 rounded-full ${badge.color}`}>
        {badge.label}
      </span>
    );
  };

  // Alert Statistics
  const stats = {
    total: alerts.length,
    volume: alerts.filter(a => a.type === 'volume').length,
    news: alerts.filter(a => a.type === 'news').length,
    price: alerts.filter(a => a.type === 'price').length,
    highSeverity: alerts.filter(a => a.severity === 'high').length,
  };

  if (loading && alerts.length === 0) {
    return (
      <div className="min-h-screen app-shell flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-cyan-400 mx-auto mb-4"></div>
          <p className="text-slate-400">Loading alerts...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen app-shell py-6">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-3">
              <Bell className="w-7 h-7 text-amber-400" />
              Alerts & Surveillance
            </h1>
            <p className="text-slate-400 mt-1">Monitor market anomalies and real-time alerts</p>
          </div>
          <div className="flex items-center gap-3 mt-4 md:mt-0">
            <span className="text-xs text-slate-500 flex items-center gap-1">
              <Clock className="w-3 h-3" />
              Last updated: {lastRefresh.toLocaleTimeString()}
            </span>
            <button
              onClick={fetchAlerts}
              disabled={loading}
              className="btn-secondary flex items-center gap-2"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-rose-500/10 border border-rose-500/50 rounded-lg text-rose-400">
            {error}
          </div>
        )}

        {/* Statistics Cards */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
          <div className="panel p-4 text-center cursor-pointer hover:bg-slate-800/50 transition-colors" onClick={() => setSelectedFilter('all')}>
            <div className="text-2xl font-bold text-slate-100">{stats.total}</div>
            <div className="text-xs text-slate-400 uppercase">Total Alerts</div>
          </div>
          <div className="panel p-4 text-center cursor-pointer hover:bg-slate-800/50 transition-colors" onClick={() => setSelectedFilter('volume')}>
            <div className="text-2xl font-bold text-purple-400">{stats.volume}</div>
            <div className="text-xs text-slate-400 uppercase">Volume</div>
          </div>
          <div className="panel p-4 text-center cursor-pointer hover:bg-slate-800/50 transition-colors" onClick={() => setSelectedFilter('price')}>
            <div className="text-2xl font-bold text-cyan-400">{stats.price}</div>
            <div className="text-xs text-slate-400 uppercase">Price</div>
          </div>
          <div className="panel p-4 text-center cursor-pointer hover:bg-slate-800/50 transition-colors" onClick={() => setSelectedFilter('news')}>
            <div className="text-2xl font-bold text-blue-400">{stats.news}</div>
            <div className="text-xs text-slate-400 uppercase">News</div>
          </div>
          <div className="panel p-4 text-center">
            <div className="text-2xl font-bold text-rose-400">{stats.highSeverity}</div>
            <div className="text-xs text-slate-400 uppercase">High Priority</div>
          </div>
        </div>

        {/* Filters and Search */}
        <div className="panel p-4 mb-6">
          <div className="flex flex-col md:flex-row gap-4">
            {/* Filter Buttons */}
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-slate-400" />
              <div className="flex gap-1 bg-slate-800/50 p-1 rounded-lg">
                {[
                  { id: 'all', label: 'All', icon: BarChart3 },
                  { id: 'volume', label: 'Volume', icon: Volume2 },
                  { id: 'price', label: 'Price', icon: Activity },
                  { id: 'news', label: 'News', icon: Newspaper },
                ].map((filter) => (
                  <button
                    key={filter.id}
                    onClick={() => setSelectedFilter(filter.id)}
                    className={`flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition-all ${
                      selectedFilter === filter.id
                        ? 'bg-cyan-500 text-slate-900 shadow-lg shadow-cyan-500/25'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-700'
                    }`}
                  >
                    <filter.icon className="w-4 h-4" />
                    {filter.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Search */}
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input
                type="text"
                placeholder="Search by symbol, name, or message..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="input-field pl-10 w-full"
              />
            </div>

            {/* Export Button */}
            <button
              onClick={handleExportAlerts}
              className="btn-secondary flex items-center gap-2"
            >
              <Download className="w-4 h-4" />
              Export CSV
            </button>
          </div>
        </div>

        {/* Alerts Feed */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Alerts List */}
          <div className="lg:col-span-2">
            <div className="panel">
              <div className="p-4 border-b border-slate-800/70">
                <h3 className="text-lg font-semibold text-slate-100 flex items-center gap-2">
                  <AlertTriangle className="w-5 h-5 text-amber-400" />
                  Alert Feed
                  <span className="ml-auto text-sm text-slate-400">
                    Showing {filteredAlerts.length > 0 ? startIndex + 1 : 0}-{Math.min(endIndex, filteredAlerts.length)} of {filteredAlerts.length} alerts
                  </span>
                </h3>
              </div>
              
              {/* Alerts List */}
              <div className="min-h-[500px]">
                {currentAlerts.length === 0 ? (
                  <div className="p-8 text-center text-slate-500">
                    <Bell className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p>No alerts match your filters</p>
                  </div>
                ) : (
                  currentAlerts.map((alert) => (
                    <div
                      key={alert.id}
                      className="p-4 border-b border-slate-800/50 hover:bg-slate-800/30 transition-colors"
                    >
                      <div className="flex items-start gap-3">
                        <div className={`p-2 rounded-lg ${getSeverityColor(alert.severity)}`}>
                          {getAlertIcon(alert.type, alert.subtype)}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1 flex-wrap">
                            <span className="font-semibold text-slate-100">{alert.symbol}</span>
                            {alert.code && alert.code !== alert.symbol && (
                              <span className="text-xs text-slate-500">({alert.code})</span>
                            )}
                            <span className={`text-xs px-2 py-0.5 rounded-full ${getTypeColor(alert.type)}`}>
                              {alert.type}
                            </span>
                            {getSubtypeBadge(alert.subtype)}
                          </div>
                          <p className="text-sm text-slate-300">{alert.message}</p>
                          <div className="flex items-center gap-4 mt-2 text-xs text-slate-500 flex-wrap">
                            <span className="flex items-center gap-1">
                              <Clock className="w-3 h-3" />
                              {alert.date || new Date(alert.timestamp).toLocaleDateString()}
                            </span>
                            {alert.value && (
                              <span>Price: {alert.value.toFixed(2)} TND</span>
                            )}
                            {alert.change != null && (
                              <span className={alert.change >= 0 ? 'text-emerald-400' : 'text-rose-400'}>
                                {alert.change >= 0 ? '+' : ''}{alert.change.toFixed(2)}%
                              </span>
                            )}
                            {alert.score != null && (
                              <span className="text-slate-400">Z: {alert.score.toFixed(1)}</span>
                            )}
                          </div>
                        </div>
                        <button
                          onClick={() => handleGetExplanation(alert)}
                          className="p-2 rounded-lg bg-slate-800/50 hover:bg-cyan-500/20 text-slate-400 hover:text-cyan-400 transition-colors"
                          title="AI Explain"
                        >
                          <Sparkles className="w-5 h-5" />
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="p-4 border-t border-slate-800/70 flex items-center justify-center gap-2">
                  {/* Previous Button */}
                  <button
                    onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                    disabled={currentPage === 1}
                    className={`p-2 rounded-lg transition-colors ${
                      currentPage === 1
                        ? 'text-slate-600 cursor-not-allowed'
                        : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
                    }`}
                  >
                    <ChevronLeft className="w-5 h-5" />
                  </button>
                  
                  {/* Page Numbers */}
                  <div className="flex items-center gap-1">
                    {getPageNumbers().map((page, idx) => (
                      page === '...' ? (
                        <span key={`ellipsis-${idx}`} className="px-2 text-slate-500">...</span>
                      ) : (
                        <button
                          key={page}
                          onClick={() => setCurrentPage(page)}
                          className={`min-w-[36px] h-9 px-3 rounded-lg text-sm font-medium transition-colors ${
                            currentPage === page
                              ? 'bg-cyan-500 text-slate-900 shadow-lg shadow-cyan-500/25'
                              : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
                          }`}
                        >
                          {page}
                        </button>
                      )
                    ))}
                  </div>
                  
                  {/* Next Button */}
                  <button
                    onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                    disabled={currentPage === totalPages}
                    className={`p-2 rounded-lg transition-colors ${
                      currentPage === totalPages
                        ? 'text-slate-600 cursor-not-allowed'
                        : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
                    }`}
                  >
                    <ChevronRight className="w-5 h-5" />
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Side Panel - AI Explanation or Summary */}
          <div className="lg:col-span-1">
            {showExplanation && selectedAlert ? (
              <div className="panel p-4 sticky top-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold text-slate-100 flex items-center gap-2">
                    <Sparkles className="w-5 h-5 text-cyan-400" />
                    AI Analysis
                  </h3>
                  <button
                    onClick={() => setShowExplanation(false)}
                    className="text-slate-400 hover:text-slate-200"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>
                
                <div className="mb-4 p-3 bg-slate-800/50 rounded-lg">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <span className="font-semibold text-slate-100">{selectedAlert.symbol}</span>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${getTypeColor(selectedAlert.type)}`}>
                      {selectedAlert.type}
                    </span>
                    {getSubtypeBadge(selectedAlert.subtype)}
                  </div>
                  <p className="text-sm text-slate-400">{selectedAlert.message}</p>
                </div>
                
                {loadingExplanation ? (
                  <div className="text-center py-8">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-cyan-400 mx-auto mb-4"></div>
                    <p className="text-slate-400 text-sm">Analyzing alert...</p>
                  </div>
                ) : (
                  <div className="text-sm text-slate-300 whitespace-pre-wrap leading-relaxed">
                    {explanation}
                  </div>
                )}
              </div>
            ) : (
              <div className="panel p-4 sticky top-6">
                <h3 className="text-lg font-semibold text-slate-100 flex items-center gap-2 mb-4">
                  <Eye className="w-5 h-5 text-emerald-400" />
                  Surveillance Summary
                </h3>
                
                <div className="space-y-4">
                  <div className="p-3 bg-slate-800/50 rounded-lg">
                    <div className="text-xs text-slate-400 uppercase mb-1">Alert Types</div>
                    <div className="space-y-1 mt-2">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-purple-400 flex items-center gap-2">
                          <Volume2 className="w-4 h-4" /> Volume
                        </span>
                        <span className="text-slate-300">{stats.volume}</span>
                      </div>
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-cyan-400 flex items-center gap-2">
                          <Activity className="w-4 h-4" /> Price
                        </span>
                        <span className="text-slate-300">{stats.price}</span>
                      </div>
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-blue-400 flex items-center gap-2">
                          <Newspaper className="w-4 h-4" /> News
                        </span>
                        <span className="text-slate-300">{stats.news}</span>
                      </div>
                    </div>
                  </div>
                  
                  <div className="p-3 bg-slate-800/50 rounded-lg">
                    <div className="text-xs text-slate-400 uppercase mb-1">Priority Items</div>
                    <div className="text-rose-400 font-medium">
                      {stats.highSeverity} high-severity alerts
                    </div>
                  </div>
                  
                  <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg">
                    <div className="text-xs text-amber-400 uppercase mb-1">⚠️ Leakage Alerts</div>
                    <div className="text-slate-300 text-sm">
                      {alerts.filter(a => a.subtype === 'leakage' || a.subtype === 'volume_leakage').length} potential information leakage events detected
                    </div>
                  </div>
                  
                  <div className="border-t border-slate-700/50 pt-4">
                    <p className="text-xs text-slate-500">
                      Click the <Sparkles className="w-3 h-3 inline text-cyan-400" /> icon on any alert 
                      to get an AI-powered analysis and explanation.
                    </p>
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

export default AlertsSurveillance;