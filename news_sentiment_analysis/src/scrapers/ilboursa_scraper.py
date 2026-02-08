import requests
from bs4 import BeautifulSoup
import json
import re
import hashlib
import time
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Get absolute path to project root
PROJECT_ROOT = Path(__file__).resolve().parents[3]

# --- 1. TICKER DETECTION (Keep this separate) ---
def load_search_dict(json_path=None):
    if json_path is None:
        json_path = PROJECT_ROOT / "news_sentiment_analysis" / "data" / "reference" / "ticker_mapping.json"
    try:
        with open(str(json_path), 'r', encoding='utf-8') as f:
            data = json.load(f)
        search_dict = {}
        for entry in data['tickers_mapping']:
            all_kw = [entry['ticker']] + entry['aliases'] + entry['arabic_aliases']
            for kw in all_kw:
                search_dict[kw.lower()] = entry['ticker']
        return search_dict
    except:
        return {}

def detect_tickers(text, search_dict):
    detected = set()
    text_clean = text.lower()
    for kw, ticker_id in search_dict.items():
        if re.search(rf"\b{re.escape(kw)}\b", text_clean):
            detected.add(ticker_id)
    return list(detected)

# --- 2. UPDATED SCRAPING LOGIC BY DATE RANGE ---
def scrape_ilboursa_by_range(start_date_str, end_date_str):
    """
    Scrapes Ilboursa from end_date back to start_date.
    Format: 'YYYY-MM-DD'
    """
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
    
    base_url = "https://www.ilboursa.com"
    list_url = f"{base_url}/marches/actualites_bourse_tunis"
    search_dict = load_search_dict()
    
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Origin": base_url,
        "Referer": list_url
    })

    articles_data = []
    # We start from the latest date in your range
    current_date = end_date 
    blacklist = ["actualites_bourse_tunis", "aaz", "historiques", "convertisseur_devises", "matieres_premieres", "bourse_tunis", "palmares"]

    print(f"📡 Starting Ilboursa Scraper | Range: {start_date_str} to {end_date_str}")

    # Loop until we go past the start date
    while current_date >= start_date:
        date_str_payload = current_date.strftime("%d/%m/%Y")
        date_str_log = current_date.strftime("%Y-%m-%d")
        
        print(f"\n--- Processing Date: {date_str_log} (Collected: {len(articles_data)}) ---")
        
        try:
            # Step 1: Get Token
            resp = session.get(list_url)
            soup = BeautifulSoup(resp.text, 'html.parser')
            token_node = soup.find('input', {'name': '__RequestVerificationToken'})
            if not token_node:
                current_date -= timedelta(days=1)
                continue
            token = token_node['value']

            # Step 2: POST Payload for specific date
            payload = {
                "__RequestVerificationToken": token,
                "dateActu": date_str_payload,
                "_Invariant": "dateActu"
            }
            
            post_res = session.post(list_url, data=payload)
            soup_list = BeautifulSoup(post_res.text, 'html.parser')
            
            day_links = []
            for a in soup_list.select("a[href^='/marches/']"):
                href = a['href']
                if "_" in href and not any(x in href for x in blacklist):
                    full_link = base_url + href
                    if full_link not in day_links:
                        day_links.append(full_link)

            if not day_links:
                print(f"  [!] No articles found for {date_str_payload}")
            
            # Step 3: Visit each link
            for link in day_links:
                try:
                    art_res = session.get(link, timeout=10)
                    art_soup = BeautifulSoup(art_res.text, 'html.parser')
                    
                    h1 = art_soup.find('h1')
                    headline = h1.get_text(strip=True) if h1 else "No Headline"
                    
                    article_body = art_soup.find('div', class_='actu_det_cord') or art_soup.find('article')
                    
                    if article_body:
                        for s in article_body(['script', 'style']):
                            s.decompose()
                        content = article_body.get_text(separator=' ', strip=True)
                        
                        found_tickers = detect_tickers(headline + " " + content, search_dict)
                        
                        if found_tickers:
                            articles_data.append({
                                "id": f"ilboursa_{hashlib.md5(link.encode()).hexdigest()[:8]}",
                                "headline": headline,
                                "content": content,
                                "date": date_str_log,
                                "url": link,
                                "tickers": found_tickers,
                                "language": "fr"
                            })
                            print(f"  [OK] {headline[:60]}... ({found_tickers})")
                        
                        time.sleep(0.3) 

                except Exception as e:
                    print(f"  [Article Error] {link}: {e}")

        except Exception as e:
            print(f"  [Page Error] {date_str_log}: {e}")

        # Move to previous day
        current_date -= timedelta(days=1)

    '''
    # Save logic
    filename = f"ilboursa_{start_date_str}_to_{end_date_str}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(articles_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n🏁 Finished! {len(articles_data)} articles saved to {filename}.")
    '''
    return articles_data


if __name__ == "__main__":
    # Example usage:
    scrape_ilboursa_by_range("2026-01-31", "2026-01-31")