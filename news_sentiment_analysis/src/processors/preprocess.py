import json
import re

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
'''
# 1. Load your scraped data
input_file = '../../data/raw/RESULTS_GLOBAL_2021-01-01_to_2026-01-08.json'
with open(input_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

# 2. Process every article
for article in data['all_articles']:
    lang = article.get('language', 'fr') # Default to French if missing
    
    # Clean the headline and the content
    article['headline'] = clean_text(article['headline'], lang)
    article['content'] = clean_text(article['content'], lang)

# 3. Save the "Machine-Ready" data
output_file = '../../data/processed/global_cleaned2.json'
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=4)

print(f"Success! {len(data['all_articles'])} articles washed and saved to {output_file}")
'''