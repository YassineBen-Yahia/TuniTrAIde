import React from 'react';
import { Link } from 'react-router-dom';
import { 
  Github, 
  Linkedin, 
  Mail,
  TrendingUp,
  BarChart3,
  LineChart,
  Bell,
  BookOpen
} from 'lucide-react';

/**
 * Footer Component
 * 
 * A consistent footer displayed across all pages of TuniTrAide.
 * Contains navigation links, contact information, and branding.
 */
const Footer = () => {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="bg-slate-950/90 border-t border-slate-800/80 mt-auto">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* Brand Section */}
          <div className="col-span-1 md:col-span-2">
            <div className="flex items-center space-x-2 mb-4">
              <img src="/icons/iconpng.png" alt="TuniTrAide" className="h-9 w-9" />
              <span className="text-xl font-semibold text-slate-100 tracking-tight">TuniTr<span className="text-cyan-400">AI</span>de</span>
            </div>
            <p className="text-slate-400 text-sm max-w-md">
              Your AI-powered platform for Tunisian stock market analysis, portfolio management, 
              and intelligent trading decisions on the BVMT.
            </p>
            <div className="flex items-center gap-4 mt-4">
              <span 
                className="text-slate-600 cursor-not-allowed"
                title="Coming soon"
              >
                <Github className="h-5 w-5" />
              </span>
              <span 
                className="text-slate-600 cursor-not-allowed"
                title="Coming soon"
              >
                <Linkedin className="h-5 w-5" />
              </span>
              <span 
                className="text-slate-600 cursor-not-allowed"
                title="Coming soon"
              >
                <Mail className="h-5 w-5" />
              </span>
            </div>
          </div>

          {/* Quick Links */}
          <div>
            <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-4">
              Quick Links
            </h3>
            <ul className="space-y-2">
              <li>
                <Link 
                  to="/marketoverview" 
                  className="flex items-center gap-2 text-slate-400 hover:text-cyan-400 transition-colors text-sm"
                >
                  <TrendingUp className="h-4 w-4" />
                  Market Overview
                </Link>
              </li>
              <li>
                <Link 
                  to="/stockanalysis" 
                  className="flex items-center gap-2 text-slate-400 hover:text-cyan-400 transition-colors text-sm"
                >
                  <LineChart className="h-4 w-4" />
                  Stock Analysis
                </Link>
              </li>
              <li>
                <Link 
                  to="/dashboard" 
                  className="flex items-center gap-2 text-slate-400 hover:text-cyan-400 transition-colors text-sm"
                >
                  <BarChart3 className="h-4 w-4" />
                  My Portfolio
                </Link>
              </li>
              <li>
                <Link 
                  to="/alerts" 
                  className="flex items-center gap-2 text-slate-400 hover:text-cyan-400 transition-colors text-sm"
                >
                  <Bell className="h-4 w-4" />
                  Alerts & Surveillance
                </Link>
              </li>
              <li>
                <Link 
                  to="/guide" 
                  className="flex items-center gap-2 text-slate-400 hover:text-cyan-400 transition-colors text-sm"
                >
                  <BookOpen className="h-4 w-4" />
                  Dashboard Guide
                </Link>
              </li>
            </ul>
          </div>

          {/* Info */}
          <div>
            <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-4">
              Market Info
            </h3>
            <ul className="space-y-2 text-sm text-slate-400">
              <li>
                <span className="text-slate-500">Market:</span>{' '}
                <span className="text-slate-300">BVMT Tunisia</span>
              </li>
              <li>
                <span className="text-slate-500">Currency:</span>{' '}
                <span className="text-slate-300">TND (Tunisian Dinar)</span>
              </li>
              <li>
                <span className="text-slate-500">Trading Hours:</span>{' '}
                <span className="text-slate-300">08:00 - 17:00</span>
              </li>
              <li>
                <span className="text-slate-500">Timezone:</span>{' '}
                <span className="text-slate-300">UTC+1 (Tunis)</span>
              </li>
            </ul>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="mt-8 pt-6 border-t border-slate-800/70">
          <div className="flex flex-col md:flex-row justify-between items-center gap-4">
            <p className="text-slate-500 text-sm">
              © {currentYear} TuniTrAide. All rights reserved.
            </p>
            <div className="flex items-center gap-6 text-sm text-slate-500">
              <span className="hover:text-slate-300 cursor-pointer transition-colors">Privacy Policy</span>
              <span className="hover:text-slate-300 cursor-pointer transition-colors">Terms of Service</span>
              <span className="hover:text-slate-300 cursor-pointer transition-colors">Disclaimer</span>
            </div>
          </div>
          <p className="text-center text-slate-600 text-xs mt-4">
            TuniTrAide is a simulated trading platform for educational purposes. Past performance does not guarantee future results.
          </p>
        </div>
      </div>
    </footer>
  );
};

export default Footer;