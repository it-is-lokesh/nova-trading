import pandas as pd
import numpy as np
from math import sqrt

def sma(s, n):
    return s.rolling(n, min_periods=1).mean()

def ema(s, n):
    return s.ewm(span=n, adjust=False).mean()

def rma(s, n):
    # Wilder's moving average (RMA). alpha = 1/n
    return s.ewm(alpha=1.0/n, adjust=False).mean()

def wma(s, n):
    # weighted moving average with weights 1..n
    def _wma(x):
        w = np.arange(1, len(x)+1)
        return (x * w).sum() / w.sum()
    return s.rolling(n, min_periods=1).apply(_wma, raw=True)

def tema(s, n):
    e1 = ema(s, n)
    e2 = ema(e1, n)
    e3 = ema(e2, n)
    return 3 * e1 - 3 * e2 + e3

def hma(s, n):
    n1 = max(1, int(n//2))
    n2 = max(1, int(round(sqrt(n))))
    part1 = wma(s, n1)
    part2 = wma(s, int(n))
    combined = 2 * part1 - part2
    return wma(combined, n2)

def jurik_moving_average(series, length=14, phase=0, power=2):
    """
    Approximation of Jurik Moving Average (JMA)
    -------------------------------------------
    series : pandas Series
        Input price data (e.g., close prices)
    length : int
        Smoothing period
    phase : float
        -100 to +100 (negative = smoother, positive = faster)
    power : int
        Controls the filter's responsiveness

    Returns
    -------
    pandas Series with the JMA approximation
    """

    # Ensure series is a numpy array
    price = series.to_numpy(dtype=float)
    jma = np.zeros_like(price)
    beta = 0.45 * (length - 1) / (0.45 * (length - 1) + 2.0)
    alpha = beta ** power

    phase_ratio = (phase + 100) / 200
    e0 = np.zeros_like(price)
    e1 = np.zeros_like(price)
    e2 = np.zeros_like(price)

    for i in range(len(price)):
        e0[i] = (1 - alpha) * price[i] + alpha * (e0[i - 1] if i > 0 else price[i])
        e1[i] = (price[i] - e0[i]) * (1 - beta) + beta * (e1[i - 1] if i > 0 else 0)
        e2[i] = e0[i] + phase_ratio * e1[i]
        jma[i] = (1 - alpha) * e2[i] + alpha * (jma[i - 1] if i > 0 else price[i])

    return pd.Series(jma, index=series.index)

def ma_dispatch(ma_type: str, series: pd.Series, length: int):
    """
    Minimal dispatcher for MA types used by the indicator.
    Falls back to EMA for unknown types.
    """
    ma_type = (ma_type or "").upper()
    if length <= 0:
        return series.copy()
    if ma_type == "SMA":
        return sma(series, length)
    if ma_type == "EMA":
        return ema(series, length)
    if ma_type == "RMA" or ma_type == "WILDERS" or ma_type == "RMA":
        return rma(series, length)
    if ma_type == "WMA":
        return wma(series, length)
    if ma_type == "TEMA":
        return tema(series, length)
    if ma_type == "HMA":
        return hma(series, length)
    if ma_type == "JMA":
        return jurik_moving_average(series, length)
    # default fallback
    return ema(series, length)
