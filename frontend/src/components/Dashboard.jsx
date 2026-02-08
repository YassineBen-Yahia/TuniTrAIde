import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import ApiService from '../services/api';

/**
 * Dashboard Component
 * 
 * User's main dashboard showing portfolio overview, performance, and holdings.
 * 
 * DATA SOURCES (via API endpoints → Backend):
 * ──────────────────────────────────────────────────────────────
 * 1. User Profile:
 *    - API: GET /users/me
 *    - Source: SQLite Database (users table)
 * 
 * 2. Portfolio Data:
 *    - API: GET /portfolios
 *    - Source: SQLite Database (portfolios, holdings, transactions tables)
 * 
 * 3. Portfolio Analytics:
 *    - API: GET /portfolios/{id}/equity-curve
 *    - Source: Computed from transactions + data/historical_data.csv for price lookups
 * 
 * 4. Stock Prices for Holdings:
 *    - Uses: data/historical_data.csv (latest CLOTURE for each stock)
 */

const Dashboard = () => {
    const { user, logout } = useAuth();
    const [userProfile, setUserProfile] = useState(null);
    const [portfolios, setPortfolios] = useState([]);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState('overview');

    useEffect(() => {
        if (user) {
            fetchUserData();
        }
    }, [user]);

    const fetchUserData = async () => {
        try {
            setLoading(true);
            // We already have user profile from authentication
            // Just fetch portfolios
            const portfoliosResponse = await ApiService.getUserPortfolios();
            
            setUserProfile(user); // Use the authenticated user data
            setPortfolios(portfoliosResponse);
        } catch (error) {
            console.error('Error fetching user data:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleLogout = () => {
        logout();
    };

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-cyan-400"></div>
            </div>
        );
    }

    return (
        <div className="min-h-screen app-shell">
            {/* Navigation */}
            <nav className="bg-slate-900/70 shadow-sm border-b border-slate-800/70">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex justify-between h-16">
                        <div className="flex items-center">
                            <h1 className="text-xl font-semibold text-slate-100">
                                📈 Investment Agent
                            </h1>
                        </div>
                        <div className="flex items-center space-x-4">
                            <span className="text-slate-300">Welcome, {user?.full_name || user?.username}</span>
                            <button
                                onClick={handleLogout}
                                className="bg-rose-500 hover:bg-rose-400 text-white px-4 py-2 rounded-md text-sm font-medium"
                            >
                                Logout
                            </button>
                        </div>
                    </div>
                </div>
            </nav>

            {/* Tabs */}
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
                <div className="border-b border-slate-800/70">
                    <nav className="-mb-px flex space-x-8">
                        {[
                            { id: 'overview', label: 'Portfolio Overview' },
                            { id: 'simulation', label: 'Portfolio Simulation' },
                        ].map((tab) => (
                            <button
                                key={tab.id}
                                onClick={() => setActiveTab(tab.id)}
                                className={`whitespace-nowrap py-2 px-1 border-b-2 font-medium text-sm ${
                                    activeTab === tab.id
                                        ? 'border-cyan-400 text-cyan-200'
                                        : 'border-transparent text-slate-500 hover:text-slate-300 hover:border-slate-700'
                                }`}
                            >
                                {tab.label}
                            </button>
                        ))}
                    </nav>
                </div>

                {/* Content */}
                <div className="mt-6">
                    {activeTab === 'overview' && (
                        <PortfolioOverview 
                            userProfile={userProfile} 
                            portfolios={portfolios}
                            onRefresh={fetchUserData}
                        />
                    )}
                    {activeTab === 'simulation' && (
                        <PortfolioSimulation 
                            user={user}
                            userProfile={userProfile}
                        />
                    )}
                </div>
            </div>
        </div>
    );
};

