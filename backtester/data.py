"""Price data loading: yfinance first, bundled sample CSVs as fallback."""

from pathlib import Path

import pandas as pd
import yfinance as yf

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "data" / "samples"

REQUIRED_COLUMNS = ["Open", "High", "Low", "Close", "Volume"]


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    """Flatten yfinance MultiIndex columns and keep OHLCV in a fixed order."""
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.rename(columns=str.title)
    df = df[[c for c in REQUIRED_COLUMNS if c in df.columns]].copy()
    df.index = pd.to_datetime(df.index)
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    df.index.name = "Date"
    return df.dropna()


def available_sample_tickers() -> list[str]:
    if not SAMPLE_DIR.exists():
        return []
    return sorted(p.stem for p in SAMPLE_DIR.glob("*.csv"))


def load_sample(ticker: str, start=None, end=None) -> pd.DataFrame:
    path = SAMPLE_DIR / f"{ticker.upper()}.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"No sample data for {ticker!r}. Available: {', '.join(available_sample_tickers())}"
        )
    df = pd.read_csv(path, index_col="Date", parse_dates=True)
    df = _normalize(df)
    if start is not None:
        df = df[df.index >= pd.Timestamp(start)]
    if end is not None:
        df = df[df.index <= pd.Timestamp(end)]
    return df


def load_data(ticker: str, start, end) -> tuple[pd.DataFrame, str]:
    """Return (ohlcv DataFrame, source) where source is 'yfinance' or 'sample'.

    Tries a live yfinance download; if the network is unavailable or the
    ticker returns nothing, falls back to the bundled sample CSVs so the
    app still works offline (clearly labelled as sample data).
    """
    try:
        raw = yf.download(
            ticker, start=start, end=end, auto_adjust=True, progress=False
        )
        if raw is not None and not raw.empty:
            return _normalize(raw), "yfinance"
    except Exception:
        pass

    return load_sample(ticker, start, end), "sample"
