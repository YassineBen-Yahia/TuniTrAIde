import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';

const Login = () => {
  const [isLogin, setIsLogin] = useState(true);
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    full_name: '',
    risk_score: 5,
    risk_level: 'moderate',
    investment_style: 'balanced',
  });
  
  const { login, register, isLoading, error, clearError } = useAuth();

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    clearError();
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (isLogin) {
        await login({
          username: formData.username,
          password: formData.password
        });
      } else {
        const response = await register({
          username: formData.username,
          email: formData.email,
          password: formData.password,
          full_name: formData.full_name,
          risk_score: parseInt(formData.risk_score),
          risk_level: formData.risk_level,
          investment_style: formData.investment_style,
          investment_experience_years: 0,
          monthly_investment_budget: 1000,
          avoid_anomalies: true,
          allow_short_selling: false,
          max_single_stock_percentage: 20,
          preferred_sectors: [],
          excluded_sectors: [],
          initial_cash_balance: 10000,
          target_portfolio_value: 0,
          rebalance_frequency_days: 30,
          ai_assistance_level: "medium",
          auto_execute_recommendations: false,
          notification_preferences: {},
        });
        
        if (response.success) {
          // Auto login after registration
          await login({
            username: formData.username,
            password: formData.password
          });
        }
      }
    } catch (err) {
      console.error('Authentication error:', err);
    }
  };

  const toggleMode = () => {
    setIsLogin(!isLogin);
    clearError();
    setFormData({
      username: '',
      email: '',
      password: '',
      full_name: '',
      risk_score: 5,
      risk_level: 'moderate',
      investment_style: 'balanced',
    });
  };

  return (
    <div className="min-h-screen app-shell flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full panel p-8 space-y-8">
        <div className="flex flex-col items-center">
          <img src="/icons/iconpng.png" alt="TuniTrAide" className="h-16 w-16 mb-2" />
          <h1 className="text-2xl font-bold text-slate-100 tracking-tight">TuniTr<span className="text-cyan-400">AI</span>de</h1>
          <h2 className="mt-4 text-center text-3xl font-semibold text-slate-100 tracking-tight">
            {isLogin ? 'Sign in to your account' : 'Create your account'}
          </h2>
          <p className="mt-2 text-center text-sm text-slate-400">
            {isLogin ? "Don't have an account?" : 'Already have an account?'}
            <button
              type="button"
              className="font-medium text-cyan-300 hover:text-cyan-200 ml-1"
              onClick={toggleMode}
            >
              {isLogin ? 'Sign up' : 'Sign in'}
            </button>
          </p>
        </div>
        
        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          {error && (
            <div className="bg-rose-500/10 border border-rose-400/30 text-rose-200 px-4 py-3 rounded-lg">
              <span className="block sm:inline">{error}</span>
            </div>
          )}
          
          <div className="space-y-4">
            <div>
              <label htmlFor="username" className="block text-sm font-medium text-slate-300">
                Username
              </label>
              <input
                id="username"
                name="username"
                type="text"
                required
                className="input-field mt-1"
                placeholder="Enter your username"
                value={formData.username}
                onChange={handleChange}
              />
            </div>

            {!isLogin && (
              <>
                <div>
                  <label htmlFor="email" className="block text-sm font-medium text-slate-300">
                    Email
                  </label>
                  <input
                    id="email"
                    name="email"
                    type="email"
                    required
                    className="input-field mt-1"
                    placeholder="Enter your email"
                    value={formData.email}
                    onChange={handleChange}
                  />
                </div>

                <div>
                  <label htmlFor="full_name" className="block text-sm font-medium text-slate-300">
                    Full Name
                  </label>
                  <input
                    id="full_name"
                    name="full_name"
                    type="text"
                    className="input-field mt-1"
                    placeholder="Enter your full name"
                    value={formData.full_name}
                    onChange={handleChange}
                  />
                </div>

                <div>
                  <label htmlFor="risk_score" className="block text-sm font-medium text-slate-300">
                    Risk Tolerance (1-10)
                  </label>
                  <input
                    id="risk_score"
                    name="risk_score"
                    type="range"
                    min="1"
                    max="10"
                    className="mt-1 w-full accent-cyan-400"
                    value={formData.risk_score}
                    onChange={handleChange}
                  />
                  <div className="flex justify-between text-xs text-slate-500">
                    <span>Conservative (1)</span>
                    <span>Current: {formData.risk_score}</span>
                    <span>Aggressive (10)</span>
                  </div>
                </div>

                <div>
                  <label htmlFor="investment_style" className="block text-sm font-medium text-slate-300">
                    Investment Style
                  </label>
                  <select
                    id="investment_style"
                    name="investment_style"
                    className="select-field mt-1"
                    value={formData.investment_style}
                    onChange={handleChange}
                  >
                    <option value="conservative">Conservative</option>
                    <option value="balanced">Balanced</option>
                    <option value="aggressive">Aggressive</option>
                    <option value="growth">Growth</option>
                    <option value="value">Value</option>
                    <option value="income">Income</option>
                  </select>
                </div>
              </>
            )}

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-slate-300">
                Password
              </label>
              <input
                id="password"
                name="password"
                type="password"
                required
                className="input-field mt-1"
                placeholder="Enter your password"
                value={formData.password}
                onChange={handleChange}
              />
            </div>
          </div>

          <div>
            <button
              type="submit"
              disabled={isLoading}
              className="btn-primary w-full text-sm disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <div className="flex items-center">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  {isLogin ? 'Signing in...' : 'Creating account...'}
                </div>
              ) : (
                isLogin ? 'Sign in' : 'Create account'
              )}
            </button>
          </div>

          {!isLogin && (
            <div className="text-xs text-slate-500 text-center">
              🎉 A default portfolio will be automatically created for you with your initial balance!
            </div>
          )}
        </form>
      </div>
    </div>
  );
};

export default Login;