import json
import re
from pathlib import Path
import sys

# Get absolute path to project root
PROJECT_ROOT = Path(__file__).resolve().parents[3]

def clean_text(text, lang):
    if not text:
        return ""
    
    # --- GENERAL CLEANING (For both AR and FR) ---
    # 1. Remove URLs/Links
    text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
    # 2. Remove multiple spaces and newlines
    text = re.sub(r'\s+', ' ', text).strip()
    
    # --- LANGUAGE SPECIFIC ---
    if lang == 'ar':
        # Arabic Normalization: Standardize letters
        text = re.sub(r"[إأآ]", "ا", text) # Normalize Alef
        text = re.sub(r"ى", "ي", text)     # Normalize Yaa
        text = re.sub(r"ة", "ه", text)     # Normalize Ta Marbuta
        # Remove Tashkeel (vowels/diacritics)
        tashkeel_pattern = re.compile(r'[\u064B-\u0652]')
        text = re.sub(tashkeel_pattern, '', text)
    
    elif lang == 'fr':
        # French: Lowercase everything
        text = text.lower()
        
    return text

# --- RUNNING THE CAR WASH ---

# 1. Load your scraped data
input_file = PROJECT_ROOT / 'news_sentiment_analysis' / 'data' / 'raw' / 'scraped_articles.json'
try:
    with open(str(input_file), 'r', encoding='utf-8') as f:
        data = json.load(f)
except (FileNotFoundError, json.JSONDecodeError) as e:
    print(f"Error loading file: {e}")
    exit()

# 2. Process every article
for article in data['articles']:
    lang = article.get('language', 'fr') # Default to French if missing
    
    # Clean the headline and the content
    article['headline'] = clean_text(article['headline'], lang)
    article['content'] = clean_text(article['content'], lang)

# 3. SORT ARTICLES BY DATE (New Addition)
# reverse=True puts the newest articles at the top (2026 -> 2021)
# Use reverse=False if you want the oldest articles first
data['articles'].sort(key=lambda x: x.get('date', ''), reverse=True)

# 4. Save the "Machine-Ready" data
output_file = PROJECT_ROOT / 'news_sentiment_analysis' / 'data' / 'processed' / 'global_cleaned.json'
output_file.parent.mkdir(parents=True, exist_ok=True)  # Ensure output directory exists
with open(str(output_file), 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=4)

print(f"Success! {len(data['articles'])} articles washed, sorted by date, and saved to {output_file}")