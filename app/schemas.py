from pydantic import BaseModel, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class RiskLevelEnum(str, Enum):
    VERY_LOW = "very_low"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"


class InvestmentStyleEnum(str, Enum):
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"
    GROWTH = "growth"
    VALUE = "value"
    INCOME = "income"


class UserRoleEnum(str, Enum):
    TRADER = "trader"
    REGULATOR = "regulator"


# User Schemas
class UserBase(BaseModel):
    username: str
    email: str  # Changed from EmailStr temporarily
    full_name: Optional[str] = None
    role: Optional[UserRoleEnum] = UserRoleEnum.TRADER
    risk_score: Optional[int] = 5
    risk_level: Optional[RiskLevelEnum] = RiskLevelEnum.MODERATE
    investment_style: Optional[InvestmentStyleEnum] = InvestmentStyleEnum.BALANCED
    investment_experience_years: Optional[int] = 0
    monthly_investment_budget: Optional[float] = 0.0
    avoid_anomalies: Optional[bool] = True
    allow_short_selling: Optional[bool] = False
    max_single_stock_percentage: Optional[float] = 20.0
    preferred_sectors: Optional[List[str]] = []
    excluded_sectors: Optional[List[str]] = []
    initial_cash_balance: Optional[float] = 10000.0
    target_portfolio_value: Optional[float] = None
    rebalance_frequency_days: Optional[int] = 30
    ai_assistance_level: Optional[str] = "medium"
    auto_execute_recommendations: Optional[bool] = False
    notification_preferences: Optional[Dict[str, Any]] = {}

    @validator('risk_score')
    def validate_risk_score(cls, v):
        if not 1 <= v <= 10:
            raise ValueError('Risk score must be between 1 and 10')
        return v

    @validator('max_single_stock_percentage')
    def validate_max_stock_percentage(cls, v):
        if not 0 < v <= 100:
            raise ValueError('Max single stock percentage must be between 0 and 100')
        return v


class UserCreate(UserBase):
    password: str

    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    risk_score: Optional[int] = None
    risk_level: Optional[RiskLevelEnum] = None
    investment_style: Optional[InvestmentStyleEnum] = None
    investment_experience_years: Optional[int] = None
    monthly_investment_budget: Optional[float] = None
    avoid_anomalies: Optional[bool] = None
    allow_short_selling: Optional[bool] = None
    max_single_stock_percentage: Optional[float] = None
    preferred_sectors: Optional[List[str]] = None
    excluded_sectors: Optional[List[str]] = None
    target_portfolio_value: Optional[float] = None
    rebalance_frequency_days: Optional[int] = None
    ai_assistance_level: Optional[str] = None
    auto_execute_recommendations: Optional[bool] = None
    notification_preferences: Optional[Dict[str, Any]] = None


