from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase,Session

DATABASE_URL = "sqlite:///./users.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # required for SQLite + threads
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



def get_user_by_id(db, user_id: str):
    from . import models
    user_id= int(user_id)
    user= db.query(models.User).filter(models.User.id == user_id).first()
    return {
        "id": user.id,
        "name": user.username,
        "email": user.email,
        "risk_score": user.risk_score,
        "risk_level": user.risk_level,
        "investment_style": user.investment_style,
        "stocks": [{"symbol": stock.stock_name.strip(), "quantity": stock.shares} for portfolio in user.portfolios for stock in portfolio.holdings]
    }

def get_user_portfolio(db, user_id: str):
    from . import models
    user_id= int(user_id)
    user= db.query(models.User).filter(models.User.id == user_id).first()
    portfolio_ids = []
    portfolio_ids.extend(portfolio.id for portfolio in user.portfolios)
    return portfolio_ids


def get_portfolio_pnl_and_roi(db: Session, portfolio_id: int, user_id: int) -> dict:
    """
    Calculate detailed P&L and ROI for a specific portfolio.
    
    Returns:
    - realized_pnl: Profit/loss from completed sell transactions
    - unrealized_pnl: Current profit/loss from holdings
    - total_pnl: Total profit/loss (realized + unrealized)
    - total_invested: Total amount invested (buy transactions - sell proceeds)
    - current_value: Current portfolio value (cash + holdings)
    - roi_percentage: Return on investment percentage
    """
    from . import crud
    portfolio = crud.get_portfolio_by_id(db, portfolio_id, user_id)
    if not portfolio:
        return {}
    
    # Get all transactions for this portfolio
    transactions = crud.get_portfolio_transactions(db, portfolio_id)
    
    # Calculate total invested and realized P&L
    total_buy_amount = 0
    total_sell_proceeds = 0
    realized_pnl = 0
    stock_positions = {}  # Track cost basis for each stock
    
    for transaction in transactions:
        if transaction.transaction_type == 'BUY':
            total_buy_amount += transaction.total_amount
            
            # Track cost basis for P&L calculation
            if transaction.stock_code not in stock_positions:
                stock_positions[transaction.stock_code] = {
                    'total_shares_bought': 0,
                    'total_cost': 0,
                    'shares_sold': 0,
                    'avg_cost_basis': 0
                }
            
            stock_positions[transaction.stock_code]['total_shares_bought'] += transaction.shares
            stock_positions[transaction.stock_code]['total_cost'] += transaction.total_amount
            stock_positions[transaction.stock_code]['avg_cost_basis'] = (
                stock_positions[transaction.stock_code]['total_cost'] / 
                stock_positions[transaction.stock_code]['total_shares_bought']
            )
            
        elif transaction.transaction_type == 'SELL':
            total_sell_proceeds += transaction.total_amount
            
            # Calculate realized P&L for this sell
            if transaction.stock_code in stock_positions:
                avg_cost_basis = stock_positions[transaction.stock_code]['avg_cost_basis']
                cost_of_sold_shares = transaction.shares * avg_cost_basis
                realized_pnl += transaction.total_amount - cost_of_sold_shares
                stock_positions[transaction.stock_code]['shares_sold'] += transaction.shares
    
    # Calculate net invested amount (money still in the market)
    net_invested = total_buy_amount - total_sell_proceeds
    
    # Calculate unrealized P&L from current holdings
    holdings = crud.get_portfolio_holdings(db, portfolio_id)
    unrealized_pnl = sum([h.unrealized_gain_loss or 0 for h in holdings])
    
    # Current portfolio value
    current_value = portfolio.total_value or 0
    
    # Total P&L
    total_pnl = realized_pnl + unrealized_pnl
    
    # ROI calculation
    roi_percentage = 0
    if net_invested > 0:
        roi_percentage = (total_pnl / net_invested) * 100
    elif total_buy_amount > 0:
        # If we've sold everything, calculate ROI based on original investment
        roi_percentage = (total_pnl / total_buy_amount) * 100
    
    return {
        "realized_pnl": round(realized_pnl, 2),
        "unrealized_pnl": round(unrealized_pnl, 2),
        "total_pnl": round(total_pnl, 2),
        "total_invested": round(net_invested, 2),
        "total_buy_amount": round(total_buy_amount, 2),
        "total_sell_proceeds": round(total_sell_proceeds, 2),
        "current_value": round(current_value, 2),
        "roi_percentage": round(roi_percentage, 2),
        "cash_balance": portfolio.cash_balance,
        "holdings_value": round(current_value - portfolio.cash_balance, 2) if current_value and portfolio.cash_balance else 0
    }
