import pandas as pd
import numpy as np
from core.algorithms.moving_averages import sma

def rsi(series: pd.Series, length: int = 14) -> pd.Series:
    """
    Calculate the Relative Strength Index (RSI) for a given price series.
    
    Parameters:
        series : pd.Series
            The price series (e.g., close prices).
        length : int
            Lookback period for RSI, typically 14.

    Returns:
        pd.Series : RSI values (0-100)
    """
    # Step 1: Compute daily differences
    delta = series.diff()

    # Step 2: Separate gains and losses
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    # Step 3: Compute Wilder's smoothed averages (RMA)
    avg_gain = gain.ewm(alpha=1/length, adjust=False, min_periods=length).mean()
    avg_loss = loss.ewm(alpha=1/length, adjust=False, min_periods=length).mean()

    # Step 4: Compute RSI
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return rsi

def calculate_qqe(source: pd.Series, rsi_length: int = 14, smoothing_factor: int = 5, qqe_factor: float = 4.236):
    """
    Calculate QQE Trend Line and smoothed RSI from a price series.
    
    Parameters:
        source : pd.Series - price series (e.g., close)
        rsi_length : int - length of RSI
        smoothing_factor : int - smoothing for RSI (EMA)
        qqe_factor : float - QQE factor to scale ATR of RSI
        
    Returns:
        qqe_trend_line : pd.Series
        smoothed_rsi : pd.Series
    """
    
    rsi_series = rsi(source, rsi_length)
    
    # Step 2: Smoothed RSI
    smoothed_rsi = rsi_series.ewm(span=smoothing_factor, adjust=False).mean()
    
    # Step 3: ATR of RSI
    atr_rsi = (smoothed_rsi.diff()).abs()
    
    # Step 4: Smoothed ATR using Wilder's length (PineScript uses ta.ema which corresponds to span=length)
    wilders_length = rsi_length * 2 - 1
    smoothed_atr_rsi = atr_rsi.ewm(span=wilders_length, adjust=False, min_periods=wilders_length).mean()
    
    dynamic_atr_rsi = smoothed_atr_rsi * qqe_factor
    
    # Step 5: Initialize arrays for dynamic bands and trend direction
    n = len(source)
    long_band = np.zeros(n)
    short_band = np.zeros(n)
    trend_direction = np.zeros(n)  # 1 = long, -1 = short, 0 = neutral
    qqe_trend_line = np.zeros(n)
    
    for i in range(1, n):
        atr_delta = dynamic_atr_rsi.iat[i]
        new_short_band = smoothed_rsi.iat[i] + atr_delta
        new_long_band = smoothed_rsi.iat[i] - atr_delta

        # Update longBand
        if smoothed_rsi.iat[i-1] > long_band[i-1] and smoothed_rsi.iat[i] > long_band[i-1]:
            long_band[i] = max(long_band[i-1], new_long_band)
        else:
            long_band[i] = new_long_band
        
        # Update shortBand
        if smoothed_rsi.iat[i-1] < short_band[i-1] and smoothed_rsi.iat[i] < short_band[i-1]:
            short_band[i] = min(short_band[i-1], new_short_band)
        else:
            short_band[i] = new_short_band
        
        # Cross detection (Exact translation of PineScript's ta.cross with delayed series)
        if i >= 2:
            short_cross = (smoothed_rsi.iat[i-1] <= short_band[i-2] and smoothed_rsi.iat[i] > short_band[i-1]) or \
                          (smoothed_rsi.iat[i-1] >= short_band[i-2] and smoothed_rsi.iat[i] < short_band[i-1])
            long_cross = (long_band[i-2] <= smoothed_rsi.iat[i-1] and long_band[i-1] > smoothed_rsi.iat[i]) or \
                         (long_band[i-2] >= smoothed_rsi.iat[i-1] and long_band[i-1] < smoothed_rsi.iat[i])
        else:
            short_cross = False
            long_cross = False
        
        if short_cross:
            trend_direction[i] = 1
        elif long_cross:
            trend_direction[i] = -1
        else:
            trend_direction[i] = trend_direction[i-1]
        
        # Determine QQE trend line
        qqe_trend_line[i] = long_band[i] if trend_direction[i] == 1 else short_band[i]
    
    # Convert to pandas Series
    qqe_trend_line = pd.Series(qqe_trend_line, index=source.index)
    smoothed_rsi = pd.Series(smoothed_rsi, index=source.index)
    
    return qqe_trend_line, smoothed_rsi


def qqe_mod_core(df):
    # df = df.copy()
    primaryQQETrendLine, primaryRSI = calculate_qqe(df['close'], rsi_length=6, smoothing_factor=5, qqe_factor=3.0)
    secondaryQQETrendLine, secondaryRSI = calculate_qqe(df['close'], rsi_length=6, smoothing_factor=5, qqe_factor=1.61)

    bollingerLength = 50
    bollingerMultiplier = 0.35
    threshold_secondary = 3.0

    diff = primaryQQETrendLine - 50
    bollingerBasis = sma(primaryQQETrendLine - 50, bollingerLength)
    # PineScript ta.stdev uses population standard deviation (ddof=0)
    bollingerDeviation = bollingerMultiplier * diff.rolling(bollingerLength, min_periods=1).std(ddof=0)
    bollingerUpper = bollingerBasis + bollingerDeviation
    bollingerlower = bollingerBasis - bollingerDeviation

    # Step 2: Primary RSI coloring
    rsi_diff = primaryRSI - 50
    rsi_color_primary = np.where(
        rsi_diff > bollingerUpper, '#00c3ff',  # light blue
        np.where(rsi_diff < bollingerlower, '#ff0062', '#707070')  # red else gray
    )
    
    # Step 3: Secondary RSI coloring
    sec_diff = secondaryRSI - 50
    rsi_color_secondary = np.where(
        sec_diff > threshold_secondary, '#707070',  # gray
        np.where(sec_diff < -threshold_secondary, '#707070', None)  # gray else NA
    )
    
    # Step 4: QQE signals (up/down)
    qqe_up_signal = np.where(
        (sec_diff > threshold_secondary) & (rsi_diff > bollingerUpper),
        sec_diff,
        np.nan
    )
    
    qqe_down_signal = np.where(
        (sec_diff < -threshold_secondary) & (rsi_diff < bollingerlower),
        sec_diff,
        np.nan
    )

    df['qqe_up_signal'] = pd.Series(qqe_up_signal, index=df.index).fillna(0)
    df['qqe_down_signal'] = pd.Series(qqe_down_signal, index=df.index).fillna(0)

    return df
