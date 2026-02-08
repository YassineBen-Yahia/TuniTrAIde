from typing import Optional, Dict, Any, List
import pandas as pd
from fastapi import HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from app import models


# -------------------------
# REGULATOR FUNCTIONS
# -------------------------
def get_all_transactions(db: Session, skip: int = 0, limit: int = 100):
    """Get all transactions across all users (for regulators)"""
    return db.query(models.Transaction).order_by(models.Transaction.transaction_date.desc()).offset(skip).limit(limit).all()


def get_suspicious_transactions(db: Session, skip: int = 0, limit: int = 100):
    """Get all transactions marked as suspicious"""
    return db.query(models.Transaction).filter(models.Transaction.is_suspicious == True).order_by(models.Transaction.transaction_date.desc()).offset(skip).limit(limit).all()


def flag_transaction(db: Session, transaction_id: int, regulator_id: int, is_suspicious: bool, suspicious_reason: Optional[str] = None):
    """Mark a transaction as suspicious or not"""
    tx = db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    tx.is_suspicious = is_suspicious
    tx.suspicious_reason = suspicious_reason
    tx.flagged_by_regulator_id = regulator_id if is_suspicious else None
    tx.flagged_at = datetime.now() if is_suspicious else None
    
    db.commit()
    db.refresh(tx)
    return tx


def get_stock_anomalies_from_csv(csv_path: str, stock_code: Optional[str] = None):
    """Read anomalies from the CSV file"""
    df = pd.read_csv(csv_path)
    df.columns = [c.strip() for c in df.columns]
    
    # Filter anomalies
    anomaly_cols = ['VOLUME_Anomaly', 'VARIATION_ANOMALY', 'VARIATION_ANOMALY_POST_NEWS', 
                    'VARIATION_ANOMALY_PRE_NEWS', 'VOLUME_ANOMALY_POST_NEWS', 'VOLUME_ANOMALY_PRE_NEWS']
    
    # Ensure validated / regulator_note columns exist
    if 'VALIDATED' not in df.columns:
        df['VALIDATED'] = 0
    if 'REGULATOR_NOTE' not in df.columns:
        df['REGULATOR_NOTE'] = ''
    
    # Make sure these columns exist and convert to numeric
    for col in anomaly_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
    
    # Filter for rows with at least one anomaly
    df['has_anomaly'] = False
    for col in anomaly_cols:
        if col in df.columns:
            df['has_anomaly'] = df['has_anomaly'] | (df[col] == 1)
    
    df_anomalies = df[df['has_anomaly'] == True].copy()
    
    # Filter by stock code if provided
    if stock_code:
        df_anomalies = df_anomalies[df_anomalies['CODE'] == stock_code]
    
    # Return relevant columns
    result = []
    for _, row in df_anomalies.iterrows():
        result.append({
            'stock_code': row.get('CODE', ''),
            'stock_name': row.get('VALEUR', ''),
            'date': str(row.get('SEANCE', '')),
            'volume_anomaly': int(row.get('VOLUME_Anomaly', 0)),
            'variation_anomaly': int(row.get('VARIATION_ANOMALY', 0)),
            'variation_anomaly_post_news': int(row.get('VARIATION_ANOMALY_POST_NEWS', 0)),
            'variation_anomaly_pre_news': int(row.get('VARIATION_ANOMALY_PRE_NEWS', 0)),
            'volume_anomaly_post_news': int(row.get('VOLUME_ANOMALY_POST_NEWS', 0)),
            'volume_anomaly_pre_news': int(row.get('VOLUME_ANOMALY_PRE_NEWS', 0)),
            'validated': bool(int(row.get('VALIDATED', 0))),
            'regulator_note': str(row.get('REGULATOR_NOTE', '') or ''),
        })
    
    return result


