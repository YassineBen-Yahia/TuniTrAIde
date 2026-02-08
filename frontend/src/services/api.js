const API_BASE_URL = 'http://localhost:8000';

class ApiService {
  constructor() {
    // Token is always read fresh from localStorage in getHeaders()
  }

  setToken(token) {
    localStorage.setItem('token', token);
  }

  removeToken() {
    localStorage.removeItem('token');
  }

  getHeaders() {
    const headers = {
      'Content-Type': 'application/json',
    };
    
    // Always get fresh token from localStorage to avoid stale token issues
    const token = localStorage.getItem('token');
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }
    
    return headers;
  }

  async request(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    const config = {
      ...options,
      headers: {
        ...this.getHeaders(),
        ...options.headers,
      },
    };

    // Don't add Content-Type for FormData - let browser set it automatically
    if (options.body instanceof FormData) {
      delete config.headers['Content-Type'];
    }

    try {
      const response = await fetch(url, config);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'API request failed');
      }

      return data;
    } catch (error) {
      throw error;
    }
  }

  // Authentication
  async register(userData) {
    return this.request('/register', {
      method: 'POST',
      body: JSON.stringify(userData),
    });
  }

  async login(credentials) {
    // FastAPI OAuth2PasswordRequestForm expects form data, not JSON
    const formData = new FormData();
    formData.append('username', credentials.username);
    formData.append('password', credentials.password);
    
    const response = await this.request('/token', {
      method: 'POST',
      body: formData,
      headers: {
        // Remove Content-Type header to let browser set it for FormData
      },
    });
    
    if (response.access_token) {
      this.setToken(response.access_token);
    }
    
    return response;
  }

  async getCurrentUser() {
    return this.request('/users/me');
  }

  // User Profile - No separate profile endpoint, use getCurrentUser instead

  async updateUserProfile(userId, profileData) {
    return this.request(`/users/${userId}`, {
      method: 'PUT',
      body: JSON.stringify(profileData),
    });
  }

  // Portfolios
  async getUserPortfolios() {
    return this.request('/portfolios');
  }

  async createPortfolio(userId, portfolioData) {
    return this.request('/portfolios', {
      method: 'POST',
      body: JSON.stringify(portfolioData),
    });
  }

  async getPortfolio(portfolioId) {
    return this.request(`/portfolios/${portfolioId}`);
  }

  // Transactions (remove duplicate incorrect ones)
  async createTransaction(portfolioId, transactionData) {
    return this.request(`/portfolios/${portfolioId}/transactions`, {
      method: 'POST',
      body: JSON.stringify(transactionData),
    });
  }

  async getPortfolioTransactions(portfolioId) {
    return this.request(`/portfolios/${portfolioId}/transactions`);
  }

  // Market Data
  async getMarketData(symbol) {
    return this.request(`/market-data/${symbol}`);
  }

  async getMarketDataWithForecast(symbol, start = null, end = null) {
    let url = `/market-data/${encodeURIComponent(symbol)}/with-forecast`;
    const params = [];
    if (start) params.push(`start=${start}`);
    if (end) params.push(`end=${end}`);
    if (params.length > 0) url += '?' + params.join('&');
    return this.request(url);
  }

  // Market Overview endpoints
  async getTunindexData(days = 30, indexType = 'tunindex') {
    return this.request(`/market-overview/tunindex?days=${days}&index_type=${indexType}`);
  }

  async getMarketSentiment(date = null) {
    let url = '/market-overview/sentiment';
    if (date) url += `?date=${date}`;
    return this.request(url);
  }

  async getTopMovers(date = null) {
    let url = '/market-overview/top-movers';
    if (date) url += `?date=${date}`;
    return this.request(url);
  }

  async getMarketAlerts(limit = 10) {
    return this.request(`/market-overview/alerts?limit=${limit}`);
  }

  async getStockSentiment(symbol, start = null, end = null) {
    let url = `/sentiment/${encodeURIComponent(symbol)}`;
    const params = [];
    if (start) params.push(`start=${start}`);
    if (end) params.push(`end=${end}`);
    if (params.length > 0) url += '?' + params.join('&');
    return this.request(url);
  }

  async searchStocks(query, limit = 10) {
    return this.request(`/stocks/search?q=${encodeURIComponent(query)}&limit=${limit}`);
  }

  async getAllStocks(limit = 100) {
    return this.request(`/stocks/all?limit=${limit}`);
  }

  // Analytics
  async getPortfolioAnalytics(portfolioId) {
    return this.request(`/portfolios/${portfolioId}/analytics`);
  }

  async getPortfolioPerformance(portfolioId, days = 180) {
    return this.request(`/portfolios/${portfolioId}/performance?days=${days}`);
  }

  async getUserAnalytics() {
    return this.request('/users/me/analytics');
  }

  // Chatbot
  async createChatSession() {
    return this.request('/chat/session', {
      method: 'POST'
    });
  }

  async sendChatMessage(sessionId, message) {
    return this.request(`/chat/${sessionId}/message`, {
      method: 'POST',
      body: JSON.stringify({ content: message })
    });
  }

  async getChatHistory(sessionId) {
    return this.request(`/chat/${sessionId}/history`);
  }

  // Regulator endpoints
  async getAllTransactions(skip = 0, limit = 100) {
    return this.request(`/regulator/transactions?skip=${skip}&limit=${limit}`);
  }

  async getSuspiciousTransactions(skip = 0, limit = 100) {
    return this.request(`/regulator/transactions/suspicious?skip=${skip}&limit=${limit}`);
  }

  async getUserTransactions(userId, skip = 0, limit = 100) {
    return this.request(`/regulator/users/${userId}/transactions?skip=${skip}&limit=${limit}`);
  }

  async flagTransaction(transactionId, isSuspicious, reason = null) {
    return this.request(`/regulator/transactions/${transactionId}/flag`, {
      method: 'POST',
      body: JSON.stringify({
        transaction_id: transactionId,
        is_suspicious: isSuspicious,
        suspicious_reason: reason,
      }),
    });
  }

  async getStockAnomalies(stockCode = null) {
    let url = '/regulator/anomalies';
    if (stockCode) url += `?stock_code=${encodeURIComponent(stockCode)}`;
    return this.request(url);
  }

  async updateAnomaly(stockCode, date, anomalyType, value) {
    return this.request('/regulator/anomalies/update', {
      method: 'POST',
      body: JSON.stringify({
        stock_code: stockCode,
        date,
        anomaly_type: anomalyType,
        value,
      }),
    });
  }

  async addAnomaly(data) {
    return this.request('/regulator/anomalies/add', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async deleteAnomaly(stockCode, date) {
    return this.request('/regulator/anomalies/delete', {
      method: 'POST',
      body: JSON.stringify({ stock_code: stockCode, date }),
    });
  }

  async validateAnomaly(stockCode, date, validated = true, regulatorNote = '') {
    return this.request('/regulator/anomalies/validate', {
      method: 'POST',
      body: JSON.stringify({
        stock_code: stockCode,
        date,
        validated,
        regulator_note: regulatorNote,
      }),
    });
  }

  async editAnomaly(data) {
    return this.request('/regulator/anomalies/edit', {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  logout() {
    this.removeToken();
  }
}

export default new ApiService();