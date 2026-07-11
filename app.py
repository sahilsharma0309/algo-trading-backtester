"""Streamlit dashboard for the algorithmic trading backtester."""

import datetime as dt

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from backtester.data import available_sample_tickers, load_data
from backtester.engine import run_backtest
from backtester.metrics import drawdown_series
from backtester.strategies import STRATEGIES

# Chart palette (validated categorical slots + status colors, light surface)
C_STRATEGY = "#2a78d6"   # series 1 — blue
C_BENCHMARK = "#1baf7a"  # series 2 — aqua
C_DRAWDOWN = "#e34948"   # series 6 — red
C_BUY = "#0ca30c"        # status: good
C_SELL = "#d03b3b"       # status: critical
C_GRID = "#e1e0d9"
C_AXIS = "#898781"
C_INK = "#0b0b0b"

st.set_page_config(page_title="Algo Trading Backtester", page_icon="📈", layout="wide")


def base_layout(fig: go.Figure, ytitle: str = "") -> go.Figure:
    fig.update_layout(
        template="none",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="system-ui, -apple-system, Segoe UI, sans-serif", color=C_AXIS, size=13),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(color=C_INK)),
        margin=dict(l=70, r=90, t=30, b=40),
        height=420,
    )
    fig.update_xaxes(gridcolor=C_GRID, linecolor=C_GRID, zeroline=False)
    fig.update_yaxes(gridcolor=C_GRID, linecolor=C_GRID, zeroline=False, title=ytitle)
    return fig


def end_label(fig: go.Figure, series: pd.Series, text: str, color: str):
    fig.add_annotation(
        x=series.index[-1], y=series.iloc[-1], text=text, showarrow=False,
        xanchor="left", xshift=6, font=dict(color=color, size=12),
    )


@st.cache_data(ttl=3600, show_spinner=False)
def cached_load(ticker: str, start: dt.date, end: dt.date):
    df, source = load_data(ticker, start, end)
    return df, source


st.title("📈 Algorithmic Trading Backtester")
st.caption(
    "Backtest classic strategies on free Yahoo Finance data and compare them "
    "against buy-and-hold. Built with backtrader, yfinance and Streamlit. "
    "For education only — not investment advice."
)

with st.sidebar:
    st.header("Backtest settings")

    popular = ["AAPL", "MSFT", "GOOGL", "TSLA", "SPY", "NVDA", "AMZN", "META"]
    ticker = st.selectbox("Ticker", popular, index=0, accept_new_options=True,
                          help="Pick a ticker or type any Yahoo Finance symbol")
    ticker = (ticker or "AAPL").strip().upper()

    today = dt.date.today()
    col_a, col_b = st.columns(2)
    start = col_a.date_input("Start", value=today - dt.timedelta(days=5 * 365))
    end = col_b.date_input("End", value=today)

    strategy_key = st.selectbox(
        "Strategy", list(STRATEGIES), format_func=lambda k: STRATEGIES[k]["label"]
    )
    spec = STRATEGIES[strategy_key]
    st.caption(spec["description"])

    params = {}
    for name, p in spec["params"].items():
        params[name] = st.slider(p["label"], p["min"], p["max"], p["default"], p["step"])

    with st.expander("Portfolio settings"):
        cash = st.number_input("Initial capital ($)", 1_000, 10_000_000, 100_000, step=1_000)
        commission_bps = st.slider("Commission (bps per trade)", 0, 50, 10, 1)

    run = st.button("Run backtest", type="primary", use_container_width=True)

if strategy_key == "sma_crossover" and params["fast"] >= params["slow"]:
    st.sidebar.error("Fast SMA period must be smaller than the slow SMA period.")
    st.stop()

if start >= end:
    st.sidebar.error("Start date must be before end date.")
    st.stop()

if not run and "ran_once" not in st.session_state:
    st.info("⬅️ Choose a ticker and strategy in the sidebar, then hit **Run backtest**.")
    st.stop()
st.session_state["ran_once"] = True

with st.spinner(f"Loading {ticker} data…"):
    try:
        df, source = cached_load(ticker, start, end)
    except FileNotFoundError:
        st.error(
            f"Could not download **{ticker}** from Yahoo Finance and no offline "
            f"sample exists for it. Offline samples: "
            f"{', '.join(available_sample_tickers())}."
        )
        st.stop()

if len(df) < 60:
    st.error(f"Only {len(df)} trading days of data — pick a longer date range.")
    st.stop()

if source == "sample":
    st.warning(
        "Yahoo Finance is unreachable from this deployment right now, so the app "
        "is running on **bundled synthetic sample data** (not real prices). "
        "Run it with internet access to Yahoo Finance for live data.",
        icon="⚠️",
    )

with st.spinner("Running backtest…"):
    result = run_backtest(df, strategy_key, params, cash=cash, commission=commission_bps / 10_000)

m, b = result.metrics, result.benchmark_metrics

st.subheader(f"{spec['label']} on {ticker}")
st.caption(
    f"{df.index[0].date()} → {df.index[-1].date()} · {len(df)} trading days · "
    f"data source: {'Yahoo Finance' if source == 'yfinance' else 'bundled sample (synthetic)'}"
)