def update_anomaly_in_csv(csv_path: str, stock_code: str, date: str, anomaly_type: str, value: int):
    """Update anomaly value in the CSV file"""
    # Read the CSV
    df = pd.read_csv(csv_path)
    df.columns = [c.strip() for c in df.columns]
    
    # Map anomaly type to column name
    anomaly_column_map = {
        'volume': 'VOLUME_Anomaly',
        'variation': 'VARIATION_ANOMALY',
        'variation_post_news': 'VARIATION_ANOMALY_POST_NEWS',
        'variation_pre_news': 'VARIATION_ANOMALY_PRE_NEWS',
        'volume_post_news': 'VOLUME_ANOMALY_POST_NEWS',
        'volume_pre_news': 'VOLUME_ANOMALY_PRE_NEWS'
    }
    
    if anomaly_type not in anomaly_column_map:
        raise HTTPException(status_code=400, detail=f"Invalid anomaly type. Must be one of: {list(anomaly_column_map.keys())}")
    
    column_name = anomaly_column_map[anomaly_type]
    
    if column_name not in df.columns:
        raise HTTPException(status_code=400, detail=f"Column {column_name} not found in CSV")
    
    # Find the row matching stock_code and date
    mask = (df['CODE'] == stock_code) & (df['SEANCE'].astype(str) == str(date))
    
    if not mask.any():
        raise HTTPException(status_code=404, detail=f"No data found for stock {stock_code} on date {date}")
    
    # Update the anomaly value
    df.loc[mask, column_name] = value
    
    # Save back to CSV
    df.to_csv(csv_path, index=False)
    
    return {"message": f"Anomaly updated successfully for {stock_code} on {date}"}


