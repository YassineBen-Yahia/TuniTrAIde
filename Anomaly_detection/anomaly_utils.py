"""
Utility functions for anomaly detection analysis and Streamlit GUI.

This module provides functions to:
- Filter and retrieve stock data by CODE and date range
- Get date range boundaries for specific stocks
- Retrieve detailed information for anomaly visualization
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Tuple, Dict, List, Optional

dataset = pd.read_csv('data/filtered_anomaly_detected_dataset.csv', parse_dates=['SEANCE'])

def get_available_date_range(code: str) -> Tuple[datetime, datetime]:
    """
    Get the available date range for a specific CODE (ticker).
    
    Args:
        code (str): The stock ticker code (e.g., 'TN0001000248')
    
    Returns:
        Tuple[datetime, datetime]: (min_date, max_date) available for this CODE
    
    Example:
        >>> start, end = get_available_date_range('TN0001000248')
        >>> print(f"Data available from {start} to {end}")
    """
    stock_data = dataset[dataset['CODE'] == code]
    
    if len(stock_data) == 0:
        raise ValueError(f"CODE '{code}' not found in dataset")
    
    min_date = stock_data['SEANCE'].min()
    max_date = stock_data['SEANCE'].max()
    
    return min_date, max_date


def get_stock_data_filtered(
    code: str, 
    start_date: Optional[datetime] = None, 
    end_date: Optional[datetime] = None
) -> pd.DataFrame:
    """
    Get CLOTURE, VOLUME, and anomaly data for a specific CODE within a date range.
    
    Args:
        code (str): The stock ticker code
        start_date (datetime, optional): Start date for filtering. If None, uses earliest date.
        end_date (datetime, optional): End date for filtering. If None, uses latest date.
    
    Returns:
        pd.DataFrame: Filtered data with columns:
            - SEANCE (date)
            - CLOTURE (closing price)
            - QUANTITE_NEGOCIEE (volume)
            - ANOMALY (binary flag)
            - ANOMALY_SCORE (0-100 score)
            - VALEUR (stock name)
    
    Example:
        >>> data = get_stock_data_filtered('TN0001000248', 
        ...                                 start_date=pd.Timestamp('2023-01-01'),
        ...                                 end_date=pd.Timestamp('2023-12-31'))
        >>> print(data[['SEANCE', 'CLOTURE', 'ANOMALY']].head())
    """
    # Filter by CODE
    stock_data = dataset[dataset['CODE'] == code].copy()
    
    if len(stock_data) == 0:
        raise ValueError(f"CODE '{code}' not found in dataset")
    
    # Apply date filters if provided
    if start_date is not None:
        stock_data = stock_data[stock_data['SEANCE'] >= start_date]
    
    if end_date is not None:
        stock_data = stock_data[stock_data['SEANCE'] <= end_date]
    
    # Sort by date
    stock_data = stock_data.sort_values('SEANCE').reset_index(drop=True)
    
    # Select relevant columns for visualization
    columns_to_return = [
        'SEANCE', 'CLOTURE', 'QUANTITE_NEGOCIEE', 
        'ANOMALY', 'ANOMALY_SCORE', 'VALEUR'
    ]
    
    return stock_data[columns_to_return]


def get_anomaly_details(
    code: str, 
    date: datetime
) -> Dict[str, any]:
    """
    Get detailed information for a specific CODE and date (used for anomaly inspection).
    
    Args:
        code (str): The stock ticker code
        date (datetime): The specific date to get details for
    
    Returns:
        Dict[str, any]: Dictionary containing all relevant information:
            - SEANCE: Trading date
            - VALEUR: Stock name
            - CODE: Ticker code
            - OUVERTURE: Opening price
            - CLOTURE: Closing price
            - PLUS_HAUT: Highest price
            - PLUS_BAS: Lowest price
            - QUANTITE_NEGOCIEE: Volume traded
            - NB_TRANSACTION: Number of transactions
            - CAPITAUX: Capital traded
            - GROUPE: Market group
            - ANOMALY: Anomaly flag (0 or 1)
            - ANOMALY_SCORE: Anomaly score (0-100)
            - Intraday_Range_Pct: Intraday volatility
            - Daily_Return_Pct: Daily return percentage
            - Price_Position: Price position in range
            - Avg_Trade_Size: Average trade size
            - Price_Impact: Price impact
    
    Raises:
        ValueError: If CODE or date not found in dataset
    
    Example:
        >>> details = get_anomaly_details('TN0001000248', pd.Timestamp('2023-06-15'))
        >>> print(f"Opening: {details['OUVERTURE']}, Closing: {details['CLOTURE']}")
    """
    # Filter by CODE and date
    stock_data = dataset[(dataset['CODE'] == code) & (dataset['SEANCE'] == date)]
    
    if len(stock_data) == 0:
        raise ValueError(f"No data found for CODE '{code}' on date {date}")
    
    # Get the single row as a dictionary
    row_data = stock_data.iloc[0]
    
    # Define columns to include in details
    detail_columns = [
        'SEANCE', 'VALEUR', 'CODE',
        'OUVERTURE', 'CLOTURE', 'PLUS_HAUT', 'PLUS_BAS',
        'QUANTITE_NEGOCIEE', 'NB_TRANSACTION', 'CAPITAUX', 'GROUPE',
        'ANOMALY', 'ANOMALY_SCORE',
        'Intraday_Range_Pct', 'Daily_Return_Pct', 'Price_Position',
        'Avg_Trade_Size', 'Price_Impact', 'Upper_Shadow_Ratio', 'Lower_Shadow_Ratio'
    ]
    
    # Build dictionary with available columns
    details = {}
    for col in detail_columns:
        if col in row_data.index:
            details[col] = row_data[col]
    
    return details


def get_all_codes() -> List[str]:
    """
    Get a list of all unique stock codes in the dataset.
    
    Args:
        dataset (pd.DataFrame): The main dataset with stock data
    
    Returns:
        List[str]: Sorted list of unique CODE values
    
    Example:
        >>> codes = get_all_codes(dataset)
        >>> print(f"Total stocks: {len(codes)}")
    """
    return sorted(dataset['CODE'].unique().tolist())


def get_code_name_mapping() -> Dict[str, str]:
    """
    Get a mapping of CODE to VALEUR (stock name) for dropdown display.
    
    Args:
        dataset (pd.DataFrame): The main dataset with stock data
    
    Returns:
        Dict[str, str]: Dictionary mapping CODE to stock name
    
    Example:
        >>> mapping = get_code_name_mapping(dataset)
        >>> print(mapping['TN0001000248'])  # e.g., 'MONOPRIX'
    """
    code_name_map = dataset.groupby('CODE')['VALEUR'].first().to_dict()
    return code_name_map


def get_anomaly_summary_for_code(
    code: str, 
    start_date: Optional[datetime] = None, 
    end_date: Optional[datetime] = None
) -> Dict[str, any]:
    """
    Get summary statistics about anomalies for a specific CODE and date range.
    
    Args:
        code (str): The stock ticker code
        start_date (datetime, optional): Start date for filtering
        end_date (datetime, optional): End date for filtering
    
    Returns:
        Dict[str, any]: Summary statistics including:
            - total_days: Total trading days in range
            - anomaly_days: Number of anomaly days
            - anomaly_percentage: Percentage of days flagged as anomalies
            - avg_anomaly_score: Average anomaly score
            - max_anomaly_score: Maximum anomaly score
            - anomaly_dates: List of dates flagged as anomalies
    
    Example:
        >>> summary = get_anomaly_summary_for_code('TN0001000248')
        >>> print(f"Anomalies: {summary['anomaly_days']} / {summary['total_days']}")
    """
    # Get filtered data
    stock_data = get_stock_data_filtered(code, start_date, end_date)
    
    anomaly_data = stock_data[stock_data['ANOMALY'] == 1]
    
    summary = {
        'total_days': len(stock_data),
        'anomaly_days': len(anomaly_data),
        'anomaly_percentage': (len(anomaly_data) / len(stock_data) * 100) if len(stock_data) > 0 else 0,
        'avg_anomaly_score': stock_data['ANOMALY_SCORE'].mean(),
        'max_anomaly_score': stock_data['ANOMALY_SCORE'].max(),
        'anomaly_dates': anomaly_data['SEANCE'].tolist()
    }
    
    return summary