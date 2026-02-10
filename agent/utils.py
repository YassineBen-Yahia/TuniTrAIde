import sys
import os
import json
from pathlib import Path

import pandas as pd
import numpy as np

# Add project root to path if needed (logic from original file)
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app import models

# --- Data Fetching Functions ---

def get_symbols(data: str):
    """Get the list of unique symbols from the data."""
    try:
        df = pd.read_csv(data)
        symbols = df['VALEUR'].unique().tolist()
        s=[]
        s.extend(symbol for symbol in symbols)
        symbols=list(set(s))
        return symbols
    except FileNotFoundError:
        print(f"Warning: Data file {data} not found, returning empty symbol list")
        return []
    except Exception as e:
        print(f"Warning: Could not load symbols from {data}: {e}")
        return []

def get_last_days(data : str, days : int):
    """Get the last 'days' number of entries from the data."""
    try:
        df = pd.read_csv(data)
    except FileNotFoundError:
        print(f"Warning: Data file {data} not found, returning empty dataframe")
        return pd.DataFrame()
    except Exception as e:
        print(f"Warning: Could not load data from {data}: {e}")
        return pd.DataFrame()
    # Sort by SEANCE to ensure proper ordering
    df_sorted = df.sort_values('SEANCE')
    # Get unique dates and take the last 'days' number of them
    unique_dates = df_sorted['SEANCE'].unique()
    last_dates = unique_dates[-days:]
    return df_sorted[df_sorted['SEANCE'].isin(last_dates)]

def get_previous_days(df, idx, lookback=5):
    start = max(0, idx - lookback)
    return df.iloc[start:idx+1]

def get_article_analysis(symbol: str = None, data="data/sentiment_features.csv"):
    """
    Load and return article sentiment analysis data.
    
    If symbol is provided: Returns list of last 5 records for that symbol.
    If symbol is None: Returns dictionary {symbol: [last 3 records]} for all symbols.
    """
    try:
        df = pd.read_csv(data)
        
        # Ensure date column is datetime
        if 'SEANCE' in df.columns:
            df['SEANCE'] = pd.to_datetime(df['SEANCE'], errors='coerce')
        
        if symbol:
            # Specific symbol logic
            mask = df['VALEUR'].astype(str).str.strip().str.upper() == symbol.strip().upper()
            df_symbol = df[mask].copy()
            
            if df_symbol.empty:
                return []
            
            # Sort and take last 5
            df_symbol = df_symbol.sort_values('SEANCE')
            df_symbol = df_symbol.tail(5)
            
            # Format date to string
            df_symbol['SEANCE'] = df_symbol['SEANCE'].dt.strftime('%Y-%m-%d')
            
            return df_symbol.to_dict(orient='records')
            
        else:
            # All symbols logic (last 3 rows each)
            result = {}
            for sym, group in df.groupby('VALEUR'):
                group = group.sort_values('SEANCE')
                last_3 = group.tail(3).copy()
                last_3['SEANCE'] = last_3['SEANCE'].dt.strftime('%Y-%m-%d')
                result[str(sym)] = last_3.to_dict(orient='records')
            return result

    except Exception as e:
        print(f"❌ Error loading article analysis data: {e}")
        return [] if symbol else {}

def get_user_by_id_database(user_id: str, db):
    """Fetch user profile from database by user_id."""
    try:
        user = db.query(models.UserProfile).filter(models.UserProfile.user_id == user_id).first()
        if user:
            return {
                "user_id": user.user_id,
                "risk_tolerance": user.risk_tolerance,
                "investment_goals": user.investment_goals,
                "preferred_sectors": user.preferred_sectors,
                "investment_horizon": user.investment_horizon
            }
        else:
            return None
    except Exception as e:
        print(f"❌ Error fetching user profile from database: {e}")
        return None

# --- Forecast & Prediction Functions ---