class User(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    role: Optional[str] = "trader"

    class Config:
        from_attributes = True


# Portfolio Schemas
class HoldingBase(BaseModel):
    stock_code: str
    stock_name: Optional[str] = None
    shares: float
    avg_purchase_price: float


class HoldingCreate(HoldingBase):
    pass


class Holding(HoldingBase):
    id: int
    portfolio_id: int
    current_price: Optional[float] = 0.0
    total_value: Optional[float] = 0.0
    unrealized_gain_loss: Optional[float] = 0.0
    unrealized_gain_loss_percentage: Optional[float] = 0.0
    last_price_update: Optional[datetime] = None

    class Config:
        from_attributes = True


class PortfolioBase(BaseModel):
    name: str
    description: Optional[str] = None
    cash_balance: Optional[float] = 0.0


class PortfolioCreate(PortfolioBase):
    pass


class Portfolio(PortfolioBase):
    id: int
    user_id: int
    is_active: bool
    total_value: Optional[float] = 0.0
    created_at: datetime
    updated_at: Optional[datetime] = None
    holdings: List[Holding] = []

    class Config:
        from_attributes = True


class PortfolioDetail(Portfolio):
    """Extended portfolio schema with additional details"""
    pass


# Transaction Schemas
class TransactionBase(BaseModel):
    stock_code: str
    stock_name: Optional[str] = None
    transaction_type: str  # 'BUY' or 'SELL'
    shares: float
    price_per_share: float
    fees: Optional[float] = 0.0
    notes: Optional[str] = None
    recommended_by_ai: Optional[bool] = False
    confidence_score: Optional[float] = None
    reasoning: Optional[str] = None

    @validator('transaction_type')
    def validate_transaction_type(cls, v):
        if v.upper() not in ['BUY', 'SELL']:
            raise ValueError('Transaction type must be BUY or SELL')
        return v.upper()


class TransactionCreate(TransactionBase):
    pass  # No portfolio_id needed since it comes from the URL path


class TransactionCreateWithPortfolio(TransactionBase):
    portfolio_id: int


class Transaction(TransactionBase):
    id: int
    user_id: int
    portfolio_id: int
    total_amount: float
    transaction_date: datetime
    is_suspicious: Optional[bool] = False
    suspicious_reason: Optional[str] = None
    flagged_by_regulator_id: Optional[int] = None
    flagged_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Simulation Schemas
class SimulationTradeBase(BaseModel):
    stock_code: str
    stock_name: Optional[str] = None
    trade_type: str
    shares: float
    price_per_share: float
    trade_date: datetime
    entry_signal: Optional[str] = None
    exit_signal: Optional[str] = None
    ai_confidence: Optional[float] = None
    ai_reasoning: Optional[str] = None
    market_conditions: Optional[Dict[str, Any]] = None


class SimulationTrade(SimulationTradeBase):
    id: int
    simulation_id: int
    total_amount: float
    profit_loss: Optional[float] = 0.0
    profit_loss_percentage: Optional[float] = 0.0
    holding_days: Optional[int] = 0

    class Config:
        from_attributes = True


class PortfolioSimulationBase(BaseModel):
    name: str
    description: Optional[str] = None
    start_date: datetime
    end_date: datetime
    initial_capital: float
    strategy_config: Optional[Dict[str, Any]] = None


class PortfolioSimulationCreate(PortfolioSimulationBase):
    pass


class PortfolioSimulation(PortfolioSimulationBase):
    id: int
    user_id: int
    final_portfolio_value: Optional[float] = None
    total_return: Optional[float] = None
    total_return_percentage: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None
    volatility: Optional[float] = None
    beta: Optional[float] = None
    alpha: Optional[float] = None
    winning_trades: Optional[int] = 0
    losing_trades: Optional[int] = 0
    win_rate: Optional[float] = 0.0
    avg_win: Optional[float] = 0.0
    avg_loss: Optional[float] = 0.0
    status: str = "pending"
    progress_percentage: Optional[float] = 0.0
    created_at: datetime
    completed_at: Optional[datetime] = None
    simulation_trades: List[SimulationTrade] = []

    class Config:
        from_attributes = True


class PortfolioSimulationDetail(PortfolioSimulation):
    """Extended simulation schema with additional details"""
    pass


# Market Data Schemas
class MarketDataBase(BaseModel):
    stock_code: str
    stock_name: Optional[str] = None
    date: datetime
    open_price: Optional[float] = None
    high_price: Optional[float] = None
    low_price: Optional[float] = None
    close_price: float
    volume: Optional[int] = None
    adjusted_close: Optional[float] = None


class MarketData(MarketDataBase):
    id: int
    sma_20: Optional[float] = None
    sma_50: Optional[float] = None
    ema_12: Optional[float] = None
    ema_26: Optional[float] = None
    rsi: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    bollinger_upper: Optional[float] = None
    bollinger_lower: Optional[float] = None
    is_anomaly: Optional[bool] = False
    anomaly_score: Optional[float] = None
    anomaly_type: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# Response Models
class Token(BaseModel):
    access_token: str
    token_type: str


class UserResponse(BaseModel):
    success: bool
    message: str
    user: Optional[User] = None


class PortfolioResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Portfolio] = None


class TransactionResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Transaction] = None


class SimulationResponse(BaseModel):
    success: bool
    message: str
    data: Optional[PortfolioSimulation] = None


# Chat Schemas
class ChatMessage(BaseModel):
    content: str


# Regulator Schemas
class FlagTransactionRequest(BaseModel):
    transaction_id: int
    is_suspicious: bool
    suspicious_reason: Optional[str] = None


class StockAnomalyInfo(BaseModel):
    stock_code: str
    stock_name: str
    date: str
    volume_anomaly: int
    variation_anomaly: int
    variation_anomaly_post_news: int
    variation_anomaly_pre_news: int
    volume_anomaly_post_news: int
    volume_anomaly_pre_news: int


class UpdateAnomalyRequest(BaseModel):
    stock_code: str
    date: str
    anomaly_type: str  # 'volume' or 'variation'
    value: int  # 0 or 1 for the anomaly


class TransactionWithUser(Transaction):
    user: User
    portfolio: Portfolio
    
    class Config:
        from_attributes = True

class ChatResponse(BaseModel):
    type: str  # "user" or "agent"
    content: str
    rationale: Optional[str] = None
    comparison: Optional[str] = None
    timestamp: str

class ChatSession(BaseModel):
    session_id: str
    messages: List[ChatResponse]