const PortfolioOverview = ({ userProfile, portfolios, onRefresh }) => {
    if (!userProfile) return <div>Loading...</div>;

    // Calculate portfolio performance from portfolios data
    const totalValue = portfolios?.reduce((sum, portfolio) => sum + (portfolio.total_value || portfolio.cash_balance || 0), 0) || 0;
    const totalInitialValue = portfolios?.reduce((sum, portfolio) => sum + (portfolio.cash_balance || 0), 0) || 1;
    const returnPercentage = ((totalValue - totalInitialValue) / totalInitialValue) * 100;

    return (
        <div className="space-y-6">
            {/* User Info Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="panel overflow-hidden">
                    <div className="p-5">
                        <div className="flex items-center">
                            <div className="flex-shrink-0">
                                <div className="w-8 h-8 bg-cyan-500 rounded-full flex items-center justify-center">
                                    <span className="text-white font-medium text-sm">
                                        {userProfile.username?.charAt(0).toUpperCase() || 'U'}
                                    </span>
                                </div>
                            </div>
                            <div className="ml-5 w-0 flex-1">
                                <dl>
                                    <dt className="text-sm font-medium text-slate-500 truncate">Investment Profile</dt>
                                    <dd className="text-lg font-medium text-slate-100">
                                        {userProfile.investment_style || 'Balanced'} • Risk {userProfile.risk_score || 5}/10
                                    </dd>
                                </dl>
                            </div>
                        </div>
                    </div>
                </div>

                <div className="panel overflow-hidden">
                    <div className="p-5">
                        <div className="flex items-center">
                            <div className="flex-shrink-0">
                                <div className="w-8 h-8 bg-emerald-400 rounded-full flex items-center justify-center">
                                    <span className="text-white font-bold text-sm">TND</span>
                                </div>
                            </div>
                            <div className="ml-5 w-0 flex-1">
                                <dl>
                                    <dt className="text-sm font-medium text-slate-500 truncate">Total Portfolio Value</dt>
                                    <dd className="text-lg font-medium text-slate-100">
                                        {totalValue.toFixed(2)} TND
                                    </dd>
                                </dl>
                            </div>
                        </div>
                    </div>
                </div>

                <div className="panel overflow-hidden">
                    <div className="p-5">
                        <div className="flex items-center">
                            <div className="flex-shrink-0">
                                <div className="w-8 h-8 bg-cyan-400 rounded-full flex items-center justify-center">
                                    <span className="text-white font-bold text-sm">%</span>
                                </div>
                            </div>
                            <div className="ml-5 w-0 flex-1">
                                <dl>
                                    <dt className="text-sm font-medium text-slate-500 truncate">Total Return</dt>
                                    <dd className={`text-lg font-medium ${
                                        returnPercentage >= 0 ? 'text-emerald-300' : 'text-rose-300'
                                    }`}>
                                        {returnPercentage >= 0 ? '+' : ''}
                                        {returnPercentage.toFixed(2)}%
                                    </dd>
                                </dl>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Portfolios List */}
            <div className="panel overflow-hidden">
                <div className="px-4 py-5 sm:px-6">
                    <h3 className="text-lg leading-6 font-medium text-slate-100">Your Portfolios</h3>
                    <p className="mt-1 max-w-2xl text-sm text-slate-500">
                        🎉 Default portfolio was automatically created when you registered!
                    </p>
                </div>
                <ul className="divide-y divide-slate-800/70">
                    {portfolios.map((portfolio) => (
                        <li key={portfolio.id}>
                            <div className="px-4 py-4 sm:px-6">
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center">
                                        <div className="flex-shrink-0 h-10 w-10">
                                            <div className="h-10 w-10 rounded-full bg-cyan-500 flex items-center justify-center">
                                                <span className="text-white font-medium text-sm">
                                                    {portfolio.name.charAt(0)}
                                                </span>
                                            </div>
                                        </div>
                                        <div className="ml-4">
                                            <div className="text-sm font-medium text-slate-100">
                                                {portfolio.name}
                                            </div>
                                            <div className="text-sm text-slate-500">
                                                {portfolio.description || 'No description'}
                                            </div>
                                        </div>
                                    </div>
                                    <div className="flex flex-col items-end">
                                        <div className="text-sm font-medium text-slate-100">
                                            {(portfolio.total_value || portfolio.cash_balance || 0).toFixed(2)} TND
                                        </div>
                                        <div className="text-sm text-slate-500">
                                            Cash: {(portfolio.cash_balance || 0).toFixed(2)} TND
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </li>
                    ))}
                </ul>
            </div>
        </div>
    );
};

