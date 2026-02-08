import json
import re

def load_ticker_mapping(json_path):
    """Loads the JSON file and prepares a flat dictionary for searching."""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # We flatten the JSON into a dictionary: { "alias": "TICKER_ID" }
    search_dict = {}
    for entry in data['tickers_mapping']:
        ticker_id = entry['ticker']
        # Add the ticker itself, plus all aliases (French & Arabic)
        all_keywords = [ticker_id] + entry['aliases'] + entry['arabic_aliases']
        
        for kw in all_keywords:
            search_dict[kw.lower()] = ticker_id
            
    return search_dict

def detect_tickers(text, search_dict):
    """
    Scans text for keywords and returns a unique list of detected Tickers.
    Uses regex \b (word boundaries) to ensure exact matches only.
    """
    detected = set()
    text_clean = text.lower()
    
    for keyword, ticker_id in search_dict.items():
        # \b ensures we match "BT" but not "Bluetooth"
        # We escape the keyword to handle characters like '-' in Euro-Cycles
        pattern = rf"\b{re.escape(keyword)}\b"
        
        if re.search(pattern, text_clean):
            detected.add(ticker_id)
            
    return list(detected)

# --- EXAMPLE USAGE ---

# 1. Save your JSON as 'mapping.json' first
# 2. Run the detection
mapping = load_ticker_mapping('../../data/reference/ticker_mapping.json')

raw_article = """
Le bénéfice de la BIAT a augmenté de 10% ce trimestre. 
En revanche, les indicateurs de la SFBTs ) sont stables.
تعتزمل (Euro Cycles) توسيع نشاطها وان تك في الخارج.
"""

found = detect_tickers(raw_article, mapping)

print(f"Tickers detected in article: {found}")
# Output: ['BIAT', 'SFBT', 'EURO-CYCLES']