import json
import os
from datetime import datetime

from ilboursa_scraper import scrape_ilboursa_by_range
from tustex_scraper import scrape_tustex_by_range
from tunisien_scraper import scrape_tunisien_ar_by_range


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def save_json(path: str, data: dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def run_global_scraping(start_date, end_date):
    print("=" * 60)
    print(f"🚀 GLOBAL SCRAPING LAUNCH")
    print(f"📅 PERIOD: {start_date} to {end_date}")
    print("=" * 60)

    # Output folder (adjust if you want)
    out_dir = "../../data/raw"
    ensure_dir(out_dir)

    # Global dictionary to store all results
    report = {
        "execution_info": {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "range": [start_date, end_date]
        },
        "all_articles": []
    }

    scrapers = [
       # {"name": "Ilboursa", "slug": "ilboursa", "func": scrape_ilboursa_by_range},
       #  {"name": "Tustex", "slug": "tustex", "func": scrape_tustex_by_range},
        {"name": "Tunisien.tn", "slug": "tunisien", "func": scrape_tunisien_ar_by_range},
    ]

    for scraper in scrapers:
        print(f"\n--- 🛰️ Executing {scraper['name']} ---")
        try:
            data = scraper["func"](start_date, end_date)

            # Build per-site payload (same structure each time)
            site_payload = {
                "execution_info": report["execution_info"],
                "source": scraper["name"],
                "articles": data or []
            }

            # ✅ Save per-site file immediately
            site_filename = f"RESULTS_{scraper['slug']}_{start_date}_to_{end_date}.json"
            site_path = os.path.join(out_dir, site_filename)
            save_json(site_path, site_payload)

            if data:
                report["all_articles"].extend(data)
                print(f"✅ {scraper['name']}: {len(data)} articles retrieved.")
                print(f"📂 Saved: {site_path}")
            else:
                print(f"⚠️ {scraper['name']}: No articles found for this period.")
                print(f"📂 Saved empty file: {site_path}")

        except Exception as e:
            # Still save an error file for that website (useful for debugging)
            err_payload = {
                "execution_info": report["execution_info"],
                "source": scraper["name"],
                "error": str(e),
                "articles": []
            }
            site_filename = f"RESULTS_{scraper['slug']}_{start_date}_to_{end_date}.json"
            site_path = os.path.join(out_dir, site_filename)
            save_json(site_path, err_payload)

            print(f"❌ Critical error on {scraper['name']}: {e}")
            print(f"📂 Error saved to: {site_path}")

    # ✅ Final global save
    output_filename = f"RESULTS_GLOBAL_{start_date}_to_{end_date}.json"
    output_path = os.path.join(out_dir, output_filename)
    save_json(output_path, report)

    print("\n" + "=" * 60)
    print(f"🏁 ALL SCRAPERS HAVE FINISHED")
    print(f"📊 TOTAL: {len(report['all_articles'])} articles collected.")
    print(f"📂 GLOBAL FILE: {output_path}")
    print("=" * 60)


if __name__ == "__main__":
    START = "2021-01-01"
    END = "2024-07-08"
    run_global_scraping(START, END)
