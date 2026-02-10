from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func
from passlib.context import CryptContext
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import pandas as pd
import os

from . import models, schemas

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


# User CRUD operations
def get_user(db: Session, user_id: int) -> Optional[models.User]:
    """Get a user by ID."""
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_username(db: Session, username: str) -> Optional[models.User]:
    """Get a user by username."""
    return db.query(models.User).filter(models.User.username == username).first()


def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    """Get a user by email."""
    return db.query(models.User).filter(models.User.email == email).first()


def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[models.User]:
    """Get all users with pagination."""
    return db.query(models.User).offset(skip).limit(limit).all()


def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    """Create a new user."""
    hashed_password = get_password_hash(user.password)
    
    # Convert enum values to strings if they are enum objects, otherwise use as-is
    risk_level_value = user.risk_level.value if hasattr(user.risk_level, 'value') else user.risk_level
    investment_style_value = user.investment_style.value if hasattr(user.investment_style, 'value') else user.investment_style
    role_value = user.role.value if hasattr(user.role, 'value') else (user.role or "trader")
    
    db_user = models.User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        full_name=user.full_name,
        role=role_value,
        risk_score=user.risk_score,
        risk_level=risk_level_value,
        investment_style=investment_style_value,
        investment_experience_years=user.investment_experience_years or 0,
        monthly_investment_budget=user.monthly_investment_budget or 0.0,
        avoid_anomalies=user.avoid_anomalies if user.avoid_anomalies is not None else True,
        allow_short_selling=user.allow_short_selling if user.allow_short_selling is not None else False,
        initial_cash_balance=user.initial_cash_balance or 10000.0,
        target_portfolio_value=user.target_portfolio_value,
        rebalance_frequency_days=user.rebalance_frequency_days or 30,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Create a default portfolio for the user
    create_portfolio(db, schemas.PortfolioCreate(
        name="Main Portfolio",
        description="Default investment portfolio",
        cash_balance=user.initial_cash_balance or 10000.0
    ), db_user.id)
    
    return db_user


def update_user(db: Session, user_id: int, user_update: schemas.UserUpdate) -> Optional[models.User]:
    """Update a user's information."""
    db_user = get_user(db, user_id)
    if not db_user:
        return None
    
    update_data = user_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(db_user, field):
            if field in ['risk_level', 'investment_style'] and value:
                value = value.value
            setattr(db_user, field, value)
    
    db_user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_user)
    return db_user


def delete_user(db: Session, user_id: int) -> bool:
    """Delete a user."""
    db_user = get_user(db, user_id)
    if not db_user:
        return False
    
    db.delete(db_user)
    db.commit()
    return True


# Portfolio CRUD operations
def create_portfolio(db: Session, portfolio: schemas.PortfolioCreate, user_id: int) -> models.Portfolio:
    """Create a new portfolio for a user."""
    payload = portfolio.dict()
    cash_balance = payload.get("cash_balance") or 0.0
    db_portfolio = models.Portfolio(
        **payload,
        user_id=user_id,
        total_value=cash_balance
    )
    db.add(db_portfolio)
    db.commit()
    db.refresh(db_portfolio)
    return db_portfolio


def get_user_portfolios(db: Session, user_id: int) -> List[models.Portfolio]:
    """Get all portfolios for a user."""
    return db.query(models.Portfolio).filter(
        and_(models.Portfolio.user_id == user_id, models.Portfolio.is_active == True)
    ).all()


def get_portfolio(db: Session, portfolio_id: int, user_id: int) -> Optional[models.Portfolio]:
    """Get a specific portfolio for a user."""
    return db.query(models.Portfolio).filter(
        and_(
            models.Portfolio.id == portfolio_id,
            models.Portfolio.user_id == user_id,
            models.Portfolio.is_active == True
        )
    ).first()


def get_portfolio_by_id(db: Session, portfolio_id: int, user_id: int) -> Optional[models.Portfolio]:
    """Get a specific portfolio by ID for a user."""
    return db.query(models.Portfolio).filter(
        and_(
            models.Portfolio.id == portfolio_id,
            models.Portfolio.user_id == user_id,
            models.Portfolio.is_active == True
        )
    ).first()


def update_portfolio_value(db: Session, portfolio_id: int) -> Optional[models.Portfolio]:
    """Update portfolio total value based on holdings."""
    portfolio = db.query(models.Portfolio).filter(models.Portfolio.id == portfolio_id).first()
    if not portfolio:
        return None
    
    total_holdings_value = sum([holding.total_value or 0 for holding in portfolio.holdings])
    portfolio.total_value = portfolio.cash_balance + total_holdings_value
    portfolio.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(portfolio)
    return portfolio


# Holding CRUD operations
def create_or_update_holding(db: Session, portfolio_id: int, holding_data: schemas.HoldingCreate) -> models.Holding:
    """Create a new holding or update existing one."""
    existing_holding = db.query(models.Holding).filter(
        and_(
            models.Holding.portfolio_id == portfolio_id,
            models.Holding.stock_code == holding_data.stock_code
        )
    ).first()
    
    if existing_holding:
        # Update existing holding (average price calculation)
        total_shares = existing_holding.shares + holding_data.shares
        if total_shares > 0:
            weighted_avg_price = (
                (existing_holding.shares * existing_holding.avg_purchase_price) +
                (holding_data.shares * holding_data.avg_purchase_price)
            ) / total_shares
            existing_holding.shares = total_shares
            existing_holding.avg_purchase_price = weighted_avg_price
        else:
            existing_holding.shares = 0
            
        db.commit()
        db.refresh(existing_holding)
        return existing_holding
    else:
        # Create new holding
        db_holding = models.Holding(
            portfolio_id=portfolio_id,
            **holding_data.dict()
        )
        db.add(db_holding)
        db.commit()
        db.refresh(db_holding)
        return db_holding


def get_portfolio_holdings(db: Session, portfolio_id: int) -> List[models.Holding]:
    """Get all holdings for a portfolio."""
    return db.query(models.Holding).filter(
        and_(
            models.Holding.portfolio_id == portfolio_id,
            models.Holding.shares > 0
        )
    ).all()


def update_holding_prices(db: Session, stock_code: str, current_price: float) -> List[models.Holding]:
    """Update current prices for all holdings of a stock."""
    holdings = db.query(models.Holding).filter(models.Holding.stock_code == stock_code).all()
    
    for holding in holdings:
        holding.current_price = current_price
        holding.total_value = holding.shares * current_price
        holding.unrealized_gain_loss = holding.total_value - (holding.shares * holding.avg_purchase_price)
        if holding.avg_purchase_price > 0:
            holding.unrealized_gain_loss_percentage = (
                holding.unrealized_gain_loss / (holding.shares * holding.avg_purchase_price)
            ) * 100
        holding.last_price_update = datetime.utcnow()
    
    db.commit()
    return holdings


# Transaction CRUD operations
def create_transaction(db: Session, transaction: schemas.TransactionCreate, portfolio_id: int) -> models.Transaction:
    """Create a new transaction."""
    # Get the portfolio to validate ownership
    portfolio = db.query(models.Portfolio).filter(models.Portfolio.id == portfolio_id).first()
    if not portfolio:
        raise ValueError("Portfolio not found")
    
    # Compute net cash flow amount:
    # - BUY: cash decreases by price + fees
    # - SELL: cash increases by price minus fees
    if transaction.transaction_type == 'SELL':
        total_amount = (transaction.shares * transaction.price_per_share) - (transaction.fees or 0)
    else:
        total_amount = (transaction.shares * transaction.price_per_share) + (transaction.fees or 0)
    
    # Check if SELL transaction has sufficient shares
    if transaction.transaction_type == 'SELL':
        holding = db.query(models.Holding).filter(
            models.Holding.portfolio_id == portfolio_id,
            models.Holding.stock_code == transaction.stock_code
        ).first()
        
        if not holding:
            raise ValueError(f"You don't own any shares of {transaction.stock_code}. Cannot sell what you don't own.")
        
        if holding.shares < transaction.shares:
            raise ValueError(f"Insufficient shares to sell. You own {holding.shares} shares but trying to sell {transaction.shares} shares of {transaction.stock_code}.")
        
        if holding.shares <= 0:
            raise ValueError(f"No shares available to sell for {transaction.stock_code}.")
    
    # Check if BUY transaction has sufficient cash
    if transaction.transaction_type == 'BUY':
        if portfolio.cash_balance < total_amount:
            raise ValueError("Insufficient cash balance")
    
    db_transaction = models.Transaction(
        user_id=portfolio.user_id,
        portfolio_id=portfolio_id,
        stock_code=transaction.stock_code,
        stock_name=transaction.stock_name,
        transaction_type=transaction.transaction_type,
        shares=transaction.shares,
        price_per_share=transaction.price_per_share,
        total_amount=total_amount,
        fees=transaction.fees or 0,
        notes=transaction.notes,
        recommended_by_ai=transaction.recommended_by_ai or False,
        reasoning=transaction.reasoning
    )
    
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)
    
    # Update portfolio holdings after transaction
    update_portfolio_holdings_after_transaction(db, db_transaction)
    
    return db_transaction


