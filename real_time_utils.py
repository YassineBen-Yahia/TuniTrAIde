import json
import pandas as pd
import numpy as np
import os
import joblib
from scipy.stats import percentileofscore
from statsmodels.tsa.arima.model import ARIMA

# Calculate PROB_LIQUIDITY for historical data
epsilon = 1e-6
def compute_liquidity(volume, close, avg_range, epsilon=1e-6):
    """Compute liquidity score. Returns -inf when volume*close <= 0."""
    numerator = volume * close
    if numerator <= 0:
        return float('-inf')  # No trades -> lowest possible liquidity
    denom = avg_range + (epsilon if avg_range == 0 else 0)
    if denom <= 0:
        denom = epsilon
    return np.log(numerator / denom)

def feature_engineer(market_df: pd.DataFrame, sentiment_df: pd.DataFrame, historical_indices_df: pd.DataFrame, historical_df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Combines market data and sentiment data, adding engineered features.
    
    Args:
        market_df: DataFrame with 20 rows of market data (current trading day).
        sentiment_df: DataFrame with new sentiment analysis data.
        historical_indices_df: DataFrame with index data including various TUN indices.
        historical_df: DataFrame with historical market data for context and rolling features.
        
    Returns:
        tuple[pd.DataFrame, dict]: A combined dataframe with features ready for forecasting/history and a dictionary of additional features.
    """
    market_df = market_df.copy()
    sentiment_df = sentiment_df.copy()
    historical_indices_df = historical_indices_df.copy()
    historical_df = historical_df.copy()

    new_data_df = market_df.merge(sentiment_df, on=['VALEUR', 'SEANCE'], how='left')
        
    historical_df = historical_df[['SEANCE', 'GROUPE', 'CODE', 'VALEUR', 'OUVERTURE', 'CLOTURE', 'PLUS_BAS', 'PLUS_HAUT', 'QUANTITE_NEGOCIEE', 'NB_TRANSACTION', 'CAPITAUX', 'Mean_Weighted_Sentiment', 'Article_Count', 'Sentiment_Intensity']]
    historical_df = historical_df.merge(historical_indices_df, on='SEANCE', how='left')

    # CRITICAL FIX: Compute historical liquidity BEFORE adding new data to avoid data leakage
    # This ensures the distribution is built only from historical data (like in the notebook)
    historical_df['SEANCE'] = pd.to_datetime(historical_df['SEANCE'])
    historical_df = historical_df.sort_values(by=['CODE', 'SEANCE']).reset_index(drop=True)
    
    historical_liquidity = {}
    for code in historical_df['CODE'].unique():
        stock_df = historical_df[historical_df['CODE'] == code].sort_values('SEANCE').reset_index(drop=True)
                
        # Calculate rolling 5-day average range
        stock_df['range'] = stock_df['PLUS_HAUT'] - stock_df['PLUS_BAS']
        stock_df['rolling_avg_range'] = stock_df['range'].rolling(window=5, min_periods=1).mean()
        
        volume = stock_df['QUANTITE_NEGOCIEE'].values
        close = stock_df['CLOTURE'].values
        rolling_avg_range = stock_df['rolling_avg_range'].values
        
        liq = []
        for i in range(len(volume)):
            liq_val = compute_liquidity(volume[i], close[i], rolling_avg_range[i], epsilon)
            if np.isfinite(liq_val):
                liq.append(liq_val)
        
        # Add a floor value for zero-volume days so percentileofscore ranks them at the bottom
        if len(liq) > 0:
            floor_val = min(liq) - 1.0
            liq.append(floor_val)
        
        historical_liquidity[code] = np.array(liq)

    combined_df = pd.concat([historical_df, new_data_df], ignore_index=True, sort=False)

    combined_df['SEANCE'] = pd.to_datetime(combined_df['SEANCE'])
    combined_df = combined_df.sort_values(by=['CODE', 'SEANCE']).reset_index(drop=True)

    # Calculate INDICE_VEILLE as previous day's INDICE_JOUR (shifted by 1 day)
    indices_jour_cols = [
        'TUNBANQ_INDICE_JOUR', 'TUNFIN_INDICE_JOUR', 'TUNINDEX_INDICE_JOUR',
        'TUNINDEX20_INDICE_JOUR', 'TUNSAC_INDICE_JOUR'
    ]
    
    indices_veille_cols = [
        'TUNBANQ_INDICE_VEILLE', 'TUNFIN_INDICE_VEILLE', 'TUNINDEX_INDICE_VEILLE',
        'TUNINDEX20_INDICE_VEILLE', 'TUNSAC_INDICE_VEILLE'
    ]
    
    # For each CODE group, shift INDICE_JOUR by 1 to get previous day's value
    for jour_col, veille_col in zip(indices_jour_cols, indices_veille_cols):
        combined_df[veille_col] = combined_df.groupby('CODE')[jour_col].shift(1)
        # Fill NaN with forward fill for the first row of each group
        combined_df[veille_col] = combined_df.groupby('CODE')[veille_col].ffill()
    
    # Calculate VARIATION_VEILLE as % change from INDICE_VEILLE to INDICE_JOUR
    variation_cols = [
        'TUNBANQ_VARIATION_VEILLE', 'TUNFIN_VARIATION_VEILLE', 
        'TUNINDEX_VARIATION_VEILLE', 'TUNINDEX20_VARIATION_VEILLE', 
        'TUNSAC_VARIATION_VEILLE'
    ]
    
    for jour_col, veille_col, var_col in zip(indices_jour_cols, indices_veille_cols, variation_cols):
        combined_df[var_col] = ((combined_df[jour_col] - combined_df[veille_col]) / 
                                 combined_df[veille_col].replace(0, np.nan)) * 100
        combined_df[var_col] = combined_df[var_col].fillna(0)

    ## financial features
    def compute_financial_features(group):
        """Compute financial features for each CODE group independently"""
        
        # 1. Intraday Volatility (Price Range as % of Close)
        group['Intraday_Range_Pct'] = 0.0
        valid_mask = group['CLOTURE'] > 0
        group.loc[valid_mask, 'Intraday_Range_Pct'] = (
            (group.loc[valid_mask, 'PLUS_HAUT'] - group.loc[valid_mask, 'PLUS_BAS']) / 
            group.loc[valid_mask, 'CLOTURE']
        ) * 100
        
        # 2. Daily Return (% change from open to close)
        group['Daily_Return_Pct'] = 0.0
        valid_mask = group['OUVERTURE'] > 0
        group.loc[valid_mask, 'Daily_Return_Pct'] = (
            (group.loc[valid_mask, 'CLOTURE'] - group.loc[valid_mask, 'OUVERTURE']) / 
            group.loc[valid_mask, 'OUVERTURE']
        ) * 100
        
        # 3. Price Position in Range (0 to 1)
        group['Price_Position'] = 0.5  # default to middle
        range_diff = group['PLUS_HAUT'] - group['PLUS_BAS']
        valid_mask = range_diff > 0
        group.loc[valid_mask, 'Price_Position'] = (
            (group.loc[valid_mask, 'CLOTURE'] - group.loc[valid_mask, 'PLUS_BAS']) / 
            range_diff[valid_mask]
        )
        
        # 4. Average Trade Size
        group['Avg_Trade_Size'] = 0.0
        valid_mask = group['NB_TRANSACTION'] > 0
        group.loc[valid_mask, 'Avg_Trade_Size'] = (
            group.loc[valid_mask, 'QUANTITE_NEGOCIEE'] / 
            group.loc[valid_mask, 'NB_TRANSACTION']
        )
        
        # 5. Price Impact
        group['Price_Impact'] = 0.0
        valid_mask = group['QUANTITE_NEGOCIEE'] > 0
        price_change = abs(group['CLOTURE'] - group['OUVERTURE'])
        group.loc[valid_mask, 'Price_Impact'] = (
            price_change[valid_mask] / group.loc[valid_mask, 'QUANTITE_NEGOCIEE']
        )
        
        # 6. Upper Shadow Ratio
        group['Upper_Shadow_Ratio'] = 0.0
        upper_body = group[['OUVERTURE', 'CLOTURE']].max(axis=1)
        valid_mask = range_diff > 0
        group.loc[valid_mask, 'Upper_Shadow_Ratio'] = (
            (group.loc[valid_mask, 'PLUS_HAUT'] - upper_body[valid_mask]) / 
            range_diff[valid_mask]
        )
        
        # 7. Lower Shadow Ratio
        group['Lower_Shadow_Ratio'] = 0.0
        lower_body = group[['OUVERTURE', 'CLOTURE']].min(axis=1)
        valid_mask = range_diff > 0
        group.loc[valid_mask, 'Lower_Shadow_Ratio'] = (
            (lower_body[valid_mask] - group.loc[valid_mask, 'PLUS_BAS']) / 
            range_diff[valid_mask]
        )

        # 8. Closing price variation from previous day
        group['VARIATION'] = group['CLOTURE'].pct_change() * 100
        group['VARIATION'] = group['VARIATION'].replace([np.inf, -np.inf], 0).fillna(0)
        
        # Clamp ratios to [0, 1]
        group['Price_Position'] = group['Price_Position'].clip(0, 1)
        group['Upper_Shadow_Ratio'] = group['Upper_Shadow_Ratio'].clip(0, 1)
        group['Lower_Shadow_Ratio'] = group['Lower_Shadow_Ratio'].clip(0, 1)
        
        return group
    
    combined_df = combined_df.groupby('CODE').apply(compute_financial_features).reset_index(drop=True)
    
    #Sentiment rolling features
    combined_df['Mean_Weighted_Sentiment'] = combined_df['Mean_Weighted_Sentiment'].fillna(0)
    combined_df['Sentiment_Intensity'] = combined_df['Sentiment_Intensity'].fillna(0)
    combined_df['Article_Count'] = combined_df['Article_Count'].fillna(0)

    # Create rolling features to capture lingering effects
    for window in [3, 7]:
        combined_df[f'Mean_Sentiment_{window}d'] = combined_df.groupby('CODE')['Mean_Weighted_Sentiment'].transform(
            lambda x: x.rolling(window=window, min_periods=1).mean()
        )
        combined_df[f'Intensity_{window}d'] = combined_df.groupby('CODE')['Sentiment_Intensity'].transform(
            lambda x: x.rolling(window=window, min_periods=1).mean()
        )
        combined_df[f'Article_Count_{window}d'] = combined_df.groupby('CODE')['Article_Count'].transform(
            lambda x: x.rolling(window=window, min_periods=1).mean()
        )

    # Compute PROB_LIQUIDITY using the historical_liquidity computed before merging new data
    combined_df['PROB_LIQUIDITY'] = np.nan

    for code in combined_df['CODE'].unique():
        if code not in historical_liquidity:
            continue
        
        # Get indices for this code in the original dataset
        code_mask = combined_df['CODE'] == code
        stock_indices = combined_df[code_mask].index
        
        # Get stock data for this code
        stock_df = combined_df[code_mask].sort_values('SEANCE').copy()
        
        # Calculate rolling 5-day average range
        stock_df['range'] = stock_df['PLUS_HAUT'] - stock_df['PLUS_BAS']
        stock_df['rolling_avg_range'] = stock_df['range'].rolling(window=5, min_periods=1).mean()
        
        # Get historical liquidity distribution for this ticker
        hist_liq = historical_liquidity[code]
        
        # Calculate liquidity and probability for each row
        for idx, row in stock_df.iterrows():
            volume = row['QUANTITE_NEGOCIEE']
            close = row['CLOTURE']
            rolling_avg_range = row['rolling_avg_range']
            
            # Compute liquidity
            liquidity_val = compute_liquidity(volume, close, rolling_avg_range, epsilon)
            
            # Compute probability based on historical distribution
            if np.isfinite(liquidity_val):
                prob = percentileofscore(hist_liq, liquidity_val) / 100.0
            else:
                # Zero volume -> minimum liquidity -> probability = 0
                prob = 0.0
            
            # Update the dataset with the computed probability using the original index
            combined_df.loc[idx, 'PROB_LIQUIDITY'] = prob

    # Reorder columns to match model training order
    feature_order = ['OUVERTURE',
                    'CLOTURE',
                    'PLUS_BAS',
                    'PLUS_HAUT',
                    'QUANTITE_NEGOCIEE',
                    'NB_TRANSACTION',
                    'CAPITAUX',
                    'Intraday_Range_Pct',
                    'Daily_Return_Pct',
                    'Price_Position',
                    'Avg_Trade_Size',
                    'Price_Impact',
                    'Upper_Shadow_Ratio',
                    'Lower_Shadow_Ratio',
                    'VARIATION',
                    'TUNBANQ_INDICE_JOUR',
                    'TUNFIN_INDICE_JOUR',
                    'TUNINDEX_INDICE_JOUR',
                    'TUNINDEX20_INDICE_JOUR',
                    'TUNSAC_INDICE_JOUR',
                    'TUNBANQ_INDICE_VEILLE',
                    'TUNFIN_INDICE_VEILLE',
                    'TUNINDEX_INDICE_VEILLE',
                    'TUNINDEX20_INDICE_VEILLE',
                    'TUNSAC_INDICE_VEILLE',
                    'TUNBANQ_VARIATION_VEILLE',
                    'TUNFIN_VARIATION_VEILLE',
                    'TUNINDEX_VARIATION_VEILLE',
                    'TUNINDEX20_VARIATION_VEILLE',
                    'TUNSAC_VARIATION_VEILLE',
                    'Mean_Weighted_Sentiment',
                    'Sentiment_Intensity',
                    'Article_Count',
                    'Mean_Sentiment_3d',
                    'Intensity_3d',
                    'Article_Count_3d',
                    'Mean_Sentiment_7d',
                    'Intensity_7d',
                    'Article_Count_7d',
                    'PROB_LIQUIDITY']
    
    # Build the final column order: identifiers + ordered features
    identifier_cols = ['SEANCE', 'GROUPE', 'CODE', 'VALEUR']
    ordered_cols = identifier_cols.copy()
    for col in feature_order:
        if col in combined_df.columns and col not in ordered_cols:
            ordered_cols.append(col)
    
    combined_df = combined_df[ordered_cols]
    
    new_indices_output = combined_df[combined_df['SEANCE'] == market_df['SEANCE'].iloc[0]][['SEANCE','TUNBANQ_INDICE_JOUR', 'TUNFIN_INDICE_JOUR', 'TUNINDEX_INDICE_JOUR',
        'TUNINDEX20_INDICE_JOUR', 'TUNSAC_INDICE_JOUR', 'TUNBANQ_INDICE_VEILLE',
        'TUNFIN_INDICE_VEILLE', 'TUNINDEX_INDICE_VEILLE', 'TUNINDEX20_INDICE_VEILLE',
        'TUNSAC_INDICE_VEILLE', 'TUNBANQ_VARIATION_VEILLE', 'TUNFIN_VARIATION_VEILLE',
        'TUNINDEX_VARIATION_VEILLE', 'TUNINDEX20_VARIATION_VEILLE', 'TUNSAC_VARIATION_VEILLE']].reset_index(drop=True)

    return combined_df, historical_liquidity, new_indices_output


def forecast(processed_df: pd.DataFrame, models_path: str, historical_liquidity: dict) -> pd.DataFrame:
    """
    Generates 5-day forecasts using Hybrid ARIMA(5,1,0) + XGBoost MultiOutput Residual models.
    
    Uses saved ARIMA + XGBoost models for price & volume,
    then computes VAR_CLOTURE, VAR_VOLUME, and PROB_LIQUIDITY.
    VAR_X = (X_day - X_day-1) / X_day-1  (day-over-day % variation)
    Zero-volume forecasts -> PROB_LIQUIDITY = 0.0.
    
    Args:
        processed_df: Full DataFrame resulting from feature_engineer (complete history + new day).
        models_path: Path to saved forecasting models (price models root dir).
        historical_liquidity: Dict of historical liquidity distributions per CODE.
    Returns:
        pd.DataFrame: Forecast DataFrame with columns SEANCE, CODE, VALEUR, CLOTURE, VOLUME, VAR_CLOTURE, VAR_VOLUME, PROB_LIQUIDITY.
    """
    dataset = processed_df.copy()
    
    HORIZON = 5
    PRICE_MODELS_DIR = models_path
    VOLUME_MODELS_DIR = os.path.join(models_path, 'volume')
    
    # XGBoost residual features: all columns except identifiers (must match training order)
    xgb_residual_features = [col for col in dataset.columns if col not in ['SEANCE', 'GROUPE', 'CODE', 'VALEUR']]
    
    # Build CODE -> VALEUR mapping
    code_valeur_map = dataset.drop_duplicates('CODE').set_index('CODE')['VALEUR'].to_dict()

    # Calculating non-trading days for 2026
    holidays_2026 = [
        pd.Timestamp('2026-01-01'),
        pd.Timestamp('2026-03-20'), pd.Timestamp('2026-03-21'), pd.Timestamp('2026-03-22'),
        pd.Timestamp('2026-04-09'), pd.Timestamp('2026-04-27'), pd.Timestamp('2026-04-28'),
        pd.Timestamp('2026-05-01'),
        pd.Timestamp('2026-06-16'),
        pd.Timestamp('2026-07-25'),
        pd.Timestamp('2026-08-13'), pd.Timestamp('2026-08-25'),
        pd.Timestamp('2026-10-15'),
        pd.Timestamp('2026-12-17')
    ]

    # Generate all weekends in 2026
    weekends_2026 = pd.date_range('2026-01-01', '2026-12-31', freq='D')
    weekends_2026 = [d for d in weekends_2026 if d.dayofweek >= 5]

    # Combine holidays and weekends
    non_trading_days_2026 = sorted(list(set(holidays_2026 + weekends_2026)))

    # Generate next 5 business trading days after last recorded date
    last_date = dataset['SEANCE'].max()
    forecast_dates = []
    candidate = last_date + pd.Timedelta(days=1)
    while len(forecast_dates) < HORIZON:
        if candidate not in non_trading_days_2026:
            forecast_dates.append(candidate)
        candidate += pd.Timedelta(days=1)

    # Forecast for each ticker
    tickers = dataset['CODE'].unique()
    forecast_rows = []

    for code in tickers:
        ticker_df = dataset[dataset['CODE'] == code].sort_values('SEANCE').reset_index(drop=True)
        
        if len(ticker_df) < 20:
            continue
        
        origin_row = ticker_df.iloc[-1]
        origin_close = origin_row['CLOTURE']
        origin_volume = origin_row['QUANTITE_NEGOCIEE']
        valeur = code_valeur_map.get(code, code)
        
        # ---- Load and extend PRICE models ----
        try:
            price_arima = joblib.load(os.path.join(PRICE_MODELS_DIR, f"arima_model_{code}.pkl"))
            price_xgb = joblib.load(os.path.join(PRICE_MODELS_DIR, f"xgb_residual_model_{code}.pkl"))
            
            # Extend ARIMA to the full series (model was trained on partial data)
            full_close = ticker_df['CLOTURE']
            extended_price_arima = price_arima.apply(full_close)
            price_arima_forecast = extended_price_arima.forecast(steps=HORIZON)
            
            # XGBoost residual prediction using last row features
            origin_features = origin_row[xgb_residual_features].values.reshape(1, -1)
            price_xgb_pred = price_xgb.predict(origin_features)[0]
            
            forecasted_close = price_arima_forecast.values + price_xgb_pred
        except Exception:
            forecasted_close = np.full(HORIZON, origin_close)
        
        # ---- Load and extend VOLUME models ----
        try:
            vol_arima = joblib.load(os.path.join(VOLUME_MODELS_DIR, f"arima_model_volume_{code}.pkl"))
            vol_xgb = joblib.load(os.path.join(VOLUME_MODELS_DIR, f"xgb_residual_model_volume_{code}.pkl"))
            
            full_volume = ticker_df['QUANTITE_NEGOCIEE']
            extended_vol_arima = vol_arima.apply(full_volume)
            vol_arima_forecast = extended_vol_arima.forecast(steps=HORIZON)
            
            origin_features = origin_row[xgb_residual_features].values.reshape(1, -1)
            vol_xgb_pred = vol_xgb.predict(origin_features)[0]
            
            forecasted_volume = np.maximum(vol_arima_forecast.values + vol_xgb_pred, 0)
        except Exception:
            forecasted_volume = np.full(HORIZON, origin_volume)
        
        # ---- Compute rolling avg range (last 5 known days) ----
        range_vals = (ticker_df['PLUS_HAUT'] - ticker_df['PLUS_BAS']).tail(5)
        last_avg_range = range_vals.mean()
        
        # ---- Compute PROB_LIQUIDITY ----
        hist_liq = historical_liquidity.get(code)
        
        # Track previous day's values for day-over-day variation
        prev_close = origin_close
        prev_volume = origin_volume
        
        for h in range(HORIZON):
            fc_close = forecasted_close[h]
            fc_volume = forecasted_volume[h]
            
            # Day-over-day percentage variation
            var_cloture = (fc_close - prev_close) / prev_close if prev_close != 0 else 0
            var_volume = (fc_volume - prev_volume) / prev_volume if prev_volume != 0 else 0
            
            # Liquidity probability
            prob_liq = 0.0  # Default: minimum liquidity
            if hist_liq is not None and len(hist_liq) > 0:
                liq_val = compute_liquidity(fc_volume, fc_close, last_avg_range, epsilon)
                if np.isfinite(liq_val):
                    prob_liq = percentileofscore(hist_liq, liq_val) / 100.0
            
            forecast_rows.append({
                'SEANCE': forecast_dates[h],
                'CODE': code,
                'VALEUR': valeur,
                'CLOTURE': round(fc_close, 3),
                'VOLUME': int(round(fc_volume)),
                'VAR_CLOTURE': round(var_cloture, 6),
                'VAR_VOLUME': round(var_volume, 6),
                'PROB_LIQUIDITY': round(prob_liq, 4),
            })
            
            # Update previous day values for next iteration
            prev_close = fc_close
            prev_volume = fc_volume

    # Build final DataFrame
    forecast_df = pd.DataFrame(forecast_rows)
    forecast_df = forecast_df.sort_values(['CODE', 'SEANCE']).reset_index(drop=True)

    return forecast_df

def detect_anomalies_with_params(df: pd.DataFrame, anomaly_params: dict) -> pd.DataFrame:
    """
    Detect anomalies using pre-fitted parameters (no retraining on new data).
    
    Args:
        df: DataFrame with new data (must have CODE, QUANTITE_NEGOCIEE, VARIATION columns)
        anomaly_params: Dictionary of fitted parameters from fit_anomaly_detectors()
    
    Returns:
        pd.DataFrame: Input dataframe with anomaly flags added
    """
    df = df.copy()
    
    # Initialize columns
    df['volume_z_score'] = 0.0
    df['VOLUME_Anomaly'] = 0
    df['variation_z_score'] = 0.0
    df['VARIATION_ANOMALY'] = 0
    
    for code in df['CODE'].unique():
        if code not in anomaly_params:
            continue
            
        params = anomaly_params[code]
        code_mask = df['CODE'] == code
        
        # Volume z-score using FIXED historical parameters
        volume_mean = params['volume_mean']
        volume_std = params['volume_std']
        
        if volume_std > 0:
            df.loc[code_mask, 'volume_z_score'] = (
                (df.loc[code_mask, 'QUANTITE_NEGOCIEE'] - volume_mean) / volume_std
            )
        
        df.loc[code_mask, 'VOLUME_Anomaly'] = (
            df.loc[code_mask, 'volume_z_score'] > params['volume_threshold']
        ).astype(int)
        
        # Variation z-score using FIXED historical parameters
        variation_mean = params['variation_mean']
        variation_std = params['variation_std']
        
        if variation_std > 0:
            df.loc[code_mask, 'variation_z_score'] = (
                (df.loc[code_mask, 'VARIATION'] - variation_mean) / variation_std
            )
        
        df.loc[code_mask, 'VARIATION_ANOMALY'] = (
            np.abs(df.loc[code_mask, 'variation_z_score']) > params['variation_threshold']
        ).astype(int)
    
    return df

def link_anomalies_to_news(df: pd.DataFrame, news_window=3) -> pd.DataFrame:
    """
    Link detected anomalies to news events (post-news reaction vs pre-news leakage).
    
    Args:
        df: DataFrame with anomaly flags and sentiment data
        news_window: Number of days to look back/forward for news
    
    Returns:
        pd.DataFrame: Input dataframe with news-linked anomaly flags
    """
    df = df.copy()
    df = df.sort_values(['CODE', 'SEANCE'])
    
    # Identify news events
    df['has_news'] = (df['Article_Count'] > 0).astype(int)
    df['news_pos'] = ((df['Article_Count'] > 0) & (df['Mean_Weighted_Sentiment'] > 0)).astype(int)
    df['news_neg'] = ((df['Article_Count'] > 0) & (df['Mean_Weighted_Sentiment'] < 0)).astype(int)
    
    # Prior news (for post-news analysis)
    grouped = df.groupby('CODE')
    df['prior_any_news'] = grouped['has_news'].transform(
        lambda x: x.rolling(window=news_window, min_periods=1).sum().shift(1).fillna(0)
    ) > 0
    df['prior_pos_news'] = grouped['news_pos'].transform(
        lambda x: x.rolling(window=news_window, min_periods=1).sum().shift(1).fillna(0)
    ) > 0
    df['prior_neg_news'] = grouped['news_neg'].transform(
        lambda x: x.rolling(window=news_window, min_periods=1).sum().shift(1).fillna(0)
    ) > 0
    
    # Future news (for pre-news/leakage analysis)
    def get_future_rolling(series, w):
        return series.iloc[::-1].rolling(window=w, min_periods=1).sum().shift(1).iloc[::-1].fillna(0) > 0
    
    df['future_any_news'] = grouped['has_news'].transform(lambda x: get_future_rolling(x, news_window))
    df['future_pos_news'] = grouped['news_pos'].transform(lambda x: get_future_rolling(x, news_window))
    df['future_neg_news'] = grouped['news_neg'].transform(lambda x: get_future_rolling(x, news_window))
    
    # VARIATION anomalies
    df['VARIATION_ANOMALY_POST_NEWS'] = 0
    df['VARIATION_ANOMALY_PRE_NEWS'] = 0
    
    cond_var_post_pos = (df['VARIATION_ANOMALY'] == 1) & (df['variation_z_score'] > 0) & df['prior_pos_news']
    cond_var_post_neg = (df['VARIATION_ANOMALY'] == 1) & (df['variation_z_score'] < 0) & df['prior_neg_news']
    df.loc[cond_var_post_pos | cond_var_post_neg, 'VARIATION_ANOMALY_POST_NEWS'] = 1
    
    not_post_var = (df['VARIATION_ANOMALY'] == 1) & (df['VARIATION_ANOMALY_POST_NEWS'] == 0)
    cond_var_pre_pos = not_post_var & (df['variation_z_score'] > 0) & df['future_pos_news']
    cond_var_pre_neg = not_post_var & (df['variation_z_score'] < 0) & df['future_neg_news']
    df.loc[cond_var_pre_pos | cond_var_pre_neg, 'VARIATION_ANOMALY_PRE_NEWS'] = 1
    
    # VOLUME anomalies
    df['VOLUME_ANOMALY_POST_NEWS'] = 0
    df['VOLUME_ANOMALY_PRE_NEWS'] = 0
    
    cond_vol_post = (df['VOLUME_Anomaly'] == 1) & df['prior_any_news']
    df.loc[cond_vol_post, 'VOLUME_ANOMALY_POST_NEWS'] = 1
    
    not_post_vol = (df['VOLUME_Anomaly'] == 1) & (df['VOLUME_ANOMALY_POST_NEWS'] == 0)
    cond_vol_pre = not_post_vol & df['future_any_news']
    df.loc[cond_vol_pre, 'VOLUME_ANOMALY_PRE_NEWS'] = 1
    
    # Cleanup
    df = df.drop(columns=['has_news', 'news_pos', 'news_neg', 
                          'prior_any_news', 'prior_pos_news', 'prior_neg_news',
                          'future_any_news', 'future_pos_news', 'future_neg_news'])
    
    return df

def detect_anomalies(combined_df: pd.DataFrame, anomaly_params: dict) -> pd.DataFrame:
    """
    Detects anomalies in the current data batch using pre-fitted parameters.
    
    Args:
        combined_df: DataFrame resulting from feature_engineer.
        anomaly_params: Pre-fitted anomaly detection parameters.
        
    Returns:
        pd.DataFrame: The input dataframe enriched with final anomaly flags.
    """
    combined_df = combined_df.copy()
    
    # Detect anomalies using FIXED historical parameters
    combined_df = detect_anomalies_with_params(combined_df, anomaly_params)
    
    # Link anomalies to news (your existing logic)
    combined_df = link_anomalies_to_news(combined_df, news_window=3)
    
    # Filter columns for output
    historical_columns = [
        'SEANCE', 'GROUPE', 'CODE', 'VALEUR', 'OUVERTURE', 'CLOTURE', 'PLUS_BAS', 'PLUS_HAUT',
        'QUANTITE_NEGOCIEE', 'NB_TRANSACTION', 'CAPITAUX', 'VARIATION', 'PROB_LIQUIDITY',
        'TUNINDEX_INDICE_JOUR', 'TUNINDEX20_INDICE_JOUR', 'Mean_Weighted_Sentiment',
        'Article_Count', 'Sentiment_Intensity', 'DirectionScore', 'BreadthScore',
        'LiquidityScore', 'IntensityScore', 'NewsScore', 'MarketMood', 'volume_z_score',
        'VOLUME_Anomaly', 'variation_z_score', 'VARIATION_ANOMALY',
        'VARIATION_ANOMALY_POST_NEWS', 'VARIATION_ANOMALY_PRE_NEWS',
        'VOLUME_ANOMALY_POST_NEWS', 'VOLUME_ANOMALY_PRE_NEWS'
    ]
    
    combined_df = combined_df[historical_columns]
    combined_df = combined_df[combined_df['SEANCE'] == combined_df['SEANCE'].max()]
    return combined_df

def calc_daily_score(historical_df: pd.DataFrame, score_params: dict) -> pd.DataFrame:
    """
    Calculates daily scores using pre-fitted normalization parameters.
    
    Args:
        historical_df: DataFrame with historical data including anomaly flags.
        score_params: Dictionary containing normalization parameters from fit_daily_score_params()
        
    Returns:
        pd.DataFrame: DataFrame with additional score columns.
    """
    df = historical_df.copy()
    
    # Extract unique daily values for indices (using groupby to handle repeated values per ticker)
    market_daily = df.groupby('SEANCE').first().reset_index()[
        ['SEANCE', 'TUNINDEX_INDICE_JOUR', 'TUNINDEX20_INDICE_JOUR']
    ]
    
    # --- Score 1: Market Direction ---
    # Formula: 50 + 25*z(ΔTUNINDEX) + 25*z(ΔTUNINDEX20)
    market_daily['TUNINDEX_RET'] = market_daily['TUNINDEX_INDICE_JOUR'].pct_change().fillna(0)
    market_daily['TUNINDEX20_RET'] = market_daily['TUNINDEX20_INDICE_JOUR'].pct_change().fillna(0)
    
    # Calculate Z-scores using FIXED historical parameters
    ti_mean = score_params['tunindex_ret_mean']
    ti_std = score_params['tunindex_ret_std']
    ti20_mean = score_params['tunindex20_ret_mean']
    ti20_std = score_params['tunindex20_ret_std']
    
    market_daily['z_TUNINDEX'] = (market_daily['TUNINDEX_RET'] - ti_mean) / ti_std if ti_std > 0 else 0
    market_daily['z_TUNINDEX20'] = (market_daily['TUNINDEX20_RET'] - ti20_mean) / ti20_std if ti20_std > 0 else 0
    
    market_daily['DirectionScore'] = 50 + 25 * market_daily['z_TUNINDEX'] + 25 * market_daily['z_TUNINDEX20']
    market_daily['DirectionScore'] = market_daily['DirectionScore'].clip(0, 100)
    
    # --- Score 2: Market Breadth ---
    # Percentage of stocks with positive returns
    breadth_series = df.groupby('SEANCE')['VARIATION'].apply(lambda x: (x > 0).mean() * 100)
    market_daily = market_daily.merge(breadth_series.rename('BreadthScore'), on='SEANCE', how='left')
    
    # --- Score 3: Market Intensity ---
    # Average absolute return, normalized using historical percentiles
    intensity_raw = df.groupby('SEANCE')['VARIATION'].apply(lambda x: x.abs().mean())
    
    p10 = score_params['intensity_p10']
    p90 = score_params['intensity_p90']
    denom = p90 - p10 if (p90 - p10) > 0 else 1.0
    
    # Normalize: 100 * (Intensity - P10) / (P90 - P10)
    intensity_scores = 100 * (intensity_raw.values - p10) / denom
    market_daily['IntensityScore'] = intensity_scores
    market_daily['IntensityScore'] = market_daily['IntensityScore'].clip(0, 100)
    
    # --- Score 4: Liquidity Score ---
    # Average probability of liquidity across all stocks
    liquidity_series = df.groupby('SEANCE')['PROB_LIQUIDITY'].mean() * 100
    market_daily = market_daily.merge(liquidity_series.rename('LiquidityScore'), on='SEANCE', how='left')
    market_daily['LiquidityScore'] = market_daily['LiquidityScore'].fillna(50)
    
    # --- Score 5: News Score ---
    # Z-score of daily average sentiment
    daily_sentiment = df.groupby('SEANCE')['Mean_Weighted_Sentiment'].mean()
    
    sent_mean = score_params['sentiment_mean']
    sent_std = score_params['sentiment_std']
    z_sentiment = (daily_sentiment - sent_mean) / sent_std if sent_std > 0 else 0
    
    news_score = 50 + 50 * z_sentiment
    market_daily = market_daily.merge(news_score.rename('NewsScore'), on='SEANCE', how='left')
    market_daily['NewsScore'] = market_daily['NewsScore'].fillna(50).clip(0, 100)
    
    # --- Composite Score: Market Mood ---
    # Weighted average of all sub-scores
    market_daily['MarketMood'] = (
        0.30 * market_daily['DirectionScore'] +
        0.20 * market_daily['BreadthScore'] + 
        0.20 * market_daily['LiquidityScore'] + 
        0.15 * market_daily['IntensityScore'] + 
        0.15 * market_daily['NewsScore']
    )
    
    # Clean up columns to avoid duplicates
    cols_to_merge = ['DirectionScore', 'BreadthScore', 'LiquidityScore', 'IntensityScore', 'NewsScore', 'MarketMood']
    df = df.drop(columns=[c for c in cols_to_merge if c in df.columns], errors='ignore')
    
    # Merge scores back into the main dataframe
    df = pd.merge(df, market_daily[['SEANCE'] + cols_to_merge], on='SEANCE', how='left')
    df = df[df['SEANCE'] == df['SEANCE'].max()]
    return df

def process_sentiment(sentiment_path:str, new_date:str) -> pd.DataFrame:
    """
    Reads and processes sentiment data for the current day.
    
    Args:
        sentiment_path: Path to the sentiment json file for the current day.
    Returns:
        pd.DataFrame: Processed sentiment DataFrame with columns SEANCE, CODE, Mean_Weighted_Sentiment, Article_Count, Sentiment_Intensity.
    """
    with open(sentiment_path, 'r', encoding='utf-8') as f:
        json_data = json.load(f)

    sentiment_df = pd.DataFrame(json_data['articles'])
    sentiment_df['date'] = pd.to_datetime(sentiment_df['date'])
    sentiment_df = sentiment_df[['date', 'tickers', 'sentiment_score', 'confidence']].reset_index(drop=True)
    # Convert tickers column from string representation of list to actual list
    sentiment_df['tickers'] = sentiment_df['tickers'].astype(str)
    sentiment_df['tickers'] = sentiment_df['tickers'].apply(eval)

    # Explode the tickers list into separate rows
    sentiment_df = sentiment_df.explode('tickers')

    # Rename tickers to VALEUR
    sentiment_df = sentiment_df.rename(columns={'tickers': 'VALEUR'})

    # Reset index to get consecutive row numbers
    sentiment_df = sentiment_df.reset_index(drop=True)
    
    sentiment_df['weighted_sentiment'] = sentiment_df['sentiment_score'] * sentiment_df['confidence']

    daily_sentiment = sentiment_df.groupby(['VALEUR', 'date']).agg({
        'weighted_sentiment': ['mean'],  # Mean weighted sentiment
        'sentiment_score': 'count'  # Article count
    }).reset_index()

    # Flatten column names
    daily_sentiment.columns = ['VALEUR', 'date', 'Mean_Weighted_Sentiment', 'Article_Count']

    # Rename date to SEANCE for merging
    daily_sentiment = daily_sentiment.rename(columns={'date': 'SEANCE'})

    # Compute absolute sentiment intensity (sum of |s_i|)
    sentiment_df['abs_weighted_sentiment'] = sentiment_df['weighted_sentiment'].abs()

    absolute_intensity = sentiment_df.groupby(['VALEUR', 'date']).agg({
        'abs_weighted_sentiment': 'sum'
    }).reset_index()

    absolute_intensity.columns = ['VALEUR', 'SEANCE', 'Sentiment_Intensity']

    # Merge absolute intensity with daily_sentiment
    daily_sentiment = daily_sentiment.merge(absolute_intensity, on=['VALEUR', 'SEANCE'], how='left')
    daily_sentiment = daily_sentiment[daily_sentiment['SEANCE'] == pd.to_datetime(new_date)]

    return daily_sentiment

def analyze_new_data(new_date: str, market_df: pd.DataFrame, sentiment_path: str, 
                     historical_df: pd.DataFrame, historical_indices_df: pd.DataFrame,
                     models_path: str, anomaly_params_path: str, score_params_path: str) -> tuple:
    """
    Main pipeline function for real-time analysis.
    
    Args:
        market_df: Current trading day market data
        sentiment_path: Path to current sentiment data
        historical_df: Historical market data
        historical_indices_df: Historical indices data
        models_path: Path to saved forecasting models
        anomaly_params_path: Path to pre-fitted anomaly detection parameters
        score_params_path: Path to pre-fitted daily score normalization parameters
        
    Returns:
        tuple: (forecast_df, new_historical_df)
    """
    
    new_sentiment_output = process_sentiment(sentiment_path, new_date)
    with open(anomaly_params_path, 'r') as f:
        anomaly_params = json.load(f)

    with open(score_params_path, 'r') as f:
        score_params = json.load(f)

    # 1. Feature Engineering (returns full combined dataset for ARIMA extension)
    combined_df, historical_liquidity, new_indices_output = feature_engineer(
        market_df, new_sentiment_output, historical_indices_df, historical_df
    )

    new_indices_output = new_indices_output.iloc[:1,]
    
    # 2. Forecasting (needs full series for ARIMA.apply() extension)
    forecast_output = forecast(combined_df, models_path, historical_liquidity)
    
    # 3. Daily Scores (using FIXED parameters) - operates on full df, filters internally
    new_historical_output = calc_daily_score(combined_df, score_params)
    
    # 4. Anomaly Detection (using FIXED parameters) - operates on score output
    new_historical_output = detect_anomalies(new_historical_output, anomaly_params)
    
    return forecast_output, new_historical_output, new_indices_output, new_sentiment_output