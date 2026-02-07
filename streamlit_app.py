import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# API Base URL
API_BASE_URL = "http://localhost:8000"

# Initialize session state
if 'token' not in st.session_state:
    st.session_state.token = None
if 'user' not in st.session_state:
    st.session_state.user = None
if 'role' not in st.session_state:
    st.session_state.role = None


def register_user(username, email, password, full_name, role):
    """Register a new user"""
    payload = {
        "username": username,
        "email": email,
        "password": password,
        "full_name": full_name,
        "role": role
    }
    response = requests.post(f"{API_BASE_URL}/auth/register", json=payload)
    return response


def login_user(username, password):
    """Login user and get token"""
    data = {
        "username": username,
        "password": password
    }
    response = requests.post(f"{API_BASE_URL}/auth/login", data=data)
    return response


def get_current_user(token):
    """Get current user info"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{API_BASE_URL}/me", headers=headers)
    return response


def get_portfolio(portfolio_id, token):
    """Get portfolio details"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{API_BASE_URL}/portfolios/{portfolio_id}", headers=headers)
    return response


def buy_stock(portfolio_id, stock_code, shares, token):
    """Buy stock"""
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "stock_code": stock_code,
        "transaction_type": "BUY",
        "shares": shares,
        "price_per_share": 0  # Will be fetched from CSV
    }
    response = requests.post(f"{API_BASE_URL}/portfolios/{portfolio_id}/buy", json=payload, headers=headers)
    return response


def sell_stock(portfolio_id, stock_code, shares, token):
    """Sell stock"""
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "stock_code": stock_code,
        "transaction_type": "SELL",
        "shares": shares,
        "price_per_share": 0  # Will be fetched from CSV
    }
    response = requests.post(f"{API_BASE_URL}/portfolios/{portfolio_id}/sell", json=payload, headers=headers)
    return response


def get_all_transactions(token, skip=0, limit=100):
    """Get all transactions (regulator only)"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{API_BASE_URL}/regulator/transactions?skip={skip}&limit={limit}", headers=headers)
    return response


def get_suspicious_transactions(token):
    """Get suspicious transactions (regulator only)"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{API_BASE_URL}/regulator/transactions/suspicious", headers=headers)
    return response


def flag_transaction(transaction_id, is_suspicious, reason, token):
    """Flag a transaction as suspicious (regulator only)"""
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "transaction_id": transaction_id,
        "is_suspicious": is_suspicious,
        "suspicious_reason": reason
    }
    response = requests.post(f"{API_BASE_URL}/regulator/transactions/{transaction_id}/flag", json=payload, headers=headers)
    return response


def get_anomalies(token, stock_code=None):
    """Get stock anomalies (regulator only)"""
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{API_BASE_URL}/regulator/anomalies"
    if stock_code:
        url += f"?stock_code={stock_code}"
    response = requests.get(url, headers=headers)
    return response


def update_anomaly(stock_code, date, anomaly_type, value, token):
    """Update anomaly in CSV (regulator only)"""
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "stock_code": stock_code,
        "date": date,
        "anomaly_type": anomaly_type,
        "value": value
    }
    response = requests.post(f"{API_BASE_URL}/regulator/anomalies/update", json=payload, headers=headers)
    return response


def login_page():
    """Login/Register Page"""
    st.title("🏦 Trading Platform")
    
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        st.subheader("Login")
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        
        if st.button("Login"):
            if username and password:
                response = login_user(username, password)
                if response.status_code == 200:
                    data = response.json()
                    st.session_state.token = data['access_token']
                    
                    # Get user info
                    user_response = get_current_user(st.session_state.token)
                    if user_response.status_code == 200:
                        user_data = user_response.json()
                        st.session_state.user = user_data
                        st.session_state.role = user_data.get('role', 'trader')
                        st.success(f"Welcome back, {user_data['username']}!")
                        st.rerun()
                else:
                    st.error("Invalid credentials")
            else:
                st.warning("Please enter username and password")
    
    with tab2:
        st.subheader("Register")
        new_username = st.text_input("Username", key="reg_username")
        new_email = st.text_input("Email", key="reg_email")
        new_password = st.text_input("Password", type="password", key="reg_password")
        new_full_name = st.text_input("Full Name", key="reg_full_name")
        new_role = st.selectbox("Role", ["trader", "regulator"], key="reg_role")
        
        if st.button("Register"):
            if new_username and new_email and new_password:
                response = register_user(new_username, new_email, new_password, new_full_name, new_role)
                if response.status_code == 200:
                    st.success("Registration successful! Please login.")
                else:
                    st.error(f"Registration failed: {response.text}")
            else:
                st.warning("Please fill in all required fields")


