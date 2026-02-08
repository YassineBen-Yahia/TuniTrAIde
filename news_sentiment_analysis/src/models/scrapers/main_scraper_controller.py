import json
import os
from datetime import datetime
# Import your scraping functions
from ilboursa_scraper import scrape_ilboursa_by_range
from tustex_scraper import scrape_tustex_by_range
from tunisien_scraper import scrape_tunisien_ar_by_range

def run_global_scraping(start_date, end_date):
    print("="*60)
    print(f"🚀 GLOBAL SCRAPING LAUNCH")
    print(f"📅 PERIOD: {start_date} to {end_date}")
    print("="*60)

    # Global dictionary to store all results
    report = {
        "execution_info": {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "range": [start_date, end_date]
        },
        "all_articles": []
    }

    # List of scrapers to execute
    scrapers = [
        {"name": "Ilboursa", "func": scrape_ilboursa_by_range},
        {"name": "Tustex", "func": scrape_tustex_by_range},
        {"name": "Tunisien.tn", "func": scrape_tunisien_ar_by_range}
    ]

    for scraper in scrapers:
        print(f"\n--- 🛰️ Executing {scraper['name']} ---")
        try:
            # Call the function and retrieve data
            data = scraper['func'](start_date, end_date)
            if data:
                report["all_articles"].extend(data)
                print(f"✅ {scraper['name']}: {len(data)} articles retrieved.")
            else:
                print(f"⚠️ {scraper['name']}: No articles found for this period.")
        except Exception as e:
            print(f"❌ Critical error on {scraper['name']}: {e}")

    # --- Final Save ---
    output_filename = f"../../data/raw/RESULTS_GLOBAL_{start_date}_to_{end_date}.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("\n" + "="*60)
    print(f"🏁 ALL SCRAPERS HAVE FINISHED")
    print(f"📊 TOTAL: {len(report['all_articles'])} articles collected.")
    print(f"📂 FILE: {output_filename}")
    print("="*60)

if __name__ == "__main__":
    # Define your desired date range for all sites here
    START = "2021-01-01"
    END = "2026-01-08"
    run_global_scraping(START, END)