def get_user_transactions(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    """Get all transactions for a specific user"""
    return db.query(models.Transaction).filter(models.Transaction.user_id == user_id).order_by(models.Transaction.transaction_date.desc()).offset(skip).limit(limit).all()


def get_transaction_with_details(db: Session, transaction_id: int):
    """Get a transaction with user and portfolio details"""
    tx = db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return tx


def add_anomaly_to_csv(csv_path: str, stock_code: str, date: str,
                       volume_anomaly: int = 0, variation_anomaly: int = 0,
                       variation_anomaly_post_news: int = 0, variation_anomaly_pre_news: int = 0,
                       volume_anomaly_post_news: int = 0, volume_anomaly_pre_news: int = 0,
                       regulator_note: str = ''):
    """Add anomaly flags to an existing row, or mark anomaly on a row in the CSV."""
    df = pd.read_csv(csv_path)
    df.columns = [c.strip() for c in df.columns]

    if 'VALIDATED' not in df.columns:
        df['VALIDATED'] = 0
    if 'REGULATOR_NOTE' not in df.columns:
        df['REGULATOR_NOTE'] = ''

    mask = (df['CODE'] == stock_code) & (df['SEANCE'].astype(str) == str(date))

    if not mask.any():
        raise HTTPException(status_code=404,
                            detail=f"No row found for stock {stock_code} on date {date}. The row must already exist in historical data.")

    df.loc[mask, 'VOLUME_Anomaly'] = volume_anomaly
    df.loc[mask, 'VARIATION_ANOMALY'] = variation_anomaly
    df.loc[mask, 'VARIATION_ANOMALY_POST_NEWS'] = variation_anomaly_post_news
    df.loc[mask, 'VARIATION_ANOMALY_PRE_NEWS'] = variation_anomaly_pre_news
    df.loc[mask, 'VOLUME_ANOMALY_POST_NEWS'] = volume_anomaly_post_news
    df.loc[mask, 'VOLUME_ANOMALY_PRE_NEWS'] = volume_anomaly_pre_news
    if regulator_note:
        df.loc[mask, 'REGULATOR_NOTE'] = regulator_note

    df.to_csv(csv_path, index=False)
    return {"message": f"Anomaly added for {stock_code} on {date}"}


def delete_anomaly_from_csv(csv_path: str, stock_code: str, date: str):
    """Clear all anomaly flags for a given stock/date row (sets them to 0)."""
    df = pd.read_csv(csv_path)
    df.columns = [c.strip() for c in df.columns]

    if 'VALIDATED' not in df.columns:
        df['VALIDATED'] = 0
    if 'REGULATOR_NOTE' not in df.columns:
        df['REGULATOR_NOTE'] = ''

    mask = (df['CODE'] == stock_code) & (df['SEANCE'].astype(str) == str(date))

    if not mask.any():
        raise HTTPException(status_code=404, detail=f"No data found for stock {stock_code} on date {date}")

    anomaly_cols = ['VOLUME_Anomaly', 'VARIATION_ANOMALY', 'VARIATION_ANOMALY_POST_NEWS',
                    'VARIATION_ANOMALY_PRE_NEWS', 'VOLUME_ANOMALY_POST_NEWS', 'VOLUME_ANOMALY_PRE_NEWS']
    for col in anomaly_cols:
        if col in df.columns:
            df.loc[mask, col] = 0
    df.loc[mask, 'VALIDATED'] = 0
    df.loc[mask, 'REGULATOR_NOTE'] = ''

    df.to_csv(csv_path, index=False)
    return {"message": f"Anomaly cleared for {stock_code} on {date}"}


def validate_anomaly_in_csv(csv_path: str, stock_code: str, date: str, validated: bool = True, regulator_note: str = ''):
    """Mark an anomaly as validated (or un-validated) by a regulator."""
    df = pd.read_csv(csv_path)
    df.columns = [c.strip() for c in df.columns]

    if 'VALIDATED' not in df.columns:
        df['VALIDATED'] = 0
    if 'REGULATOR_NOTE' not in df.columns:
        df['REGULATOR_NOTE'] = ''

    mask = (df['CODE'] == stock_code) & (df['SEANCE'].astype(str) == str(date))

    if not mask.any():
        raise HTTPException(status_code=404, detail=f"No data found for stock {stock_code} on date {date}")

    df.loc[mask, 'VALIDATED'] = 1 if validated else 0
    if regulator_note:
        df.loc[mask, 'REGULATOR_NOTE'] = regulator_note

    df.to_csv(csv_path, index=False)
    return {"message": f"Anomaly {'validated' if validated else 'unvalidated'} for {stock_code} on {date}"}


def update_anomaly_bulk_in_csv(csv_path: str, stock_code: str, date: str,
                               volume_anomaly: int = None, variation_anomaly: int = None,
                               variation_anomaly_post_news: int = None, variation_anomaly_pre_news: int = None,
                               volume_anomaly_post_news: int = None, volume_anomaly_pre_news: int = None,
                               regulator_note: str = None):
    """Update specific anomaly fields for a given stock/date."""
    df = pd.read_csv(csv_path)
    df.columns = [c.strip() for c in df.columns]

    if 'VALIDATED' not in df.columns:
        df['VALIDATED'] = 0
    if 'REGULATOR_NOTE' not in df.columns:
        df['REGULATOR_NOTE'] = ''

    mask = (df['CODE'] == stock_code) & (df['SEANCE'].astype(str) == str(date))

    if not mask.any():
        raise HTTPException(status_code=404, detail=f"No data found for stock {stock_code} on date {date}")

    field_map = {
        'VOLUME_Anomaly': volume_anomaly,
        'VARIATION_ANOMALY': variation_anomaly,
        'VARIATION_ANOMALY_POST_NEWS': variation_anomaly_post_news,
        'VARIATION_ANOMALY_PRE_NEWS': variation_anomaly_pre_news,
        'VOLUME_ANOMALY_POST_NEWS': volume_anomaly_post_news,
        'VOLUME_ANOMALY_PRE_NEWS': volume_anomaly_pre_news,
    }

    for col, val in field_map.items():
        if val is not None and col in df.columns:
            df.loc[mask, col] = val

    if regulator_note is not None:
        df.loc[mask, 'REGULATOR_NOTE'] = regulator_note

    df.to_csv(csv_path, index=False)
    return {"message": f"Anomaly updated for {stock_code} on {date}"}