def trader_dashboard():
    """Trader Dashboard"""
    st.title(f"👨‍💼 Trader Dashboard - {st.session_state.user['username']}")
    
    if st.button("Logout"):
        st.session_state.token = None
        st.session_state.user = None
        st.session_state.role = None
        st.rerun()
    
    st.divider()
    
    # Get portfolio (assuming portfolio ID 1 for default)
    portfolio_id = 1
    portfolio_response = get_portfolio(portfolio_id, st.session_state.token)
    
    if portfolio_response.status_code == 200:
        portfolio = portfolio_response.json()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Cash Balance", f"${portfolio['cash_balance']:.2f}")
        with col2:
            st.metric("Total Value", f"${portfolio.get('total_value', 0):.2f}")
        with col3:
            st.metric("Holdings", len(portfolio.get('holdings', [])))
        
        st.divider()
        
        # Holdings
        if portfolio.get('holdings'):
            st.subheader("📊 Your Holdings")
            holdings_df = pd.DataFrame(portfolio['holdings'])
            st.dataframe(holdings_df[['stock_code', 'stock_name', 'shares', 'avg_purchase_price', 'current_price', 'total_value']], use_container_width=True)
        
        st.divider()
        
        # Trading Section
        st.subheader("💰 Make a Trade")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Buy Stock**")
            buy_stock_code = st.text_input("Stock Code", key="buy_code", placeholder="e.g., TN0001100254")
            buy_shares = st.number_input("Shares", min_value=1, value=10, key="buy_shares")
            
            if st.button("Buy", type="primary"):
                if buy_stock_code:
                    response = buy_stock(portfolio_id, buy_stock_code, buy_shares, st.session_state.token)
                    if response.status_code == 200:
                        st.success(f"Successfully bought {buy_shares} shares of {buy_stock_code}")
                        st.rerun()
                    else:
                        st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
                else:
                    st.warning("Please enter a stock code")
        
        with col2:
            st.write("**Sell Stock**")
            sell_stock_code = st.text_input("Stock Code", key="sell_code", placeholder="e.g., TN0001100254")
            sell_shares = st.number_input("Shares", min_value=1, value=10, key="sell_shares")
            
            if st.button("Sell", type="secondary"):
                if sell_stock_code:
                    response = sell_stock(portfolio_id, sell_stock_code, sell_shares, st.session_state.token)
                    if response.status_code == 200:
                        st.success(f"Successfully sold {sell_shares} shares of {sell_stock_code}")
                        st.rerun()
                    else:
                        st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
                else:
                    st.warning("Please enter a stock code")
    else:
        st.error("Could not load portfolio")


def regulator_dashboard():
    """Regulator Dashboard"""
    st.title(f"🔍 Regulator Dashboard - {st.session_state.user['username']}")
    
    if st.button("Logout"):
        st.session_state.token = None
        st.session_state.user = None
        st.session_state.role = None
        st.rerun()
    
    st.divider()
    
    tab1, tab2, tab3 = st.tabs(["All Transactions", "Suspicious Transactions", "Stock Anomalies"])
    
    with tab1:
        st.subheader("📋 All Transactions")
        
        response = get_all_transactions(st.session_state.token)
        if response.status_code == 200:
            transactions = response.json()
            if transactions:
                df = pd.DataFrame(transactions)
                df['transaction_date'] = pd.to_datetime(df['transaction_date']).dt.strftime('%Y-%m-%d %H:%M')
                
                st.dataframe(df[['id', 'user_id', 'stock_code', 'transaction_type', 'shares', 'price_per_share', 'total_amount', 'transaction_date', 'is_suspicious']], use_container_width=True)
                
                st.divider()
                st.subheader("Flag Transaction")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    tx_id = st.number_input("Transaction ID", min_value=1, value=1)
                with col2:
                    is_suspicious = st.checkbox("Mark as Suspicious")
                with col3:
                    reason = st.text_input("Reason")
                
                if st.button("Flag Transaction"):
                    response = flag_transaction(tx_id, is_suspicious, reason, st.session_state.token)
                    if response.status_code == 200:
                        st.success("Transaction flagged successfully")
                        st.rerun()
                    else:
                        st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
            else:
                st.info("No transactions found")
        else:
            st.error(f"Error loading transactions: {response.status_code}")
    
    with tab2:
        st.subheader("⚠️ Suspicious Transactions")
        
        response = get_suspicious_transactions(st.session_state.token)
        if response.status_code == 200:
            suspicious = response.json()
            if suspicious:
                df = pd.DataFrame(suspicious)
                df['transaction_date'] = pd.to_datetime(df['transaction_date']).dt.strftime('%Y-%m-%d %H:%M')
                df['flagged_at'] = pd.to_datetime(df['flagged_at']).dt.strftime('%Y-%m-%d %H:%M')
                
                st.dataframe(df[['id', 'user_id', 'stock_code', 'transaction_type', 'shares', 'total_amount', 'suspicious_reason', 'flagged_at']], use_container_width=True)
            else:
                st.info("No suspicious transactions")
        else:
            st.error(f"Error loading suspicious transactions: {response.status_code}")
    
    with tab3:
        st.subheader("📊 Stock Anomalies")
        
        stock_filter = st.text_input("Filter by Stock Code (optional)", placeholder="e.g., TN0001100254")
        
        if st.button("Load Anomalies"):
            response = get_anomalies(st.session_state.token, stock_filter if stock_filter else None)
            if response.status_code == 200:
                anomalies = response.json()
                if anomalies:
                    df = pd.DataFrame(anomalies)
                    st.dataframe(df, use_container_width=True)
                    
                    st.divider()
                    st.subheader("Update Anomaly")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        upd_stock = st.text_input("Stock Code", key="upd_stock")
                    with col2:
                        upd_date = st.text_input("Date", placeholder="YYYY-MM-DD", key="upd_date")
                    with col3:
                        upd_type = st.selectbox("Anomaly Type", ["volume", "variation", "variation_post_news", "variation_pre_news", "volume_post_news", "volume_pre_news"])
                    with col4:
                        upd_value = st.selectbox("Value", [0, 1])
                    
                    if st.button("Update CSV"):
                        response = update_anomaly(upd_stock, upd_date, upd_type, upd_value, st.session_state.token)
                        if response.status_code == 200:
                            st.success("Anomaly updated in CSV!")
                        else:
                            st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
                else:
                    st.info("No anomalies found")
            else:
                st.error(f"Error loading anomalies: {response.status_code}")


def main():
    st.set_page_config(page_title="Trading Platform", page_icon="🏦", layout="wide")
    
    if st.session_state.token is None:
        login_page()
    else:
        if st.session_state.role == "regulator":
            regulator_dashboard()
        else:
            trader_dashboard()


if __name__ == "__main__":
    main()
