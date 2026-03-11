from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def safe_div(a: float, b: float) -> float:
    return float(a / b) if b not in (0, np.nan) and b != 0 else np.nan


def cagr(returns: pd.Series) -> float:
    if returns.empty:
        return np.nan
    eq = (1 + returns).cumprod()
    years = len(returns) / TRADING_DAYS
    if years <= 0:
        return np.nan
    return float(eq.iloc[-1] ** (1 / years) - 1)


def sharpe(returns: pd.Series) -> float:
    vol = returns.std(ddof=0)
    if vol == 0 or np.isnan(vol):
        return np.nan
    return float((returns.mean() / vol) * np.sqrt(TRADING_DAYS))


def max_drawdown(returns: pd.Series) -> float:
    if returns.empty:
        return np.nan
    eq = (1 + returns).cumprod()
    dd = eq / eq.cummax() - 1
    return float(dd.min())


def annualized_vol(returns: pd.Series) -> float:
    return float(returns.std(ddof=0) * np.sqrt(TRADING_DAYS))


def annualized_alpha_beta(strategy_returns: pd.Series, benchmark_returns: pd.Series) -> tuple[float, float, float]:
    df = pd.concat([strategy_returns, benchmark_returns], axis=1).dropna()
    if df.empty:
        return np.nan, np.nan, np.nan
    y = df.iloc[:, 0].to_numpy()
    x = df.iloc[:, 1].to_numpy()
    x_mean = x.mean()
    y_mean = y.mean()
    cov = ((x - x_mean) * (y - y_mean)).mean()
    var = ((x - x_mean) ** 2).mean()
    beta = cov / var if var > 0 else np.nan
    alpha_daily = y_mean - beta * x_mean if np.isfinite(beta) else np.nan
    alpha_ann = alpha_daily * TRADING_DAYS if np.isfinite(alpha_daily) else np.nan
    # R^2
    y_hat = alpha_daily + beta * x if np.isfinite(alpha_daily) and np.isfinite(beta) else np.full_like(y, np.nan)
    ss_res = np.sum((y - y_hat) ** 2) if np.isfinite(y_hat).all() else np.nan
    ss_tot = np.sum((y - y_mean) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 and np.isfinite(ss_res) else np.nan
    return float(alpha_ann), float(beta), float(r2)


def summarize_performance(strategy_returns: pd.Series, benchmark_returns: pd.Series, turnover: float, invested_pct: float) -> dict[str, float]:
    alpha, beta, r2 = annualized_alpha_beta(strategy_returns, benchmark_returns)
    bench_sharpe = sharpe(benchmark_returns)
    return {
        "CAGR": cagr(strategy_returns),
        "Sharpe": sharpe(strategy_returns),
        "Max Drawdown": max_drawdown(strategy_returns),
        "Volatility": annualized_vol(strategy_returns),
        "Alpha (ann)": alpha,
        "Beta": beta,
        "R^2": r2,
        "Turnover": turnover,
        "% Time Invested": invested_pct,
        "Benchmark Sharpe": bench_sharpe,
    }
