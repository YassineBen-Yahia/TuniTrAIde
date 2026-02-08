import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { ChatProvider } from './contexts/ChatContext';
import { ThemeProvider } from './contexts/ThemeContext';
import Login from './components/Login';
import Dashboard from './components/Dashboard';
import EnhancedDashboard from './components/EnhancedDashboard';
import TradingSimulation from './components/TradingSimulation';
import StockAnalysis from './components/StockAnalysis';
import MarketOverview from './components/MarketOverview';
import AlertsSurveillance from './components/AlertsSurveillance';
import RegulatorDashboard from './components/RegulatorDashboard';
import Profile from './components/Profile';
import DashboardGuide from './components/DashboardGuide';
import ErrorBoundary from './components/ErrorBoundary';
import Navigation from './components/Navigation';
import ChatBot from './components/ChatBot';
import Footer from './components/Footer';
import './App.css';

function ProtectedRoute({ children }) {
  const { isAuthenticated } = useAuth();
  return isAuthenticated ? children : <Navigate to="/login" />;
}

function PublicRoute({ children }) {
  const { isAuthenticated } = useAuth();
  return !isAuthenticated ? children : <Navigate to="/marketoverview" />;
}

function AppRoutes() {
  const { isAuthenticated } = useAuth();
  
  return (
    <div className="flex flex-col min-h-screen">
      {isAuthenticated && <Navigation />}
      <main className="flex-1">
        <Routes>
          <Route
            path="/login"
            element={
              <PublicRoute>
                <Login />
              </PublicRoute>
            }
          />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <EnhancedDashboard />
              </ProtectedRoute>
            }
          />
          {/* Market Overview - both old and new URLs */}
          <Route
            path="/market"
            element={
              <ProtectedRoute>
                <ErrorBoundary>
                  <MarketOverview />
                </ErrorBoundary>
              </ProtectedRoute>
            }
          />
          <Route
            path="/marketoverview"
            element={
              <ProtectedRoute>
                <ErrorBoundary>
                  <MarketOverview />
                </ErrorBoundary>
              </ProtectedRoute>
            }
          />
          {/* Stock Analysis - both old and new URLs */}
          <Route
            path="/stock-analysis"
            element={
              <ProtectedRoute>
                <ErrorBoundary>
                  <StockAnalysis />
                </ErrorBoundary>
              </ProtectedRoute>
            }
          />
          <Route
            path="/stockanalysis"
            element={
              <ProtectedRoute>
                <ErrorBoundary>
                  <StockAnalysis />
                </ErrorBoundary>
              </ProtectedRoute>
            }
          />
          <Route
            path="/profile"
            element={
              <ProtectedRoute>
                <Profile />
              </ProtectedRoute>
            }
          />
          <Route
            path="/trading"
            element={
              <ProtectedRoute>
                <TradingSimulation />
              </ProtectedRoute>
            }
          />
          {/* Alerts & Surveillance */}
          <Route
            path="/alerts"
            element={
              <ProtectedRoute>
                <ErrorBoundary>
                  <AlertsSurveillance />
                </ErrorBoundary>
              </ProtectedRoute>
            }
          />
          {/* Regulator Dashboard */}
          <Route
            path="/regulator"
            element={
              <ProtectedRoute>
                <ErrorBoundary>
                  <RegulatorDashboard />
                </ErrorBoundary>
              </ProtectedRoute>
            }
          />
          {/* Dashboard Guide */}
          <Route
            path="/guide"
            element={
              <ProtectedRoute>
                <DashboardGuide />
              </ProtectedRoute>
            }
          />
          <Route path="/" element={<Navigate to="/marketoverview" />} />
        </Routes>
      </main>
      {isAuthenticated && <Footer />}
      {isAuthenticated && <ChatBot />}
    </div>
  );
}

function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <ChatProvider>
          <Router>
            <div className="App">
              <AppRoutes />
            </div>
          </Router>
        </ChatProvider>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;