t1, t2, t3, t4, t5 = st.columns(5)
t1.metric("Total return", f"{m['total_return']:+.1%}", f"{m['total_return'] - b['total_return']:+.1%} vs B&H")
t2.metric("CAGR", f"{m['cagr']:+.1%}", f"{m['cagr'] - b['cagr']:+.1%} vs B&H")
t3.metric("Sharpe ratio", f"{m['sharpe']:.2f}", f"{m['sharpe'] - b['sharpe']:+.2f} vs B&H")
t4.metric("Max drawdown", f"{m['max_drawdown']:.1%}", f"{m['max_drawdown'] - b['max_drawdown']:+.1%} vs B&H")
t5.metric(
    "Trades",
    f"{result.trade_stats['closed_trades']}",
    f"{result.trade_stats['win_rate']:.0%} win rate",
    delta_color="off",
)

tab_equity, tab_dd, tab_price, tab_table = st.tabs(
    ["Equity curve", "Drawdown", "Price & trades", "Details"]
)

with tab_equity:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=result.equity.index, y=result.equity, name="Strategy",
        line=dict(color=C_STRATEGY, width=2),
        hovertemplate="$%{y:,.0f}<extra>Strategy</extra>",
    ))
    fig.add_trace(go.Scatter(
        x=result.benchmark_equity.index, y=result.benchmark_equity, name="Buy & hold",
        line=dict(color=C_BENCHMARK, width=2),
        hovertemplate="$%{y:,.0f}<extra>Buy & hold</extra>",
    ))
    base_layout(fig, "Portfolio value ($)")
    end_label(fig, result.equity, "Strategy", C_STRATEGY)
    end_label(fig, result.benchmark_equity, "Buy & hold", C_BENCHMARK)
    st.plotly_chart(fig, use_container_width=True)

with tab_dd:
    dd_s = drawdown_series(result.equity)
    dd_b = drawdown_series(result.benchmark_equity)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dd_s.index, y=dd_s, name="Strategy",
        line=dict(color=C_DRAWDOWN, width=2), fill="tozeroy",
        fillcolor="rgba(227,73,72,0.15)",
        hovertemplate="%{y:.1%}<extra>Strategy</extra>",
    ))
    fig.add_trace(go.Scatter(
        x=dd_b.index, y=dd_b, name="Buy & hold",
        line=dict(color=C_AXIS, width=2, dash="dot"),
        hovertemplate="%{y:.1%}<extra>Buy & hold</extra>",
    ))
    base_layout(fig, "Drawdown")
    fig.update_yaxes(tickformat=".0%")
    st.plotly_chart(fig, use_container_width=True)

with tab_price:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df.index, y=df["Close"], name="Close",
        line=dict(color=C_STRATEGY, width=2),
        hovertemplate="$%{y:,.2f}<extra>Close</extra>",
    ))
    if not result.trades.empty:
        buys = result.trades[result.trades["side"] == "buy"]
        sells = result.trades[result.trades["side"] == "sell"]
        fig.add_trace(go.Scatter(
            x=buys["date"], y=buys["price"], name="Buy", mode="markers",
            marker=dict(symbol="triangle-up", size=11, color=C_BUY,
                        line=dict(width=1, color="#ffffff")),
            hovertemplate="Buy @ $%{y:,.2f}<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=sells["date"], y=sells["price"], name="Sell", mode="markers",
            marker=dict(symbol="triangle-down", size=11, color=C_SELL,
                        line=dict(width=1, color="#ffffff")),
            hovertemplate="Sell @ $%{y:,.2f}<extra></extra>",
        ))
    base_layout(fig, "Price ($)")
    st.plotly_chart(fig, use_container_width=True)

with tab_table:
    left, right = st.columns(2)
    with left:
        st.markdown("**Strategy vs buy-and-hold**")
        comparison = pd.DataFrame(
            {
                "Strategy": {
                    "Total return": f"{m['total_return']:+.2%}",
                    "CAGR": f"{m['cagr']:+.2%}",
                    "Sharpe ratio": f"{m['sharpe']:.2f}",
                    "Max drawdown": f"{m['max_drawdown']:.2%}",
                    "Annualized volatility": f"{m['volatility']:.2%}",
                    "Final value": f"${m['final_value']:,.0f}",
                },
                "Buy & hold": {
                    "Total return": f"{b['total_return']:+.2%}",
                    "CAGR": f"{b['cagr']:+.2%}",
                    "Sharpe ratio": f"{b['sharpe']:.2f}",
                    "Max drawdown": f"{b['max_drawdown']:.2%}",
                    "Annualized volatility": f"{b['volatility']:.2%}",
                    "Final value": f"${b['final_value']:,.0f}",
                },
            }
        )
        st.table(comparison)
    with right:
        st.markdown("**Executed orders**")
        if result.trades.empty:
            st.caption("No trades were executed with these settings.")
        else:
            trades_view = result.trades.copy()
            trades_view["price"] = trades_view["price"].map("${:,.2f}".format)
            trades_view["size"] = trades_view["size"].map("{:,.0f}".format)
            st.dataframe(trades_view, use_container_width=True, height=300)
