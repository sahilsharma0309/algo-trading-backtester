"""Algorithmic trading backtester built on backtrader + yfinance."""

from backtester.data import load_data
from backtester.engine import run_backtest, BacktestResult
from backtester.metrics import compute_metrics
from backtester.strategies import STRATEGIES

__all__ = ["load_data", "run_backtest", "BacktestResult", "compute_metrics", "STRATEGIES"]
