"""Backtest runner: wires a strategy + data feed into backtrader and
returns equity curves, trades and metrics for both the strategy and a
buy-and-hold benchmark on the same data."""

from dataclasses import dataclass, field

import backtrader as bt
import pandas as pd

from backtester.metrics import compute_metrics
from backtester.strategies import STRATEGIES


@dataclass
class BacktestResult:
    equity: pd.Series
    returns: pd.Series
    benchmark_equity: pd.Series
    benchmark_returns: pd.Series
    trades: pd.DataFrame
    metrics: dict = field(default_factory=dict)
    benchmark_metrics: dict = field(default_factory=dict)
    trade_stats: dict = field(default_factory=dict)


def _buy_and_hold(close: pd.Series, cash: float, commission: float) -> tuple[pd.Series, pd.Series]:
    """Invest everything on day one (paying commission once), hold to the end."""
    returns = close.pct_change().fillna(0.0)
    equity = cash * (1 - commission) * (1 + returns).cumprod()
    return equity, returns


def run_backtest(
    df: pd.DataFrame,
    strategy_key: str,
    params: dict | None = None,
    cash: float = 100_000.0,
    commission: float = 0.001,
) -> BacktestResult:
    spec = STRATEGIES[strategy_key]
    params = params or {}

    cerebro = bt.Cerebro()
    cerebro.adddata(bt.feeds.PandasData(dataname=df))
    cerebro.addstrategy(spec["class"], **params)
    cerebro.broker.setcash(cash)
    cerebro.broker.setcommission(commission=commission)
    cerebro.addanalyzer(bt.analyzers.TimeReturn, timeframe=bt.TimeFrame.Days, _name="timereturn")
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")

    strat = cerebro.run()[0]

    timereturn = strat.analyzers.timereturn.get_analysis()
    returns = pd.Series(timereturn)
    returns.index = pd.to_datetime(returns.index)
    equity = cash * (1 + returns).cumprod()

    trades = pd.DataFrame(strat.executed_orders, columns=["date", "side", "price", "size"])

    ta = strat.analyzers.trades.get_analysis()
    closed = ta.get("total", {}).get("closed", 0)
    won = ta.get("won", {}).get("total", 0)
    trade_stats = {
        "closed_trades": closed,
        "won": won,
        "lost": ta.get("lost", {}).get("total", 0),
        "win_rate": won / closed if closed else 0.0,
        "pnl_net": ta.get("pnl", {}).get("net", {}).get("total", 0.0),
    }

    bench_equity, bench_returns = _buy_and_hold(df["Close"], cash, commission)

    return BacktestResult(
        equity=equity,
        returns=returns,
        benchmark_equity=bench_equity,
        benchmark_returns=bench_returns,
        trades=trades,
        metrics=compute_metrics(equity, returns),
        benchmark_metrics=compute_metrics(bench_equity, bench_returns),
        trade_stats=trade_stats,
    )