def get_predicted_prices(csv_path='data/forecast_next_5_days.csv', symbol=None, 
                        date_column='SEANCE', symbol_column='VALEUR', code_column='CODE'):
    """
    Retrieve predicted prices with liquidity and volume data from the forecast CSV file.
    """
    try:
        # Load the forecast CSV file
        df = pd.read_csv(csv_path)
        
        # Strip whitespace from column names
        df.columns = df.columns.str.strip()
        
        # Ensure required columns exist
        required_columns = [date_column, symbol_column, code_column, 'CLOTURE', 'VOLUME', 'PROB_LIQUIDITY']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        # Convert date column to datetime if it's not already
        if not pd.api.types.is_datetime64_any_dtype(df[date_column]):
            df[date_column] = pd.to_datetime(df[date_column], errors='coerce')
        
        # Filter by symbol if specified
        if symbol is not None:
            # Try to match by both symbol name and code
            symbol_upper = symbol.upper()
            mask = (df[symbol_column].str.upper() == symbol_upper) | (df[code_column].str.upper() == symbol_upper)
            df_filtered = df[mask].copy()
            
            if len(df_filtered) == 0:
                print(f"Warning: No data found for symbol: {symbol}")
                return pd.DataFrame()
            
            df = df_filtered
        
        # Add derived features for better analysis
        df['predicted_price'] = df['CLOTURE']  # Alias for clarity
        df['predicted_volume'] = df['VOLUME']
        df['liquidity_probability'] = df['PROB_LIQUIDITY']
        
        # Calculate additional useful metrics if VAR_CLOTURE and VAR_VOLUME exist
        if 'VAR_CLOTURE' in df.columns:
            df['price_change_pct'] = df['VAR_CLOTURE']
        
        if 'VAR_VOLUME' in df.columns:
            df['volume_change_pct'] = df['VAR_VOLUME']
        
        # Sort by date and symbol for better readability
        df = df.sort_values([date_column, symbol_column]).reset_index(drop=True)
        
        # Select and reorder columns for output
        output_columns = [date_column, code_column, symbol_column, 'predicted_price', 
                         'predicted_volume', 'liquidity_probability']
        
        # Add optional columns if they exist
        optional_columns = ['price_change_pct', 'volume_change_pct']
        for col in optional_columns:
            if col in df.columns:
                output_columns.append(col)
        
        return df[output_columns]
        
    except FileNotFoundError:
        print(f"Error: Forecast file not found at {csv_path}")
        return pd.DataFrame()
    except Exception as e:
        print(f"Error reading forecast data: {e}")
        return pd.DataFrame()

def format_forecast_by_days(csv_path='data/forecast_next_5_days.csv', symbol=None):
    """
    Format the predicted prices, volume, and liquidity data by days for each symbol.
    """
    # Get the forecast data
    forecast_df = get_predicted_prices(csv_path, symbol)
    
    if forecast_df.empty:
        return {}
    
    formatted_data = {}
    
    # Group by symbol
    for symbol_name, symbol_group in forecast_df.groupby('VALEUR'):
        # Sort by date to ensure correct day ordering
        symbol_group = symbol_group.sort_values('SEANCE').reset_index(drop=True)
        
        # Initialize symbol data
        symbol_data = {
            'symbol_info': {
                'code': symbol_group.iloc[0]['CODE'],
                'name': symbol_name
            },
            'dates': symbol_group['SEANCE'].dt.strftime('%Y-%m-%d').tolist()
        }
        
        # Add day-by-day predictions
        for idx, (_, row) in enumerate(symbol_group.iterrows(), 1):
            day_suffix = f"_day{idx}"
            
            # Predicted prices
            symbol_data[f'predicted_price{day_suffix}'] = round(row['predicted_price'], 3)
            
            # Predicted volumes
            symbol_data[f'predicted_volume{day_suffix}'] = int(row['predicted_volume'])
            
            # Liquidity probabilities
            symbol_data[f'liquidity_prob{day_suffix}'] = round(row['liquidity_probability'], 3)
            
            # Optional: Price and volume changes if available
            if 'price_change_pct' in row and pd.notna(row['price_change_pct']):
                symbol_data[f'price_change_pct{day_suffix}'] = round(row['price_change_pct'], 2)
            
            if 'volume_change_pct' in row and pd.notna(row['volume_change_pct']):
                symbol_data[f'volume_change_pct{day_suffix}'] = round(row['volume_change_pct'], 2)
        
        # Add summary statistics
        symbol_data['summary'] = {
            'total_days': len(symbol_group),
            'avg_predicted_price': round(symbol_group['predicted_price'].mean(), 3),
            'price_trend': 'increasing' if symbol_group['predicted_price'].iloc[-1] > symbol_group['predicted_price'].iloc[0] else 'decreasing',
            'avg_volume': int(symbol_group['predicted_volume'].mean()),
            'avg_liquidity_prob': round(symbol_group['liquidity_probability'].mean(), 3),
            'min_price': round(symbol_group['predicted_price'].min(), 3),
            'max_price': round(symbol_group['predicted_price'].max(), 3)
        }
        
        formatted_data[symbol_name] = symbol_data
    
    return formatted_data

