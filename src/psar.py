from __future__ import annotations

import numpy as np
import pandas as pd


def parabolic_sar(high: pd.Series, low: pd.Series, close: pd.Series, step: float = 0.02, max_step: float = 0.2) -> pd.Series:
    """Compute Parabolic SAR using Wilder's standard recursive definition."""
    if len(high) < 2:
        return pd.Series(np.nan, index=high.index, name="psar")

    h = high.to_numpy(dtype=float)
    l = low.to_numpy(dtype=float)
    c = close.to_numpy(dtype=float)
    psar = np.zeros_like(c)

    bull = c[1] >= c[0]
    af = step
    ep = h[1] if bull else l[1]
    psar[0] = l[0] if bull else h[0]
    psar[1] = min(l[0], l[1]) if bull else max(h[0], h[1])

    for i in range(2, len(c)):
        prior_psar = psar[i - 1]
        candidate = prior_psar + af * (ep - prior_psar)

        if bull:
            candidate = min(candidate, l[i - 1], l[i - 2])
            if l[i] < candidate:
                bull = False
                psar[i] = ep
                ep = l[i]
                af = step
            else:
                psar[i] = candidate
                if h[i] > ep:
                    ep = h[i]
                    af = min(af + step, max_step)
        else:
            candidate = max(candidate, h[i - 1], h[i - 2])
            if h[i] > candidate:
                bull = True
                psar[i] = ep
                ep = h[i]
                af = step
            else:
                psar[i] = candidate
                if l[i] < ep:
                    ep = l[i]
                    af = min(af + step, max_step)

    return pd.Series(psar, index=close.index, name="psar")
