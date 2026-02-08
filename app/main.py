from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import timedelta, datetime
import uvicorn
from typing import Dict, Any, List
import sys
import os
import traceback
import uuid
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))

from . import models, schemas, crud, auth
from .database import SessionLocal, engine, get_db, get_portfolio_pnl_and_roi
from .routes_regulator import router as regulator_router

# Add the root directory to Python path for agent imports
parent_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(parent_dir))

# Import refresh utility
try:
    from utils.refresh import refresh_data
except ImportError as e:
    refresh_data = None
    print(f"Warning: Could not import refresh_data: {e}")

# Import the investment agent
try:
    from agent.agents.investment_agent import app as agent_app, AgentState
    print("Investment agent imported successfully")
except ImportError as e:
    agent_app = None
    print(f"Warning: Could not import investment agent: {e}")

# Store chat sessions in memory (in production, use Redis or database)
chat_sessions: Dict[str, List[Dict]] = {}

# Create database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Investment Agent API",
    description="API for investment agent with portfolio simulation",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "http://127.0.0.1:3000",
        "http://localhost:5173", 
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include regulator router
app.include_router(regulator_router)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@app.post("/register", response_model=schemas.UserResponse)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # sourcery skip: use-named-expression
    """Register a new user and create a default portfolio"""
    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user and default portfolio
    created_user = crud.create_user(db=db, user=user)
    return {"success": True, "message": "User created successfully", "user": created_user}

@app.post("/auth/register", response_model=schemas.UserResponse)
def auth_register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """Alias for /register to support frontend clients."""
    return register_user(user=user, db=db)

