# 📈 Tunisian Financial Sentiment Analysis Pipeline

This project automates the **collection, preprocessing, and sentiment classification** of financial news related to the Tunisian market.  
It is designed specifically for the **BVMT ecosystem**, addressing two key challenges:

- **Multilingual news** (French + Arabic)
- **Local financial terminology & tickers** (BVMT-specific entities)

---

## ✨ Key Features

- ✅ **3-source scraping** (Ilboursa, Tustex, Tunisien.tn)
- ✅ **Date-range scraping** (e.g., 2021 → 2026)
- ✅ **Fault-tolerant orchestration**
- ✅ **Arabic + French normalization**
- ✅ **Ticker detection using multilingual aliases**
- ✅ **Tunisian financial vocabulary support**
- ✅ **XLM-RoBERTa-based sentiment engine (cross-lingual)**
- ✅ **Headline vs Content agreement logic** (confidence management)
- ✅ **Aggregated sentiment signals per ticker**

---

## 🏗️ System Architecture & Logic Flow

The system follows a modular **logic order** to maintain data integrity and consistent performance.

### 1) Web Scraping Module (`src/scrapers`)

The system targets three primary sources of Tunisian financial news:

- **Ilboursa** → High-frequency financial news and market updates  
- **Tustex** → BVMT-focused portal for listed companies  
- **Tunisien.tn** → Arabic economic news and general market coverage  

#### 🛡️ Resilience Logic
Inspired by real-world scraping issues (e.g., DNS / `NameResolutionError`), the pipeline is built to resist failures:

- **Error Catching**: one scraper failure does not stop the global run  
- **Atomic Saving**: results are saved **per-site immediately** after collection  
- **Historical Range Support**: scrape specific date ranges (example: 2021–2024)

---

### 2) Preprocessing & Normalization (`src/processors`)

Before any NLP, raw text is transformed into clean, “machine-ready” input:

#### Cleaning
- Remove URLs
- Strip HTML artifacts
- Normalize whitespace

#### Arabic normalization
- Normalize **Alef / Yaa / Ta Marbuta**
- Remove **Tashkeel** (diacritics)

#### French normalization
- Case folding
- Normalize common financial abbreviations

#### Deduplication
- Prevent analyzing the same article twice using **MD5 hashing on URLs**

---

### 3) Tunisian Finance Vocabulary (`data/reference`)

A custom JSON vocabulary bridges the gap between generic NLP and Tunisian finance.

Includes:
- **Entities**: 100+ tickers & company names  
  (examples: `BIAT`, `SFBT`, `SAH Lilas`)
- **Multilingual Terms**: Arabic + French financial terms  
  (ex: `رأس المال`, `PNB`, `EBITDA`)
- **Sentiment Anchors**: domain triggers like  
  `"profit warning"`, `"distribution de dividendes"`

---

### 4) NLP Engine: XLM-RoBERTa (`src/models`)

We use a fine-tuned **XLM-RoBERTa Base** model, chosen for strong cross-lingual performance.

#### Custom Tokenization
The tokenizer vocabulary is extended using the Tunisian Finance Vocab to reduce “unknown token” issues on local entities (banks, tickers, institutions).

#### Agreement Logic (Headline vs Content)
To increase precision, sentiment is computed on **both headline and full article**:

- If **they agree** → confidence is boosted  
- If **they disagree** → headline is prioritized, but confidence is penalized  

---

## 🚀 Execution Guide

### ✅ Live Pipeline (Production)
Runs the full flow: **Scrape → Analyze → Export** for the current day:
```bash
python src/pipeline/live_engine.py
