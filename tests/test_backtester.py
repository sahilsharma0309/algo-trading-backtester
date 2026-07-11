"""Sanity tests for the backtesting core (run on bundled sample data, no network)."""

import pandas as pd
import pytest

from backtester.data import available_sample_tickers, load_sample
from backtester.engine import run_backtest
from backtester.metrics import cagr, compute_metrics, max_drawdown, sharpe_ratio
from backtester.strategies import STRATEGIES


@pytest.fixture(scope="module")
def sample_df() -> pd.DataFrame:
    return load_sample("AAPL", "2020-01-01", "2024-12-31")


def test_sample_data_available():
    assert "AAPL" in available_sample_tickers()


def test_sample_data_shape(sample_df):
    assert list(sample_df.columns) == ["Open", "High", "Low", "Close", "Volume"]
    assert len(sample_df) > 1000
    assert sample_df.index.is_monotonic_increasing
    assert (sample_df["High"] >= sample_df["Low"]).all()
    assert not sample_df.isna().any().any()


@pytest.mark.parametrize("strategy_key", list(STRATEGIES))
def test_strategy_runs(sample_df, strategy_key):
    result = run_backtest(sample_df, strategy_key, cash=100_000)

    assert len(result.equity) == len(sample_df)
    assert (result.equity > 0).all()
    assert len(result.benchmark_equity) == len(sample_df)

    for metrics in (result.metrics, result.benchmark_metrics):
        assert -1 <= metrics["max_drawdown"] <= 0
        assert metrics["final_value"] > 0

    if result.trade_stats["closed_trades"]:
        assert 0 <= result.trade_stats["win_rate"] <= 1
        # every closed trade produced a buy and a sell record
        assert (result.trades["side"] == "buy").sum() >= result.trade_stats["closed_trades"]


def test_custom_params_change_result(sample_df):
    a = run_backtest(sample_df, "sma_crossover", {"fast": 10, "slow": 30})
    b = run_backtest(sample_df, "sma_crossover", {"fast": 50, "slow": 200})
    assert not a.equity.equals(b.equity)


def test_metrics_known_values():
    idx = pd.bdate_range("2020-01-01", periods=253)
    equity = pd.Series(range(100_000, 100_000 + 253 * 10, 10), index=idx, dtype=float)
    returns = equity.pct_change().dropna()

    m = compute_metrics(equity, returns)
    assert m["total_return"] == pytest.approx(0.0252, abs=1e-4)
    assert m["max_drawdown"] == 0.0
    assert m["sharpe"] > 0

    flat = pd.Series([100.0] * 10, index=pd.bdate_range("2020-01-01", periods=10))
    assert sharpe_ratio(flat.pct_change().dropna()) == 0.0
    assert max_drawdown(flat) == 0.0
    assert cagr(flat) == pytest.approx(0.0)


def test_max_drawdown_simple_case():
    idx = pd.bdate_range("2020-01-01", periods=4)
    equity = pd.Series([100.0, 200.0, 100.0, 150.0], index=idx)
    assert max_drawdown(equity) == pytest.approx(-0.5)
