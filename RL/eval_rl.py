# eval_rl.py
import numpy as np
from stable_baselines3 import PPO
from rl_env import MultiCodeTunisEnv

CSV_PATH = "../data/historical_data.csv"
MODEL_PATH = "models/ppo_all_codes.zip"

INITIAL_CASH = 10_000.0
EPISODE_LEN = 200
TOP_N_CODES = 50

def run_episode(env, policy="ppo", model=None, forced_code=None):
    obs, info = env.reset(options={"forced_code": forced_code} if forced_code else None)
    code = info.get("code")

    done = False
    while not done:
        if policy == "hold":
            action = 0
        elif policy == "buy_hold":
            # buy at first step only, then hold
            action = 1 if env.t == env.start_idx else 0
        else:
            action, _ = model.predict(obs, deterministic=True)
            action = int(action)

        obs, reward, terminated, truncated, info = env.step(action)
        done = terminated or truncated

    final_value = info["portfolio_value"]
    return code, final_value

def main():
    env = MultiCodeTunisEnv(
        csv_path=CSV_PATH,
        episode_len=EPISODE_LEN,
        top_n_codes=TOP_N_CODES,
        min_rows_per_code=120,
        drawdown_lambda=0.05,
        initial_cash=INITIAL_CASH,
    )

    model = PPO.load(MODEL_PATH)

    # Evaluate across random codes
    n_eval = 30
    results = {"ppo": [], "hold": [], "buy_hold": []}

    rng = np.random.default_rng(0)
    codes = env.codes

    for _ in range(n_eval):
        code = codes[int(rng.integers(0, len(codes)))]

        _, v_ppo = run_episode(env, policy="ppo", model=model, forced_code=code)
        _, v_hold = run_episode(env, policy="hold", model=None, forced_code=code)
        _, v_bh = run_episode(env, policy="buy_hold", model=None, forced_code=code)

        results["ppo"].append(v_ppo)
        results["hold"].append(v_hold)
        results["buy_hold"].append(v_bh)

    def summarize(name):
        arr = np.array(results[name], dtype=float)
        avg = arr.mean()
        med = np.median(arr)
        win = (arr > INITIAL_CASH).mean() * 100
        return avg, med, win

    print("Initial cash:", INITIAL_CASH)
    for name in ["ppo", "hold", "buy_hold"]:
        avg, med, win = summarize(name)
        print(f"{name:8s} | avg_final={avg:,.2f} | median={med:,.2f} | win%={win:.1f}")

if __name__ == "__main__":
    main()
