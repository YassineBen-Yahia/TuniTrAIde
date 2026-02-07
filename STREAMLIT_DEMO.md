# Simple Trading Platform Demo

This is a simple demo with:
- **Traders**: Can register, login, and make buy/sell transactions
- **Regulators**: Can inspect all transactions, flag suspicious ones, and manage stock anomalies

## Quick Start

### 1. Install Streamlit
```bash
uv add streamlit
```

### 2. Start the FastAPI Backend
```bash
uvicorn app.main:app --reload
```

### 3. Start the Streamlit Frontend (in a new terminal)
```bash
streamlit run streamlit_app.py
```

### 4. Access the App
- Streamlit UI: http://localhost:8501
- API Docs: http://localhost:8000/docs

## Usage

### Register a Trader
1. Go to "Register" tab
2. Fill in details and select role: "trader"
3. Click Register
4. Login with your credentials

### Register a Regulator
1. Go to "Register" tab
2. Fill in details and select role: "regulator"
3. Click Register
4. Login with your credentials

### Trader Features
- View portfolio and holdings
- Buy stocks (e.g., stock code: TN0001100254)
- Sell stocks

### Regulator Features
- View all transactions across all users
- View suspicious transactions
- Flag transactions as suspicious with a reason
- View stock anomalies from the CSV
- Update anomaly values in the CSV

## Stock Codes
Use stock codes from `data/historical_data.csv`, for example:
- TN0001100254 (SFBT)

## Notes
- The app connects to FastAPI backend at http://localhost:8000
- Make sure the backend is running before starting Streamlit
- Default portfolio ID is 1 for traders
