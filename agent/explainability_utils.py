import json
import os
from datetime import datetime

def get_headlines(ticker: str, date: str) -> list[str]:
    """
    Gets the headlines of articles for a certain day and ticker symbol.
    
    Args:
        ticker (str): The ticker symbol (e.g., 'SFBT').
        date (str): The date in 'YYYY-MM-DD' format.
        
    Returns:
        list[str]: A list of headlines found.
    """
    # Define potential paths to the data file
    # Using absolute path based on the user's workspace structure
    file_path = r"C:/ML/hackathon/news_sentiment_analysis/data/articles_with_sentiment.json"
    
    if not os.path.exists(file_path):
        # Fallback to try relative path if absolute fails (e.g. diff environment)
        # Assumes this script is in new_agent/
        file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                 "financial-news-sentimental-analysis", "data", "articles_with_sentiment_2021_2026.json")
    
    if not os.path.exists(file_path):
        print(f"Error: Data file not found at {file_path}")
        return []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        all_articles = data.get("articles", [])
        headlines = []
        sentiments = []
        target_ticker = ticker.upper()
        
        for article in all_articles:
            article_date = article.get("date")
            article_tickers = article.get("tickers", [])
            
            # Ensure article_tickers is a list of strings
            if not isinstance(article_tickers, list):
                continue
                
            # Check criteria
            if article_date == date:
                # Case-insensitive check for ticker
                if any(t.upper() == target_ticker for t in article_tickers):
                    headlines.append(article.get("headline"))
                    sentiments.append(article.get("sentiment_label"))
        return {
            "headlines": headlines,
            "sentiments": sentiments
        }

    except Exception as e:
        print(f"Error processing headlines: {e}")
        return {
            "headlines": [],
            "sentiments": []
        }



if __name__ == "__main__":
    print(get_headlines("SFBT", "2025-08-06"))