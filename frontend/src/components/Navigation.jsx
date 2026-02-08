import React from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { 
  BarChart3, TrendingUp, User, LogOut, LineChart, Settings, Bell, Wallet, Shield
} from 'lucide-react';

const Navigation = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const isRegulator = user?.role === 'regulator';

  const investorNav = [
    { name: 'Market Overview', href: '/marketoverview', icon: TrendingUp },
    { name: 'Stock Analysis', href: '/stockanalysis', icon: LineChart },
    { name: 'My Portfolio', href: '/dashboard', icon: BarChart3 },
    { name: 'Trading', href: '/trading', icon: Wallet },
    { name: 'Alerts', href: '/alerts', icon: Bell },
  ];

  const regulatorNav = [
    { name: 'Market Overview', href: '/marketoverview', icon: TrendingUp },
    { name: 'Stock Analysis', href: '/stockanalysis', icon: LineChart },
    { name: 'Regulator Panel', href: '/regulator', icon: Shield },
    { name: 'Alerts', href: '/alerts', icon: Bell },
  ];

  const navigation = isRegulator ? regulatorNav : investorNav;

  return (
    <nav className="bg-slate-950/80 backdrop-blur border-b border-slate-800/80 shadow-[0_10px_30px_rgba(2,6,23,0.45)]">
      <div className="container mx-auto px-4">
        <div className="flex justify-between h-16">
          <div className="flex items-center">
            <div className="flex items-center space-x-2">
              <img src="/icons/iconpng.png" alt="TuniTrAide" className="h-8 w-8" />
              <span className="text-xl font-semibold text-slate-100 tracking-tight">TuniTr<span className="text-cyan-400">AI</span>de</span>
            </div>
            
            <div className="hidden md:ml-6 md:flex md:space-x-8">
              {navigation.map((item) => {
                const isActive = location.pathname === item.href;
                return (
                  <Link
                    key={item.name}
                    to={item.href}
                    className={`inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium ${
                      isActive
                        ? 'border-cyan-400 text-cyan-200'
                        : 'border-transparent text-slate-400 hover:border-slate-700 hover:text-slate-200'
                    }`}
                  >
                    <item.icon className="h-4 w-4 mr-2" />
                    {item.name}
                  </Link>
                );
              })}
            </div>
          </div>

          <div className="flex items-center space-x-4">
            <Link
              to="/profile"
              className="flex items-center space-x-2 text-sm text-slate-400 hover:text-cyan-200 transition-colors"
            >
              <User className="h-5 w-5" />
              <span className="hidden sm:block">{user?.username}</span>
            </Link>
            <button
              onClick={handleLogout}
              className="flex items-center space-x-2 text-sm text-slate-400 hover:text-cyan-200 transition-colors"
            >
              <LogOut className="h-4 w-4" />
              <span className="hidden sm:block">Logout</span>
            </button>
          </div>
        </div>
      </div>

      {/* Mobile menu */}
      <div className="md:hidden border-t border-slate-800/80">
        <div className="pt-2 pb-3 space-y-1 bg-slate-950/80">
          {navigation.map((item) => {
            const isActive = location.pathname === item.href;
            return (
              <Link
                key={item.name}
                to={item.href}
                className={`flex items-center pl-3 pr-4 py-2 border-l-4 text-base font-medium ${
                  isActive
                    ? 'bg-cyan-500/10 border-cyan-400 text-cyan-200'
                    : 'border-transparent text-slate-400 hover:bg-slate-900/60 hover:border-slate-700 hover:text-slate-200'
                }`}
              >
                <item.icon className="h-5 w-5 mr-3" />
                {item.name}
              </Link>
            );
          })}
        </div>
      </div>
    </nav>
  );
};

export default Navigation;