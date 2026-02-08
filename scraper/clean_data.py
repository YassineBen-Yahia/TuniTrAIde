import numpy as np
import pandas as pd

COLUMNS = [
    "SEANCE","GROUPE","CODE","VALEUR",
    "OUVERTURE","CLOTURE","PLUS_BAS","PLUS_HAUT",
    "QUANTITE_NEGOCIEE","NB_TRANSACTION","CAPITAUX"
]

def generate_dummy_dataset(
    enterprises,
    start_date="2025-12-31",
    end_date="2026-02-01",
    seed=42
) -> pd.DataFrame:
    """
    enterprises: list of dicts like:
      {"VALEUR":"SFBT", "CODE":"TN0001100254", "GROUPE":11, "base_price":12.5}
    """
    rng = np.random.default_rng(seed)

    dates = pd.date_range(start_date, end_date, freq="D")
    rows = []

    # Keep a last close per enterprise so prices evolve smoothly (not random jumps)
    last_close = {}
    for e in enterprises:
        key = (e["VALEUR"], e["CODE"])
        last_close[key] = float(e.get("base_price", 10.0))

    for d in dates:
        seance = d.date().isoformat()

        for e in enterprises:
            valeur = e["VALEUR"]
            code = e["CODE"]
            groupe = int(e.get("GROUPE", 0))
            key = (valeur, code)

            prev_close = last_close[key]

            # Daily move (small drift + noise)
            # You can tune these numbers to be more/less volatile
            daily_ret = rng.normal(loc=0.0003, scale=0.02)  # ~2% std
            close = max(0.1, prev_close * (1.0 + daily_ret))

            # Open near previous close
            open_ = max(0.1, prev_close * (1.0 + rng.normal(0, 0.005)))

            # Intraday range
            base = max(open_, close)
            low_base = min(open_, close)

            # Make high/low consistent
            up_wick = abs(rng.normal(0.0, 0.01))   # ~1% wick
            dn_wick = abs(rng.normal(0.0, 0.01))

            high = base * (1.0 + up_wick)
            low = low_base * (1.0 - dn_wick)
            low = max(0.1, low)

            # Ensure strict ordering
            high = max(high, open_, close)
            low = min(low, open_, close)

            # Volume & transactions
            qty = int(rng.integers(50, 100_000))
            nb_tx = int(rng.integers(1, max(2, qty // 200)))  # correlated-ish
            cap = round(qty * close, 2)

            rows.append({
                "SEANCE": seance,
                "GROUPE": groupe,
                "CODE": code,
                "VALEUR": valeur,
                "OUVERTURE": round(open_, 3),
                "CLOTURE": round(close, 3),
                "PLUS_BAS": round(low, 3),
                "PLUS_HAUT": round(high, 3),
                "QUANTITE_NEGOCIEE": qty,
                "NB_TRANSACTION": nb_tx,
                "CAPITAUX": cap
            })

            last_close[key] = close

    df = pd.DataFrame(rows, columns=COLUMNS)

    # Sort to keep dataset "in order"
    df = df.sort_values(["SEANCE", "VALEUR", "CODE"]).reset_index(drop=True)

    return df


if __name__ == "__main__":
    # Example enterprises list (replace with yours)
    df_unique = pd.read_csv("data/cleaned_stock_data.csv")[["VALEUR","CODE","GROUPE"]].drop_duplicates()
    enterprises = [
        {"VALEUR": r["VALEUR"], "CODE": r["CODE"], "GROUPE": r["GROUPE"], "base_price": 10.0}
        for _, r in df_unique.iterrows()
        if pd.notna(r["CODE"])
    ]


    df = generate_dummy_dataset(enterprises, "2026-01-01", "2026-02-01", seed=7)
    df.to_csv("data/dummy_bvmt_ohlc_2025-12-31_to_2026-02-01.csv", index=False, encoding="utf-8")
    print(df.head(12))
    print("Saved:", "dummy_bvmt_ohlc_2025-12-31_to_2026-02-01.csv")