def get_user_transactions(
    db: Session, 
    user_id: int, 
    portfolio_id: Optional[int] = None,
    limit: int = 50
) -> List[models.Transaction]:
    """Get user transactions with optional portfolio filter."""
    query = db.query(models.Transaction).filter(models.Transaction.user_id == user_id)
    
    if portfolio_id:
        query = query.filter(models.Transaction.portfolio_id == portfolio_id)
    
    return query.order_by(desc(models.Transaction.transaction_date)).limit(limit).all()


def get_portfolio_transactions(db: Session, portfolio_id: int) -> List[models.Transaction]:
    """Get all transactions for a specific portfolio."""
    return db.query(models.Transaction).filter(
        models.Transaction.portfolio_id == portfolio_id
    ).order_by(desc(models.Transaction.transaction_date)).all()


# Simulation CRUD operations
def create_simulation(db: Session, simulation: schemas.PortfolioSimulationCreate, user_id: int) -> models.PortfolioSimulation:
    """Create a new portfolio simulation."""
    db_simulation = models.PortfolioSimulation(
        user_id=user_id,
        **simulation.dict()
    )
    db.add(db_simulation)
    db.commit()
    db.refresh(db_simulation)
    return db_simulation


def get_user_simulations(db: Session, user_id: int) -> List[models.PortfolioSimulation]:
    """Get all simulations for a user."""
    return db.query(models.PortfolioSimulation).filter(
        models.PortfolioSimulation.user_id == user_id
    ).order_by(desc(models.PortfolioSimulation.created_at)).all()


def update_simulation_results(
    db: Session, 
    simulation_id: int, 
    results: Dict[str, Any]
) -> Optional[models.PortfolioSimulation]:
    """Update simulation with results."""
    simulation = db.query(models.PortfolioSimulation).filter(
        models.PortfolioSimulation.id == simulation_id
    ).first()
    
    if not simulation:
        return None
    
    for key, value in results.items():
        if hasattr(simulation, key):
            setattr(simulation, key, value)
    
    simulation.status = "completed"
    simulation.completed_at = datetime.utcnow()
    
    db.commit()
    db.refresh(simulation)
    return simulation


# Analytics functions
def get_user_portfolio_performance(db: Session, user_id: int) -> Dict[str, Any]:
    """Get user's overall portfolio performance."""
    portfolios = get_user_portfolios(db, user_id)
    
    total_portfolio_value = sum([p.total_value or 0 for p in portfolios])
    total_cash = sum([p.cash_balance for p in portfolios])
    
    # Get recent transactions for performance calculation
    recent_transactions = get_user_transactions(db, user_id, limit=100)
    total_invested = sum([
        t.total_amount for t in recent_transactions 
        if t.transaction_type == 'BUY'
    ])
    
    total_return = total_portfolio_value - total_invested
    return_percentage = (total_return / total_invested * 100) if total_invested > 0 else 0
    
    return {
        "total_portfolio_value": total_portfolio_value,
        "total_cash": total_cash,
        "total_invested": total_invested,
        "total_return": total_return,
        "return_percentage": return_percentage,
        "number_of_portfolios": len(portfolios),
        "number_of_transactions": len(recent_transactions)
    }


