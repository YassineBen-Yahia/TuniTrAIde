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

# --- 2. THE SCRAPER (DATE RANGE & TARGETED CONTENT) ---
def scrape_tustex_by_range(start_date_str, end_date_str):
    start_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date_str, "%Y-%m-%d")
    
    base_url = "https://www.tustex.com"
    list_url = f"{base_url}/bourse-tunis"
    search_dict = load_search_dict()
    
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    })

    articles_data = []
    seen_urls = set()
    page_num = 0
    keep_searching = True

    print(f"📡 Tustex Scraper | Plage : {start_date_str} -> {end_date_str}")

    while keep_searching:
        current_page_url = f"{list_url}?page={page_num}"
        print(f"\n--- 📄 Page {page_num + 1} | Collectés : {len(articles_data)} ---")
        
        try:
            resp = session.get(current_page_url, timeout=15)
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # --- CIBLAGE DU CONTENEUR PRINCIPAL ---
            # On cible la zone centrale (#content) pour éviter les sidebars
            main_content = soup.find(id="content")
            if not main_content:
                print("🛑 Conteneur principal (#content) introuvable.")
                break

            # Localiser la pagination pour s'arrêter juste avant
            pager = main_content.find('ul', class_='pager') or main_content.find('div', class_='item-list')
            
            # Extraire les lignes d'articles (.views-row) situées à l'intérieur de la vue bourse
            # On utilise select() sur main_content pour être sûr de rester dans la zone centrale
            main_rows = main_content.select('.view-bourse-tunis .views-row') or \
                        main_content.select('.view-content .views-row')

            if not main_rows:
                print("🛑 Plus aucune ligne trouvée sur cette page.")
                break

            for row in main_rows:
                # Vérifier si cet élément est situé APRÈS la pagination (au cas où)
                if pager and row in pager.find_all_next():
                    continue

                # 1. Extraction Titre et Lien
                title_node = row.find('div', class_='views-field-title')
                if not title_node or not title_node.find('a'): continue
                
                href = title_node.find('a')['href']
                full_link = base_url + href if href.startswith('/') else href
                if full_link in seen_urls: continue

                # 2. Extraction et Validation de la Date
                formatted_date = None
                date_node = row.find('div', class_='views-field-created')
                if date_node:
                    date_text_node = date_node.find('span', class_='field-content')
                    if date_text_node:
                        match = re.search(r'(\d{2})/(\d{2})/(\d{4})', date_text_node.get_text())
                        if match:
                            d, m, y = match.groups()
                            formatted_date = f"{y}-{m}-{d}"
                
                if formatted_date:
                    current_art_dt = datetime.strptime(formatted_date, "%Y-%m-%d")
                    if current_art_dt > end_dt:
                        continue 
                    if current_art_dt < start_dt:
                        print(f"🛑 Article du {formatted_date} < {start_date_str}. Fin du scraping.")
                        keep_searching = False
                        break

                headline = title_node.get_text(strip=True)
                if "analyse hebdomadaire" in headline.lower(): continue

                # 3. Récupération du contenu (sur la page individuelle)
                try:
                    art_res = session.get(full_link, timeout=10)
                    art_soup = BeautifulSoup(art_res.text, 'html.parser')
                    
                    body_node = art_soup.find('div', class_='field-name-body')
                    if not body_node: continue
                    
                    content = body_node.get_text(separator=' ', strip=True)

                    if content and len(content) > 100:
                        found_tickers = detect_tickers(headline + " " + content, search_dict)
                        if found_tickers:
                            articles_data.append({
                                "id": f"tustex_{hashlib.md5(full_link.encode()).hexdigest()[:8]}",
                                "date": formatted_date or datetime.now().strftime("%Y-%m-%d"),
                                "headline": headline,
                                "content": content,
                                "url": full_link,
                                "tickers": found_tickers,
                                "language": "fr"
                            })
                            seen_urls.add(full_link)
                            print(f"  ✅ [MATCH] {headline[:50]}... ({formatted_date})")
                            time.sleep(0.1)

                except Exception as e:
                    print(f"  ⚠️ Erreur Article: {e}")

            page_num += 1
            time.sleep(0.3)

        except Exception as e:
            print(f"  ❌ Erreur Page: {e}")
            break
    ''''    
    # Sauvegarde
    if articles_data:
        filename = f"tustex_{start_date_str}_to_{end_date_str}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(articles_data, f, ensure_ascii=False, indent=2)
        print(f"\n🏁 Terminé : {len(articles_data)} articles sauvegardés.")
    '''

    return articles_data

if __name__ == "__main__":
    # Test sur une plage de fin Janvier 2026
    scrape_tustex_by_range("2026-01-20", "2026-01-31")