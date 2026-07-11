"""Trading strategies implemented on backtrader.

Each strategy inherits LoggedStrategy so executed orders are recorded and
can be plotted as buy/sell markers in the dashboard. The STRATEGIES
registry drives the Streamlit UI (labels, defaults and slider ranges).
"""

import backtrader as bt


class LoggedStrategy(bt.Strategy):
    """Base strategy that records every executed order."""

    def __init__(self):
        self.executed_orders = []

    def notify_order(self, order):
        if order.status == order.Completed:
            self.executed_orders.append(
                {
                    "date": bt.num2date(order.executed.dt).date(),
                    "side": "buy" if order.isbuy() else "sell",
                    "price": order.executed.price,
                    "size": order.executed.size,
                }
            )


class SmaCrossover(LoggedStrategy):
    """Golden-cross trend following: long when fast SMA crosses above slow SMA."""

    params = dict(fast=20, slow=50)

    def __init__(self):
        super().__init__()
        fast = bt.indicators.SMA(self.data.close, period=self.p.fast)
        slow = bt.indicators.SMA(self.data.close, period=self.p.slow)
        self.crossover = bt.indicators.CrossOver(fast, slow)

    def next(self):
        if not self.position and self.crossover[0] > 0:
            self.order_target_percent(target=0.95)
        elif self.position and self.crossover[0] < 0:
            self.close()


class RsiMeanReversion(LoggedStrategy):
    """Buy oversold dips (RSI below lower band), exit once RSI recovers."""

    params = dict(period=14, lower=30, upper=60)

    def __init__(self):
        super().__init__()
        self.rsi = bt.indicators.RSI(self.data.close, period=self.p.period)

    def next(self):
        if not self.position and self.rsi[0] < self.p.lower:
            self.order_target_percent(target=0.95)
        elif self.position and self.rsi[0] > self.p.upper:
            self.close()


class Momentum(LoggedStrategy):
    """Time-series momentum: long while trailing return over the lookback is positive."""

    params = dict(lookback=90)

    def __init__(self):
        super().__init__()
        self.roc = bt.indicators.RateOfChange(self.data.close, period=self.p.lookback)

    def next(self):
        if not self.position and self.roc[0] > 0:
            self.order_target_percent(target=0.95)
        elif self.position and self.roc[0] < 0:
            self.close()


STRATEGIES = {
    "sma_crossover": {
        "label": "Moving Average Crossover",
        "class": SmaCrossover,
        "description": (
            "Trend following. Goes long when the fast SMA crosses above the "
            "slow SMA, exits when it crosses back below."
        ),
        "params": {
            "fast": {"label": "Fast SMA period", "default": 20, "min": 5, "max": 100, "step": 1},
            "slow": {"label": "Slow SMA period", "default": 50, "min": 20, "max": 250, "step": 5},
        },
    },
    "rsi_mean_reversion": {
        "label": "RSI Mean Reversion",
        "class": RsiMeanReversion,
        "description": (
            "Contrarian. Buys when RSI drops below the lower threshold "
            "(oversold) and exits once RSI recovers above the upper threshold."
        ),
        "params": {
            "period": {"label": "RSI period", "default": 14, "min": 5, "max": 30, "step": 1},
            "lower": {"label": "Oversold threshold", "default": 30, "min": 10, "max": 45, "step": 1},
            "upper": {"label": "Exit threshold", "default": 60, "min": 50, "max": 90, "step": 1},
        },
    },
    "momentum": {
        "label": "Momentum",
        "class": Momentum,
        "description": (
            "Time-series momentum. Stays long while the trailing return over "
            "the lookback window is positive, exits when it turns negative."
        ),
        "params": {
            "lookback": {"label": "Lookback (days)", "default": 90, "min": 20, "max": 252, "step": 5},
        },
    },
}
