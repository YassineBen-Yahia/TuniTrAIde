import sys
import os
import json
from pathlib import Path

import pandas as pd

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.database import get_user_by_id, SessionLocal
from app.crud import load_predicted_market_data_from_csv
from agent.utils import (
    get_last_days, 
    get_article_analysis, 
    get_symbol_forecast_dict,
    format_forecast_by_days,
    get_all_symbols_forecast_dict
)

# --- Database Session ---

db = SessionLocal()

# --- Prompts ---

INVESTMENT_PROMPT = """
You are an expert financial investment advisor.

You are provided with:
- User risk profile and preferences
- Historical stock market data for the last N trading days
- Model-generated features (anomaly flags, volatility metrics, and price predictions)
- Article sentiment analysis (if available)

Your job is to analyze this data and recommend: "buy", "sell", or "hold".

You MUST base your decision ONLY on the supplied data.
DO NOT use external knowledge.
DO NOT invent missing values.

-------------------------
AVAILABLE DATA FIELDS PER DAY
-------------------------
Your input is a single list that includes:

5 historical trading-day records for the same stock (SYMBOL, CODE )

1 extra object at the end with a "forcasts" (forecasts) dictionary
→ this contains next 5-day price predictions for that same stock.

Each historical record contains the following fields:
VALEUR: Stock symbol/name
SEANCE: Trading date
GROUPE: Market group code
CODE: Stock ISIN code
OUVERTURE: Opening price
CLOTURE: Closing price
PLUS_BAS: Lowest price of the day
PLUS_HAUT: Highest price of the day
QUANTITE_NEGOCIEE: Traded volume (quantity)
NB_TRANSACTION: Number of transactions
CAPITAUX: Traded capital (value)
VARIATION: Daily price variation (percentage)
PROB_LIQUIDITY: Probability of liquidity
TUNINDEX_INDICE_JOUR: Daily TUNINDEX index value
TUNINDEX20_INDICE_JOUR: Daily TUNINDEX20 index value
Mean_Weighted_Sentiment: Average sentiment score weighted by relevance
Article_Count: Number of related articles
Sentiment_Intensity: Intensity of sentiment in news
DirectionScore: Score indicating directional sentiment trend
BreadthScore: Measure of sentiment breadth across sources
LiquidityScore: Liquidity score
IntensityScore: Intensity score
NewsScore: Overall news impact score
MarketMood: General market mood indicator
volume_z_score: Z-score of trading volume
VOLUME_Anomaly: 1 if volume anomaly detected, else 0
variation_z_score: Z-score of price variation
VARIATION_ANOMALY: 1 if price variation anomaly detected, else 0
VARIATION_ANOMALY_POST_NEWS: Price anomaly flag after news release
VARIATION_ANOMALY_PRE_NEWS: Price anomaly flag before news release
VOLUME_ANOMALY_POST_NEWS: Volume anomaly flag after news release
VOLUME_ANOMALY_PRE_NEWS: Volume anomaly flag before news release
forecasts: (only in the last object)
    predicted_day_1: Predicted closing price for Day 1
    predicted_day_2: Predicted closing price for Day 2
    predicted_day_3: Predicted closing price for Day 3
    predicted_day_4: Predicted closing price for Day 4
    predicted_day_5: Predicted closing price for Day 5
    avg_predicted_price: Average predicted price over next 5 days
    date: date of the next trading day

-------------------------
ANALYSIS REQUIREMENTS
-------------------------

1. Stock Trend Analysis:
   - Examine CLOTURE values across the last N days.
   - Determine if price trend is bullish, bearish, or neutral.

2. Anomaly Detection:
   - Count how many days have ANOMALY = 1.
   - Assess average ANOMALY_SCORE.
   - Treat frequent or high-score anomalies as higher risk.

3. Volatility Assessment:
   - Analyze magnitude of Daily_Return_Pct.
   - Large absolute values indicate higher volatility.

4. Price Predictions:
   - Analyze the sequence PREDICTED_DAY_1 → PREDICTED_DAY_5.
   - Determine if predicted trend is bullish, bearish, or neutral.

5. Risk Profile Alignment:
   - Conservative → avoid volatility and anomalies.
   - Moderate → tolerate mild anomalies.
   - Aggressive → tolerate risk if upside exists.

6. Article Sentiment :
    - Positive sentiment → supports buy.
    - Negative sentiment → supports sell.
    - Neutral/No data → no impact.
    - Consider the timeliness and confidence of the analysis.
    - Cross-reference sentiment with stock trends.

-------------------------
DECISION RULES (Soft)
-------------------------
- If the user doesn't have the stock, only "buy" or "hold" are valid.
- If the user owns the stock, "buy", "sell" or "hold" are all valid.
- if the predicted prices show strong upside, favor "buy".
- if the predicted prices show strong downside, favor "sell".
- Strong bullish trend + low anomalies/volatility → BUY
- Strong bullish trend + bullish predictions → BUY
- Strong bearish trend + bearish predictions → SELL
- Mixed or uncertain signals → HOLD
- If user avoids anomalies and anomalies exist → prefer HOLD or SELL
- If sentiment is strongly positive → lean towards BUY
- If sentiment is strongly negative → lean towards SELL
- If sentiment analysis dates back more than 20 days → reduce its weight

-------------------------
OUTPUT FORMAT (JSON ONLY)
-------------------------
{
  "recommendation": "buy | sell | hold",
  "rationale": "Short explanation referencing trends, anomalies, volatility, and predictions"
}
-------------------------
Analyze the forecasts and historical data provided below along with the user's risk profile.
if the predicted prices show strong upside, favor "buy".
if the predicted prices show strong downside, favor "sell".
The explanation MUST reference specific data points and align with the user's risk profile.
the rationale MUST NOT exceed 150 words.

"""


