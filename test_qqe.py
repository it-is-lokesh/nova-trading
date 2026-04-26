import pandas as pd
import numpy as np

def rsi(series: pd.Series, length: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/length, adjust=False, min_periods=length).mean()
    avg_loss = loss.ewm(alpha=1/length, adjust=False, min_periods=length).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calculate_qqe(source: pd.Series, rsi_length: int = 14, smoothing_factor: int = 5, qqe_factor: float = 4.236):
    rsi_series = rsi(source, rsi_length)
    smoothed_rsi = rsi_series.ewm(span=smoothing_factor, adjust=False).mean()
    atr_rsi = (smoothed_rsi.diff()).abs()
    wilders_length = rsi_length * 2 - 1
    # PineScript uses ta.ema(atrRsi, wildersLength), which is an EMA with span=wilders_length
    smoothed_atr_rsi = atr_rsi.ewm(span=wilders_length, adjust=False).min_periods=wilders_length).mean() # wait, syntax error
