"""Generate synthetic OHLCV sample data bundled with the repo.

Used as an offline fallback / demo mode when Yahoo Finance is unreachable.
The series are regime-switching geometric Brownian motion, seeded so the
files are reproducible — they are NOT real market prices.

Run from the repo root:  python scripts/generate_sample_data.py
"""

from pathlib import Path

import numpy as np
import pandas as pd

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "samples"

TICKERS = {
    # name: (start price, seed)
    "AAPL": (40.0, 1),
    "MSFT": (85.0, 2),
    "GOOGL": (55.0, 3),
    "TSLA": (20.0, 4),
    "SPY": (250.0, 5),
}

START, END = "2018-01-02", "2025-12-31"


def generate(start_price: float, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range(START, END)
    n = len(dates)

    # Regime-switching drift/volatility so trend and mean-reversion
    # strategies both have something to chew on.
    drift = np.empty(n)
    vol = np.empty(n)
    i = 0
    while i < n:
        length = rng.integers(60, 250)
        mu = rng.choice([0.35, 0.15, 0.0, -0.25], p=[0.3, 0.35, 0.2, 0.15])
        sigma = rng.choice([0.15, 0.25, 0.45], p=[0.4, 0.4, 0.2])
        drift[i : i + length] = mu
        vol[i : i + length] = sigma
        i += length

    dt = 1 / 252
    log_returns = (drift - 0.5 * vol**2) * dt + vol * np.sqrt(dt) * rng.standard_normal(n)
    close = start_price * np.exp(np.cumsum(log_returns))

    gap = rng.normal(0, 0.003, n)
    open_ = np.empty(n)
    open_[0] = start_price
    open_[1:] = close[:-1] * (1 + gap[1:])
    spread = np.abs(rng.normal(0, 0.01, n))
    high = np.maximum(open_, close) * (1 + spread)
    low = np.minimum(open_, close) * (1 - spread)
    volume = rng.lognormal(mean=16.5, sigma=0.4, size=n).astype(int)

    return pd.DataFrame(
        {
            "Open": open_.round(4),
            "High": high.round(4),
            "Low": low.round(4),
            "Close": close.round(4),
            "Volume": volume,
        },
        index=pd.Index(dates, name="Date"),
    )


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ticker, (price, seed) in TICKERS.items():
        df = generate(price, seed)
        path = OUT_DIR / f"{ticker}.csv"
        df.to_csv(path)
        print(f"{ticker}: {len(df)} rows -> {path}")


if __name__ == "__main__":
    main()
