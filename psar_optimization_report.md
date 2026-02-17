# PSAR Parameter Optimization Report (GOOG, 2Y Daily)

## Objective
Find PSAR parameters `(start_step, step, max_step)` that maximize strategy return on the provided 2-year GOOG daily dataset, and beat buy-and-hold by at least 70%.

## Backtest setup
- Data file: `google_2y_daily_prices.txt`
- Signal: `long` when `Close >= PSAR`, `short` when `Close < PSAR`
- Execution assumption: **1-bar lag** (today's signal is traded starting next bar) to avoid lookahead.
- Cost model: **5 bps per side** (`0.05%` buy, `0.05%` sell), including flip trades.
- Search method: random global search + local random refinement.

## Best parameters found
- `start_step = 0.01486982`
- `step = 0.00184566`
- `max_step = 0.03417311`

## Performance (net of trading costs)
- Strategy total return: **250.02%**
- Buy-and-hold return: **115.87%**
- Outperformance: **+134.15 percentage points**
- Return multiple vs buy-and-hold: **2.16x**

This exceeds the "70% over buy-and-hold" target.

## Requested strategy statistics
- Alpha (annualized): **50.78%**
- Beta (vs GOOG buy-and-hold daily returns): **0.390**
- Sharpe (rf = 0): **2.303**
- Number of trades: **10**
- Winning trades: **6**
- Win rate: **60.00%**
- Average win: **29.53%**
- Average loss: **-2.21%**
- Estimated fee drag over period: **0.95%** of starting capital

## Additional useful stats
- CAGR: **88.27%**
- Annualized volatility: **29.37%**
- Max drawdown: **-16.49%**

## Notes
- These are in-sample optimized parameters on a short history (2 years), so overfitting risk is high.
- Next step (recommended): walk-forward / out-of-sample validation before live use.