const PortfolioSimulation = ({ user, userProfile }) => {
    const [simulations, setSimulations] = useState([]);
    const [isCreating, setIsCreating] = useState(false);
    const [newSimulation, setNewSimulation] = useState({
        name: '',
        description: '',
        initial_capital: 10000,
        strategy_type: 'buy_and_hold',
        duration_days: 90,
    });

    useEffect(() => {
        fetchSimulations();
    }, [user]);

    const fetchSimulations = async () => {
        try {
            const simulations = await ApiService.getUserSimulations(user.id);
            setSimulations(simulations);
        } catch (error) {
            console.error('Error fetching simulations:', error);
        }
    };

    const handleCreateSimulation = async (e) => {
        e.preventDefault();
        setIsCreating(true);
        
        try {
            const startDate = new Date();
            startDate.setDate(startDate.getDate() - newSimulation.duration_days);
            const endDate = new Date();
            endDate.setDate(endDate.getDate() - 1);

            const simulationData = {
                name: newSimulation.name,
                description: newSimulation.description,
                start_date: startDate.toISOString(),
                end_date: endDate.toISOString(),
                initial_capital: newSimulation.initial_capital,
                strategy_config: {
                    strategy_type: newSimulation.strategy_type,
                    max_position_size: 0.2,
                    rebalance_frequency: 'monthly',
                    risk_management: {
                        stop_loss: 0.15,
                        take_profit: 0.25,
                    }
                }
            };

            await ApiService.createSimulation(user.id, simulationData);
            await fetchSimulations();
            
            // Reset form
            setNewSimulation({
                name: '',
                description: '',
                initial_capital: 10000,
                strategy_type: 'buy_and_hold',
                duration_days: 90,
            });
        } catch (error) {
            console.error('Error creating simulation:', error);
        } finally {
            setIsCreating(false);
        }
    };

    return (
        <div className="space-y-6">
            {/* Create New Simulation */}
            <div className="panel">
                <div className="px-4 py-5 sm:p-6">
                    <h3 className="text-lg leading-6 font-medium text-slate-100 mb-4">
                        Create New Portfolio Simulation
                    </h3>
                    <form onSubmit={handleCreateSimulation} className="grid grid-cols-1 gap-6 sm:grid-cols-2">
                        <div>
                            <label className="block text-sm font-medium text-slate-300">
                                Simulation Name
                            </label>
                            <input
                                type="text"
                                required
                                className="input-field mt-1"
                                value={newSimulation.name}
                                onChange={(e) => setNewSimulation({ ...newSimulation, name: e.target.value })}
                                placeholder="My Trading Strategy"
                            />
                        </div>
                        
                        <div>
                            <label className="block text-sm font-medium text-slate-300">
                                Initial Capital
                            </label>
                            <input
                                type="number"
                                required
                                min="1000"
                                step="100"
                                className="input-field mt-1"
                                value={newSimulation.initial_capital}
                                onChange={(e) => setNewSimulation({ ...newSimulation, initial_capital: parseFloat(e.target.value) })}
                            />
                        </div>
                        
                        <div>
                            <label className="block text-sm font-medium text-slate-300">
                                Strategy Type
                            </label>
                            <select
                                className="input-field mt-1"
                                value={newSimulation.strategy_type}
                                onChange={(e) => setNewSimulation({ ...newSimulation, strategy_type: e.target.value })}
                            >
                                <option value="buy_and_hold">Buy and Hold</option>
                                <option value="momentum">Momentum Trading</option>
                                <option value="value_investing">Value Investing</option>
                                <option value="swing_trading">Swing Trading</option>
                            </select>
                        </div>
                        
                        <div>
                            <label className="block text-sm font-medium text-slate-300">
                                Simulation Period (Days)
                            </label>
                            <select
                                className="input-field mt-1"
                                value={newSimulation.duration_days}
                                onChange={(e) => setNewSimulation({ ...newSimulation, duration_days: parseInt(e.target.value) })}
                            >
                                <option value="30">30 Days</option>
                                <option value="60">60 Days</option>
                                <option value="90">90 Days</option>
                                <option value="180">6 Months</option>
                                <option value="365">1 Year</option>
                            </select>
                        </div>
                        
                        <div className="sm:col-span-2">
                            <label className="block text-sm font-medium text-slate-300">
                                Description
                            </label>
                            <textarea
                                rows="3"
                                className="input-field mt-1"
                                value={newSimulation.description}
                                onChange={(e) => setNewSimulation({ ...newSimulation, description: e.target.value })}
                                placeholder="Describe your simulation strategy..."
                            />
                        </div>
                        
                        <div className="sm:col-span-2">
                            <button
                                type="submit"
                                disabled={isCreating}
                                className="btn-primary w-full text-sm disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                {isCreating ? 'Creating Simulation...' : 'Create Simulation'}
                            </button>
                        </div>
                    </form>
                </div>
            </div>

            {/* Existing Simulations */}
            <div className="panel overflow-hidden">
                <div className="px-4 py-5 sm:px-6">
                    <h3 className="text-lg leading-6 font-medium text-slate-100">
                        Your Simulations
                    </h3>
                    <p className="mt-1 max-w-2xl text-sm text-slate-500">
                        Track the performance of your simulated trading strategies
                    </p>
                </div>
                
                {simulations.length === 0 ? (
                    <div className="px-4 py-5 sm:px-6 text-center">
                        <p className="text-slate-500">No simulations yet. Create your first simulation above!</p>
                    </div>
                ) : (
                    <ul className="divide-y divide-slate-800/70">
                        {simulations.map((simulation) => (
                            <li key={simulation.id}>
                                <div className="px-4 py-4 sm:px-6">
                                    <div className="flex items-center justify-between">
                                        <div className="flex items-center">
                                            <div className="flex-shrink-0">
                                                <div className={`w-3 h-3 rounded-full ${
                                                    simulation.status === 'completed' ? 'bg-emerald-400' :
                                                    simulation.status === 'running' ? 'bg-cyan-400' :
                                                    simulation.status === 'failed' ? 'bg-rose-500' :
                                                    'bg-slate-600'
                                                }`}></div>
                                            </div>
                                            <div className="ml-4">
                                                <div className="text-sm font-medium text-slate-100">
                                                    {simulation.name}
                                                </div>
                                                <div className="text-sm text-slate-500">
                                                    {simulation.description}
                                                </div>
                                                <div className="text-xs text-slate-500">
                                                    Initial Capital: {simulation.initial_capital.toFixed(2)} TND • Status: {simulation.status}
                                                </div>
                                            </div>
                                        </div>
                                        <div className="flex flex-col items-end">
                                            {simulation.status === 'completed' && (
                                                <>
                                                    <div className={`text-sm font-medium ${
                                                        simulation.total_return_percentage >= 0 ? 'text-emerald-300' : 'text-rose-300'
                                                    }`}>
                                                        {simulation.total_return_percentage >= 0 ? '+' : ''}
                                                        {simulation.total_return_percentage?.toFixed(2) || '0.00'}%
                                                    </div>
                                                    <div className="text-sm text-slate-500">
                                                        Final: {simulation.final_portfolio_value?.toFixed(2) || '0.00'} TND
                                                    </div>
                                                </>
                                            )}
                                            {simulation.status === 'pending' && (
                                                <div className="text-sm text-slate-500">
                                                    Pending...
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            </li>
                        ))}
                    </ul>
                )}
            </div>
        </div>
    );
};

export default Dashboard;