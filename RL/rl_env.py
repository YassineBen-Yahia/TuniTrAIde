# rl_env.py
import numpy as np
import pandas as pd
import gymnasium as gym
from gymnasium import spaces


def _safe_num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(0.0)

def _clip_tanh(x: float, clip: float = 5.0) -> float:
    # robust squashing to [-1, 1]
    return float(np.tanh(np.clip(x, -clip, clip)))


class MultiCodeTunisEnv(gym.Env):
    """
    Multi-code training: each episode samples one CODE.
    Reward = (portfolio_return - market_return) - costs - drawdown penalty
    This prevents the "do nothing" policy.
    """

    metadata = {"render_modes": []}

    def __init__(
        self,
        csv_path: str,
        initial_cash: float = 10_000.0,
        buy_frac: float = 0.25,         # slightly stronger to show effect
        sell_frac: float = 0.25,
        fee_rate: float = 0.001,
        episode_len: int = 200,
        seed: int = 42,
        top_n_codes: int = 50,
        min_rows_per_code: int = 120,
        drawdown_lambda: float = 0.02,  # small
    ):
        super().__init__()

        self.initial_cash = float(initial_cash)
        self.buy_frac = float(buy_frac)
        self.sell_frac = float(sell_frac)
        self.fee_rate = float(fee_rate)
        self.episode_len = int(episode_len)
        self.top_n_codes = int(top_n_codes)
        self.min_rows_per_code = int(min_rows_per_code)
        self.drawdown_lambda = float(drawdown_lambda)

        self.rng = np.random.default_rng(seed)

        df = pd.read_csv(csv_path)
        df.columns = [c.strip() for c in df.columns]

        for col in ["CODE", "SEANCE", "CLOTURE"]:
            if col not in df.columns:
                raise ValueError(f"Missing column: {col}")

        df["CODE"] = df["CODE"].astype(str).str.strip()
        df["SEANCE"] = pd.to_datetime(df["SEANCE"], errors="coerce")
        df["CLOTURE"] = _safe_num(df["CLOTURE"])
        df = df.dropna(subset=["CODE", "SEANCE"]).sort_values(["CODE", "SEANCE"]).reset_index(drop=True)

        # market returns by code
        df["ret1"] = df.groupby("CODE")["CLOTURE"].pct_change().fillna(0.0)
        df["ret5"] = df.groupby("CODE")["CLOTURE"].pct_change(5).fillna(0.0)
        df["vol20"] = (
            df.groupby("CODE")["ret1"]
            .rolling(20).std()
            .reset_index(level=0, drop=True)
            .fillna(0.0)
        )

        # Your feature columns (missing -> 0). We'll squash them to stable ranges in obs.
        self.feat_cols = [
            "LiquidityScore", "NewsScore", "MarketMood", "PROB_LIQUIDITY",
            "volume_z_score", "variation_z_score",
            "VOLUME_Anomaly", "VARIATION_ANOMALY",
            "Sentiment_Intensity", "DirectionScore", "BreadthScore", "IntensityScore",
        ]
        for c in self.feat_cols:
            if c not in df.columns:
                df[c] = 0.0
            df[c] = _safe_num(df[c])

        # Rank codes by liquidity proxy
        if "QUANTITE_NEGOCIEE" in df.columns:
            df["QUANTITE_NEGOCIEE"] = _safe_num(df["QUANTITE_NEGOCIEE"])
            rank = df.groupby("CODE")["QUANTITE_NEGOCIEE"].sum().sort_values(ascending=False)
        else:
            rank = df.groupby("CODE").size().sort_values(ascending=False)

        counts = df.groupby("CODE").size()
        eligible = counts[counts >= self.min_rows_per_code].index
        ranked = [c for c in rank.index.tolist() if c in set(eligible)]
        if self.top_n_codes > 0:
            ranked = ranked[: self.top_n_codes]

        if len(ranked) < 5:
            raise ValueError("Not enough eligible CODEs. Lower min_rows_per_code/top_n_codes.")

        self.codes = ranked
        self.code_to_id = {c: i for i, c in enumerate(self.codes)}
        self.max_code_id = max(1, len(self.codes) - 1)

        df = df[df["CODE"].isin(self.codes)].copy()
        self.by_code = {c: g.reset_index(drop=True) for c, g in df.groupby("CODE")}

        # Observation:
        # [code_id, ret1, ret5, vol20] + 12 feats + [cash_ratio, pos_ratio] = 18
        self.obs_size = 18
        self.observation_space = spaces.Box(low=-1.5, high=1.5, shape=(self.obs_size,), dtype=np.float32)
        self.action_space = spaces.Discrete(3)

        self._reset_internal()

    def _reset_internal(self):
        self.cur_code = None
        self.df = None
        self.t = 0
        self.start_idx = 0
        self.end_idx = 0
        self.cash = self.initial_cash
        self.shares = 0.0
        self.last_value = self.initial_cash
        self.peak_value = self.initial_cash

    def _portfolio_value(self, price: float) -> float:
        return float(self.cash + self.shares * price)

    def _obs_transform_feats(self, row) -> list[float]:
        # squash mixed-scale features into [-1, 1]
        out = []
        for c in self.feat_cols:
            v = float(row[c])

            if c in ("PROB_LIQUIDITY",):
                # assumed 0..1
                out.append(float(np.clip(v, 0.0, 1.0)))
            elif c in ("VOLUME_Anomaly", "VARIATION_ANOMALY"):
                # flags typically 0/1
                out.append(float(np.clip(v, 0.0, 1.0)))
            elif c.endswith("_z_score") or c in ("Sentiment_Intensity", "DirectionScore", "BreadthScore", "IntensityScore", "LiquidityScore", "NewsScore", "MarketMood"):
                out.append(_clip_tanh(v, clip=5.0))
            else:
                out.append(_clip_tanh(v, clip=5.0))

        return out

    def _get_obs(self) -> np.ndarray:
        row = self.df.iloc[self.t]
        price = float(row["CLOTURE"])
        port_val = self._portfolio_value(price)
        pos_val = float(self.shares * price)

        cash_ratio = float(self.cash / (port_val + 1e-9))
        pos_ratio = float(pos_val / (port_val + 1e-9))

        code_id_norm = float(self.code_to_id[self.cur_code] / self.max_code_id)

        # squash returns/vol too
        ret1 = _clip_tanh(float(row["ret1"]), clip=0.2)   # daily returns rarely beyond 20%
        ret5 = _clip_tanh(float(row["ret5"]), clip=0.5)
        vol20 = _clip_tanh(float(row["vol20"]), clip=0.2)

        feats = self._obs_transform_feats(row)

        obs = np.array(
            [code_id_norm, ret1, ret5, vol20] + feats + [cash_ratio, pos_ratio],
            dtype=np.float32
        )
        
        # Final safety: ensure no NaN or inf values
        obs = np.nan_to_num(obs, nan=0.0, posinf=1.0, neginf=-1.0)
        obs = np.clip(obs, -1.5, 1.5)
        
        return obs

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self._reset_internal()

        forced_code = None
        if options and isinstance(options, dict):
            forced_code = options.get("forced_code")

        if forced_code is not None:
            forced_code = str(forced_code).strip()
            if forced_code not in self.codes:
                raise ValueError(f"forced_code not in env.codes: {forced_code}")
            self.cur_code = forced_code
        else:
            self.cur_code = self.codes[int(self.rng.integers(0, len(self.codes)))]

        self.df = self.by_code[self.cur_code]
        max_start = len(self.df) - self.episode_len - 2
        if max_start < 30:
            return self.reset(seed=seed, options=None)

        self.start_idx = int(self.rng.integers(20, max_start))
        self.end_idx = self.start_idx + self.episode_len
        self.t = self.start_idx

        self.cash = self.initial_cash
        self.shares = 0.0
        self.last_value = self.initial_cash
        self.peak_value = self.initial_cash

        return self._get_obs(), {"code": self.cur_code}

    def step(self, action: int):
        row = self.df.iloc[self.t]
        price = float(row["CLOTURE"])

        trading_cost = 0.0

        # execute action
        if action == 1:  # BUY
            budget = self.cash * self.buy_frac
            if budget > 1e-9:
                fee = budget * self.fee_rate
                spend = max(0.0, budget - fee)
                qty = spend / price
                self.cash -= budget
                self.shares += qty
                trading_cost += fee

        elif action == 2:  # SELL
            qty = self.shares * self.sell_frac
            if qty > 1e-9:
                proceeds = qty * price
                fee = proceeds * self.fee_rate
                self.shares -= qty
                self.cash += (proceeds - fee)
                trading_cost += fee

        # advance time
        self.t += 1
        terminated = self.t >= self.end_idx
        truncated = False

        next_row = self.df.iloc[self.t]
        next_price = float(next_row["CLOTURE"])
        value = self._portfolio_value(next_price)

        # ---- reward shaping that prevents "do nothing" ----
        prev = self.last_value

        # portfolio return
        port_ret = (value - prev) / (prev + 1e-9)
        # market return (this stock's ret1 at next step)
        mkt_ret = float(next_row["ret1"])

        # cost as percentage
        pct_cost = trading_cost / (prev + 1e-9)

        # drawdown penalty
        self.peak_value = max(self.peak_value, value)
        drawdown = (self.peak_value - value) / (self.peak_value + 1e-9)

        # excess return reward
        reward = (port_ret - mkt_ret) - pct_cost - (self.drawdown_lambda * drawdown)
        # exploration shaping: tiny bonus for trying BUY early
        if (self.t - self.start_idx) < 5 and action == 1:
            reward += 0.001

        
        # Clip reward to prevent exploding gradients
        reward = float(np.clip(reward, -1.0, 1.0))

        self.last_value = value

        info = {
            "code": self.cur_code,
            "price": float(next_price),
            "portfolio_value": float(value),
            "port_ret": float(port_ret),
            "mkt_ret": float(mkt_ret),
            "pct_cost": float(pct_cost),
            "drawdown": float(drawdown),
            "cash": float(self.cash),
            "shares": float(self.shares),
        }
        return self._get_obs(), float(reward), terminated, truncated, info