@app.post("/token", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login endpoint to get access token"""
    user = auth.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/auth/login", response_model=schemas.Token)
def auth_login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Alias for /token to support frontend clients."""
    return login_for_access_token(form_data=form_data, db=db)

@app.get("/users/me", response_model=schemas.User)
def read_users_me(current_user: models.User = Depends(auth.get_current_user)):
    """Get current user information"""
    return current_user

@app.get("/portfolios", response_model=list[schemas.Portfolio])
def get_user_portfolios(current_user: schemas.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    """Get user's portfolios"""
    portfolios = crud.get_user_portfolios(db=db, user_id=current_user.id)
    if not portfolios:
        default_cash = current_user.initial_cash_balance or 10000.0
        created = crud.create_portfolio(
            db=db,
            portfolio=schemas.PortfolioCreate(
                name="Main Portfolio",
                description="Default investment portfolio",
                cash_balance=default_cash
            ),
            user_id=current_user.id
        )
        portfolios = [created]
    return portfolios

@app.get("/portfolios/{portfolio_id}", response_model=schemas.PortfolioDetail)
def get_portfolio(portfolio_id: int, current_user: schemas.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    # sourcery skip: reintroduce-else, swap-if-else-branches, use-named-expression
    """Get specific portfolio details"""
    portfolio = crud.get_portfolio_by_id(db=db, portfolio_id=portfolio_id, user_id=current_user.id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return portfolio

@app.post("/portfolios", response_model=schemas.Portfolio)
def create_portfolio(portfolio: schemas.PortfolioCreate, current_user: schemas.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    """Create a new portfolio"""
    return crud.create_portfolio(db=db, portfolio=portfolio, user_id=current_user.id)

@app.post("/portfolios/{portfolio_id}/transactions", response_model=schemas.Transaction)
def create_transaction(
    portfolio_id: int, 
    transaction: schemas.TransactionCreate, 
    current_user: schemas.User = Depends(auth.get_current_user), 
    db: Session = Depends(get_db)
):
    """Add a transaction to a portfolio"""
    # Verify portfolio ownership
    portfolio = crud.get_portfolio_by_id(db=db, portfolio_id=portfolio_id, user_id=current_user.id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    
    return crud.create_transaction(db=db, transaction=transaction, portfolio_id=portfolio_id)

@app.get("/portfolios/{portfolio_id}/transactions", response_model=list[schemas.Transaction])
def get_portfolio_transactions(
    portfolio_id: int, 
    current_user: schemas.User = Depends(auth.get_current_user), 
    db: Session = Depends(get_db)
):
    """Get transactions for a portfolio"""
    # Verify portfolio ownership
    portfolio = crud.get_portfolio_by_id(db=db, portfolio_id=portfolio_id, user_id=current_user.id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    
    return crud.get_portfolio_transactions(db=db, portfolio_id=portfolio_id)

@app.post("/simulations", response_model=schemas.PortfolioSimulation)
def create_simulation(
    simulation: schemas.PortfolioSimulationCreate, 
    current_user: schemas.User = Depends(auth.get_current_user), 
    db: Session = Depends(get_db)
):
    """Create a new portfolio simulation"""
    return crud.create_simulation(db=db, simulation=simulation, user_id=current_user.id)

@app.get("/simulations", response_model=list[schemas.PortfolioSimulation])
def get_user_simulations(current_user: schemas.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    """Get user's simulations"""
    return crud.get_user_simulations(db=db, user_id=current_user.id)

@app.get("/simulations/{simulation_id}", response_model=schemas.PortfolioSimulationDetail)
def get_simulation(
    simulation_id: int, 
    current_user: schemas.User = Depends(auth.get_current_user), 
    db: Session = Depends(get_db)
):
    """Get specific simulation details"""
    simulation = crud.get_simulation_by_id(db=db, simulation_id=simulation_id, user_id=current_user.id)
    if not simulation:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return simulation

@app.post("/simulations/{simulation_id}/run")
def run_simulation(
    simulation_id: int, 
    current_user: schemas.User = Depends(auth.get_current_user), 
    db: Session = Depends(get_db)
):
    """Run a portfolio simulation"""
    simulation = crud.get_simulation_by_id(db=db, simulation_id=simulation_id, user_id=current_user.id)
    if not simulation:
        raise HTTPException(status_code=404, detail="Simulation not found")
    
    if simulation.is_completed:
        raise HTTPException(status_code=400, detail="Simulation already completed")
    
    # Run the simulation logic here
    result = crud.run_portfolio_simulation(db=db, simulation_id=simulation_id)
    return {"message": "Simulation completed successfully", "result": result}

@app.get("/market-data/{symbol}")
def get_market_data(symbol: str, start: str = None, end: str = None):
    """Get historical market data for a symbol between optional start/end dates (inclusive).

    Returns a dict with:
    - history: list of points with 'date' and 'close'
    - snapshot: latest market fields (close, open, high, low, volume, daily_return_pct, etc.) when available
    """
    history = crud.get_stock_history_by_symbol(symbol, start=start, end=end)
    snapshot = crud.get_stock_snapshot_by_symbol(symbol)

    return {
        'history': history,
        'snapshot': snapshot
    }


@app.get("/market-data/{symbol}/with-forecast")
def get_market_data_with_forecast(symbol: str, start: str = None, end: str = None):
    """Get historical market data combined with 5-day forecast for a symbol.

    Returns:
    - history: historical data points
    - forecast: next 5 days predictions
    - combined: merged data with isPrediction flag
    """
    history = crud.get_stock_history_with_forecast(symbol, start=start, end=end)
    return history


@app.get("/market-overview/tunindex")
def get_tunindex_data(days: int = 30, index_type: str = 'tunindex'):
    """Get TUNINDEX or TUNINDEX20 historical data for the market overview chart.
    
    Args:
        days: Number of days of history
        index_type: 'tunindex' or 'tunindex20'
    """
    data = crud.get_tunindex_history(days=days, index_type=index_type)
    return data


@app.get("/market-overview/sentiment")
def get_market_sentiment(date: str = None):
    """Get daily market mood/sentiment data."""
    sentiment = crud.get_market_mood(date=date)
    return sentiment


@app.get("/market-overview/top-movers")
def get_top_movers(date: str = None):
    """Get top 5 gainers and losers for the given date (or latest available)."""
    movers = crud.get_top_gainers_losers(date=date)
    return movers


@app.get("/market-overview/alerts")
def get_market_alerts(limit: int = 10):
    """Get recent market alerts based on detected anomalies."""
    alerts = crud.get_market_alerts(limit=limit)
    return alerts


@app.get("/sentiment/{symbol}")
def get_stock_sentiment(symbol: str, start: str = None, end: str = None):
    """Get sentiment data for a specific stock from sentiment_features.csv."""
    sentiment = crud.get_stock_sentiment_history(symbol, start=start, end=end)
    return sentiment

@app.get("/predicted-data/{symbol}")
def get_predicted_data(symbol: str):
    """Get predicted market data for a symbol"""
    predicted_data = crud.get_predicted_stock_data_by_symbol(symbol)
    if not predicted_data:
        raise HTTPException(status_code=404, detail="Predicted data not found")
    return predicted_data

@app.get("/stocks/search")
def search_stocks(q: str = "", limit: int = 10):
    """Search for stocks by name or code"""
    if not q:
        raise HTTPException(status_code=400, detail="Query parameter 'q' is required")
    
    results = crud.search_stocks_by_name(q, limit)
    return {"results": results}

@app.get("/stocks/all")
def get_all_stocks(limit: int = 100):
    """Get all available stocks with predicted data"""
    predicted_data = crud.load_predicted_market_data_from_csv()
    stocks = list(predicted_data.values())[:limit]
    return {"stocks": stocks}

@app.post("/portfolios/{portfolio_id}/update-prices")
def update_portfolio_prices(
    portfolio_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_user)
):
    """Manually update current prices for all holdings in a portfolio"""
    # Verify portfolio ownership
    portfolio = crud.get_portfolio_by_id(db=db, portfolio_id=portfolio_id, user_id=current_user.id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    
    update_portfolio_current_prices(db, portfolio_id)
    return {"message": "Prices updated successfully"}

@app.get("/portfolios/{portfolio_id}/analytics")
def get_portfolio_analytics(
    portfolio_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_user)
):
    """Get detailed P&L and ROI analytics for a portfolio using predicted prices"""
    # Update predicted prices before calculating analytics
    update_portfolio_current_prices(db, portfolio_id)
    
    analytics = get_portfolio_pnl_and_roi(db, portfolio_id, current_user.id)
    if not analytics:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    
    # Add prediction information to analytics
    analytics["prediction_based"] = True
    analytics["prediction_info"] = "P&L and ROI calculated using average of 5-day price predictions"
    
    return analytics

def update_portfolio_current_prices(db: Session, portfolio_id: int):
    """Update current prices for all holdings in a portfolio using predicted prices"""
    holdings = crud.get_portfolio_holdings(db, portfolio_id)
    
    for holding in holdings:
        # Get predicted market data instead of current data
        predicted_data = crud.get_predicted_stock_data_by_symbol(holding.stock_code)
        if predicted_data and 'avg_predicted_price' in predicted_data:
            # Use average of predicted prices for next 5 days
            predicted_price = predicted_data['avg_predicted_price']
            
            # Update holding with predicted price
            holding.current_price = predicted_price
            holding.total_value = holding.shares * predicted_price
            holding.unrealized_gain_loss = holding.total_value - (holding.shares * holding.avg_purchase_price)
            if holding.avg_purchase_price > 0:
                holding.unrealized_gain_loss_percentage = (holding.unrealized_gain_loss / (holding.shares * holding.avg_purchase_price)) * 100
            holding.last_price_update = datetime.utcnow()
            
            print(f"Updated {holding.stock_code}: Purchase: {holding.avg_purchase_price}, Predicted: {predicted_price}, P&L: {holding.unrealized_gain_loss}")
    
    # Update portfolio total value
    crud.update_portfolio_total_value(db, portfolio_id)
    db.commit()

@app.get("/users/me/analytics")
def get_user_total_analytics(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_user)
):
    """Get total P&L and ROI analytics across all user portfolios"""
    return get_user_total_pnl_and_roi(db, current_user.id)

@app.get("/portfolios/{portfolio_id}/performance")
def get_portfolio_performance(
    portfolio_id: int,
    days: int = 180,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_user)
):
    """Return portfolio performance time series (equity curve) and KPIs.

    Query params:
    - days: number of past days to include (default 180)
    """
    perf = crud.get_portfolio_equity_curve(db, portfolio_id, days=days)
    if not perf:
        raise HTTPException(status_code=404, detail="Portfolio or performance data not found")
    return perf

def get_portfolio_pnl_and_roi(db: Session, portfolio_id: int, user_id: int) -> Dict[str, Any]:
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

from typing import Dict, Any

def get_user_total_pnl_and_roi(db: Session, user_id: int) -> Dict[str, Any]:
    """
    Calculate total P&L and ROI across all user's portfolios.
    """
    portfolios = crud.get_user_portfolios(db, user_id)
    
    total_realized_pnl = 0
    total_unrealized_pnl = 0
    total_invested = 0
    total_current_value = 0
    total_buy_amount = 0
    total_sell_proceeds = 0
    
    for portfolio in portfolios:
        portfolio_metrics = get_portfolio_pnl_and_roi(db, portfolio.id, user_id)
        
        total_realized_pnl += portfolio_metrics.get('realized_pnl', 0)
        total_unrealized_pnl += portfolio_metrics.get('unrealized_pnl', 0)
        total_invested += portfolio_metrics.get('total_invested', 0)
        total_current_value += portfolio_metrics.get('current_value', 0)
        total_buy_amount += portfolio_metrics.get('total_buy_amount', 0)
        total_sell_proceeds += portfolio_metrics.get('total_sell_proceeds', 0)
    
    total_pnl = total_realized_pnl + total_unrealized_pnl
    
    # Calculate overall ROI
    roi_percentage = 0
    if total_invested > 0:
        roi_percentage = (total_pnl / total_invested) * 100
    elif total_buy_amount > 0:
        roi_percentage = (total_pnl / total_buy_amount) * 100
    
    return {
        "total_realized_pnl": round(total_realized_pnl, 2),
        "total_unrealized_pnl": round(total_unrealized_pnl, 2),
        "total_pnl": round(total_pnl, 2),
        "total_invested": round(total_invested, 2),
        "total_buy_amount": round(total_buy_amount, 2),
        "total_sell_proceeds": round(total_sell_proceeds, 2),
        "total_current_value": round(total_current_value, 2),
        "roi_percentage": round(roi_percentage, 2),
        "number_of_portfolios": len(portfolios)
    }

# Chatbot endpoints
@app.post("/chat/session")
def create_chat_session(current_user: models.User = Depends(auth.get_current_user)):
    """Create a new chat session"""
    session_id = str(uuid.uuid4())
    chat_sessions[session_id] = []
    return {"session_id": session_id}

@app.post("/chat/{session_id}/message")
def send_chat_message(session_id: str, message: schemas.ChatMessage, current_user: models.User = Depends(auth.get_current_user)):
    """Send a message to the investment agent"""
    if agent_app is None:
        raise HTTPException(status_code=503, detail="Investment agent is not available")
    
    if session_id not in chat_sessions:
        raise HTTPException(status_code=404, detail="Chat session not found")
    
    try:
        # Store user message
        user_message = {
            "type": "user",
            "content": message.content,
            "timestamp": datetime.utcnow().isoformat()
        }
        chat_sessions[session_id].append(user_message)
        
        # Create agent state
        initial_state = AgentState(
            current_step="start",
            query=message.content,
            user_id=str(current_user.id),
            intention="",
            stock_symbol=[],
            recommendation="",
            rationale="",
            comparison=""
        )
        
        # Run the agent
        result = agent_app.invoke(initial_state)
        
        # Format agent response
        agent_response = {
            "type": "agent",
            "content": result.get("recommendation", "I apologize, but I couldn't process your request."),
            "rationale": result.get("rationale", ""),
            "comparison": result.get("comparison", ""),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Store agent response
        chat_sessions[session_id].append(agent_response)
        
        return agent_response
        
    except Exception as e:
        print(f"Chat error: {str(e)}")
        print(traceback.format_exc())
        
        error_response = {
            "type": "agent",
            "content": "I apologize, but I encountered an error processing your request. Please try again.",
            "rationale": "",
            "comparison": "",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        chat_sessions[session_id].append(error_response)
        return error_response

@app.get("/chat/{session_id}/history")
def get_chat_history(session_id: str, current_user: models.User = Depends(auth.get_current_user)):
    """Get chat history for a session"""
    if session_id not in chat_sessions:
        raise HTTPException(status_code=404, detail="Chat session not found")
    
    return {
        "session_id": session_id,
        "messages": chat_sessions[session_id]
    }
try:
    from agent.agents.explain_agent import explain_anomaly
except ImportError:
    print("Explain agent not found")
    explain_anomaly = None

@app.get("/explain/{stock_symbol}/{date}")
def explain_stock(stock_symbol: str, date: str, current_user: models.User = Depends(auth.get_current_user)):
    """Explain a stock"""
    if explain_anomaly is None:
        raise HTTPException(status_code=503, detail="Explain agent is not available")
    return explain_anomaly(date=date, ticker=stock_symbol)


@app.post("/market-overview/refresh")
def refresh_market_data():
    """Refresh market data from the latest available data source.
    
    Calls the refresh utility to fetch new data and update all CSV files.
    Handles cases where data is already up-to-date gracefully.
    """
    if refresh_data is None:
        raise HTTPException(status_code=503, detail="Refresh utility is not available")
    
    try:
        # Call refresh_data - it handles updating CSV files internally
        # and returns 4 dataframes even if they're empty
        try:
            result = refresh_data()
            if result is not None:
                forecast_df, new_historical_output, new_indices_output, new_sentiment_output = result
        except ValueError as e:
            # Handle unpacking errors gracefully
            print(f"Could not unpack refresh_data result: {e}")
        except Exception as e:
            print(f"Error during refresh_data execution: {e}")
            print(traceback.format_exc())
        
        # Return success regardless - the function prints status to console
        return {
            "success": True,
            "message": "Market data refresh completed",
            "status": "Data has been checked and updated if new data was available"
        }
    except Exception as e:
        error_msg = str(e)
        print(f"Error in refresh endpoint: {error_msg}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Failed to refresh market data: {error_msg}"
        )


@app.get("/")
def read_root():
    """Root endpoint"""
    return {"message": "Investment Agent API", "version": "1.0.0"}

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}





if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
