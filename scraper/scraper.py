import requests
import pandas as pd
from bs4 import BeautifulSoup

URL = "https://www.ilboursa.com/marches/aaz"
URL = "https://www.ilboursa.com/marches/aaz"
HEADERS = {"User-Agent": "Mozilla/5.0"}

TARGET_COLUMNS = [
    "SEANCE", "GROUPE", "CODE", "VALEUR",
    "OUVERTURE", "CLOTURE", "PLUS_BAS", "PLUS_HAUT",
    "QUANTITE_NEGOCIEE", "NB_TRANSACTION", "CAPITAUX",
    'TUNBANQ_INDICE_JOUR', 'TUNFIN_INDICE_JOUR', 'TUNINDEX_INDICE_JOUR', 'TUNINDEX20_INDICE_JOUR', 'TUNSAC_INDICE_JOUR'
]
OUT_CSV = "ilboursa_tunis_aaz.csv"

def scrape_ilboursa_table(url: str) -> pd.DataFrame:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    }

    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()

    # Many finance pages render the quotes table as a plain HTML <table>.
    # pandas.read_html is the simplest + robust way to extract it.
    tables = pd.read_html(resp.text)

    if not tables:
        raise RuntimeError("No HTML tables found on the page (maybe content is loaded via JS).")

    # Usually the biggest table is the quotes table.
    df = max(tables, key=lambda t: t.shape[0] * t.shape[1])

    # Clean column names a bit
    df.columns = [str(c).strip() for c in df.columns]

    return df


def fetch_aaz_df() -> pd.DataFrame:
    r = requests.get(URL, headers=HEADERS, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    #indeces_prices = get_all_indices_prices()
    

    table = soup.find("table")
    if table is None:
        raise RuntimeError("No table found on A→Z page.")

    headers = [th.get_text(strip=True) for th in table.select("tr th")]
    rows = []
    for tr in table.select("tr"):
        tds = [td.get_text(strip=True) for td in tr.find_all("td")]
        if tds:
            rows.append(tds)

    df = pd.DataFrame(rows, columns=headers)
    df.columns = [c.strip() for c in df.columns]
    #for name, price in indeces_prices.items():
    #    df[f"{name}_INDICE_JOUR"] = price
    
    return df

if __name__ == "__main__":
    df = fetch_aaz_df()
    df.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
    print(f"Saved {len(df)} rows to {OUT_CSV}")
    print("Columns:", list(df.columns))
    print(df.head(5))
