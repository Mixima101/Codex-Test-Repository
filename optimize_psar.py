import math
import random
from dataclasses import dataclass

DATA_FILE = 'google_2y_daily_prices.txt'
TRADING_DAYS = 252
COST_PER_SIDE = 0.0005  # 5 bps per transaction side


def load_prices(path):
    rows = []
    for line in open(path, encoding='utf-8'):
        s = line.strip()
        if not s or s.startswith(('Ticker:', 'Date range', 'Frequency:', 'Source:', 'Price', 'Ticker', 'Date')):
            continue
        p = s.split()
        if len(p) != 7:
            continue
        d, _adj, close, high, low, open_, _vol = p
        rows.append({'date': d, 'open': float(open_), 'high': float(high), 'low': float(low), 'close': float(close)})
    return rows


def compute_psar(highs, lows, closes, af_start, af_step, af_max):
    n = len(closes)
    bull = closes[1] >= closes[0]
    psar = [closes[0]] * n

    ep = highs[0] if bull else lows[0]
    sar = lows[0] if bull else highs[0]
    af = af_start
    psar[0] = sar

    for i in range(1, n):
        sar = sar + af * (ep - sar)

        if bull:
            sar = min(sar, lows[i - 1])
            if i > 1:
                sar = min(sar, lows[i - 2])
            if lows[i] < sar:
                bull = False
                sar = ep
                ep = lows[i]
                af = af_start
            elif highs[i] > ep:
                ep = highs[i]
                af = min(af + af_step, af_max)
        else:
            sar = max(sar, highs[i - 1])
            if i > 1:
                sar = max(sar, highs[i - 2])
            if highs[i] > sar:
                bull = True
                sar = ep
                ep = highs[i]
                af = af_start
            elif lows[i] < ep:
                ep = lows[i]
                af = min(af + af_step, af_max)

        psar[i] = sar
    return psar


@dataclass
class Result:
    start: float
    step: float
    max_step: float
    total_return: float
    buy_hold_return: float
    alpha_ann: float
    beta: float
    sharpe: float
    volatility_ann: float
    max_drawdown: float
    cagr: float
    trades: int
    winning_trades: int
    avg_win: float
    avg_loss: float
    fee_drag: float


def _max_drawdown(equity_curve):
    peak = equity_curve[0]
    mdd = 0.0
    for x in equity_curve:
        if x > peak:
            peak = x
        dd = x / peak - 1
        if dd < mdd:
            mdd = dd
    return mdd