INVESTMENT_PROMPT_V2 = """
You are an expert financial investment advisor.
You are provided with:
- User risk profile and preferences
- Historical stock market data for the last N trading days
- Model-generated features (anomaly flags, volatility metrics, and price predictions)
- Article sentiment analysis (if available)
Your job is to analyze this data and recommend: "buy", "sell", or "hold" for each stock.
Recommend "buy", "sell", or "hold".
You MUST base your decision ONLY on the supplied data.
DO NOT use external knowledge.
DO NOT invent missing values.
-------------------------
AVAILABLE DATA FIELDS PER DAY
-------------------------
Your input is a single list that includes:
5 historical trading-day records for the DIFFERENT stocks (SYMBOL, CODE )
each historical record contains the following fields:
VALEUR: Stock symbol/name
SEANCE: Trading date
GROUPE: Market group code
CODE: Stock ISIN code
OUVERTURE: Opening price
CLOTURE: Closing price
PLUS_BAS: Lowest price of the day
PLUS_HAUT: Highest price of the day
QUANTITE_NEGOCIEE: Traded volume (quantity)
NB_TRANSACTION: Number of transactions
CAPITAUX: Traded capital (value)
VARIATION: Daily price variation (percentage)
PROB_LIQUIDITY: Probability of liquidity
TUNINDEX_INDICE_JOUR: Daily TUNINDEX index value
TUNINDEX20_INDICE_JOUR: Daily TUNINDEX20 index value
Mean_Weighted_Sentiment: Average sentiment score weighted by relevance
Article_Count: Number of related articles
Sentiment_Intensity: Intensity of sentiment in news
DirectionScore: Score indicating directional sentiment trend
BreadthScore: Measure of sentiment breadth across sources
LiquidityScore: Liquidity score
IntensityScore: Intensity score
NewsScore: Overall news impact score
MarketMood: General market mood indicator
volume_z_score: Z-score of trading volume
VOLUME_Anomaly: 1 if volume anomaly detected, else 0
variation_z_score: Z-score of price variation
VARIATION_ANOMALY: 1 if price variation anomaly detected, else 0
VARIATION_ANOMALY_POST_NEWS: Price anomaly flag after news release
VARIATION_ANOMALY_PRE_NEWS: Price anomaly flag before news release
VOLUME_ANOMALY_POST_NEWS: Volume anomaly flag after news release
VOLUME_ANOMALY_PRE_NEWS: Volume anomaly flag before news release
forecasts: (only in the last object)
    predicted_day_1: Predicted closing price for Day 1
    predicted_day_2: Predicted closing price for Day 2
    predicted_day_3: Predicted closing price for Day 3
    predicted_day_4: Predicted closing price for Day 4
    predicted_day_5: Predicted closing price for Day 5
    avg_predicted_price: Average predicted price over next 5 days
    date: date of the next trading day
-------------------------
ANALYSIS REQUIREMENTS
-------------------------
1. Stock Trend Analysis:
   - Examine CLOTURE values across the last N days.
   - Determine if price trend is bullish, bearish, or neutral.
2. Anomaly Detection:
   - Count how many days have ANOMALY = 1.
   - Assess average ANOMALY_SCORE.
   - Treat frequent or high-score anomalies as higher risk.
3. Volatility Assessment:
   - Analyze magnitude of Daily_Return_Pct. 
   - Large absolute values indicate higher volatility.
4. Price Predictions:
    - Analyze the sequence PREDICTED_DAY_1 → PREDICTED_DAY_5.
    - Determine if predicted trend is bullish, bearish, or neutral.
5. Risk Profile Alignment:
    - Conservative → avoid volatility and anomalies.
    - Moderate → tolerate mild anomalies.
    - Aggressive → tolerate risk if upside exists.
6. Article Sentiment :
    - Positive sentiment → supports buy.
    - Negative sentiment → supports sell.
    - Neutral/No data → no impact.
    - Consider the timeliness and confidence of the analysis.
    - Cross-reference sentiment with stock trends.
-------------------------
DECISION RULES (Soft)
-------------------------
- If there is a stock with a strong buy signal, mention it specifically.
- If the user doesn't have the stock, only "buy" or "hold" are valid.
- If the user owns the stock, "buy", "sell" or "hold" are all valid.
- if the predicted prices show strong upside, favor "buy".
- if the predicted prices show strong downside, favor "sell".
- Strong bullish trend + low anomalies/volatility → BUY
- Strong bullish trend + bullish predictions → BUY
- Strong bearish trend + bearish predictions → SELL
- Mixed or uncertain signals → HOLD
- If user avoids anomalies and anomalies exist → prefer HOLD or SELL
- If sentiment is strongly positive → lean towards BUY
- If sentiment is strongly negative → lean towards SELL
- If sentiment analysis dates back more than 20 days → reduce its weight
-------------------------
OUTPUT FORMAT (JSON ONLY)
-------------------------
{
  "recommendation": "buy | sell | hold",
  "rationale": "Short explanation referencing trends, anomalies, volatility, and predictions and mention the stock symbol considered"
}
-------------------------
Analyze the forecasts and historical data provided below along with the user's risk profile.
if the predicted prices show strong upside, favor "buy".
if the predicted prices show strong downside, favor "sell".
The explanation MUST reference specific data points and align with the user's risk profile.
when using data for explanation, interpret it in financial terms rather than naming the data columns directly (e.g., "the price change was statistically extreme", "the trading volume was unusually high", "the sentiment was strongly negative", etc.).
the rationale MUST NOT exceed 150 words.
"""    