def get_symbol_forecast_dict(symbol, csv_path='data/forecast_next_5_days.csv'):
    """
    Get forecast data for a specific symbol formatted as a dictionary.
    """
    if symbol is None:
        raise ValueError("Symbol must be provided for this function")
    
    formatted_data = format_forecast_by_days(csv_path, symbol)
    
    # Return the first (and should be only) symbol's data
    if formatted_data:
        return list(formatted_data.values())[0]
    else:
        return {}

def get_all_symbols_forecast_dict(csv_path='data/forecast_next_5_days.csv'):
    """
    Get forecast data for all symbols formatted as a dictionary.
    """
    return format_forecast_by_days(csv_path)

def generate_dummy_price_predictions():
    """Generate dummy price predictions for the next 5 days and save to CSV."""
    # Read the existing dataset
    df = pd.read_csv('data/historical_data.csv')

    # Set random seed for reproducibility
    np.random.seed(42)

    # Function to generate realistic price predictions
    def generate_price_predictions(current_price, days=5):
        """Generate realistic stock price predictions based on current price"""
        predictions = []
        price = current_price
        
        for day in range(1, days + 1):
            # Add some trend (small upward or downward bias)
            trend = np.random.normal(0, 0.002)  # Small daily trend
            
            # Add noise
            noise = np.random.normal(0, 0.01)   # Daily volatility
            
            # Calculate next day price (ensuring it stays positive)
            price_change = trend + noise
            price = price * (1 + price_change)
            
            # Ensure price doesn't go negative
            price = max(price, 0.01)
            
            predictions.append(round(price, 2))
        
        return predictions

    # Generate predictions for each row
    prediction_columns = []
    for i, row in df.iterrows():
        current_price = row['CLOTURE']
        predictions = generate_price_predictions(current_price)
        prediction_columns.append(predictions)

    # Convert to DataFrame and add columns
    predictions_df = pd.DataFrame(prediction_columns, 
                                columns=['PREDICTED_DAY_1', 'PREDICTED_DAY_2', 
                                    'PREDICTED_DAY_3', 'PREDICTED_DAY_4', 'PREDICTED_DAY_5'])

    # Concatenate with original DataFrame
    df_with_predictions = pd.concat([df, predictions_df], axis=1)

    # Save to new file
    df_with_predictions.to_csv('data/forecast_next_5_days.csv', index=False)

# --- Data Formatting Functions ---

def _format_market_data_summary(df: pd.DataFrame) -> str:
    # adjust column names to your actual schema
    grouped = df.groupby("VALEUR").agg(
        last_close=("CLOTURE", "last"),
        mean_close=("CLOTURE", "mean"),
        min_close=("CLOTURE", "min"),
        max_close=("CLOTURE", "max"),
        first_day_last_predicted=("PREDICTED_DAY_1", "last"),
        second_day_last_predicted=("PREDICTED_DAY_2", "last"),
        third_day_last_predicted=("PREDICTED_DAY_3", "last"),
        fourth_day_last_predicted=("PREDICTED_DAY_4", "last"),
        fifth_day_last_predicted=("PREDICTED_DAY_5", "last"),
        volume_sum=("QUANTITE_NEGOCIEE", "sum"),
        volatility_mean=("VOLATILITE", "mean"),
        anomaly_count=("ANOMALY_DETECTED", "sum"),
        anomaly_dates=("SEANCE", lambda x: x[df.loc[x.index, "ANOMALY_DETECTED"] == 1].tolist()),
    ).reset_index()

    summary = grouped.to_dict(orient="records")
    return json.dumps(summary, indent=2)

