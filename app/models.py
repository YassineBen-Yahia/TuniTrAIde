from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class RiskLevel(enum.Enum):
    VERY_LOW = "very_low"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"


class InvestmentStyle(enum.Enum):
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"
    GROWTH = "growth"
    VALUE = "value"
    INCOME = "income"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Investment Profile
    risk_score = Column(Integer, default=5)  # Scale 1-10
    risk_level = Column(String(20), default=RiskLevel.MODERATE.value)
    investment_style = Column(String(20), default=InvestmentStyle.BALANCED.value)
    investment_experience_years = Column(Integer, default=0)
    monthly_investment_budget = Column(Float, default=0.0)
    
    # Investment Preferences
    avoid_anomalies = Column(Boolean, default=True)
    allow_short_selling = Column(Boolean, default=False)
  
    # Portfolio Settings
    initial_cash_balance = Column(Float, default=10000.0)
    target_portfolio_value = Column(Float)
    rebalance_frequency_days = Column(Integer, default=30)
    
    
    
    # Relationships
    portfolios = relationship("Portfolio", back_populates="user", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
    simulations = relationship("PortfolioSimulation", back_populates="user", cascade="all, delete-orphan")


class Portfolio(Base):
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    cash_balance = Column(Float, default=0.0)
    total_value = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="portfolios")
    holdings = relationship("Holding", back_populates="portfolio", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="portfolio", cascade="all, delete-orphan")


class Holding(Base):
    __tablename__ = "holdings"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    stock_code = Column(String(50), nullable=False)  # e.g., "TN0001100254"
    stock_name = Column(String(100))
    shares = Column(Float, nullable=False, default=0.0)
    avg_purchase_price = Column(Float, nullable=False, default=0.0)
    current_price = Column(Float, default=0.0)
    total_value = Column(Float, default=0.0)
    unrealized_gain_loss = Column(Float, default=0.0)
    unrealized_gain_loss_percentage = Column(Float, default=0.0)
    last_price_update = Column(DateTime(timezone=True))
    
    # Relationships
    portfolio = relationship("Portfolio", back_populates="holdings")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    stock_code = Column(String(50), nullable=False)
    stock_name = Column(String(100))
    transaction_type = Column(String(10), nullable=False)  # 'BUY', 'SELL'
    shares = Column(Float, nullable=False)
    price_per_share = Column(Float, nullable=False)
    total_amount = Column(Float, nullable=False)
    fees = Column(Float, default=0.0)
    transaction_date = Column(DateTime(timezone=True), server_default=func.now())
    notes = Column(Text)
    
    # AI Agent related fields
    recommended_by_ai = Column(Boolean, default=False)
    reasoning = Column(Text)  # AI reasoning for the recommendation
    
    # Relationships
    user = relationship("User", back_populates="transactions")
    portfolio = relationship("Portfolio", back_populates="transactions")


class PortfolioSimulation(Base):
    __tablename__ = "portfolio_simulations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    
    # Simulation Parameters
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    initial_capital = Column(Float, nullable=False)
    strategy_config = Column(JSON)  # Strategy parameters and settings
    
    # Simulation Results
    final_portfolio_value = Column(Float)
    total_return = Column(Float)
    total_return_percentage = Column(Float)
    sharpe_ratio = Column(Float)
    max_drawdown = Column(Float)
    volatility = Column(Float)
    beta = Column(Float)
    alpha = Column(Float)
    
    # Performance Metrics
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)
    avg_win = Column(Float, default=0.0)
    avg_loss = Column(Float, default=0.0)
    
    # Simulation Status
    status = Column(String(20), default="pending")  # pending, running, completed, failed
    progress_percentage = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    
    # Relationships
    user = relationship("User", back_populates="simulations")
   
class MarketData(Base):
    __tablename__ = "market_data"

    id = Column(Integer, primary_key=True, index=True)
    stock_code = Column(String(50), nullable=False, index=True)
    stock_name = Column(String(100))
    date = Column(DateTime(timezone=True), nullable=False, index=True)
    open_price = Column(Float)
    high_price = Column(Float)
    low_price = Column(Float)
    close_price = Column(Float, nullable=False)
    volume = Column(Integer)
    adjusted_close = Column(Float)
    
    # Technical Indicators
    sma_20 = Column(Float)  # 20-day Simple Moving Average
    sma_50 = Column(Float)  # 50-day Simple Moving Average
    ema_12 = Column(Float)  # 12-day Exponential Moving Average
    ema_26 = Column(Float)  # 26-day Exponential Moving Average
    rsi = Column(Float)     # Relative Strength Index
    macd = Column(Float)    # MACD Line
    macd_signal = Column(Float)  # MACD Signal Line
    bollinger_upper = Column(Float)
    bollinger_lower = Column(Float)
    
    # Anomaly Detection
    is_anomaly = Column(Boolean, default=False)
    anomaly_score = Column(Float)
    anomaly_type = Column(String(50))  # price_spike, volume_spike, etc.
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
