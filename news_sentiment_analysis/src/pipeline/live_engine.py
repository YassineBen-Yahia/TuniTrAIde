import sys
import os
from pathlib import Path

# 1. Setup absolute paths
current_file = Path(__file__).resolve()
project_root = current_file.parents[2]  
scrapers_path = project_root / "src" / "scrapers"

# 2. Add BOTH the root and the scrapers folder to sys.path
sys.path.append(str(project_root))
sys.path.append(str(scrapers_path))

# 3. Import everything else
import json
import hashlib
from datetime import datetime
import torch
from transformers import pipeline

# These should now work perfectly
from src.scrapers.main_scraper_controller import run_global_scraping
from src.processors.preprocess import clean_text

# --- CONFIGURATION (Using Absolute Paths for safety) ---
MODEL_PATH = str(project_root / "src" / "models" / "xlm-roberta-tunisian-finance-final")
HISTORICAL_DB_PATH = str(project_root / "exports" / "history.json")
TODAY_ONLY_PATH = str(project_root / "exports" / "TODAY_SIGNALS.json")


class RealTimeSentimentPipeline:
    def __init__(self):
        print(f"🤖 Loading Model: {MODEL_PATH}")
        self.analyzer = pipeline(
            "sentiment-analysis",
            model=MODEL_PATH,
            tokenizer=MODEL_PATH,
            device=0 if torch.cuda.is_available() else -1,
            max_length=256,
            truncation=True
        )

    def parse_model_output(self, result):
        """Maps model output to -1, 0, 1."""
        label = result.get('label')
        if label in ['LABEL_0', -1, '-1']: return -1
        if label in ['LABEL_1', 0, '0']: return 0
        if label in ['LABEL_2', 1, '1']: return 1
        return 0

    def run_pipeline(self):
        # 1. SCRAPE
        today = datetime.now().strftime("%Y-%m-%d")
        #today = "2026-02-04"
        print(f"🚀 Launching Scrapers for {today}...")
        run_global_scraping(today, today)
        
        # 2. LOAD RAW DATA
        raw_file = project_root / "news_sentiment_analysis" / "data" / "raw" / f"RESULTS_GLOBAL_{today}_to_{today}.json"
        if not raw_file.exists():
            print("⚠️ No articles collected today.")
            return

        with open(str(raw_file), 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
        
        articles = raw_data.get('all_articles', [])

        if not articles:
            print(f"\nNo news articles found for {today}. Nothing to analyze.")
            return

        enriched_articles = []

        print(f"🧠 Processing {len(articles)} articles...")

        # 3. CLEAN & ANALYZE (Applying your Logic)
        for art in articles:
            lang = art.get('language', 'fr')
            
            # Clean text using your preprocess function
            clean_h = clean_text(art['headline'], lang)
            clean_c = clean_text(art['content'], lang)

            # Inference
            res_h = self.analyzer(clean_h[:512])[0]
            res_c = self.analyzer(clean_c[:512])[0]

            h_score = self.parse_model_output(res_h)
            c_score = self.parse_model_output(res_c)
            h_conf = res_h['score']
            c_conf = res_c['score']

            # --- YOUR AGREEMENT LOGIC ---
            if h_score != 0:
                if c_score == h_score:
                    final_sentiment = h_score
                    confidence = min(1.0, max(h_conf, c_conf) * 1.1)
                elif c_score == 0:
                    final_sentiment = h_score
                    confidence = h_conf
                else:
                    final_sentiment = h_score
                    confidence = h_conf * 0.7
            else:
                final_sentiment = c_score
                if c_score != 0:
                    confidence = c_conf * 0.8
                else:
                    confidence = max(h_conf, c_conf) * 0.5

            # Enrich article
            art['sentiment_score'] = int(final_sentiment)
            art['confidence'] = round(confidence, 3)
            
            # Generate a unique ID if missing
            if 'id' not in art:
                art['id'] = hashlib.md5(art['url'].encode()).hexdigest()[:10]

            enriched_articles.append(art)

        # 4. DUAL SAVING
        self.save_outputs(enriched_articles)

    def save_outputs(self, signals):
        # 1. Prepare Today's Output (keeping your structure)
        today_data = {
            "metadata": {
                "total_articles": len(signals),
                "analysis_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "model_used": "xlm-roberta-tunisian-finance"
            },
            "articles": signals
        }
        
        with open(TODAY_ONLY_PATH, 'w', encoding='utf-8') as f:
            json.dump(today_data, f, indent=4, ensure_ascii=False)
        
        # 2. Update History
        history_full = {"metadata": {}, "articles": []}
        
        if os.path.exists(HISTORICAL_DB_PATH):
            try:
                with open(HISTORICAL_DB_PATH, 'r', encoding='utf-8') as f:
                    history_full = json.load(f)
            except Exception as e:
                print(f"⚠️ Error loading history: {e}. Creating new.")

        # Get the actual list of articles
        existing_articles = history_full.get("articles", [])
        
        # Deduplication using IDs
        existing_ids = {art['id'] for art in existing_articles if isinstance(art, dict) and 'id' in art}
        new_entries = [s for s in signals if s['id'] not in existing_ids]
        
        # Append new news
        existing_articles.extend(new_entries)
        
        # 3. Update Metadata in History
        history_full["articles"] = existing_articles
        history_full["metadata"]["total_articles"] = len(existing_articles)
        history_full["metadata"]["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Recalculate sentiment distribution for the jury (Optional but looks great)
        sentiments = [a.get('sentiment_score') for a in existing_articles]
        history_full["metadata"]["sentiment_distribution"] = {
            "negative": sentiments.count(-1),
            "neutral": sentiments.count(0),
            "positive": sentiments.count(1)
        }

        with open(HISTORICAL_DB_PATH, 'w', encoding='utf-8') as f:
            json.dump(history_full, f, indent=4, ensure_ascii=False)
        
        print(f"🏁 DONE: {len(signals)} Today | {len(new_entries)} unique added to History.")

if __name__ == "__main__":
    pipeline = RealTimeSentimentPipeline()
    pipeline.run_pipeline()