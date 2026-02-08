PORTFOLIO_PROMPT="""
You are a financial advisor helping a user manage their investment portfolio.
Based on the user's query, provide advice on portfolio allocation, diversification, and risk management.
Use the user's risk profile and investment goals to tailor your recommendations.
Your response should be concise and actionable, not exceeding 150 words.

Provide portfolio advice:
if the user is risk-averse, suggest conservative investments and diversification strategies.
if the user is risk-tolerant, suggest growth-oriented investments with higher potential returns.
use market data trends to inform your advice.
use only the information provided in the User Profile and Market Data sections.
the answer should help the user optimize their portfolio performance.
optimize for long-term growth while managing risk according to the user's profile.

--------------
OUTPUT FORMAT
--------------

Structure your response in the following JSON format:
{
    "recommendation": "Specific portfolio advice based on user's query",
    "rationale": "Brief explanation referencing user's risk profile and investment goals"
}
"""

from pathlib import Path
import sys
sys.path.append(str(Path(__file__).resolve().parent.parent))
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from agent.utils import get_last_days
from app.crud import load_predicted_market_data_from_csv
from app.database import get_user_by_id, SessionLocal, get_user_portfolio,get_portfolio_pnl_and_roi
db = SessionLocal()
import json


def portfolio_advice_prompt(user_id: str, query: str) -> str:
   
        # Find the user profile
    user_profile = None
    try:
        user_profile = get_user_by_id(db, user_id)
    except Exception as e:
        user_profile = None
    if user_profile is None:    
        return "{'error': f'User {user_id} not found'}"
    try:
        portfolio_ids = get_user_portfolio(db, user_id)
    except Exception as e:
        portfolio_ids = []
    if len(portfolio_ids) == 0:
        return "{'error': f'No portfolios found for user {user_id}'}"
    roi_pnl = get_portfolio_pnl_and_roi(db,portfolio_ids[0],user_id)
    try:
        data = get_last_days("data/filtered_anomaly_detected_dataset.csv", 3)
        stock_records = data.to_dict(orient='records')
        stock_records_with_forecast = []
        all_forecasts = load_predicted_market_data_from_csv()
        for record in stock_records:
            symbol = record['VALEUR']
            record['forecast'] = all_forecasts.get(symbol.strip().upper(), {})
            stock_records_with_forecast.append(record)
        
    except Exception as e:
        return "{'error': f'Error loading data: {e}'}"
    
    return f"""
{query}

User Profile:
{json.dumps(user_profile)}
Portfolio Performance:
{json.dumps(roi_pnl)}
Market Data:
{json.dumps(stock_records_with_forecast)}
"""