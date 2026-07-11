"""Performance metrics computed from an equity curve / daily returns."""

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.0) -> float:
    """Annualized Sharpe ratio from daily returns."""
    excess = returns - risk_free_rate / TRADING_DAYS
    std = excess.std()
    if std == 0 or np.isnan(std):
        return 0.0
    return float(excess.mean() / std * np.sqrt(TRADING_DAYS))


def max_drawdown(equity: pd.Series) -> float:
    """Largest peak-to-trough decline, as a negative fraction (e.g. -0.35)."""
    running_max = equity.cummax()
    drawdown = equity / running_max - 1.0
    return float(drawdown.min())


def drawdown_series(equity: pd.Series) -> pd.Series:
    return equity / equity.cummax() - 1.0


def cagr(equity: pd.Series) -> float:
    """Compound annual growth rate using the actual calendar span."""
    if len(equity) < 2 or equity.iloc[0] <= 0:
        return 0.0
    days = (equity.index[-1] - equity.index[0]).days
    if days <= 0:
        return 0.0
    years = days / 365.25
    return float((equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1)


def total_return(equity: pd.Series) -> float:
    if len(equity) < 2 or equity.iloc[0] <= 0:
        return 0.0
    return float(equity.iloc[-1] / equity.iloc[0] - 1)


def compute_metrics(equity: pd.Series, returns: pd.Series) -> dict:
    return {
        "total_return": total_return(equity),
        "cagr": cagr(equity),
        "sharpe": sharpe_ratio(returns),
        "max_drawdown": max_drawdown(equity),
        "volatility": float(returns.std() * np.sqrt(TRADING_DAYS)),
        "final_value": float(equity.iloc[-1]) if len(equity) else 0.0,
    }
