from typing import Optional, Dict, Any, Tuple
import pandas as pd
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import models


# -------------------------
# CSV PRICES
# -------------------------
def load_stock_map(csv_path: str) -> Dict[str, Dict[str, Any]]:
    """
    Returns:
      {
        "TN0001100254": {"name": "SFBT", "price": 12.33},
        ...
      }
    """
    df = pd.read_csv(csv_path)
    df.columns = [c.strip() for c in df.columns]

    # Adjust if needed
    code_col = "CODE" if "CODE" in df.columns else "stock_code"
    name_col = "VALEUR" if "VALEUR" in df.columns else ("Nom" if "Nom" in df.columns else "stock_name")
    price_col = "CLOTURE" if "CLOTURE" in df.columns else ("Dernier" if "Dernier" in df.columns else "price")

    if code_col not in df.columns or price_col not in df.columns:
        raise ValueError(f"CSV must contain {code_col} and {price_col}. Found: {list(df.columns)}")

    df[code_col] = df[code_col].astype(str).str.strip()
    if name_col in df.columns:
        df[name_col] = df[name_col].astype(str).str.strip()
    df[price_col] = pd.to_numeric(df[price_col], errors="coerce")

    out: Dict[str, Dict[str, Any]] = {}
    for _, r in df.dropna(subset=[price_col]).iterrows():
        out[str(r[code_col])] = {
            "name": str(r[name_col]) if name_col in df.columns else None,
            "price": float(r[price_col]),
        }
    return out


# -------------------------
# USERS
# -------------------------
def get_user_by_username(db: Session, username: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.username == username).first()

def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.email == email).first()

def create_user(db: Session, user: models.User) -> models.User:
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# -------------------------
# PORTFOLIOS
# -------------------------
def create_default_portfolio(db: Session, user_id: int, initial_cash: float) -> models.Portfolio:
    p = models.Portfolio(
        user_id=user_id,
        name="Default",
        description="Auto-created default portfolio",
        cash_balance=float(initial_cash),
        total_value=float(initial_cash),
        is_active=True,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p

def create_portfolio(db: Session, user_id: int, name: str, description: Optional[str], initial_cash: float) -> models.Portfolio:
    p = models.Portfolio(
        user_id=user_id,
        name=name,
        description=description,
        cash_balance=float(initial_cash),
        total_value=float(initial_cash),
        is_active=True,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p

def get_portfolio_owned(db: Session, user_id: int, portfolio_id: int) -> models.Portfolio:
    p = db.query(models.Portfolio).filter(
        models.Portfolio.id == portfolio_id,
        models.Portfolio.user_id == user_id
    ).first()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return p

def get_portfolio_detail(db: Session, portfolio_id: int) -> Tuple[list[models.Holding], list[models.Transaction]]:
    holdings = db.query(models.Holding).filter(models.Holding.portfolio_id == portfolio_id).all()
    txs = db.query(models.Transaction).filter(models.Transaction.portfolio_id == portfolio_id).order_by(models.Transaction.transaction_date.desc()).all()
    return holdings, txs


# -------------------------
# TRADING HELPERS
# -------------------------
def _get_holding(db: Session, portfolio_id: int, stock_code: str) -> Optional[models.Holding]:
    return db.query(models.Holding).filter(
        models.Holding.portfolio_id == portfolio_id,
        models.Holding.stock_code == stock_code
    ).first()

def _recalc_portfolio_total_value(db: Session, portfolio: models.Portfolio, stock_map: Dict[str, Dict[str, Any]]) -> None:
    total_holdings_value = 0.0
    holdings = db.query(models.Holding).filter(models.Holding.portfolio_id == portfolio.id).all()

    for h in holdings:
        info = stock_map.get(h.stock_code)
        if not info:
            continue
        price = float(info["price"])
        h.current_price = price
        h.total_value = float(h.shares) * price
        h.unrealized_gain_loss = (price - float(h.avg_purchase_price)) * float(h.shares)

        cost = float(h.avg_purchase_price) * float(h.shares)
        if cost > 0:
            h.unrealized_gain_loss_percentage = (h.unrealized_gain_loss / cost) * 100.0
        else:
            h.unrealized_gain_loss_percentage = 0.0

        total_holdings_value += h.total_value

    portfolio.total_value = float(portfolio.cash_balance) + total_holdings_value


# -------------------------
# BUY / SELL
# -------------------------
def buy_stock(
    db: Session,
    user_id: int,
    portfolio: models.Portfolio,
    stock_code: str,
    shares: float,
    csv_path: str,
    fees: float = 0.0,
    notes: Optional[str] = None,
):
    if shares <= 0:
        raise HTTPException(status_code=400, detail="shares must be > 0")

    stock_map = load_stock_map(csv_path)
    if stock_code not in stock_map:
        raise HTTPException(status_code=404, detail=f"Unknown stock_code: {stock_code}")

    price = float(stock_map[stock_code]["price"])
    name = stock_map[stock_code].get("name")

    total_amount = (shares * price) + float(fees)
    if portfolio.cash_balance < total_amount:
        raise HTTPException(status_code=400, detail="Not enough cash")

    holding = _get_holding(db, portfolio.id, stock_code)
    if holding:
        old_shares = float(holding.shares)
        new_shares = old_shares + float(shares)
        holding.avg_purchase_price = ((old_shares * float(holding.avg_purchase_price)) + (shares * price)) / new_shares
        holding.shares = new_shares
        if name:
            holding.stock_name = name
    else:
        holding = models.Holding(
            portfolio_id=portfolio.id,
            stock_code=stock_code,
            stock_name=name,
            shares=float(shares),
            avg_purchase_price=price,
        )
        db.add(holding)

    portfolio.cash_balance -= total_amount

    tx = models.Transaction(
        user_id=user_id,
        portfolio_id=portfolio.id,
        stock_code=stock_code,
        stock_name=name,
        transaction_type="BUY",
        shares=float(shares),
        price_per_share=price,
        total_amount=float(shares) * price,
        fees=float(fees),
        notes=notes,
    )
    db.add(tx)

    _recalc_portfolio_total_value(db, portfolio, stock_map)
    db.commit()

def sell_stock(
    db: Session,
    user_id: int,
    portfolio: models.Portfolio,
    stock_code: str,
    shares: float,
    csv_path: str,
    fees: float = 0.0,
    notes: Optional[str] = None,
):
    if shares <= 0:
        raise HTTPException(status_code=400, detail="shares must be > 0")

    stock_map = load_stock_map(csv_path)
    if stock_code not in stock_map:
        raise HTTPException(status_code=404, detail=f"Unknown stock_code: {stock_code}")

    price = float(stock_map[stock_code]["price"])
    name = stock_map[stock_code].get("name")

    holding = _get_holding(db, portfolio.id, stock_code)
    if not holding or float(holding.shares) < float(shares):
        raise HTTPException(status_code=400, detail="Not enough shares to sell")

    proceeds = (shares * price) - float(fees)
    if proceeds < 0:
        raise HTTPException(status_code=400, detail="Fees too high")

    holding.shares = float(holding.shares) - float(shares)
    portfolio.cash_balance += proceeds

    if float(holding.shares) == 0.0:
        db.delete(holding)

    tx = models.Transaction(
        user_id=user_id,
        portfolio_id=portfolio.id,
        stock_code=stock_code,
        stock_name=name,
        transaction_type="SELL",
        shares=float(shares),
        price_per_share=price,
        total_amount=float(shares) * price,
        fees=float(fees),
        notes=notes,
    )
    db.add(tx)

    _recalc_portfolio_total_value(db, portfolio, stock_map)
    db.commit()