def get_portfolio_equity_curve(db: Session, portfolio_id: int, days: int = 180) -> Dict[str, Any]:
    """Compute daily portfolio total value (equity curve) for the last `days` days.

    Returns a dict with:
    - history: list of {'date': 'YYYY-MM-DD', 'value': float, 'market_value': float, 'cash': float}
    - roi: overall ROI percentage vs initial capital
    - realized_pnl: realized P&L up to latest date
    - unrealized_pnl: unrealized P&L on latest date
    - max_drawdown: maximum drawdown (%) over the period
    - initial_capital: inferred initial cash at period start
    """
    from datetime import timedelta
    # Get portfolio without requiring a user_id (internal helper)
    portfolio = db.query(models.Portfolio).filter(models.Portfolio.id == portfolio_id).first()
    if not portfolio:
        return {}

    # Get transactions sorted ascending
    transactions = sorted(get_portfolio_transactions(db, portfolio_id), key=lambda t: t.transaction_date)

    # Totals across all transactions (used to infer initial cash)
    total_buy_amount = sum([t.total_amount for t in transactions if t.transaction_type == 'BUY'])
    total_sell_proceeds = sum([t.total_amount for t in transactions if t.transaction_type == 'SELL'])

    # Infer initial cash at the beginning of history
    current_cash = portfolio.cash_balance or 0.0
    initial_cash = current_cash + total_buy_amount - total_sell_proceeds

    # Determine date range
    today = datetime.utcnow().date()
    if transactions:
        earliest_tx_date = transactions[0].transaction_date.date()
        start_date = max(earliest_tx_date, today - timedelta(days=days))
    else:
        # No transactions - use portfolio created_at or default to last `days`
        start_date = (portfolio.created_at.date() if portfolio.created_at else (today - timedelta(days=days)))
        start_date = max(start_date, today - timedelta(days=days))

    dates = []
    current = start_date
    while current <= today:
        dates.append(current.strftime('%Y-%m-%d'))
        current += timedelta(days=1)

    # Collect unique symbols
    symbols = set([t.stock_code for t in transactions])

    # Fetch historical prices per symbol (for range) and map date->close
    price_cache = {}
    for sym in symbols:
        series = get_stock_history_by_symbol(sym, start=start_date.strftime('%Y-%m-%d'), end=today.strftime('%Y-%m-%d'))
        # build map date->close and fill forward later
        price_map = {p['date']: p['close'] for p in series if p.get('date')}
        price_cache[sym] = price_map

    history = []
    max_value = None
    min_value = None
    realized_cumulative = 0.0

    for date_str in dates:
        # For each symbol, compute shares held up to this date and cost basis
        market_value = 0.0
        holdings_shares = {}
        holdings_cost = {}

        # compute cash up to date (initial_cash minus buys + sells up to date)
        buys_up_to = sum([t.total_amount for t in transactions if t.transaction_type == 'BUY' and t.transaction_date.date() <= datetime.strptime(date_str, '%Y-%m-%d').date()])
        sells_up_to = sum([t.total_amount for t in transactions if t.transaction_type == 'SELL' and t.transaction_date.date() <= datetime.strptime(date_str, '%Y-%m-%d').date()])
        cash_on_date = initial_cash - buys_up_to + sells_up_to

        # for realized up to date: compute realized of sells up to date using cost basis tracking
        realized_up_to = 0.0
        cost_basis_tracker = {}
        for t in transactions:
            if t.transaction_date.date() > datetime.strptime(date_str, '%Y-%m-%d').date():
                continue
            sym = t.stock_code
            if sym not in cost_basis_tracker:
                cost_basis_tracker[sym] = {
                    'shares_bought': 0.0,
                    'cost': 0.0,
                    'avg_cost': 0.0
                }
            if t.transaction_type == 'BUY':
                cost_basis_tracker[sym]['shares_bought'] += t.shares
                cost_basis_tracker[sym]['cost'] += (t.shares * t.price_per_share)
                cost_basis_tracker[sym]['avg_cost'] = (cost_basis_tracker[sym]['cost'] / cost_basis_tracker[sym]['shares_bought']) if cost_basis_tracker[sym]['shares_bought'] > 0 else 0.0
            elif t.transaction_type == 'SELL':
                avg_cost = cost_basis_tracker[sym]['avg_cost'] if cost_basis_tracker[sym]['avg_cost'] else 0.0
                cost_of_sold = t.shares * avg_cost
                # t.total_amount is already proceeds minus fees for SELL
                realized_up_to += (t.total_amount - cost_of_sold)
                # reduce shares_bought (FIFO is not implemented; using simple avg cost method)
                cost_basis_tracker[sym]['shares_bought'] = max(0.0, cost_basis_tracker[sym]['shares_bought'] - t.shares)
                # adjust cost proportionally
                cost_basis_tracker[sym]['cost'] = max(0.0, cost_basis_tracker[sym]['cost'] - (t.shares * avg_cost))
                cost_basis_tracker[sym]['avg_cost'] = (cost_basis_tracker[sym]['cost'] / cost_basis_tracker[sym]['shares_bought']) if cost_basis_tracker[sym]['shares_bought'] > 0 else 0.0

        # compute shares held up to date using transactions
        shares_map = {}
        for t in transactions:
            if t.transaction_date.date() > datetime.strptime(date_str, '%Y-%m-%d').date():
                continue
            shares_map.setdefault(t.stock_code, 0.0)
            if t.transaction_type == 'BUY':
                shares_map[t.stock_code] += t.shares
            elif t.transaction_type == 'SELL':
                shares_map[t.stock_code] -= t.shares

        # Market value using price cache with backfill to last known price
        for sym, shares in shares_map.items():
            if shares <= 0:
                continue
            price_map = price_cache.get(sym, {})
            price = price_map.get(date_str)
            if price is None:
                # backfill: find last available price before date
                # get all dates in price_map <= date_str and choose the last
                available_dates = [d for d in price_map.keys() if d <= date_str]
                if available_dates:
                    last_date = sorted(available_dates)[-1]
                    price = price_map.get(last_date)
                else:
                    # as fallback use current holding price from DB if present
                    holding = next((h for h in portfolio.holdings if h.stock_code == sym), None)
                    price = holding.current_price if holding else 0.0
            market_value += (shares * (price or 0.0))

        total_value = market_value + cash_on_date

        # record history point
        history.append({
            'date': date_str,
            'value': round(total_value, 2),
            'market_value': round(market_value, 2),
            'cash': round(cash_on_date, 2),
            'realized': round(realized_up_to, 2)
        })

        # update realized_cumulative for final metric
        realized_cumulative = realized_up_to

        # track min/max for drawdown
        if max_value is None or total_value > max_value:
            max_value = total_value
        if min_value is None or total_value < min_value:
            min_value = total_value

    # compute ROI and P&L on latest
    if history:
        latest = history[-1]
        latest_value = latest['value']
        # Recompute cost basis across all transactions up to latest date to calculate unrealized P&L below
        final_cost_basis = 0.0
        shares_tracker = {}
        for t in transactions:
            if t.transaction_type == 'BUY':
                shares_tracker.setdefault(t.stock_code, {'shares':0.0,'cost':0.0})
                shares_tracker[t.stock_code]['shares'] += t.shares
                shares_tracker[t.stock_code]['cost'] += (t.shares * t.price_per_share)
            elif t.transaction_type == 'SELL':
                # reduce shares proportionally and cost using avg cost
                if t.stock_code in shares_tracker and shares_tracker[t.stock_code]['shares'] > 0:
                    avg_cost = (shares_tracker[t.stock_code]['cost'] / shares_tracker[t.stock_code]['shares']) if shares_tracker[t.stock_code]['shares']>0 else 0.0
                    shares_tracker[t.stock_code]['shares'] = max(0.0, shares_tracker[t.stock_code]['shares'] - t.shares)
                    shares_tracker[t.stock_code]['cost'] = max(0.0, shares_tracker[t.stock_code]['cost'] - (t.shares * avg_cost))

        for sym, info in shares_tracker.items():
            final_cost_basis += info['cost']

        unrealized_pnl = round((history[-1]['market_value'] - final_cost_basis), 2)
        realized_pnl = round(realized_cumulative, 2)
        initial_capital = round(initial_cash, 2)

        # compute max drawdown
        peak = -float('inf')
        max_dd = 0.0
        for point in history:
            val = point['value']
            if val > peak:
                peak = val
            dd = (peak - val) / peak * 100 if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd
    else:
        unrealized_pnl = 0.0
        realized_pnl = 0.0
        initial_capital = round(initial_cash, 2)
        max_dd = 0.0

    # If history is empty, synthesize a minimal two-point series so the UI can render an equity curve
    if not history:
        # Use portfolio creation date or start_date as first point
        first_date = start_date.strftime('%Y-%m-%d') if 'start_date' in locals() else (portfolio.created_at.strftime('%Y-%m-%d') if portfolio.created_at else datetime.utcnow().strftime('%Y-%m-%d'))
        # Use initial_cash as first value and current portfolio total_value as latest
        history = [
            {'date': first_date, 'value': round(initial_cash, 2), 'market_value': 0.0, 'cash': round(initial_cash,2), 'realized': 0.0},
            {'date': datetime.utcnow().strftime('%Y-%m-%d'), 'value': round(portfolio.total_value or 0.0, 2), 'market_value': round(portfolio.total_value - (portfolio.cash_balance or 0.0), 2), 'cash': round(portfolio.cash_balance or 0.0,2), 'realized': round(realized_cumulative, 2)}
        ]

    # Prefer analytics ROI if available for consistency with portfolio analytics endpoint
    try:
        from app.database import get_portfolio_pnl_and_roi
        analytics = get_portfolio_pnl_and_roi(db, portfolio_id, portfolio.user_id)
        analytics_roi = analytics.get('roi_percentage')
        if analytics_roi is not None:
            roi = round(float(analytics_roi), 2)
        else:
            roi = round(((history[-1]['value'] - initial_capital) / initial_capital * 100) if initial_capital>0 and history else 0.0, 2)

        # Use analytics realized/unrealized if present
        if 'realized_pnl' in analytics and analytics.get('realized_pnl') is not None:
            realized_pnl = analytics.get('realized_pnl')
        if 'unrealized_pnl' in analytics and analytics.get('unrealized_pnl') is not None:
            unrealized_pnl = analytics.get('unrealized_pnl')
    except Exception:
        # fallback calculation
        roi = round(((history[-1]['value'] - initial_capital) / initial_capital * 100) if initial_capital>0 and history else 0.0, 2)

    return {
        'history': history,
        'roi': roi,
        'realized_pnl': realized_pnl,
        'unrealized_pnl': unrealized_pnl,
        'max_drawdown': round(max_dd, 2),
        'initial_capital': initial_capital
    }


def get_user_risk_metrics(db: Session, user_id: int) -> Dict[str, Any]:
    """Calculate user's actual risk metrics based on their portfolio."""
    portfolios = get_user_portfolios(db, user_id)
    
    total_value = sum([p.total_value or 0 for p in portfolios])
    if total_value == 0:
        return {"diversification_score": 0, "concentration_risk": 0}
    
    # Get all holdings across portfolios
    all_holdings = []
    for portfolio in portfolios:
        all_holdings.extend(portfolio.holdings)
    
    # Calculate concentration risk
    max_position_percentage = 0
    if all_holdings:
        max_position_value = max([h.total_value or 0 for h in all_holdings])
        max_position_percentage = (max_position_value / total_value) * 100
    
    # Calculate diversification (simple version based on number of holdings)
    num_holdings = len([h for h in all_holdings if h.shares > 0])
    diversification_score = min(num_holdings * 10, 100)  # Max 100, 10 points per holding
    
    return {
        "diversification_score": diversification_score,
        "concentration_risk": max_position_percentage,
        "number_of_holdings": num_holdings,
        "total_portfolio_value": total_value
    }


