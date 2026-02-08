import sys
import os
import importlib
import json
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from real_time_utils import analyze_new_data
from scraper.OCHL_scraper import fetch_aaz_df, build_valeur_lookup, build_target_table
import real_time_utils
REF_PATH = "data/historical_data.csv"
import pandas as pd
import importlib.util
from pathlib import Path

module_path = Path("news_sentimental_analysis/src/pipeline/live_engine.py").resolve()

spec = importlib.util.spec_from_file_location("live_engine", module_path)
live_engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(live_engine)

# use it




historical_indices_df = pd.read_csv('data/index_historical_data.csv', parse_dates=['SEANCE'])
historical_df = pd.read_csv('data/historical_data.csv', parse_dates=['SEANCE'])
sentiment_path = 'news_sentimental_analysis/exports/history.json'
score_params_path = 'models/market_mood_params.json'
models_path = 'models'
anomaly_params_path = 'models/anomaly_params.json'
historical_df["SEANCE"] = pd.to_datetime(historical_df["SEANCE"], errors="coerce").dt.normalize()
historical_indices_df["SEANCE"] = pd.to_datetime(historical_indices_df["SEANCE"], errors="coerce").dt.normalize()



def refresh_data():
    from agent.utils import get_symbols
    pipeline = live_engine.RealTimeSentimentPipeline()
    pipeline.run_pipeline()
    # Use the same reference dataset for both symbols and lookup
    REF_DATASET = "data/historical_data.csv"
    symbols = get_symbols(REF_DATASET)
    print(symbols)
    df_aaz = fetch_aaz_df()
    df_aaz=df_aaz[df_aaz["Nom"].isin(symbols)]
    print(len(df_aaz["Nom"].unique()))
    print()

    # 2) Load reference dataset once + build lookup
    df_ref = pd.read_csv(REF_PATH)
    lookup = build_valeur_lookup(df_ref)

    # 3) Build today table
    df_new = build_target_table(df_aaz, lookup, seance=None)
    date=df_new["SEANCE"].max()
    df_new["SEANCE"] = pd.to_datetime(df_new["SEANCE"], errors="coerce").dt.normalize()
    forecast_df, new_historical_output, new_indices_output, new_sentiment_output = analyze_new_data(date, df_new, sentiment_path, historical_df, historical_indices_df, models_path, anomaly_params_path, score_params_path)
    forecast_df.to_csv("data/forecast_next_5_days.csv", index=False)
    concat_df_if_new_date("data/historical_data.csv", new_historical_output)
    concat_df_if_new_date("data/index_historical_data.csv", new_indices_output)
    concat_df_if_new_date("data/sentiment_features.csv", new_sentiment_output)
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
    