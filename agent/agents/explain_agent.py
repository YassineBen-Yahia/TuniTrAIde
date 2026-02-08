import json
import pandas as pd
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from agent.utils import get_previous_days
from agent.prompts.explainabilty import EXPLAIN_PROMPT
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_ollama import ChatOllama
from dotenv import load_dotenv

load_dotenv()

model_kwargs = {
    "model": os.getenv("OLLAMA_MODEL"),
    "base_url": os.getenv("OLLAMA_BASE_URL")
}
if os.getenv("OLLAMA_API_KEY"):
    model_kwargs["headers"] = {
        'Authorization': f'Bearer {os.getenv("OLLAMA_API_KEY")}'
    }
llm = ChatOllama(**model_kwargs)

def explain_anomaly(data: str = "data/historical_data.csv", date: str = None, ticker: str = None) -> str:
    """
    Explain a single anomaly for a given stock on a specific date.
    
    Args:
        data: Path to the CSV file containing stock data with anomalies.
        date: Date to explain the anomaly for (format: YYYY-MM-DD).
        ticker: Ticker symbol to explain the anomaly for.
        
    Returns:
        str: The explanation of the anomaly, or an error message if not found.
    """
    if date is None or ticker is None:
        return "Error: Date and ticker must be provided."
    
    print(f"Reading data from {data}...")
    try:
        df = pd.read_csv(data)
    except FileNotFoundError:
        return f"Error: File not found: {data}"
    
    # Filter by ticker
    df = df[df["VALEUR"] == ticker.upper().strip()]
    
    if df.empty:
        return f"Error: No data found for ticker {ticker}"
    
    # Parse dates
    if 'SEANCE' in df.columns:
        df["SEANCE_PARSED"] = pd.to_datetime(df["SEANCE"], errors="coerce")
    else:
        return "Error: 'SEANCE' column not found."
    
    # Filter by date
    df_date = df[df["SEANCE"] == date]
    
    if df_date.empty:
        return f"Error: No data found for ticker {ticker} on date {date}"
    
    # Check if there's an anomaly
    anomaly_cols = ["VARIATION_ANOMALY", "VOLUME_Anomaly"]
  
    
    # Get the first matching row
    row = df_date.iloc[0]
    
    # Check if it's actually an anomaly
    try:
        def is_truthy(x):
            if x is None:
                return False
            s = str(x).strip().lower()
            return s in {"1", "true", "yes", "1.0"}

        has_anomaly = any(is_truthy(row.get(c, None)) for c in anomaly_cols)

        if not has_anomaly:
            return f"Note: No anomaly detected for {ticker} on {date}"

    except Exception as e:
        return f"Error: Unable to check anomaly status ({e})"
    
    print(f"Anomaly confirmed for {ticker} on {date}. Fetching context...")
    
    # Get historical context (read full ticker data again for context)
    df_full = pd.read_csv(data)
    df_full = df_full[df_full["VALEUR"] == ticker.upper().strip()]
    df_full["SEANCE_PARSED"] = pd.to_datetime(df_full["SEANCE"], errors="coerce")
    df_full = df_full.sort_values("SEANCE_PARSED")
    df_full = df_full.reset_index(drop=True)
    
    # Find the index of the anomaly date
    matches = df_full.index[df_full["SEANCE"] == date].tolist()
    if not matches:
        return f"Error: Unable to find date {date} in historical data"
    
    local_idx = matches[0]
    
    # Get last few days up to the anomaly day
    window = get_previous_days(df_full, local_idx, lookback=5)
    
    # Select relevant columns
    cols_to_keep = [
        'SEANCE', 'VALEUR', 'CODE', 'OUVERTURE', 'CLOTURE', 'PLUS_HAUT', 'PLUS_BAS', 
        'QUANTITE_NEGOCIEE', 'NB_TRANSACTION', 'CAPITAUX', 'GROUPE', 
        'VARIATION', 'PROB_LIQUIDITY', 
        'Mean_Weighted_Sentiment', 'Article_Count', 'Sentiment_Intensity',
        'volume_z_score', 'VOLUME_Anomaly', 'variation_z_score', 'VARIATION_ANOMALY',
        'VARIATION_ANOMALY_POST_NEWS', 'VARIATION_ANOMALY_PRE_NEWS', 
        'VOLUME_ANOMALY_POST_NEWS', 'VOLUME_ANOMALY_PRE_NEWS'
    ]
    cols = [c for c in cols_to_keep if c in window.columns]
    window_subset = window[cols]
    
    if len(window_subset) < 1:
        return "Error: Insufficient historical data for explanation"
    
    records = window_subset.to_dict(orient="records")
    
    # Fetch headlines for this specific date and ticker
    print(f"Fetching headlines for {ticker} on {date}...")
    try:
        from agent.explainability_utils import get_headlines
        headlines = get_headlines(ticker, date)
        
    except Exception as e:
        print(f"Warning: Could not fetch headlines: {e}")
        headlines = {"Headlines not available."}
    
    # Construct the user message with data and headlines
    user_prompt = f"""
    DATA:
    {json.dumps(records, indent=2)}
    
    HEADLINES FOR {ticker} ON {date}:
    {json.dumps(headlines, indent=2)}
    
    Explain why the last day ({date}) is anomalous based on the provided data history and news headlines.
    """
#    with open("logs/explainability.txt", "w") as f:
#        f.write(user_prompt)
    
    message = [
        SystemMessage(content=EXPLAIN_PROMPT),
        HumanMessage(content=user_prompt)
    ]
    
    try:
        print("Invoking LLM for explanation...")
        explanation = llm.invoke(message)
        return str(explanation.content)
    except Exception as e:
        return f"Error invoking LLM: {e}"



if __name__ == "__main__":
    print(explain_anomaly("data/historical_data.csv", "2025-08-06", "SFBT"))
