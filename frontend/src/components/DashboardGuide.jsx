import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { 
  BookOpen, 
  TrendingUp, 
  TrendingDown,
  BarChart3, 
  LineChart, 
  Bell, 
  User, 
  DollarSign,
  MessageSquare,
  ChevronRight,
  ChevronDown,
  Target,
  PieChart,
  Activity,
  AlertTriangle,
  ShoppingCart,
  Eye,
  X,
  Shield,
  CheckCircle,
  Edit3,
  Trash2,
  Flag,
  Plus,
} from 'lucide-react';

/**
 * DashboardGuide Component
 * 
 * A comprehensive guide explaining all features of TuniTrAide.
 * Accessible from the Footer and Profile sections.
 */
const DashboardGuide = ({ isModal = false, onClose = null }) => {
  const [expandedSection, setExpandedSection] = useState('getting-started');

  const toggleSection = (sectionId) => {
    setExpandedSection(expandedSection === sectionId ? null : sectionId);
  };

  const sections = [
    {
      id: 'getting-started',
      title: 'Getting Started',
      icon: BookOpen,
      color: 'text-cyan-400',
      content: (
        <div className="space-y-4">
          <p className="text-slate-300">
            Welcome to TuniTrAide! This AI-powered platform provides comprehensive tools for analyzing 
            the Tunisian Stock Exchange (BVMT) and managing your investment portfolio.
          </p>
          <div className="bg-slate-800/50 rounded-lg p-4">
            <h4 className="font-medium text-slate-100 mb-2">Quick Start Steps:</h4>
            <ol className="list-decimal list-inside space-y-2 text-slate-400">
              <li>Visit the <span className="text-cyan-400">Market Overview</span> to see the current market state</li>
              <li>Use <span className="text-cyan-400">Stock Analysis</span> to research specific stocks</li>
              <li>Create your portfolio in <span className="text-cyan-400">My Portfolio</span></li>
              <li>Execute trades using the <span className="text-cyan-400">Trading Platform</span></li>
              <li>Set up <span className="text-cyan-400">Alerts</span> to stay informed of market movements</li>
            </ol>
          </div>
        </div>
      )
    },
    {
      id: 'market-overview',
      title: 'Market Overview',
      icon: TrendingUp,
      color: 'text-emerald-400',
      content: (
        <div className="space-y-4">
          <p className="text-slate-300">
            The Market Overview page provides a real-time snapshot of the Tunisian stock market.
          </p>
          
          <div className="space-y-3">
            <div className="bg-slate-800/50 rounded-lg p-4">
              <h4 className="font-medium text-slate-100 flex items-center gap-2 mb-2">
                <BarChart3 className="w-4 h-4 text-cyan-400" />
                TUNINDEX Chart
              </h4>
              <p className="text-slate-400 text-sm">
                Displays the main market index (TUNINDEX) or the top 20 companies index (TUNINDEX20). 
                Toggle between them using the buttons above the chart. The chart shows 60 days of historical data.
              </p>
            </div>

            <div className="bg-slate-800/50 rounded-lg p-4">
              <h4 className="font-medium text-slate-100 flex items-center gap-2 mb-2">
                <Activity className="w-4 h-4 text-emerald-400" />
                Market Sentiment Gauge
              </h4>
              <p className="text-slate-400 text-sm">
                A composite score (0-100) indicating overall market sentiment. Components include:
              </p>
              <ul className="list-disc list-inside text-slate-400 text-sm mt-2 space-y-1">
                <li><span className="text-cyan-400">Direction & Breadth</span> - Market trend direction</li>
                <li><span className="text-blue-400">Liquidity Score</span> - Trading volume health</li>
                <li><span className="text-purple-400">Intensity Score</span> - Price movement strength</li>
                <li><span className="text-amber-400">News Score</span> - Sentiment from news analysis</li>
              </ul>
            </div>

            <div className="bg-slate-800/50 rounded-lg p-4">
              <h4 className="font-medium text-slate-100 flex items-center gap-2 mb-2">
                <TrendingUp className="w-4 h-4 text-emerald-400" />
                <TrendingDown className="w-4 h-4 text-rose-400" />
                Top Gainers & Losers
              </h4>
              <p className="text-slate-400 text-sm">
                Shows the 5 best and worst performing stocks of the day with their price changes.
              </p>
            </div>

            <div className="bg-slate-800/50 rounded-lg p-4">
              <h4 className="font-medium text-slate-100 flex items-center gap-2 mb-2">
                <AlertTriangle className="w-4 h-4 text-amber-400" />
                Market Alerts
              </h4>
              <p className="text-slate-400 text-sm">
                Automatic alerts for unusual market activity including volume anomalies and price spikes.
              </p>
            </div>
          </div>
        </div>
      )
    },
    {
      id: 'stock-analysis',
      title: 'Stock Analysis',
      icon: LineChart,
      color: 'text-blue-400',
      content: (
        <div className="space-y-4">
          <p className="text-slate-300">
            Detailed analysis tools for individual stocks listed on the BVMT.
          </p>
          
          <div className="space-y-3">
            <div className="bg-slate-800/50 rounded-lg p-4">
              <h4 className="font-medium text-slate-100 mb-2">Stock Search</h4>
              <p className="text-slate-400 text-sm">
                Search for any stock by name or code. The search supports partial matching and shows 
                current prices directly in the dropdown.
              </p>
            </div>

            <div className="bg-slate-800/50 rounded-lg p-4">
              <h4 className="font-medium text-slate-100 mb-2">Price Charts</h4>
              <p className="text-slate-400 text-sm">
                Interactive price charts with multiple time ranges. View historical price movements, 
                volume data, and technical indicators.
              </p>
            </div>

            <div className="bg-slate-800/50 rounded-lg p-4">
              <h4 className="font-medium text-slate-100 mb-2">AI-Powered Insights</h4>
              <p className="text-slate-400 text-sm">
                Get AI-generated explanations and analysis for stock movements. The system analyzes 
                price patterns, volume changes, and news sentiment.
              </p>
            </div>

            <div className="bg-slate-800/50 rounded-lg p-4">
              <h4 className="font-medium text-slate-100 mb-2">Forecast Data</h4>
              <p className="text-slate-400 text-sm">
                View 5-day price forecasts generated by machine learning models (when available).
              </p>
            </div>
          </div>
        </div>
      )
    },
    {
      id: 'portfolio',
      title: 'My Portfolio',
      icon: PieChart,
      color: 'text-purple-400',
      content: (
        <div className="space-y-4">
          <p className="text-slate-300">
            Manage your investment portfolio and track your performance.
          </p>
          
          <div className="space-y-3">
            <div className="bg-slate-800/50 rounded-lg p-4">
              <h4 className="font-medium text-slate-100 flex items-center gap-2 mb-2">
                <Eye className="w-4 h-4" />
                Overview Tab
              </h4>
              <p className="text-slate-400 text-sm">
                See your total portfolio value, cash balance, invested amount, and P&L at a glance. 
                Key metrics include Total Return, Realized P&L, and Unrealized P&L.
              </p>
            </div>

            <div className="bg-slate-800/50 rounded-lg p-4">
              <h4 className="font-medium text-slate-100 flex items-center gap-2 mb-2">
                <BarChart3 className="w-4 h-4" />
                Positions Tab
              </h4>
              <p className="text-slate-400 text-sm">
                View all your current holdings with details including quantity, average buy price, 
                current price, market value, and P&L for each position.
              </p>
            </div>

            <div className="bg-slate-800/50 rounded-lg p-4">
              <h4 className="font-medium text-slate-100 flex items-center gap-2 mb-2">
                <PieChart className="w-4 h-4" />
                Distribution Tab
              </h4>
              <p className="text-slate-400 text-sm">
                Visualize your portfolio allocation with an interactive pie chart. Holdings under 2% 
                are grouped as "Others" for clarity.
              </p>
            </div>

            <div className="bg-slate-800/50 rounded-lg p-4">
              <h4 className="font-medium text-slate-100 flex items-center gap-2 mb-2">
                <TrendingUp className="w-4 h-4" />
                Performance Tab
              </h4>
              <p className="text-slate-400 text-sm">
                Track your portfolio value over time with an equity curve chart showing your 
                investment performance history.
              </p>
            </div>
          </div>
        </div>
      )
    },
    {
      id: 'trading',
      title: 'Trading Platform',
      icon: ShoppingCart,
      color: 'text-emerald-400',
      content: (
        <div className="space-y-4">
          <p className="text-slate-300">
            Execute buy and sell orders for stocks in your portfolio.
          </p>
          
          <div className="space-y-3">
            <div className="bg-slate-800/50 rounded-lg p-4">
              <h4 className="font-medium text-slate-100 mb-2">How to Trade:</h4>
              <ol className="list-decimal list-inside space-y-2 text-slate-400 text-sm">
                <li>Select your portfolio from the dropdown</li>
                <li>Search and select a stock to trade</li>
                <li>Choose order type: <span className="text-emerald-400">BUY</span> or <span className="text-rose-400">SELL</span></li>
                <li>Enter the quantity (number of shares)</li>
                <li>Enter the price per share or use the current market price</li>
                <li>Review the total value and click "Execute Order"</li>
              </ol>
            </div>

            <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-4">
              <h4 className="font-medium text-amber-400 mb-2">⚠️ Important Notes:</h4>
              <ul className="list-disc list-inside text-slate-400 text-sm space-y-1">
                <li>This is a simulated trading platform for educational purposes</li>
                <li>Ensure you have sufficient cash balance before buying</li>
                <li>You can only sell shares you currently own</li>
                <li>All transactions are recorded and affect your portfolio metrics</li>
              </ul>
            </div>
          </div>
        </div>
      )
    },
    {
      id: 'alerts',
      title: 'Alerts & Surveillance',
      icon: Bell,
      color: 'text-amber-400',
      content: (
        <div className="space-y-4">
          <p className="text-slate-300">
            Set up custom alerts and monitor market surveillance data.
          </p>
          
          <div className="space-y-3">
            <div className="bg-slate-800/50 rounded-lg p-4">
              <h4 className="font-medium text-slate-100 mb-2">Alert Types:</h4>
              <ul className="list-disc list-inside text-slate-400 text-sm space-y-1">
                <li><span className="text-emerald-400">Price Alerts</span> - Triggered when a stock reaches your target price</li>
                <li><span className="text-amber-400">Volume Alerts</span> - Unusual trading volume detected</li>
                <li><span className="text-rose-400">Anomaly Alerts</span> - AI-detected unusual market behavior</li>
              </ul>
            </div>

            <div className="bg-slate-800/50 rounded-lg p-4">
              <h4 className="font-medium text-slate-100 mb-2">Surveillance Data:</h4>
              <p className="text-slate-400 text-sm">
                The system automatically monitors all stocks for anomalies and unusual patterns. 
                High, medium, and low severity alerts are color-coded for quick identification.
              </p>
            </div>
          </div>
        </div>
      )
    },
    {
      id: 'regulator',
      title: 'Regulator Dashboard',
      icon: Shield,
      color: 'text-amber-400',
      content: (
        <div className="space-y-4">
          <p className="text-slate-300">
            The Regulator Dashboard is available exclusively to users with the <span className="text-amber-400">regulator</span> role.
            It provides tools for overseeing all market transactions and managing stock anomalies.
          </p>

          <div className="space-y-3">
            <div className="bg-slate-800/50 rounded-lg p-4">
              <h4 className="font-medium text-slate-100 flex items-center gap-2 mb-2">
                <Flag className="w-4 h-4 text-rose-400" />
                Transactions Tab
              </h4>
              <p className="text-slate-400 text-sm mb-2">
                View all trades across every user account. Filter between <span className="text-cyan-400">All</span> and <span className="text-rose-400">Suspicious Only</span> modes.
              </p>
              <ul className="list-disc list-inside text-slate-400 text-sm space-y-1">
                <li><span className="text-rose-400">Flag</span> — Mark any transaction as suspicious and provide a reason</li>
                <li><span className="text-emerald-400">Unflag</span> — Remove the suspicious flag from a transaction</li>
                <li><span className="text-cyan-400">Search</span> — Filter by stock code, name, or user ID</li>
                <li><span className="text-cyan-400">Export</span> — Download all filtered transactions as CSV</li>
              </ul>
            </div>

            <div className="bg-slate-800/50 rounded-lg p-4">
              <h4 className="font-medium text-slate-100 flex items-center gap-2 mb-2">
                <MessageSquare className="w-4 h-4 text-amber-400" />
                Suspicious Trade Notes
              </h4>
              <p className="text-slate-400 text-sm">
                When viewing in <span className="text-rose-400">Suspicious Only</span> mode, click on any flagged transaction 
                row or its <span className="text-slate-200">Note</span> button to expand and read the reason it was flagged, 
                along with who flagged it and when.
              </p>
            </div>

            <div className="bg-slate-800/50 rounded-lg p-4">
              <h4 className="font-medium text-slate-100 flex items-center gap-2 mb-2">
                <Activity className="w-4 h-4 text-cyan-400" />
                Stock Anomalies Tab
              </h4>
              <p className="text-slate-400 text-sm mb-2">
                Manage anomaly data detected from historical market data. Anomalies include volume spikes,
                unusual price variations, and pre/post-news irregularities. Changes are persisted directly to the CSV file.
              </p>
              <ul className="list-disc list-inside text-slate-400 text-sm space-y-1">
                <li>
                  <span className="text-emerald-400 inline-flex items-center gap-1"><CheckCircle className="w-3 h-3 inline" /> Validate</span> — Confirm an anomaly is legitimate and optionally add a note
                </li>
                <li>
                  <span className="text-cyan-400 inline-flex items-center gap-1"><Plus className="w-3 h-3 inline" /> Add</span> — Flag a new anomaly by selecting a stock code and date from existing historical data
                </li>
                <li>
                  <span className="text-cyan-400 inline-flex items-center gap-1"><Edit3 className="w-3 h-3 inline" /> Edit</span> — Modify which anomaly types are flagged and update notes
                </li>
                <li>
                  <span className="text-rose-400 inline-flex items-center gap-1"><Trash2 className="w-3 h-3 inline" /> Delete</span> — Clear all anomaly flags for a specific stock and date
                </li>
              </ul>
            </div>

            <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-4">
              <h4 className="font-medium text-amber-400 mb-2">How Anomaly CRUD Works</h4>
              <ol className="list-decimal list-inside text-slate-400 text-sm space-y-1">
                <li>Navigate to the <span className="text-cyan-400">Stock Anomalies</span> tab</li>
                <li>Use the search field to filter by stock code</li>
                <li>Click <span className="text-cyan-400">Add Anomaly</span> to flag a new entry in the CSV</li>
                <li>Use <span className="text-cyan-400">Edit</span> to toggle individual anomaly flags</li>
                <li>Click <span className="text-emerald-400">Validate</span> to confirm an anomaly is real</li>
                <li>Use <span className="text-rose-400">Delete</span> to clear all flags (sets all to 0)</li>
              </ol>
            </div>
          </div>
        </div>
      )
    },
    {
      id: 'chatbot',
      title: 'AI Assistant (ChatBot)',
      icon: MessageSquare,
      color: 'text-cyan-400',
      content: (
        <div className="space-y-4">
          <p className="text-slate-300">
            Get instant help and market insights from our AI-powered assistant.
          </p>
          
          <div className="bg-slate-800/50 rounded-lg p-4">
            <h4 className="font-medium text-slate-100 mb-2">What you can ask:</h4>
            <ul className="list-disc list-inside text-slate-400 text-sm space-y-1">
              <li>Stock information and current prices</li>
              <li>Market trends and analysis</li>
              <li>Portfolio advice and recommendations</li>
              <li>Explanation of market movements</li>
              <li>Help with platform features</li>
            </ul>
          </div>

          <div className="bg-cyan-500/10 border border-cyan-500/30 rounded-lg p-4">
            <p className="text-cyan-300 text-sm">
              💡 <span className="font-medium">Tip:</span> Click the chat bubble icon in the bottom-right 
              corner of any page to open the AI assistant.
            </p>
          </div>
        </div>
      )
    },
    {
      id: 'profile',
      title: 'Profile & Settings',
      icon: User,
      color: 'text-slate-400',
      content: (
        <div className="space-y-4">
          <p className="text-slate-300">
            Manage your account settings and preferences.
          </p>
          
          <div className="space-y-3">
            <div className="bg-slate-800/50 rounded-lg p-4">
              <h4 className="font-medium text-slate-100 mb-2">Profile Tab</h4>
              <p className="text-slate-400 text-sm">
                Update your personal information including username, email, name, and bio.
              </p>
            </div>

            <div className="bg-slate-800/50 rounded-lg p-4">
              <h4 className="font-medium text-slate-100 mb-2">Security Tab</h4>
              <p className="text-slate-400 text-sm">
                Change your password and enable two-factor authentication for enhanced security.
              </p>
            </div>

            <div className="bg-slate-800/50 rounded-lg p-4">
              <h4 className="font-medium text-slate-100 mb-2">Notifications Tab</h4>
              <p className="text-slate-400 text-sm">
                Configure email and push notification preferences for alerts and updates.
              </p>
            </div>
          </div>
        </div>
      )
    }
  ];

  const content = (
    <div className={isModal ? "" : "min-h-screen app-shell py-6"}>
      <div className={isModal ? "" : "max-w-4xl mx-auto px-4 sm:px-6 lg:px-8"}>
        {/* Header */}
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-3">
              <BookOpen className="w-7 h-7 text-cyan-400" />
              Dashboard Guide
            </h1>
            <p className="text-slate-400 mt-1">
              Learn how to use all features of TuniTrAide
            </p>
          </div>
          {isModal && onClose && (
            <button
              onClick={onClose}
              className="p-2 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          )}
        </div>

        {/* Quick Navigation */}
        <div className="panel p-4 mb-6">
          <h3 className="text-sm font-medium text-slate-400 uppercase tracking-wider mb-3">Quick Navigation</h3>
          <div className="flex flex-wrap gap-2">
            {sections.map((section) => (
              <button
                key={section.id}
                onClick={() => {
                  setExpandedSection(section.id);
                  document.getElementById(section.id)?.scrollIntoView({ behavior: 'smooth' });
                }}
                className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors
                  ${expandedSection === section.id 
                    ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30' 
                    : 'bg-slate-800/50 text-slate-400 hover:bg-slate-800 hover:text-slate-200'
                  }`}
              >
                <section.icon className={`w-4 h-4 ${section.color}`} />
                {section.title}
              </button>
            ))}
          </div>
        </div>

        {/* Sections */}
        <div className="space-y-4">
          {sections.map((section) => (
            <div 
              key={section.id} 
              id={section.id}
              className="panel overflow-hidden"
            >
              <button
                onClick={() => toggleSection(section.id)}
                className="w-full flex items-center justify-between p-4 text-left hover:bg-slate-800/30 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-lg bg-slate-800/50`}>
                    <section.icon className={`w-5 h-5 ${section.color}`} />
                  </div>
                  <h2 className="text-lg font-semibold text-slate-100">{section.title}</h2>
                </div>
                {expandedSection === section.id ? (
                  <ChevronDown className="w-5 h-5 text-slate-400" />
                ) : (
                  <ChevronRight className="w-5 h-5 text-slate-400" />
                )}
              </button>
              
              {expandedSection === section.id && (
                <div className="px-4 pb-4 pt-2 border-t border-slate-800/70">
                  {section.content}
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Footer CTA */}
        <div className="mt-8 panel p-6 text-center">
          <h3 className="text-lg font-semibold text-slate-100 mb-2">Ready to Start?</h3>
          <p className="text-slate-400 mb-4">
            Jump into the market overview to see what's happening today.
          </p>
          <Link 
            to="/marketoverview"
            className="btn-primary inline-flex items-center gap-2"
            onClick={isModal && onClose ? onClose : undefined}
          >
            <TrendingUp className="w-4 h-4" />
            Go to Market Overview
          </Link>
        </div>

        {/* External Resources */}
        <div className="mt-6 panel p-6">
          <h3 className="text-lg font-semibold text-slate-100 mb-4">External Resources</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <a
              href="http://www.bvmt.com.tn"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-3 p-4 bg-slate-800/50 rounded-lg hover:bg-slate-800 transition-colors group"
            >
              <DollarSign className="w-8 h-8 text-cyan-400 group-hover:text-cyan-300" />
              <div>
                <div className="font-medium text-slate-100 group-hover:text-cyan-300">BVMT Official Website</div>
                <div className="text-sm text-slate-400">Bourse des Valeurs Mobilières de Tunis</div>
              </div>
            </a>
            <a
              href="http://www.bvmt.com.tn/fr/cours/tunindex"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-3 p-4 bg-slate-800/50 rounded-lg hover:bg-slate-800 transition-colors group"
            >
              <BarChart3 className="w-8 h-8 text-emerald-400 group-hover:text-emerald-300" />
              <div>
                <div className="font-medium text-slate-100 group-hover:text-emerald-300">TUNINDEX Live Data</div>
                <div className="text-sm text-slate-400">Real-time index information</div>
              </div>
            </a>
          </div>
        </div>
      </div>
    </div>
  );

  return content;
};

export default DashboardGuide;