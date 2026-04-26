import pandas as pd
import numpy as np
from core.algorithms.moving_averages import sma, ema, rma, wma, tema, hma, jurik_moving_average, ma_dispatch

# --- support helpers ---
def true_range(df):
    prev = df['close'].shift(1)
    tr1 = df['high'] - df['low']
    tr2 = (df['high'] - prev).abs()
    tr3 = (df['low'] - prev).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr

def crossover(a, b):
    """Series boolean where a crosses above b at current index (i.e. prev a <= prev b and a > b)."""
    return (a.shift(1) <= b.shift(1)) & (a > b)

def crossunder(a, b):
    return (a.shift(1) >= b.shift(1)) & (a < b)

def ssl_hybrid_core(df,
                    ma_type="HMA", length=60,                 # baseline
                    ssl2_type="JMA", len2=5,                 # SSL2 (continuation)
                    ssl3_type="HMA", len3=15,                 # SSL exit
                    atrlen=14, atr_mult=1.0, atr_smoothing="RMA",
                    atr_crit=0.9,
                    use_true_range=True,
                    src_col="close"):
    """
    Add core SSL Hybrid columns to df (modified copy).
    This version uses explicit bar-by-bar state propagation for Hlv/ssl,
    and uses Wilder/RMA ATR by default to better match Pine's ta.atr().
    """

    # --- preserve index and don't reset it (keeps Date column unchanged) ---
    # df = df.copy()

    # ensure required cols
    for c in ("open", "high", "low", "close"):
        if c not in df.columns:
            raise ValueError(f"DataFrame must contain '{c}' column")

    # --- helper: compute a Pine-like SSL series with stateful propagation ---
    def compute_ssl_state(price_s: pd.Series, ma_high_s: pd.Series, ma_low_s: pd.Series):
        """
        Mimic Pine's bar-by-bar Hlv and ssl calculation:
          Hlv[i] =  1  if price > ma_high
                   -1  if price < ma_low
                    Hlv[i-1] otherwise (persist previous)
          ssl[i] = ma_high[i] if Hlv[i] < 0 else ma_low[i]
        When MA values are NaN we preserve previous Hlv (and ssl will be NaN until MA appears).
        """
        n = len(price_s)
        Hlv = np.zeros(n, dtype=float)  # use 0 as initial fallback like Pine's nz(..., 0)
        ssl = np.full(n, np.nan)

        prev_hlv = 0.0
        for i in range(n):
            p = price_s.iat[i]
            eh = ma_high_s.iat[i]
            el = ma_low_s.iat[i]

            # if either MA not available, keep previous Hlv
            if pd.isna(eh) or pd.isna(el):
                hlv = prev_hlv
            else:
                if p > eh:
                    hlv = 1.0
                elif p < el:
                    hlv = -1.0
                else:
                    hlv = prev_hlv

            # set ssl value (may be NaN if eh/el NaN)
            ssl_val = (eh if hlv < 0 else el) if (not pd.isna(eh) and not pd.isna(el)) else np.nan

            Hlv[i] = hlv
            ssl[i] = ssl_val
            prev_hlv = hlv

        return pd.Series(Hlv, index=price_s.index), pd.Series(ssl, index=price_s.index)

    # --- baseline MA (BBMC) and channel ---
    src = df[src_col]
    BBMC = ma_dispatch(ma_type, src, length)           # baseline moving average
    Keltma = ma_dispatch(ma_type, src, length)         # same as baseline in original scripts

    # true-range and rangema used for channel
    tr = true_range(df) if use_true_range else (df['high'] - df['low'])
    rangema = ema(tr, length)   # Pine often uses EMA of TR for some channel calcs

    # channel (keep same multiplier semantics you used)
    upperk = Keltma + rangema * atr_mult * 0.2
    lowerk = Keltma - rangema * atr_mult * 0.2

    # ATR: use Wilder/RMA by default to match ta.atr()
    smoothing = (atr_smoothing or "RMA").upper()
    if smoothing == "RMA":
        atr = rma(tr, atrlen)
    elif smoothing == "SMA":
        atr = sma(tr, atrlen)
    elif smoothing == "EMA":
        atr = ema(tr, atrlen)
    else:
        atr = wma(tr, atrlen)

    # simple upper/lower bands based on ATR (keeps previous semantics but uses ATR)
    upper_band = df['close'] + atr * 0.2
    lower_band = df['close'] - atr * 0.2

    # --- SSL1 (baseline SSL) ---
    emahigh = ma_dispatch(ma_type, df['high'], length)
    emalow  = ma_dispatch(ma_type, df['low'], length)
    _, ssl1 = compute_ssl_state(df['close'], emahigh, emalow)

    # --- SSL2 (continuation) ---
    mahigh2 = ma_dispatch(ssl2_type, df['high'], len2)
    malow2  = ma_dispatch(ssl2_type, df['low'], len2)
    _, ssl2 = compute_ssl_state(df['close'], mahigh2, malow2)

    # --- sslExit (exit MA) ---
    Exithigh = ma_dispatch(ssl3_type, df['high'], len3)
    Exitlow  = ma_dispatch(ssl3_type, df['low'], len3)
    _, sslExit = compute_ssl_state(df['close'], Exithigh, Exitlow)

    # --- write to dataframe ---
    df['BBMC'] = BBMC.values
    df['upperk'] = upperk.values
    df['lowerk'] = lowerk.values
    df['atr'] = atr.values
    df['upper_band'] = upper_band.values
    df['lower_band'] = lower_band.values
    df['ssl1'] = ssl1.values
    df['ssl2'] = ssl2.values
    df['sslExit'] = sslExit.values

    # --- continuation / ATR-based conditions (core signals) ---
    upper_half = df['close'] + df['atr'] * atr_crit
    lower_half = df['close'] - df['atr'] * atr_crit

    buy_inatr = lower_half < df['ssl2']
    sell_inatr = upper_half > df['ssl2']

    buy_cont = (df['close'] > df['BBMC']) & (df['close'] > df['ssl2'])
    sell_cont = (df['close'] < df['BBMC']) & (df['close'] < df['ssl2'])

    buy_atr = buy_inatr & buy_cont
    sell_atr = sell_inatr & sell_cont

    df['buy_atr'] = buy_atr
    df['sell_atr'] = sell_atr

    # detect edge-trigger signals (transition from False->True)
    df['ssl2_buy_signal']  = buy_atr & (~buy_atr.shift(1).astype(bool).fillna(False))
    df['ssl2_sell_signal'] = sell_atr & (~sell_atr.shift(1).astype(bool).fillna(False))

    # base cross / exit signals using sslExit (closed-bar crossover detection)
    df['base_cross_long']  = (df['close'] > df['sslExit']) & (df['close'].shift(1) <= df['sslExit'].shift(1))
    df['base_cross_short'] = (df['close'] < df['sslExit']) & (df['close'].shift(1) >= df['sslExit'].shift(1))

    df['exit_long']  = (df['close'] < df['sslExit']) & (df['close'].shift(1) >= df['sslExit'].shift(1))
    df['exit_short'] = (df['close'] > df['sslExit']) & (df['close'].shift(1) <= df['sslExit'].shift(1))

    # keep the DataFrame index and Date column as-is (visualize() expects Date present)
    return df
