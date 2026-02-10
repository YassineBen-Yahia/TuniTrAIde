import sys
import os
import importlib
import json
from pathlib import Path

# Get the project root directory (parent of utils directory)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
os.chdir(PROJECT_ROOT)  # Ensure working directory is set to project root

sys.path.append(str(PROJECT_ROOT))

from real_time_utils import analyze_new_data
from scraper.OCHL_scraper import fetch_aaz_df, build_valeur_lookup, build_target_table
import real_time_utils
import pandas as pd
import importlib.util

from news_sentiment_analysis.src.pipeline import live_engine

# Define paths relative to project root
REF_PATH = PROJECT_ROOT / "data" / "historical_data.csv"
historical_indices_path = PROJECT_ROOT / "data" / "index_historical_data.csv"
sentiment_path = PROJECT_ROOT / "news_sentimental_analysis" / "exports" / "history.json"
score_params_path = PROJECT_ROOT / "models" / "market_mood_params.json"
models_path = PROJECT_ROOT / "models"
anomaly_params_path = PROJECT_ROOT / "models" / "anomaly_params.json"

# Load historical data
historical_indices_df = pd.read_csv(historical_indices_path, parse_dates=['SEANCE'])
historical_df = pd.read_csv(REF_PATH, parse_dates=['SEANCE'])
historical_df["SEANCE"] = pd.to_datetime(historical_df["SEANCE"], errors="coerce").dt.normalize()
historical_indices_df["SEANCE"] = pd.to_datetime(historical_indices_df["SEANCE"], errors="coerce").dt.normalize()



def refresh_data():
    from agent.utils import get_symbols
    pipeline = live_engine.RealTimeSentimentPipeline()
    pipeline.run_pipeline()
    # Use the same reference dataset for both symbols and lookup
    REF_DATASET = str(REF_PATH)
    symbols = get_symbols(REF_DATASET)
    print(symbols)
    df_aaz = fetch_aaz_df()
    df_aaz = df_aaz[df_aaz["Nom"].isin(symbols)]
    print(len(df_aaz["Nom"].unique()))
    print()

    # Load reference dataset once + build lookup
    df_ref = pd.read_csv(REF_DATASET)
    lookup = build_valeur_lookup(df_ref)

    # Build today table
    df_new = build_target_table(df_aaz, lookup, seance=None)
    date = df_new["SEANCE"].max()
    df_new["SEANCE"] = pd.to_datetime(df_new["SEANCE"], errors="coerce").dt.normalize()
    
    # Analyze new data
    forecast_df, new_historical_output, new_indices_output, new_sentiment_output = analyze_new_data(
        date, 
        df_new, 
        str(sentiment_path), 
        historical_df, 
        historical_indices_df, 
        str(models_path), 
        str(anomaly_params_path), 
        str(score_params_path)
    )
    
    # Save forecast data
    forecast_csv_path = PROJECT_ROOT / "data" / "forecast_next_5_days.csv"
    forecast_df.to_csv(forecast_csv_path, index=False)
    print(f"Saved forecast to {forecast_csv_path}")
    
    # Update historical data files
    concat_df_if_new_date(str(REF_PATH), new_historical_output)
    concat_df_if_new_date(str(PROJECT_ROOT / "data" / "index_historical_data.csv"), new_indices_output)
    concat_df_if_new_date(str(PROJECT_ROOT / "data" / "sentiment_features.csv"), new_sentiment_output)
    
    return forecast_df, new_historical_output, new_indices_output, new_sentiment_output


import pandas as pd

def concat_df_if_new_date(path, df, date_col="SEANCE"):
    df_existing = pd.read_csv(path)

    # normalize both sides
    df_existing[date_col] = pd.to_datetime(df_existing[date_col], errors="coerce").dt.normalize()
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce").dt.normalize()

    new_dates = set(df[date_col].dropna().unique())
    existing_dates = set(df_existing[date_col].dropna().unique())

    if new_dates.issubset(existing_dates):
        print(f"  Skip {path}: date(s) already exist -> {sorted(new_dates)}")
        return

    df_out = pd.concat([df_existing, df], ignore_index=True)
    df_out.to_csv(path, index=False)
    print(f" Appended to {path}: {sorted(new_dates - existing_dates)}")


if __name__ == "__main__":
    forecast_df, new_historical_output, new_indices_output, new_sentiment_output = refresh_data()
    print(new_historical_output.head())
    