COMPARE_STOCK_PROMPT = """
You are an expert financial investment advisor.
Your task is to compare multiple stocks based on their recent performance and provide a ranking along with brief justifications.
You are provided with historical stock market data for the last 5 trading days for multiple stocks.
You MUST base your comparison ONLY on the supplied data.
DO NOT use external knowledge.
DO NOT invent missing values.
-------------------------
AVAILABLE DATA FIELDS PER DAY
-------------------------
the data for each stock for the last 5 days is as follows:

VALEUR: Stock symbol/name
last_close: Most recent closing price
first_close: First closing price in the dataset period
mean_close: Average closing price over the period
min_close: Minimum closing price in the period
max_close: Maximum closing price in the period
n_obs: Number of observations/trading days for this stock


Liquidity Metrics:
volume_sum: Total volume traded over the period
volume_mean: Average daily volume
tx_mean: Average number of transactions per day


Trend Analysis:
up_days_count: Number of days with positive returns
period_return_pct: Total percentage return from first to last day
trend_slope_pct_per_day: Daily percentage trend slope

Anomaly Detection:
anomaly_count: Total number of anomalies detected
anomaly_score_latest: Most recent anomaly score
anomaly_score_max: Maximum anomaly score in the period
anomaly_score_mean: Average anomaly score
anomaly_dates: List of dates when anomalies were detected
last_anomaly_date: Date of the most recent anomaly

Forecast Data:
forecast: Dictionary containing predicted prices, volumes, and liquidity probabilities for the next 5 days, with fields like:
predicted_price_day1 through predicted_price_day5
predicted_volume_day1 through predicted_volume_day5
liquidity_prob_day1 through liquidity_prob_day5
summary: Contains trend direction, averages, min/max prices
symbol_info: Stock code and name
dates: List of forecast dates

-------------------------
OUTPUT 
-------------------------
A brief ranking of the stocks from most to least favorable investment based on recent performance, along with justification.
when using data for explanation, interpret it in financial terms rather than naming the data columns directly (e.g., "the price change was statistically extreme", "the trading volume was unusually high", "the sentiment was strongly negative", etc.).
the justification for MUST NOT exceed 100 words.
"""

