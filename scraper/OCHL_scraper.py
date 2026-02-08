import os
import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import date

URL = "https://www.ilboursa.com/marches/aaz"
HEADERS = {"User-Agent": "Mozilla/5.0"}

TARGET_COLUMNS = [
    "SEANCE", "GROUPE", "CODE", "VALEUR",
    "OUVERTURE", "CLOTURE", "PLUS_BAS", "PLUS_HAUT",
    "QUANTITE_NEGOCIEE", "NB_TRANSACTION", "CAPITAUX",
    'TUNBANQ_INDICE_JOUR', 'TUNFIN_INDICE_JOUR', 'TUNINDEX_INDICE_JOUR', 'TUNINDEX20_INDICE_JOUR', 'TUNSAC_INDICE_JOUR'
]
INDICES_URLS = {
    "TUNINDEX": "https://www.investing.com/indices/tunindex",
    "TUNINDEX20": "https://www.investing.com/indices/tunindex20",
    "TUNBANQ" : "https://www.investing.com/indices/tunbank",    
    "TUNFIN" : "https://www.investing.com/indices/tunfin",
    "TUNSAC" : "https://www.investing.com/indices/tunsac",
}   

REF_PATH = r"data/historical_data.csv"  # dataset reference

def get_indice_price(indice_url: str):
    headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.investing.com/",
    }

    resp = requests.get(indice_url, headers=headers, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "lxml")

    el = soup.select_one('[data-test="instrument-price-last"]')
    if not el:
        raise RuntimeError("Closing price element not found (page structure or blocking).")

    close_text = el.get_text(strip=True)  # e.g. '5,434.91'
    close_price = float(close_text.replace(",", ""))  # 5434.91 as float
    return close_price

def get_all_indices_prices():
    indices_prices = {}
    for indice_name, indice_url in INDICES_URLS.items():
        indices_prices[indice_name] = get_indice_price(indice_url)
    return indices_prices


def fr_to_float(x: str):
    if x is None:
        return None
    x = str(x).strip().replace("\xa0", " ").replace(" ", "")
    x = x.replace(",", ".")
    if x in ("", "-", "—"):
        return None
    try:
        return float(x)
    except ValueError:
        return None

def fetch_aaz_df() -> pd.DataFrame:
    r = requests.get(URL, headers=HEADERS, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    indeces_prices = get_all_indices_prices()
    

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
    for name, price in indeces_prices.items():
        df[f"{name}_INDICE_JOUR"] = price
    
    return df

def build_valeur_lookup(df_ref: pd.DataFrame) -> dict:
    """
    Build dict: VALEUR (uppercase stripped) -> (CODE, GROUPE)
    Missing values become "".
    """
    temp = df_ref.copy()
    temp["VALEUR"] = temp["VALEUR"].astype(str).str.strip().str.upper()

    def first_non_empty(series):
        for x in series:
            if pd.notna(x) and str(x).strip() not in ("", "nan", "None"):
                return str(x).strip()
        return ""

    agg = temp.groupby("VALEUR").agg(
        CODE=("CODE", first_non_empty),
        GROUPE=("GROUPE", first_non_empty),
    )

    return {v: (row["CODE"], row["GROUPE"]) for v, row in agg.iterrows()}

def build_target_table(df_aaz: pd.DataFrame, lookup: dict, seance: str | None = None) -> pd.DataFrame:
    seance = seance or date.today().isoformat()

    valeur_series = df_aaz["Nom"].astype(str).str.strip()
    valeur_key = valeur_series.str.upper()

    mapped = valeur_key.map(lambda v: lookup.get(v, ("", "")))

    out = pd.DataFrame({
        "SEANCE": seance,
        "GROUPE": mapped.map(lambda t: t[1]),  # string group based on Nom
        "CODE": mapped.map(lambda t: t[0]),
        "VALEUR": valeur_series,

        "OUVERTURE": df_aaz["Ouverture"].apply(fr_to_float),
        "CLOTURE": df_aaz["Dernier"].apply(fr_to_float),
        "PLUS_BAS": df_aaz["+Bas"].apply(fr_to_float),
        "PLUS_HAUT": df_aaz["+Haut"].apply(fr_to_float),

        "QUANTITE_NEGOCIEE": df_aaz["Volume (titres)"].apply(fr_to_float),
        "NB_TRANSACTION": (df_aaz["Volume (titres)"].apply(fr_to_float) / 300).round().clip(lower=1).astype("Int64"),
        "CAPITAUX": df_aaz["Volume (DT)"].apply(fr_to_float),
        'TUNBANQ_INDICE_JOUR': df_aaz['TUNBANQ_INDICE_JOUR'],
        'TUNFIN_INDICE_JOUR': df_aaz['TUNFIN_INDICE_JOUR'],
        'TUNINDEX_INDICE_JOUR': df_aaz['TUNINDEX_INDICE_JOUR'],
        'TUNINDEX20_INDICE_JOUR': df_aaz['TUNINDEX20_INDICE_JOUR'],
        'TUNSAC_INDICE_JOUR': df_aaz['TUNSAC_INDICE_JOUR']
    })

    return out[TARGET_COLUMNS]

def append_to_csv_table(df_new: pd.DataFrame, path: str):
    if os.path.exists(path):
        df_existing = pd.read_csv(path)

        # avoid duplicates on (SEANCE, CODE) if CODE exists
        df_all = pd.concat([df_existing, df_new], ignore_index=True)
        df_all = df_all.drop_duplicates(subset=["SEANCE", "VALEUR", "CODE"], keep="last")
    else:
        df_all = df_new.copy()

    df_all.to_csv(path, index=False, encoding="utf-8")
    print(f"✅ Appended {len(df_new)} rows to {path}")

if __name__ == "__main__":
    # 1) Fetch A→Z
    from agent.utils import get_symbols
    symbols = get_symbols("data/historical_data.csv")
    print(symbols)
    df_aaz = fetch_aaz_df()
    df_aaz=df_aaz[df_aaz["Nom"].isin(symbols)]
    print(len(df_aaz["Nom"].unique()))
    print()

    # 2) Load reference dataset once + build lookup
    df_ref = pd.read_csv(REF_PATH)
    lookup = build_valeur_lookup(df_ref)

    # 3) Build today table
    df_new = build_target_table(df_aaz, lookup, seance=None)

    # 4) Append
    append_to_csv_table(df_new, path="data/new.csv")

    print(df_new.head(10))
