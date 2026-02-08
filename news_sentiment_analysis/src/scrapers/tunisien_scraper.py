import requests
from bs4 import BeautifulSoup
import json
import re
import hashlib
import time
from datetime import datetime

# --- 1. TICKER DETECTION ---
def load_search_dict(json_path='financial-news-sentimental-analysis/data/reference/ticker_mapping.json'):
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        search_dict = {}
        for entry in data['tickers_mapping']:
            all_kw = [entry['ticker']] + entry['aliases'] + entry['arabic_aliases']
            for kw in all_kw:
                search_dict[kw.lower()] = entry['ticker']
        return search_dict
    except Exception as e:
        print(f"  ⚠️ Error loading mapping: {e}")
        return {}

def detect_tickers(text, search_dict):
    detected = set()
    text_clean = text.lower()
    for kw, ticker_id in search_dict.items():
        if re.search(rf"\b{re.escape(kw)}\b", text_clean):
            detected.add(ticker_id)
    return list(detected)

# --- 2. THE ARABIC SCRAPER (DATE RANGE VERSION) ---
def scrape_tunisien_ar_by_range(start_date_str, end_date_str):
    """
    Scrapes Tunisien.tn between start_date and end_date.
    Format: 'YYYY-MM-DD'
    """
    start_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date_str, "%Y-%m-%d")
    
    list_url = "https://www.tunisien.tn/cat/%D8%A7%D9%84%D8%A5%D9%82%D8%AA%D8%B5%D8%A7%D8%AF"
    search_dict = load_search_dict()
    
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    })

    articles_data = []
    seen_urls = set()
    page_num = 1
    keep_searching = True

    print(f"📡 Tunisien.tn | Plage : {start_date_str} -> {end_date_str}")

    while keep_searching:
        current_page_url = list_url if page_num == 1 else f"{list_url}/page/{page_num}"
        print(f"\n--- 📄 Page {page_num} | Collectés : {len(articles_data)} ---")
        
        try:
            resp = session.get(current_page_url, timeout=15)
            if resp.status_code != 200: 
                print("🛑 Page non trouvée ou fin des articles.")
                break
                
            soup = BeautifulSoup(resp.text, 'html.parser')
            article_links = soup.find_all('div', id='titreacta')

            if not article_links:
                break

            for container in article_links:
                link_node = container.find('a')
                if not link_node: continue
                
                full_link = link_node['href']
                if full_link in seen_urls: continue

                try:
                    art_res = session.get(full_link, timeout=10)
                    art_soup = BeautifulSoup(art_res.text, 'html.parser')
                    
                    # 1. Headline
                    h1 = art_soup.find('h1', class_='entry-title')
                    headline = h1.get_text(strip=True) if h1 else "No Title"
                    
                    # 2. DATE EXTRACTION & VALIDATION
                    formatted_date = None
                    date_container = art_soup.find('div', class_='dateArticle')
                    
                    if date_container:
                        raw_date_text = date_container.get_text(strip=True)
                        match = re.search(r'(\d{2})/(\d{2})/(\d{4})', raw_date_text)
                        if match:
                            day, month, year = match.groups()
                            formatted_date = f"{year}-{month}-{day}"
                    
                    # LOGIQUE DE FILTRAGE PAR DATE
                    if formatted_date:
                        current_art_dt = datetime.strptime(formatted_date, "%Y-%m-%d")
                        
                        # Si l'article est plus récent que la date de fin, on passe au suivant
                        if current_art_dt > end_dt:
                            continue
                            
                        # Si l'article est plus vieux que la date de début, on arrête tout
                        if current_art_dt < start_dt:
                            print(f"🛑 Article du {formatted_date} avant la plage demandée. Scraping terminé.")
                            keep_searching = False
                            break
                    else:
                        # Si pas de date, on ignore l'article par sécurité
                        continue

                    # 3. Content filtering (Your original logic)
                    content_container = art_soup.find('div', class_='entry-content')
                    if not content_container: continue

                    cutoff_node = content_container.find(id='bTag')
                    if cutoff_node:
                        for element in cutoff_node.find_all_next():
                            element.decompose()
                        cutoff_node.decompose()

                    content = content_container.get_text(separator=' ', strip=True)

                    if content and len(content) > 100:
                        found_tickers = detect_tickers(headline + " " + content, search_dict)
                        
                        if found_tickers:
                            articles_data.append({
                                "id": f"tunisien_{hashlib.md5(full_link.encode()).hexdigest()[:8]}",
                                "date": formatted_date,
                                "headline": headline,
                                "content": content,
                                "url": full_link,
                                "tickers": found_tickers,
                                "language": "ar"
                            })
                            seen_urls.add(full_link)
                            print(f"  ✅ [MATCH] {headline[:50]}... ({formatted_date})")
                            time.sleep(0.1)

                except Exception as e:
                    print(f"  ⚠️ Article Error: {e}")

            page_num += 1
            time.sleep(0.5)

        except Exception as e:
            print(f"  ❌ Page Error: {e}")
            break
    
    #print(f"\n🏁 Tunisien.tn scraper finished! {len(articles_data)} articles collected.")
    return articles_data

if __name__ == "__main__":
    # Exemple d'utilisation
    scrape_tunisien_ar_by_range("2025-01-01", "2025-12-31")