ANALYSIS_PROMPT = """
You are a market analysis expert.
You are provided with historical stock market data for the last N trading days for a specific stock.
Your task is to analyze the stock's recent performance and provide insights on its trend, volatility,
and potential outlook.
You MUST base your analysis ONLY on the supplied data.
DO NOT use external knowledge.
DO NOT invent missing values.
-------------------------
AVAILABLE DATA FIELDS 
-------------------------
VALEUR: Stock symbol/name
last_close: Most recent closing price
first_close: First closing price in the dataset period
mean_close: Average closing price over the period
min_close: Minimum closing price in the period
max_close: Maximum closing price in the period
n_obs: Number of observations/trading days for this stock


Liquidity Metrics:
volume_sum: Total volume traded over the period
volume_mean: Average daily volume
tx_mean: Average number of transactions per day


Trend Analysis:
up_days_count: Number of days with positive returns
period_return_pct: Total percentage return from first to last day
trend_slope_pct_per_day: Daily percentage trend slope

Anomaly Detection:
anomaly_count: Total number of anomalies detected
anomaly_score_latest: Most recent anomaly score
anomaly_score_max: Maximum anomaly score in the period
anomaly_score_mean: Average anomaly score
anomaly_dates: List of dates when anomalies were detected
last_anomaly_date: Date of the most recent anomaly

Forecast Data:
forecast: Dictionary containing predicted prices, volumes, and liquidity probabilities for the next 5 days, with fields like:
predicted_price_day1 through predicted_price_day5
predicted_volume_day1 through predicted_volume_day5
liquidity_prob_day1 through liquidity_prob_day5
summary: Contains trend direction, averages, min/max prices
symbol_info: Stock code and name
dates: List of forecast dates
-------------------------
OUTPUT
-------------------------
A brief analysis of the stock's recent performance, including:
- Trend direction
- Volatility assessment
- Notable anomalies
- Predicted outlook based on model forecasts
when using data for explanation, interpret it in financial terms rather than naming the data columns directly (e.g., "the price change was statistically extreme", "the trading volume was unusually high", "the sentiment was strongly negative", etc.).
the analysis MUST NOT exceed 150 words.
"""

# --- Prompt Factory Functions ---