def load_market_data_from_csv() -> Dict[str, Any]:
    """Load per-stock latest snapshot from data/historical_data.csv, aligned to a reference date.

    - Ensures rows are sorted by date and picks the last date per CODE (<= 2025-12-31)
    - Coerces numeric fields (handles percent signs, NBSP, commas)
    - Computes a safe daily_return_pct fallback if VARIATION is missing
    """
    csv_url = "data/historical_data.csv"
    try:
        df = pd.read_csv(csv_url)

        # Parse session date and use the latest date in the CSV as reference
        if 'SEANCE' in df.columns:
            df['SEANCE'] = pd.to_datetime(df['SEANCE'], errors='coerce')
            df = df[df['SEANCE'].notna()]
            # Dynamically detect the latest date from the data
            reference_date = df['SEANCE'].max()

        # Coerce numerics robustly (remove %, NBSP, commas -> dots)
        def _coerce_numeric(series: pd.Series) -> pd.Series:
            try:
                s = series.astype(str)
                s = s.str.replace('%', '', regex=False)
                s = s.str.replace('\u202f', '', regex=False)  # narrow no-break space
                s = s.str.replace('\xa0', '', regex=False)    # no-break space
                s = s.str.replace(',', '.', regex=False)
                return pd.to_numeric(s, errors='coerce')
            except Exception:
                return pd.to_numeric(series, errors='coerce')

        numeric_cols = [
            'CLOTURE', 'OUVERTURE', 'PLUS_HAUT', 'PLUS_BAS', 'QUANTITE_NEGOCIEE',
            'VARIATION', 'variation_z_score', 'volume_z_score',
            'TUNINDEX_INDICE_JOUR', 'TUNINDEX20_INDICE_JOUR'
        ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = _coerce_numeric(df[col])

        # Sort by CODE then date and pick the last date per stock
        if 'CODE' in df.columns:
            sort_cols = ['CODE'] + (['SEANCE'] if 'SEANCE' in df.columns else [])
            df = df.sort_values(sort_cols)
            if 'SEANCE' in df.columns:
                idx = df.groupby('CODE')['SEANCE'].idxmax()
                latest_data = df.loc[idx].reset_index(drop=True)
            else:
                # Fallback: take the last row per group if date missing
                latest_data = df.groupby('CODE').tail(1).reset_index(drop=True)
        else:
            latest_data = df

        market_data: Dict[str, Any] = {}
        for _, row in latest_data.iterrows():
            stock_code = str(row.get('CODE', '')).strip().upper()

            close_price = float(row['CLOTURE']) if pd.notna(row.get('CLOTURE')) else 0.0
            open_price = float(row['OUVERTURE']) if pd.notna(row.get('OUVERTURE')) else 0.0

            # Robust daily return: prefer VARIATION; fallback compute from open/close
            var = row.get('VARIATION')
            if pd.notna(var):
                daily_return_pct = float(var)
            else:
                daily_return_pct = ((close_price - open_price) / open_price * 100) if open_price else 0.0

            # Safe volume (handles NBSP and floats)
            vol_raw = row.get('QUANTITE_NEGOCIEE')
            volume = int(float(vol_raw)) if pd.notna(vol_raw) else 0

            # Anomaly: interpret 1/0 or truthy numbers/booleans correctly
            anomaly_val = row.get('VARIATION_ANOMALY') if 'VARIATION_ANOMALY' in row else 0
            try:
                anomaly_num = _coerce_numeric(pd.Series([anomaly_val])).iloc[0]
                anomaly_flag = bool(int(anomaly_num)) if pd.notna(anomaly_num) else False
            except Exception:
                anomaly_flag = False

            market_data[stock_code] = {
                'stock_code': stock_code,
                'stock_name': str(row.get('VALEUR', '')).strip(),
                'close_price': close_price,
                'open_price': open_price,
                'high_price': float(row['PLUS_HAUT']) if pd.notna(row.get('PLUS_HAUT')) else 0.0,
                'low_price': float(row['PLUS_BAS']) if pd.notna(row.get('PLUS_BAS')) else 0.0,
                'volume': volume,
                'date': row['SEANCE'].strftime('%Y-%m-%d') if pd.notna(row.get('SEANCE')) else str(row.get('SEANCE', '')),
                'anomaly': anomaly_flag,
                'anomaly_score': float(row['variation_z_score']) if pd.notna(row.get('variation_z_score')) else 0.0,
                'daily_return_pct': round(float(daily_return_pct), 6),
            }

        return market_data
    except Exception as e:
        print(f"Error loading market data: {e}")
        return {}


def get_stock_snapshot_by_symbol(symbol: str) -> Optional[Dict[str, Any]]:
    """Return the latest market snapshot for a stock code or name.

    Returns a dict with fields: stock_code, stock_name, close_price, open_price, high_price, low_price, volume, daily_return_pct, anomaly, anomaly_score, date
    """
    try:
        data = load_market_data_from_csv()
        symbol_up = str(symbol).strip().upper()
        # Direct code lookup
        if symbol_up in data:
            return data[symbol_up]
        # Try matching by name
        for code, info in data.items():
            if info.get('stock_name', '').upper() == symbol_up:
                return info
        return None
    except Exception as e:
        print(f"Error getting stock snapshot: {e}")
        return None


def load_predicted_market_data_from_csv() -> Dict[str, Any]:
    """Load predicted market data from forecast_next_5_days.csv.
    
    Data Source: data/forecast_next_5_days.csv
    Contains: 5-day price and volume forecasts for BVMT stocks.
    """
    csv_url = "data/forecast_next_5_days.csv"
    try:
        df = pd.read_csv(csv_url)
        # Group by stock code and get forecast data
        latest_data = df.groupby('CODE').last().reset_index()
        
        market_data = {}
        for _, row in latest_data.iterrows():
            stock_name=str(row['VALEUR']).strip()
            stock_code = row['CODE']
            price = float(row['CLOTURE']) if pd.notna(row['CLOTURE']) else 0
            market_data[stock_name] = {
                'stock_code': stock_code,
                'stock_name': stock_name,
                'current_price': price,
                'predicted_price': price,
                'volume': int(row['VOLUME']) if pd.notna(row['VOLUME']) else 0,
                'variation': float(row['VAR_CLOTURE']) if pd.notna(row['VAR_CLOTURE']) else 0,
                'prob_liquidity': float(row['PROB_LIQUIDITY']) if pd.notna(row.get('PROB_LIQUIDITY')) else 0,
                'date': str(row['SEANCE']),
                'anomaly': False,
                'anomaly_score': 0
            }

        return market_data

    except Exception as e:
        print(f"Error loading predicted market data: {e}")
        return {}



def get_stock_data_by_symbol(symbol: str) -> Optional[Dict[str, Any]]:
    """Get specific stock data by symbol (latest snapshot)."""
    market_data = load_market_data_from_csv()
    return market_data.get(symbol.upper())


def get_predicted_stock_data_by_symbol(symbol: str) -> Optional[Dict[str, Any]]:
    """Get specific predicted stock data by symbol."""
    market_data = load_predicted_market_data_from_csv()
    return market_data.get(symbol.upper())


def get_stock_history_by_symbol(symbol: str, start: Optional[str] = None, end: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return historical time series for a stock code or name (CLOTURE prices).

    Data Source: data/historical_data.csv
    Contains: Daily OHLCV data for BVMT stocks.

    Parameters:
    - symbol: stock code (e.g., 'TN0001100254') or stock name/symbol (e.g., 'SFBT')
    - start, end: optional ISO date strings (YYYY-MM-DD) to filter the range (inclusive)

    Returns a list of dicts: [{ 'date': 'YYYY-MM-DD', 'close': float }, ...] sorted ascending by date.
    """
    csv_url = "data/historical_data.csv"
    try:
        df = pd.read_csv(csv_url)
        # Normalize inputs and columns
        symbol_up = str(symbol).strip().upper()
        df['VALEUR'] = df['VALEUR'].astype(str).str.strip()
        df['CODE'] = df['CODE'].astype(str).str.strip()

        # Filter by CODE equals symbol or VALEUR equals symbol
        mask = (df['CODE'].str.upper() == symbol_up) | (df['VALEUR'].str.upper() == symbol_up)
        filtered = df[mask].copy()

        if filtered.empty:
            # No direct matches - try contains on VALEUR or CODE
            mask2 = df['CODE'].str.upper().str.contains(symbol_up, na=False) | df['VALEUR'].str.upper().str.contains(symbol_up, na=False)
            filtered = df[mask2].copy()

        if filtered.empty:
            return []

        # Parse dates
        filtered['SEANCE'] = pd.to_datetime(filtered['SEANCE'], errors='coerce')
        if start:
            start_dt = pd.to_datetime(start, errors='coerce')
            if not pd.isna(start_dt):
                filtered = filtered[filtered['SEANCE'] >= start_dt]
        if end:
            end_dt = pd.to_datetime(end, errors='coerce')
            if not pd.isna(end_dt):
                filtered = filtered[filtered['SEANCE'] <= end_dt]

        # Sort ascending by date
        filtered = filtered.sort_values('SEANCE')

        series = []
        for _, row in filtered.iterrows():
            date_str = row['SEANCE'].strftime('%Y-%m-%d') if not pd.isna(row['SEANCE']) else str(row.get('SEANCE', ''))
            close_val = row.get('CLOTURE')
            try:
                close_val = float(close_val) if not pd.isna(close_val) else None
            except Exception:
                close_val = None
            series.append({'date': date_str, 'close': close_val})

        return series
    except Exception as e:
        print(f"Error loading stock history: {e}")
        return []


def search_stocks_by_name(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Search stocks by name or code.
    
    Data Source: data/historical_data.csv
    """
    csv_url = "data/historical_data.csv"
    
    try:
        df = pd.read_csv(csv_url)
        df['VALEUR'] = df['VALEUR'].astype(str).str.strip()
        # Get unique stocks
        unique_stocks = df.drop_duplicates(['CODE', 'VALEUR'])
        
        # Filter by query
        query_upper = query.upper()
        filtered = unique_stocks[
            (unique_stocks['CODE'].str.contains(query_upper, na=False)) |
            (unique_stocks['VALEUR'].str.contains(query_upper, na=False))
        ].head(limit)
        
        results = []
        for _, row in filtered.iterrows():
            results.append({
                'stock_code': row['CODE'],
                'stock_name': row['VALEUR'],
                'close_price': row['CLOTURE']
            })
        
        return results
    except Exception as e:
        print(f"Error searching stocks: {e}")
        return []


def update_portfolio_holdings_after_transaction(db: Session, transaction: models.Transaction) -> None:
    """
    Update portfolio holdings after a transaction is created.
    This function modifies portfolio holdings and cash balance based on a buy or sell transaction.
    For buy transactions, it either updates existing holdings with new average price or creates
    new holdings, then deducts the transaction amount from portfolio cash. For sell transactions,
    it reduces the holding shares and adds the proceeds to portfolio cash. After the transaction,
    it updates current prices and portfolio total value.
    Args:
        db (Session): Database session for executing queries
        transaction (models.Transaction): Transaction object containing details like portfolio_id,
            user_id, stock_code, shares, price_per_share, transaction_type, and total_amount
    Returns:
        None
    Raises:
        ValueError: If attempting to sell more shares than currently held in the portfolio
    Note:
        This function requires the following undefined functions to be implemented:
        - get_portfolio_by_id: Retrieve portfolio by ID and user ID
        - get_stock_data_by_symbol: Get current stock price data
        - update_portfolio_total_value: Recalculate total portfolio value
    """
    """Update portfolio holdings after a transaction is created."""
    portfolio = get_portfolio_by_id(db, transaction.portfolio_id, transaction.user_id)
    if not portfolio:
        return
    
    # Find existing holding or create new one
    holding = db.query(models.Holding).filter(
        models.Holding.portfolio_id == transaction.portfolio_id,
        models.Holding.stock_code == transaction.stock_code
    ).first()
    
    if transaction.transaction_type == 'BUY':
        if holding:
            # Update existing holding - calculate new average price
            total_cost = (holding.shares * holding.avg_purchase_price) + (transaction.shares * transaction.price_per_share)
            total_shares = holding.shares + transaction.shares
            holding.avg_purchase_price = total_cost / total_shares
            holding.shares = total_shares
        else:
            # Create new holding
            holding = models.Holding(
                portfolio_id=transaction.portfolio_id,
                stock_code=transaction.stock_code,
                stock_name=transaction.stock_name,
                shares=transaction.shares,
                avg_purchase_price=transaction.price_per_share
            )
            db.add(holding)
        
        # Update portfolio cash balance
        portfolio.cash_balance -= transaction.total_amount
        
    elif transaction.transaction_type == 'SELL':
        if holding and holding.shares >= transaction.shares:
            holding.shares -= transaction.shares
            if holding.shares == 0:
                # Remove holding if no shares left
                db.delete(holding)
            
            # Update portfolio cash balance
            portfolio.cash_balance += transaction.total_amount
        else:
            raise ValueError("Insufficient shares to sell")
    
    # Update holding current price and values
    if holding and holding.shares > 0:
        stock_data = get_stock_data_by_symbol(holding.stock_code)
        if stock_data:
            holding.current_price = stock_data['close_price']
            holding.total_value = holding.shares * holding.current_price
            holding.unrealized_gain_loss = holding.total_value - (holding.shares * holding.avg_purchase_price)
            if holding.avg_purchase_price > 0:
                holding.unrealized_gain_loss_percentage = (holding.unrealized_gain_loss / (holding.shares * holding.avg_purchase_price)) * 100
    
    # Update portfolio total value
    update_portfolio_total_value(db, portfolio.id)
    
    db.commit()


def update_portfolio_total_value(db: Session, portfolio_id: int) -> None:
    """Update the total value of a portfolio based on holdings."""
    portfolio = db.query(models.Portfolio).filter(models.Portfolio.id == portfolio_id).first()
    if not portfolio:
        return
    
    holdings = db.query(models.Holding).filter(models.Holding.portfolio_id == portfolio_id).all()
    
    holdings_value = 0
    for holding in holdings:
        if holding.current_price:
            holdings_value += holding.shares * holding.current_price
        else:
            holdings_value += holding.shares * holding.avg_purchase_price
    
    portfolio.total_value = holdings_value + (portfolio.cash_balance or 0)
    portfolio.updated_at = datetime.utcnow()
    
    db.commit()


def get_tunindex_history(days: int = 30, index_type: str = 'tunindex') -> Dict[str, Any]:
    """Get TUNINDEX or TUNINDEX20 historical data.
    
    Data Source: data/historical_data.csv
    Columns: TUNINDEX_INDICE_JOUR, TUNINDEX20_INDICE_JOUR
    
    Args:
        days: Number of days of history to return
        index_type: 'tunindex' or 'tunindex20'
    """
    #csv_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'historical_data.csv')
    csv_url = "data/historical_data.csv"
    try:
        df = pd.read_csv(csv_url)
        df['SEANCE'] = pd.to_datetime(df['SEANCE'], errors='coerce')
        df = df[df['SEANCE'].notna()]
        
        # Dynamically detect the latest date from the data
        REFERENCE_DATE = df['SEANCE'].max()
        
        # Choose column based on index type
        index_column = 'TUNINDEX20_INDICE_JOUR' if index_type == 'tunindex20' else 'TUNINDEX_INDICE_JOUR'
        
        # Get unique dates with index values
        tunindex_data = df.groupby('SEANCE').agg({
            index_column: 'first',
            'VARIATION': 'mean'
        }).reset_index()
        
        # Sort by date descending and take last N days
        tunindex_data = tunindex_data.sort_values('SEANCE', ascending=False).head(days)
        tunindex_data = tunindex_data.sort_values('SEANCE', ascending=True)
        
        # Format response
        history = []
        for _, row in tunindex_data.iterrows():
            if pd.notna(row[index_column]):
                history.append({
                    'date': row['SEANCE'].strftime('%Y-%m-%d'),
                    'value': round(float(row[index_column]), 2)
                })
        
        if history:
            # Calculate current value and change
            latest = history[-1]
            previous = history[-2] if len(history) > 1 else history[-1]
            change = latest['value'] - previous['value']
            change_percent = (change / previous['value'] * 100) if previous['value'] > 0 else 0
            
            return {
                'history': history,
                'current': {
                    'value': latest['value'],
                    'change': round(change, 2),
                    'changePercent': round(change_percent, 2)
                },
                'lastDate': latest['date'],
                'indexType': index_type
            }
        
        return {'history': [], 'current': {'value': 0, 'change': 0, 'changePercent': 0}, 'lastDate': None, 'indexType': index_type}
    
    except Exception as e:
        print(f"Error loading TUNINDEX data: {e}")
        return {'history': [], 'current': {'value': 0, 'change': 0, 'changePercent': 0}, 'lastDate': None, 'indexType': index_type}


def get_market_mood(date: str = None) -> Dict[str, Any]:
    """Get market mood/sentiment for a specific date or latest available.
    
    Data Source: data/historical_data.csv
    Columns: MarketMood, DirectionScore, BreadthScore, IntensityScore, LiquidityScore, NewsScore
    """
    #csv_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'historical_data.csv')
    csv_url = "data/historical_data.csv"
    try:
        df = pd.read_csv(csv_url)
        df['SEANCE'] = pd.to_datetime(df['SEANCE'], errors='coerce')
        df = df[df['SEANCE'].notna()]
        
        # Dynamically detect the latest date from the data
        REFERENCE_DATE = df['SEANCE'].max()
        
        # Get unique dates with MarketMood values
        mood_data = df.groupby('SEANCE').agg({
            'MarketMood': 'mean',
            'DirectionScore': 'mean',
            'BreadthScore': 'mean',
            'IntensityScore': 'mean',
            'LiquidityScore': 'mean',
            'NewsScore': 'mean'
        }).reset_index()
        
        mood_data = mood_data.sort_values('SEANCE', ascending=False)
        
        if date:
            target_date = pd.to_datetime(date, errors='coerce')
            mood_row = mood_data[mood_data['SEANCE'] == target_date]
            if mood_row.empty:
                # Get closest date before target
                mood_row = mood_data[mood_data['SEANCE'] <= target_date].head(1)
        else:
            # Use reference date (latest in filtered data)
            mood_row = mood_data.head(1)
        
        if mood_row.empty:
            return {'mood': 50, 'date': None, 'scores': {}}
        
        row = mood_row.iloc[0]
        
        # MarketMood is already a score, normalize to 0-100 scale
        mood_value = float(row['MarketMood']) if pd.notna(row['MarketMood']) else 50
        # The MarketMood in the CSV seems to be a raw score, normalize it
        # Based on the data, it ranges from about 0-100, so use it directly
        mood_normalized = max(0, min(100, mood_value))
        
        return {
            'mood': round(mood_normalized, 1),
            'date': row['SEANCE'].strftime('%Y-%m-%d'),
            'scores': {
                'direction': round(float(row['DirectionScore']) if pd.notna(row['DirectionScore']) else 0, 1),
                'breadth': round(float(row['BreadthScore']) if pd.notna(row['BreadthScore']) else 0, 1),
                'intensity': round(float(row['IntensityScore']) if pd.notna(row['IntensityScore']) else 0, 1),
                'liquidity': round(float(row['LiquidityScore']) if pd.notna(row['LiquidityScore']) else 0, 1),
                'news': round(float(row['NewsScore']) if pd.notna(row['NewsScore']) else 0, 1)
            }
        }
    
    except Exception as e:
        print(f"Error loading market mood: {e}")
        return {'mood': 50, 'date': None, 'scores': {}}


def get_top_gainers_losers(date: str = None) -> Dict[str, Any]:
    """Get top 5 gainers and losers for a given date.
    
    Data Source: data/historical_data.csv
    Columns: VALEUR, CODE, CLOTURE, VARIATION
    """
    csv_url = "data/historical_data.csv"
    try:
        df = pd.read_csv(csv_url)
        df['SEANCE'] = pd.to_datetime(df['SEANCE'], errors='coerce')
        df = df[df['SEANCE'].notna()]
        
        # Dynamically detect the latest date from the data
        REFERENCE_DATE = df['SEANCE'].max()
        
        # Get the target date or reference date (latest in filtered data)
        if date:
            target_date = pd.to_datetime(date, errors='coerce')
        else:
            target_date = REFERENCE_DATE
        
        # Filter for the target date
        day_data = df[df['SEANCE'] == target_date].copy()
        
        if day_data.empty:
            # Try to get the closest previous date
            available_dates = df['SEANCE'].dropna().unique()
            available_dates = sorted(available_dates, reverse=True)
            for d in available_dates:
                if d <= target_date:
                    target_date = d
                    break
            day_data = df[df['SEANCE'] == target_date].copy()
        
        if day_data.empty:
            return {'gainers': [], 'losers': [], 'date': None}
        
        # Get top 5 gainers (highest positive variation)
        gainers = day_data.nlargest(5, 'VARIATION')[['VALEUR', 'CODE', 'CLOTURE', 'VARIATION']].to_dict('records')
        
        # Get top 5 losers (most negative variation)
        losers = day_data.nsmallest(5, 'VARIATION')[['VALEUR', 'CODE', 'CLOTURE', 'VARIATION']].to_dict('records')
        
        def format_mover(row):
            return {
                'symbol': str(row['VALEUR']).strip(),
                'code': str(row['CODE']).strip(),
                'name': str(row['VALEUR']).strip(),
                'price': round(float(row['CLOTURE']), 2) if pd.notna(row['CLOTURE']) else 0,
                'change': round(float(row['VARIATION']), 2) if pd.notna(row['VARIATION']) else 0,
                'changePercent': round(float(row['VARIATION']), 2) if pd.notna(row['VARIATION']) else 0
            }
        
        s= {
            'gainers': [format_mover(g) for g in gainers if pd.notna(g['VARIATION']) and g['VARIATION'] > 0],
            'losers': [format_mover(l) for l in losers if pd.notna(l['VARIATION']) and l['VARIATION'] < 0],
            'date': target_date.strftime('%Y-%m-%d') if pd.notna(target_date) else None
        }
        print(f"Top movers for {s['date']}: {len(s['gainers'])} gainers, {len(s['losers'])} losers")
        return s
    
    
    except Exception as e:
        print(f"Error loading top movers: {e}")
        return {'gainers': [], 'losers': [], 'date': None}


def get_market_alerts(limit: int = 500) -> List[Dict[str, Any]]:
    """Get market alerts based on anomalies detected.
    
    Data Source: data/historical_data.csv
    
    Alert Types:
    - 'volume': Based on VOLUME_Anomaly column
    - 'price': Based on VARIATION_ANOMALY column  
    - 'news': Based on VARIATION_ANOMALY_POST_NEWS, VARIATION_ANOMALY_PRE_NEWS, 
              VOLUME_ANOMALY_POST_NEWS, VOLUME_ANOMALY_PRE_NEWS columns
    
    Returns all anomalies sorted by date (newest first) for frontend pagination.
    """
    csv_url = "data/historical_data.csv"
    try:
        df = pd.read_csv(csv_url)
        df['SEANCE'] = pd.to_datetime(df['SEANCE'], errors='coerce')
        df = df[df['SEANCE'].notna()]
        
        # Dynamically detect the latest date from the data
        REFERENCE_DATE = df['SEANCE'].max()
        
        alerts = []
        
        # ===== VOLUME ANOMALIES (based on VOLUME_Anomaly column) =====
        volume_anomalies = df[df['VOLUME_Anomaly'] == 1].copy()
        for _, row in volume_anomalies.iterrows():
            z_score = row.get('volume_z_score')
            alerts.append({
                'id': f"vol_{row['CODE']}_{row['SEANCE'].strftime('%Y%m%d') if pd.notna(row['SEANCE']) else 'unknown'}",
                'symbol': str(row['VALEUR']).strip(),
                'code': str(row['CODE']).strip(),
                'message': f"Unusual volume detected - {z_score:.1f}x standard deviation" if pd.notna(z_score) else "Unusual trading volume detected",
                'severity': 'high' if pd.notna(z_score) and abs(z_score) > 3 else 'medium',
                'timestamp': row['SEANCE'].isoformat() if pd.notna(row['SEANCE']) else '',
                'date': row['SEANCE'].strftime('%Y-%m-%d') if pd.notna(row['SEANCE']) else '',
                'type': 'volume',
                'value': float(row['CLOTURE']) if pd.notna(row.get('CLOTURE')) else None,
                'change': float(row['VARIATION']) if pd.notna(row.get('VARIATION')) else None,
                'score': float(z_score) if pd.notna(z_score) else None
            })
        
        # ===== PRICE ANOMALIES (based on VARIATION_ANOMALY column) =====
        price_anomalies = df[df['VARIATION_ANOMALY'] == 1].copy()
        for _, row in price_anomalies.iterrows():
            variation = row['VARIATION'] if pd.notna(row['VARIATION']) else 0
            z_score = row.get('variation_z_score')
            alerts.append({
                'id': f"price_{row['CODE']}_{row['SEANCE'].strftime('%Y%m%d') if pd.notna(row['SEANCE']) else 'unknown'}",
                'symbol': str(row['VALEUR']).strip(),
                'code': str(row['CODE']).strip(),
                'message': f"Significant price {'increase' if variation > 0 else 'drop'} detected ({variation:+.2f}%)",
                'severity': 'high' if abs(variation) > 5 else 'medium',
                'timestamp': row['SEANCE'].isoformat() if pd.notna(row['SEANCE']) else '',
                'date': row['SEANCE'].strftime('%Y-%m-%d') if pd.notna(row['SEANCE']) else '',
                'type': 'price',
                'value': float(row['CLOTURE']) if pd.notna(row.get('CLOTURE')) else None,
                'change': float(variation),
                'score': float(z_score) if pd.notna(z_score) else None
            })
        
        # ===== NEWS ANOMALIES (based on 4 news columns) =====
        # Post-news price anomalies
        news_var_post = df[df['VARIATION_ANOMALY_POST_NEWS'] == 1].copy()
        for _, row in news_var_post.iterrows():
            variation = row['VARIATION'] if pd.notna(row['VARIATION']) else 0
            alerts.append({
                'id': f"news_var_post_{row['CODE']}_{row['SEANCE'].strftime('%Y%m%d') if pd.notna(row['SEANCE']) else 'unknown'}",
                'symbol': str(row['VALEUR']).strip(),
                'code': str(row['CODE']).strip(),
                'message': f"News reaction: Price {'surge' if variation > 0 else 'drop'} after news ({variation:+.2f}%)",
                'severity': 'high' if abs(variation) > 3 else 'medium',
                'timestamp': row['SEANCE'].isoformat() if pd.notna(row['SEANCE']) else '',
                'date': row['SEANCE'].strftime('%Y-%m-%d') if pd.notna(row['SEANCE']) else '',
                'type': 'news',
                'subtype': 'reaction',
                'value': float(row['CLOTURE']) if pd.notna(row.get('CLOTURE')) else None,
                'change': float(variation),
                'score': float(row.get('variation_z_score')) if pd.notna(row.get('variation_z_score')) else None
            })
        
        # Pre-news price anomalies (potential leakage)
        news_var_pre = df[df['VARIATION_ANOMALY_PRE_NEWS'] == 1].copy()
        for _, row in news_var_pre.iterrows():
            variation = row['VARIATION'] if pd.notna(row['VARIATION']) else 0
            alerts.append({
                'id': f"news_var_pre_{row['CODE']}_{row['SEANCE'].strftime('%Y%m%d') if pd.notna(row['SEANCE']) else 'unknown'}",
                'symbol': str(row['VALEUR']).strip(),
                'code': str(row['CODE']).strip(),
                'message': f"Possible leakage: Price movement before news ({variation:+.2f}%)",
                'severity': 'high',
                'timestamp': row['SEANCE'].isoformat() if pd.notna(row['SEANCE']) else '',
                'date': row['SEANCE'].strftime('%Y-%m-%d') if pd.notna(row['SEANCE']) else '',
                'type': 'news',
                'subtype': 'leakage',
                'value': float(row['CLOTURE']) if pd.notna(row.get('CLOTURE')) else None,
                'change': float(variation),
                'score': float(row.get('variation_z_score')) if pd.notna(row.get('variation_z_score')) else None
            })
        
        # Post-news volume anomalies
        news_vol_post = df[df['VOLUME_ANOMALY_POST_NEWS'] == 1].copy()
        for _, row in news_vol_post.iterrows():
            z_score = row.get('volume_z_score')
            alerts.append({
                'id': f"news_vol_post_{row['CODE']}_{row['SEANCE'].strftime('%Y%m%d') if pd.notna(row['SEANCE']) else 'unknown'}",
                'symbol': str(row['VALEUR']).strip(),
                'code': str(row['CODE']).strip(),
                'message': f"News reaction: Volume spike after news release",
                'severity': 'medium',
                'timestamp': row['SEANCE'].isoformat() if pd.notna(row['SEANCE']) else '',
                'date': row['SEANCE'].strftime('%Y-%m-%d') if pd.notna(row['SEANCE']) else '',
                'type': 'news',
                'subtype': 'volume_reaction',
                'value': float(row['CLOTURE']) if pd.notna(row.get('CLOTURE')) else None,
                'change': float(row['VARIATION']) if pd.notna(row.get('VARIATION')) else None,
                'score': float(z_score) if pd.notna(z_score) else None
            })
        
        # Pre-news volume anomalies (potential leakage)
        news_vol_pre = df[df['VOLUME_ANOMALY_PRE_NEWS'] == 1].copy()
        for _, row in news_vol_pre.iterrows():
            z_score = row.get('volume_z_score')
            alerts.append({
                'id': f"news_vol_pre_{row['CODE']}_{row['SEANCE'].strftime('%Y%m%d') if pd.notna(row['SEANCE']) else 'unknown'}",
                'symbol': str(row['VALEUR']).strip(),
                'code': str(row['CODE']).strip(),
                'message': f"Possible leakage: Volume spike before news release",
                'severity': 'high',
                'timestamp': row['SEANCE'].isoformat() if pd.notna(row['SEANCE']) else '',
                'date': row['SEANCE'].strftime('%Y-%m-%d') if pd.notna(row['SEANCE']) else '',
                'type': 'news',
                'subtype': 'volume_leakage',
                'value': float(row['CLOTURE']) if pd.notna(row.get('CLOTURE')) else None,
                'change': float(row['VARIATION']) if pd.notna(row.get('VARIATION')) else None,
                'score': float(z_score) if pd.notna(z_score) else None
            })
        
        # Remove duplicates by ID and sort by date (newest first)
        seen_ids = set()
        unique_alerts = []
        for alert in sorted(alerts, key=lambda x: x.get('timestamp', ''), reverse=True):
            if alert['id'] not in seen_ids:
                seen_ids.add(alert['id'])
                unique_alerts.append(alert)
        
        return unique_alerts[:limit]
    
    except Exception as e:
        print(f"Error loading market alerts: {e}")
        return []


def get_stock_history_with_forecast(symbol: str, start: str = None, end: str = None) -> Dict[str, Any]:
    """Get stock history combined with 5-day forecast.
    
    Data Sources:
    - Historical: data/historical_data.csv (OHLCV, anomalies, sentiment indicators)
    - Forecast: data/forecast_next_5_days.csv (5-day price/volume predictions)
    """
    csv_url = "data/historical_data.csv"
    forecast_csv = "data/forecast_next_5_days.csv"
    try:
        df_history = pd.read_csv(csv_url)
        df_history['SEANCE'] = pd.to_datetime(df_history['SEANCE'], errors='coerce')
        
        # Normalize symbol
        symbol_up = str(symbol).strip().upper()
        
        # Filter historical data
        mask = (df_history['CODE'].astype(str).str.strip().str.upper() == symbol_up) | \
               (df_history['VALEUR'].astype(str).str.strip().str.upper() == symbol_up)
        filtered_history = df_history[mask].copy()
        
        if filtered_history.empty:
            # Try contains match
            mask2 = df_history['VALEUR'].astype(str).str.upper().str.contains(symbol_up, na=False)
            filtered_history = df_history[mask2].copy()
        
        # Apply date filters
        if start:
            start_dt = pd.to_datetime(start, errors='coerce')
            if pd.notna(start_dt):
                filtered_history = filtered_history[filtered_history['SEANCE'] >= start_dt]
        if end:
            end_dt = pd.to_datetime(end, errors='coerce')
            if pd.notna(end_dt):
                filtered_history = filtered_history[filtered_history['SEANCE'] <= end_dt]
        
        filtered_history = filtered_history.sort_values('SEANCE')
        
        # Build history list with anomaly data
        history = []
        stock_code = None
        stock_name = None
        last_historical_price = None
        last_historical_variation = None
        for _, row in filtered_history.iterrows():
            if stock_code is None:
                stock_code = row['CODE']
                stock_name = str(row['VALEUR']).strip()
            
            price = float(row['CLOTURE']) if pd.notna(row['CLOTURE']) else 0
            variation = float(row['VARIATION']) if pd.notna(row['VARIATION']) else 0
            last_historical_price = price
            last_historical_variation = variation
            
            history.append({
                'date': row['SEANCE'].strftime('%Y-%m-%d') if pd.notna(row['SEANCE']) else '',
                'price': price,
                'close': price,
                'open': float(row['OUVERTURE']) if pd.notna(row['OUVERTURE']) else 0,
                'high': float(row['PLUS_HAUT']) if pd.notna(row['PLUS_HAUT']) else 0,
                'low': float(row['PLUS_BAS']) if pd.notna(row['PLUS_BAS']) else 0,
                'volume': int(row['QUANTITE_NEGOCIEE']) if pd.notna(row['QUANTITE_NEGOCIEE']) else 0,
                'variation': variation,
                'isPrediction': False,
                # Price/Variation Anomaly data - 3 types
                'variationAnomaly': bool(row['VARIATION_ANOMALY']) if pd.notna(row.get('VARIATION_ANOMALY')) else False,
                'variationAnomalyPostNews': bool(row['VARIATION_ANOMALY_POST_NEWS']) if pd.notna(row.get('VARIATION_ANOMALY_POST_NEWS')) else False,
                'variationAnomalyPreNews': bool(row['VARIATION_ANOMALY_PRE_NEWS']) if pd.notna(row.get('VARIATION_ANOMALY_PRE_NEWS')) else False,
                # Volume Anomaly data - 3 types
                'volumeAnomaly': bool(row['VOLUME_Anomaly']) if pd.notna(row.get('VOLUME_Anomaly')) else False,
                'volumeAnomalyPostNews': bool(row['VOLUME_ANOMALY_POST_NEWS']) if pd.notna(row.get('VOLUME_ANOMALY_POST_NEWS')) else False,
                'volumeAnomalyPreNews': bool(row['VOLUME_ANOMALY_PRE_NEWS']) if pd.notna(row.get('VOLUME_ANOMALY_PRE_NEWS')) else False,
                # Z-scores
                'volumeZScore': float(row['volume_z_score']) if pd.notna(row.get('volume_z_score')) else 0,
                'variationZScore': float(row['variation_z_score']) if pd.notna(row.get('variation_z_score')) else 0,
                # Sentiment/News data
                'newsScore': float(row['NewsScore']) if pd.notna(row.get('NewsScore')) else 0,
                'marketMood': float(row['MarketMood']) if pd.notna(row.get('MarketMood')) else 0,
                'articleCount': int(row['Article_Count']) if pd.notna(row.get('Article_Count')) else 0
            })
        
        # Load forecast data
        forecast = []
        if stock_code:
            df_forecast = pd.read_csv(forecast_csv)
            df_forecast['SEANCE'] = pd.to_datetime(df_forecast['SEANCE'], errors='coerce')
            
            # Filter by CODE
            forecast_mask = df_forecast['CODE'].astype(str).str.strip() == str(stock_code).strip()
            filtered_forecast = df_forecast[forecast_mask].copy()
            
            if filtered_forecast.empty:
                # Try by VALEUR
                forecast_mask2 = df_forecast['VALEUR'].astype(str).str.strip().str.upper() == symbol_up
                filtered_forecast = df_forecast[forecast_mask2].copy()
            
            filtered_forecast = filtered_forecast.sort_values('SEANCE')
            
            for _, row in filtered_forecast.iterrows():
                forecast.append({
                    'date': row['SEANCE'].strftime('%Y-%m-%d') if pd.notna(row['SEANCE']) else '',
                    'price': float(row['CLOTURE']) if pd.notna(row['CLOTURE']) else 0,
                    'close': float(row['CLOTURE']) if pd.notna(row['CLOTURE']) else 0,
                    'volume': int(row['VOLUME']) if pd.notna(row['VOLUME']) else 0,
                    'variation': float(row['VAR_CLOTURE']) if pd.notna(row['VAR_CLOTURE']) else 0,
                    'probLiquidity': float(row['PROB_LIQUIDITY']) if pd.notna(row.get('PROB_LIQUIDITY')) else 0,
                    'isPrediction': True,
                    'volumeAnomaly': False,
                    'variationAnomaly': False,
                    'variationAnomalyPostNews': False,
                    'variationAnomalyPreNews': False,
                    'volumeAnomalyPostNews': False,
                    'volumeAnomalyPreNews': False
                })
        
        # Combine history and forecast
        combined = history + forecast
        
        # Get last historical date
        last_history_date = history[-1]['date'] if history else None
        
        return {
            'history': history,
            'forecast': forecast,
            'combined': combined,
            'lastHistoricalDate': last_history_date,
            'lastHistoricalPrice': last_historical_price,
            'lastHistoricalVariation': last_historical_variation,
            'symbol': symbol,
            'code': stock_code,
            'name': stock_name
        }
    
    except Exception as e:
        print(f"Error loading stock history with forecast: {e}")
        return {'history': [], 'forecast': [], 'combined': [], 'lastHistoricalDate': None, 'symbol': symbol}


def get_stock_sentiment_history(symbol: str, start: str = None, end: str = None) -> Dict[str, Any]:
    """Get sentiment data for a stock.
    
    Data Source: data/sentiment_features.csv
    Columns: VALEUR, SEANCE, Mean_Weighted_Sentiment, Article_Count, Sentiment_Intensity
    """
    csv_url = "data/sentiment_features.csv"
    try:
        df = pd.read_csv(csv_url)
        df['SEANCE'] = pd.to_datetime(df['SEANCE'], errors='coerce')
        
        # Normalize symbol - handle URL encoding and strip
        symbol_clean = str(symbol).strip().upper()
        
        # Try exact match first
        mask = df['VALEUR'].astype(str).str.strip().str.upper() == symbol_clean
        filtered = df[mask].copy()
        
        if filtered.empty:
            # Try if symbol contains any VALEUR
            for valeur in df['VALEUR'].unique():
                valeur_up = str(valeur).strip().upper()
                if valeur_up in symbol_clean or symbol_clean in valeur_up:
                    mask2 = df['VALEUR'].astype(str).str.strip().str.upper() == valeur_up
                    filtered = df[mask2].copy()
                    if not filtered.empty:
                        break
        
        if filtered.empty:
            # Try contains match as fallback
            mask3 = df['VALEUR'].astype(str).str.upper().str.contains(symbol_clean, na=False, regex=False)
            filtered = df[mask3].copy()
        
        # Apply date filters
        if start:
            start_dt = pd.to_datetime(start, errors='coerce')
            if pd.notna(start_dt):
                filtered = filtered[filtered['SEANCE'] >= start_dt]
        if end:
            end_dt = pd.to_datetime(end, errors='coerce')
            if pd.notna(end_dt):
                filtered = filtered[filtered['SEANCE'] <= end_dt]
        
        filtered = filtered.sort_values('SEANCE')
        
        # Build sentiment list
        sentiment = []
        for _, row in filtered.iterrows():
            # Mean_Weighted_Sentiment ranges from -1 to 1, normalize to 0-100
            raw_sentiment = float(row['Mean_Weighted_Sentiment']) if pd.notna(row['Mean_Weighted_Sentiment']) else 0
            normalized_sentiment = (raw_sentiment + 1) * 50  # -1 -> 0, 0 -> 50, 1 -> 100
            
            sentiment.append({
                'date': row['SEANCE'].strftime('%Y-%m-%d') if pd.notna(row['SEANCE']) else '',
                'sentiment': round(normalized_sentiment, 1),
                'rawSentiment': round(raw_sentiment, 3),
                'articleCount': int(row['Article_Count']) if pd.notna(row['Article_Count']) else 0,
                'intensity': float(row['Sentiment_Intensity']) if pd.notna(row['Sentiment_Intensity']) else 0
            })
        
        return {
            'data': sentiment,
            'symbol': symbol,
            'count': len(sentiment)
        }
    
    except Exception as e:
        print(f"Error loading sentiment data: {e}")
        return {'data': [], 'symbol': symbol, 'count': 0}
