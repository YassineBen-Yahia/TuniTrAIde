from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.init_db import init_db
from app import models, schemas, crud
from app.auth import hash_password, create_access_token, get_current_user, get_current_regulator
from app import crud_regulator
from app.routes_regulator import router as regulator_router

CSV_PATH = "data/historical_data.csv"
HISTORICAL_CSV_PATH = "data/historical_data.csv"

app = FastAPI(title="Trading Simulation Test API")

# Include regulator routes
app.include_router(regulator_router)

@app.on_event("startup")
def startup():
    init_db()

# ---------- AUTH ----------
@app.post("/auth/register", response_model=schemas.User)
def register(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    if crud.get_user_by_username(db, payload.username):
        raise HTTPException(status_code=400, detail="Username already exists")
    if crud.get_user_by_email(db, payload.email):
        raise HTTPException(status_code=400, detail="Email already exists")

    user = models.User(
        username=payload.username,
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=payload.role.value if payload.role else "trader",

        risk_score=payload.risk_score,
        risk_level=payload.risk_level.value,
        investment_style=payload.investment_style.value,
        investment_experience_years=payload.investment_experience_years,
        monthly_investment_budget=payload.monthly_investment_budget,
        avoid_anomalies=payload.avoid_anomalies,
        allow_short_selling=payload.allow_short_selling,
        initial_cash_balance=payload.initial_cash_balance,
        target_portfolio_value=payload.target_portfolio_value,
        rebalance_frequency_days=payload.rebalance_frequency_days,
    )

    user = crud.create_user(db, user)

    # auto default portfolio (only for traders)
    if user.role == "trader":
        crud.create_default_portfolio(db, user.id, user.initial_cash_balance)
    return user

@app.post("/auth/login", response_model=schemas.Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = crud.get_user_by_username(db, form.username)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    from app.auth import verify_password
    if not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}


@app.get("/me", response_model=schemas.User)
def me(current_user: models.User = Depends(get_current_user)):
    return current_user


# ---------- PORTFOLIOS ----------
@app.post("/portfolios", response_model=schemas.Portfolio)
def create_portfolio(
    payload: schemas.PortfolioCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return crud.create_portfolio(db, current_user.id, payload.name, payload.description, payload.cash_balance or 0.0)

@app.get("/portfolios/{portfolio_id}", response_model=schemas.Portfolio)
def get_portfolio(
    portfolio_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    p = crud.get_portfolio_owned(db, current_user.id, portfolio_id)
    # load holdings into response
    p.holdings = db.query(models.Holding).filter(models.Holding.portfolio_id == p.id).all()
    return p


# ---------- TRADE ----------
@app.post("/portfolios/{portfolio_id}/buy", response_model=schemas.Transaction)
def buy(
    portfolio_id: int,
    payload: schemas.TransactionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    p = crud.get_portfolio_owned(db, current_user.id, portfolio_id)

    crud.buy_stock(
        db=db,
        user_id=current_user.id,
        portfolio=p,
        stock_code=payload.stock_code.strip(),
        shares=payload.shares,
        csv_path=CSV_PATH,
        fees=payload.fees or 0.0,
        notes=payload.notes,
    )

    tx = db.query(models.Transaction).order_by(models.Transaction.id.desc()).first()
    return tx

@app.post("/portfolios/{portfolio_id}/sell", response_model=schemas.Transaction)
def sell(
    portfolio_id: int,
    payload: schemas.TransactionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    p = crud.get_portfolio_owned(db, current_user.id, portfolio_id)

    crud.sell_stock(
        db=db,
        user_id=current_user.id,
        portfolio=p,
        stock_code=payload.stock_code.strip(),
        shares=payload.shares,
        csv_path=CSV_PATH,
        fees=payload.fees or 0.0,
        notes=payload.notes,
    )

    tx = db.query(models.Transaction).order_by(models.Transaction.id.desc()).first()
    return tx