def create_investment_prompt(user_id: str, stock_symbol: str) -> str:
    """
    Create a tailored investment prompt based on user profile and stock data.
    
    Args:
        user_profile: Dictionary containing user risk profile and preferences.
        stock_data: Dictionary containing recent stock market data.
    """
    try:
        #with open('new_agent/user_profile.json', 'r') as f:
        #    content = f.read()
        #    # Handle the JSON format issue
        #    profiles = json.loads(content)
        
        # Find the user profile
        user_profile = None
        try:
            user_profile = get_user_by_id(db, user_id)
        except Exception as e:
            user_profile = None
        if user_profile is None:    
            return "{'error': f'User {user_id} not found'}"
                
        if not user_profile:
            return "{'error': f'User {user_id} not found'}"
    except Exception as e:
        return "{'error': f'Error loading user profile: {e}'}"
    try:
        article_analysis = get_article_analysis(stock_symbol)
        # article_analysis is now a list of dicts or empty list
    except Exception as e:
        article_analysis = []
    try:
        df = get_last_days("data/historical_data.csv", 5)
        if stock_symbol:
            df = df[df['VALEUR'].astype(str).str.strip() == stock_symbol]
            df = df.tail(5)
        
        # Get last 5 days of data
        
        if df.empty:
            return "{'error': 'No data available'}"
        stock_records = df.to_dict(orient='records')
        forcast = load_predicted_market_data_from_csv()
        forecasted_stock = forcast[stock_symbol]
        
        stock_records.append({"forcasts": forecasted_stock})
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"{{'error': 'Error loading data: {e}'}}"
    
    return f"""
Tell me whether to "buy", "sell", or "hold" the stock {stock_symbol}.
Analyze the forecasts and historical data provided below along with the user's risk profile.
if the predicted prices show strong upside, favor "buy".
if the predicted prices show strong downside, favor "sell".



------------------------
USER_PROFILE:
{json.dumps(user_profile, indent=2)}

------------------------
ARTICLE_SENTIMENT_ANALYSIS:
{json.dumps(article_analysis, indent=2)}

------------------------
HISTORICAL_DATA_LAST_5_DAYS:
{json.dumps(stock_records, indent=2)}

------------------------
Now analyze the data and produce your JSON recommendation.
"""


def advice_prompt_without_symbol(user_id: str) -> str:
    """
    Create a prompt for general investment advice based on user profile.
    
    Args:
        user_id: User ID as string.
    """
    try:
        # Try to load user profile from database
        try:
            user_profile = get_user_by_id(db, user_id)
            if user_profile is None:
                return json.dumps({"error": f"User {user_id} not found in database"})
        except Exception as e:
            return json.dumps({"error": f"Error loading user profile from database: {str(e)}"})
        
        # Get article analysis for all symbols (last 3 rows each)
        try:
            article_analysis = get_article_analysis(None)
        except Exception as e:
            print(f"Warning: Could not load article analysis: {e}")
            article_analysis = {}
        
        # Load historical data and forecasts
        try:
            data = get_last_days("data/historical_data.csv", 3)
            stock_records = data.to_dict(orient='records')
            stock_records_with_forecast = []
            all_forecasts = load_predicted_market_data_from_csv()
            for record in stock_records:
                symbol = record['VALEUR']
                record['forecast'] = all_forecasts.get(symbol.strip().upper(), {})
                stock_records_with_forecast.append(record)
        except Exception as e:
            return json.dumps({"error": f"Error loading market data: {str(e)}"})
        
        # Create the prompt
        prompt = f"""
Provide general investment advice for the user.
------------------------
USER_PROFILE:
{json.dumps(user_profile, indent=2)}
------------------------
ARTICLE_SENTIMENT_ANALYSIS:
{json.dumps(article_analysis, indent=2)}
------------------------
HISTORICAL_DATA_LAST_3_DAYS:
{json.dumps(stock_records, indent=2)}
------------------------

Now analyze the data and provide tailored investment advice. 
Your advice should consider the user's risk profile and preferences.
Provide your response in JSON format with these fields:
  "advice": "Your tailored investment advice here",
  "rationale": "Short explanation referencing user profile and data"

If there is a stock with a strong buy signal, mention it specifically.
"""
        
        # Save to log file
        with open("logs/general_advice_prompt.txt", "w") as f:
            f.write(prompt)
        
        return prompt
        
    except Exception as e:
        return json.dumps({"error": f"Unexpected error in advice_prompt_without_symbol: {str(e)}"})
