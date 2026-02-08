# ML Hackathon - Market Surveillance and Investment Advisor

End-to-end demo combining market surveillance, anomaly detection, forecasting, sentiment analysis, and an investment advisor with trader and regulator roles.

## Features
- Role-based access: Trader and Regulator
- Market overview dashboards (index, movers, sentiment, alerts)
- Alerts and surveillance with explain agent for anomalies
- Stock analysis with rule-based market insights (last 5 days + next 5 days forecast)
- Portfolio management, transactions, and analytics
- Data refresh pipeline (updates CSVs on demand)
- News sentiment pipeline and scrapers
- Streamlit demo and React frontend

## Project Structure (high-level)
- app/ : FastAPI backend (auth, CRUD, routes)
- frontend/ : React UI
- agent/ : LLM prompts and agents (investment + explain)
- news_sentiment_analysis/ : scrapers, preprocess, live pipeline
- data/ : CSV datasets (historical, forecast, sentiment)
- utils/refresh.py : refresh_data() for CSV updates

## Prerequisites
- Python 3.10+ (recommended)
- Node.js 18+ (for frontend)
- SQLite (users.db)

## Installation
1. Clone the repository and open the project folder.
2. Install backend dependencies:
	```bash
	uv venv
	uv pip install -r requirements.txt
	```
3. Install frontend dependencies:
	```bash
	cd frontend
	npm install
	```

## Setup

### 1) Backend (FastAPI)
```bash
cd TuniTrAIde
uv venv
uv pip install -r requirements.txt
```

Start the API:
```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2) Frontend (React)
```bash
cd TuniTrAIde\frontend
npm install
npm run dev
```



## Authentication
- Register: `POST /register` or `POST /auth/register`
- Login: `POST /token`
- Current user: `GET /users/me`

Tokens are stored in `localStorage` by the frontend.

## Roles
- Trader: standard portfolio and market tools
- Regulator: view all transactions, flag suspicious activity, manage anomalies

## Market Data Refresh
Refresh is only triggered when the user clicks the Refresh button on the Market Overview or Alerts pages.
The backend endpoint `POST /market-overview/refresh` calls `utils.refresh.refresh_data()` and updates CSV files:
- data/historical_data.csv
- data/index_historical_data.csv
- data/sentiment_features.csv
- data/forecast_next_5_days.csv

If Refresh is not clicked, CSVs remain unchanged.

## Explain Agent
Alerts page uses:
`GET /explain/{stock_symbol}/{date}`

This calls the explain agent to generate a short anomaly explanation for that stock/date.

## Key Endpoints
- `GET /market-overview/alerts`
- `POST /market-overview/refresh`
- `GET /market-data/{symbol}/with-forecast`
- `GET /sentiment/{symbol}`
- `GET /stocks/search?q=...`
- `GET /portfolios` and `POST /portfolios`
- `POST /portfolios/{id}/transactions`
- `GET /regulator/transactions`
- `POST /regulator/suspicious`
- `GET /regulator/anomalies`

## Data Sources
- `data/historical_data.csv`
- `data/forecast_next_5_days.csv`
- `data/sentiment_features.csv`
- `data/index_historical_data.csv`

## How to Use
1. Start the backend and frontend.
2. Register a new user or login with an existing account.
3. Open the Market Overview page to view indices, movers, and sentiment.
4. Use the Alerts page to review anomalies and click the explain button for details.
5. Use the Stock Analysis page to review last 5 days and next 5 days forecast insights.
6. For data updates, click Refresh on Market Overview or Alerts (this triggers CSV refresh).
7. If you are a regulator, visit the Regulator views to inspect transactions and manage anomalies.

## Troubleshooting
- If `uvicorn` fails to start, check missing imports or path errors.
- If news sentiment pipeline fails, verify paths under `news_sentiment_analysis/`.
- If `users/me` fails, ensure a valid JWT token is present in localStorage.

## Notes
- This project is a hackathon-grade demo. For production, add caching, retries, background jobs, and stronger security controls.