def backtest(rows, s0, s1, s2, cost=COST_PER_SIDE):
    closes = [r['close'] for r in rows]
    highs = [r['high'] for r in rows]
    lows = [r['low'] for r in rows]
    n = len(rows)

    psar = compute_psar(highs, lows, closes, s0, s1, s2)
    signal = [1 if closes[i] >= psar[i] else -1 for i in range(n)]

    # One bar lag to avoid lookahead.
    pos = [0] * n
    for i in range(1, n):
        pos[i] = signal[i - 1]

    strat = [0.0] * n
    bh = [0.0] * n
    fees = 0.0

    for i in range(1, n):
        rb = closes[i] / closes[i - 1] - 1.0
        bh[i] = rb
        fee = abs(pos[i] - pos[i - 1]) * cost
        fees += fee
        strat[i] = pos[i - 1] * rb - fee

    eq_curve = [1.0]
    bh_curve = [1.0]
    for i in range(1, n):
        eq_curve.append(eq_curve[-1] * (1 + strat[i]))
        bh_curve.append(bh_curve[-1] * (1 + bh[i]))

    tr = eq_curve[-1] - 1
    bhr = bh_curve[-1] - 1

    m_s = sum(strat[1:]) / (n - 1)
    m_b = sum(bh[1:]) / (n - 1)
    var_b = sum((x - m_b) ** 2 for x in bh[1:]) / (n - 1)
    cov = sum((strat[i] - m_s) * (bh[i] - m_b) for i in range(1, n)) / (n - 1)
    beta = cov / var_b if var_b > 0 else float('nan')
    alpha_ann = (m_s - beta * m_b) * TRADING_DAYS if var_b > 0 else float('nan')

    var_s = sum((x - m_s) ** 2 for x in strat[1:]) / (n - 1)
    vol_ann = math.sqrt(var_s) * math.sqrt(TRADING_DAYS) if var_s > 0 else float('nan')
    sharpe = (m_s / math.sqrt(var_s)) * math.sqrt(TRADING_DAYS) if var_s > 0 else float('nan')

    years = (n - 1) / TRADING_DAYS
    cagr = eq_curve[-1] ** (1 / years) - 1 if years > 0 else float('nan')
    mdd = _max_drawdown(eq_curve)

    trades = []
    curr = pos[1]
    entry = closes[1]
    for i in range(2, n):
        if pos[i] != curr:
            ex = closes[i - 1]
            t_ret = (ex / entry - 1 if curr == 1 else entry / ex - 1) - 2 * cost
            trades.append(t_ret)
            curr = pos[i]
            entry = closes[i]

    ex = closes[-1]
    t_ret = (ex / entry - 1 if curr == 1 else entry / ex - 1) - 2 * cost
    trades.append(t_ret)

    wins = [t for t in trades if t > 0]
    losses = [t for t in trades if t <= 0]

    return Result(
        s0,
        s1,
        s2,
        tr,
        bhr,
        alpha_ann,
        beta,
        sharpe,
        vol_ann,
        mdd,
        cagr,
        len(trades),
        len(wins),
        sum(wins) / len(wins) if wins else 0.0,
        sum(losses) / len(losses) if losses else 0.0,
        fees,
    )


def optimize(rows):
    random.seed(7)
    best = None

    for _ in range(12000):
        a = 10 ** random.uniform(-4, -0.6)
        b = 10 ** random.uniform(-4, -0.6)
        c = max(a, b, 10 ** random.uniform(-3, -0.2))
        r = backtest(rows, a, b, c)
        if best is None or r.total_return > best.total_return:
            best = r

    for _ in range(6000):
        a = max(1e-5, best.start * random.uniform(0.4, 1.8))
        b = max(1e-5, best.step * random.uniform(0.4, 1.8))
        c = max(a, b, best.max_step * random.uniform(0.4, 2.0))
        r = backtest(rows, a, b, min(c, 1.5))
        if r.total_return > best.total_return:
            best = r

    return best


def main():
    rows = load_prices(DATA_FILE)
    best = optimize(rows)

    print(f'start_step={best.start:.8f}')
    print(f'step={best.step:.8f}')
    print(f'max_step={best.max_step:.8f}')
    print(f'strategy_return={best.total_return * 100:.2f}%')
    print(f'buy_hold_return={best.buy_hold_return * 100:.2f}%')
    print(f'outperformance_pct_points={(best.total_return - best.buy_hold_return) * 100:.2f}%')
    print(f'outperformance_multiple={(best.total_return / best.buy_hold_return):.2f}x' if best.buy_hold_return != 0 else 'outperformance_multiple=inf')
    print(f'cagr={best.cagr * 100:.2f}%')
    print(f'max_drawdown={best.max_drawdown * 100:.2f}%')
    print(f'volatility_ann={best.volatility_ann * 100:.2f}%')
    print(f'alpha_ann={best.alpha_ann * 100:.2f}%')
    print(f'beta={best.beta:.3f}')
    print(f'sharpe={best.sharpe:.3f}')
    print(f'trades={best.trades}')
    print(f'winning_trades={best.winning_trades}')
    print(f'win_rate={(best.winning_trades / best.trades * 100):.2f}%')
    print(f'avg_win={best.avg_win * 100:.2f}%')
    print(f'avg_loss={best.avg_loss * 100:.2f}%')
    print(f'fee_drag={best.fee_drag * 100:.2f}%')


if __name__ == '__main__':
    main()