def format_market_data_summary(df: pd.DataFrame) -> str:
    d = df.copy()

    # 1) Ensure ordering so "last" really means latest
    d["SEANCE_PARSED"] = pd.to_datetime(d["SEANCE"], errors="coerce")
    if d["SEANCE_PARSED"].notna().any():
        d = d.sort_values(["VALEUR", "SEANCE_PARSED"])
    else:
        d = d.sort_values(["VALEUR", "SEANCE"])

    # 2) Normalize anomaly flag (using VARIATION_ANOMALY from new schema)
    #    The new file uses VARIATION_ANOMALY which is likely 0 or 1.
    d["ANOMALY_FLAG"] = d["VARIATION_ANOMALY"].apply(
        lambda x: 1 if str(x).strip().lower() in {"1", "true", "yes"} else 0
    )

    grouped = d.groupby("VALEUR").agg(
        # --- Price snapshot ---
        last_close=("CLOTURE", "last"),
        first_close=("CLOTURE", "first"),
        mean_close=("CLOTURE", "mean"),
        min_close=("CLOTURE", "min"),
        max_close=("CLOTURE", "max"),
        n_obs=("CLOTURE", "size"),

        # --- Liquidity ---
        volume_sum=("QUANTITE_NEGOCIEE", "sum"),
        volume_mean=("QUANTITE_NEGOCIEE", "mean"),
        tx_mean=("NB_TRANSACTION", "mean"),

        # --- Risk / volatility ---
        #volatility_mean=("VOLATILITE", "mean"),

        # --- Trend/momentum (using VARIATION) ---
        up_days_count=("VARIATION", lambda s: int((s > 0).sum())),

        # --- Anomalies presence + details ---
        anomaly_count=("ANOMALY_FLAG", "sum"),
        anomaly_score_latest=("variation_z_score", "last"),
        anomaly_score_max=("variation_z_score", "max"),
        anomaly_score_mean=("variation_z_score", "mean"),

        # List of anomaly dates (keeps details for inspection)
        anomaly_dates=("SEANCE", lambda s: s[d.loc[s.index, "ANOMALY_FLAG"] == 1].astype(str).tolist()),

        # Scalar recency indicator
        last_anomaly_date=("SEANCE", lambda s: (
            s[d.loc[s.index, "ANOMALY_FLAG"] == 1].astype(str).iloc[-1]
            if (d.loc[s.index, "ANOMALY_FLAG"] == 1).any()
            else None
        )),
    ).reset_index()
    # Add forecast data for each symbol
    grouped['forecast'] = grouped['VALEUR'].apply(
        lambda symbol: (
            format_forecast_by_days(
                csv_path='data/forecast_next_5_days.csv',
                symbol=symbol.strip().upper()
            ).get(symbol.strip().upper(), {})
        )
    )

    # 3) Add derived trend metrics (directionality)
    grouped["period_return_pct"] = (
        (grouped["last_close"] / grouped["first_close"] - 1.0) * 100
    ).replace([np.inf, -np.inf], np.nan)

    grouped["trend_slope_pct_per_day"] = (
        ((grouped["last_close"] - grouped["first_close"]) / (grouped["n_obs"].clip(lower=2) - 1))
        / grouped["last_close"]
        * 100
    ).replace([np.inf, -np.inf], np.nan)
   

   
    def _pred_ret(pred_col):
        return ((grouped[pred_col] / grouped["last_close"]) - 1.0) * 100

    
    grouped = grouped.replace({np.nan: None})

    summary = grouped.to_dict(orient="records")
    return json.dumps(summary, indent=2)