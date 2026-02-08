from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.auth import get_current_regulator
from app import crud_regulator

router = APIRouter(prefix="/regulator", tags=["regulator"])

HISTORICAL_CSV_PATH = "data/historical_data.csv"


@router.get("/transactions", response_model=list[schemas.Transaction])
def get_all_transactions_regulator(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_regulator),
):
    """Get all transactions across all users (regulators only)"""
    return crud_regulator.get_all_transactions(db, skip, limit)


@router.get("/transactions/suspicious", response_model=list[schemas.Transaction])
def get_suspicious_transactions_regulator(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_regulator),
):
    """Get all suspicious transactions (regulators only)"""
    return crud_regulator.get_suspicious_transactions(db, skip, limit)


@router.get("/users/{user_id}/transactions", response_model=list[schemas.Transaction])
def get_user_transactions_regulator(
    user_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_regulator),
):
    """Get all transactions for a specific user (regulators only)"""
    return crud_regulator.get_user_transactions(db, user_id, skip, limit)


@router.post("/transactions/{transaction_id}/flag", response_model=schemas.Transaction)
def flag_transaction_regulator(
    transaction_id: int,
    payload: schemas.FlagTransactionRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_regulator),
):
    """Mark a transaction as suspicious or not (regulators only)"""
    return crud_regulator.flag_transaction(
        db,
        transaction_id,
        current_user.id,
        payload.is_suspicious,
        payload.suspicious_reason
    )


@router.get("/anomalies", response_model=list[schemas.StockAnomalyInfo])
def get_stock_anomalies_regulator(
    stock_code: str = None,
    current_user: models.User = Depends(get_current_regulator),
):
    """Get all stock anomalies from CSV (regulators only)"""
    return crud_regulator.get_stock_anomalies_from_csv(HISTORICAL_CSV_PATH, stock_code)


@router.post("/anomalies/update")
def update_anomaly_regulator(
    payload: schemas.UpdateAnomalyRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_regulator),
):
    """Add or remove anomalies in the CSV (regulators only)"""
    return crud_regulator.update_anomaly_in_csv(
        HISTORICAL_CSV_PATH,
        payload.stock_code,
        payload.date,
        payload.anomaly_type,
        payload.value
    )


@router.post("/anomalies/add")
def add_anomaly_regulator(
    payload: schemas.AddAnomalyRequest,
    current_user: models.User = Depends(get_current_regulator),
):
    """Add anomaly flags to a historical row (regulators only)"""
    return crud_regulator.add_anomaly_to_csv(
        HISTORICAL_CSV_PATH,
        payload.stock_code,
        payload.date,
        payload.volume_anomaly,
        payload.variation_anomaly,
        payload.variation_anomaly_post_news,
        payload.variation_anomaly_pre_news,
        payload.volume_anomaly_post_news,
        payload.volume_anomaly_pre_news,
        payload.regulator_note or '',
    )


@router.post("/anomalies/delete")
def delete_anomaly_regulator(
    payload: schemas.DeleteAnomalyRequest,
    current_user: models.User = Depends(get_current_regulator),
):
    """Clear all anomaly flags for a stock/date row (regulators only)"""
    return crud_regulator.delete_anomaly_from_csv(
        HISTORICAL_CSV_PATH,
        payload.stock_code,
        payload.date,
    )


@router.post("/anomalies/validate")
def validate_anomaly_regulator(
    payload: schemas.ValidateAnomalyRequest,
    current_user: models.User = Depends(get_current_regulator),
):
    """Validate or unvalidate an anomaly (regulators only)"""
    return crud_regulator.validate_anomaly_in_csv(
        HISTORICAL_CSV_PATH,
        payload.stock_code,
        payload.date,
        payload.validated,
        payload.regulator_note or '',
    )


@router.put("/anomalies/edit")
def edit_anomaly_regulator(
    payload: schemas.AddAnomalyRequest,
    current_user: models.User = Depends(get_current_regulator),
):
    """Update specific anomaly fields (regulators only)"""
    return crud_regulator.update_anomaly_bulk_in_csv(
        HISTORICAL_CSV_PATH,
        payload.stock_code,
        payload.date,
        payload.volume_anomaly,
        payload.variation_anomaly,
        payload.variation_anomaly_post_news,
        payload.variation_anomaly_pre_news,
        payload.volume_anomaly_post_news,
        payload.volume_anomaly_pre_news,
        payload.regulator_note,
    )
