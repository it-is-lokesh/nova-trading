import os
import sys
from abc import ABC, abstractmethod

import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime, timezone

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if base_dir not in sys.path:
    sys.path.append(base_dir)


class BaseVisualizer(ABC):
    """
    Abstract base class for algorithm-specific visualizers.

    Subclasses must implement:
        - chart_type (property): "overlay" or "panel"
        - compute(): run the algorithm and store results
        - get_chart_data(): return list of {"chart": ..., "series": ...} dicts
    """

    def __init__(self, symbol: str):
        self.symbol = symbol
        self.data: pd.DataFrame | None = None
        self.x_dates: list | None = None

    # ── data loading ─────────────────────────────────────────────────────

    def update_data(self, show_caption: bool = True):
        """Load OHLC CSV from cache/min15/{symbol}.csv and prepare chart timestamps.

        Args:
            show_caption: If True, display a Streamlit caption with the first
                candle timestamp. Set to False to suppress duplicates when
                multiple visualizers load the same symbol.
        """
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        df = pd.read_csv(
            os.path.join(base_dir, "cache", "min15", f"{self.symbol}.csv"),
            parse_dates=True,
        )
        df["datetime"] = pd.to_datetime(df["datetime"])
        df.sort_values("datetime", inplace=True)

        interval_counts = df["datetime"].diff().dropna().value_counts()
        if not interval_counts.empty and interval_counts.index[0] != pd.Timedelta(minutes=15):
            st.warning(
                f"{self.symbol} cache is not 15-minute data. "
                f"Most common interval: {interval_counts.index[0]}."
            )

        # Lightweight Charts formats intraday timestamps as UTC, so encode the
        # NSE wall-clock time as UTC to keep labels in IST market time.
        chart_datetimes = df["datetime"].dt.tz_localize(None).dt.tz_localize("UTC")
        df["time"] = chart_datetimes.map(lambda value: int(value.timestamp()))

        # drop duplicate times to avoid lightweight-charts rendering failure
        df.drop_duplicates(subset=["time"], keep="last", inplace=True)

        self.data = df
        self.x_dates = df["time"].tolist()

        if show_caption:
            first_chart_label = datetime.fromtimestamp(
                self.x_dates[0], tz=timezone.utc
            ).strftime("%Y-%m-%d %H:%M")
            st.caption(
                f"{self.symbol} first candle: {df['datetime'].iloc[0]} "
                f"| chart time: {first_chart_label}"
            )

    # ── shared helpers ───────────────────────────────────────────────────

    def get_series(self, column: pd.Series, color: str | None = None) -> list[dict]:
        """Convert a pandas column to a lightweight-charts line series list."""
        series = []
        for dt, v in zip(self.x_dates, column):
            if pd.notna(v):
                item = {"time": dt, "value": round(float(v), 2)}
                if color is not None:
                    item["color"] = color
                series.append(item)
        return series

    def get_candles(self) -> list[dict]:
        """Build the candlestick data list from self.data."""
        return [
            dict(
                time=dt,
                open=round(o, 2),
                high=round(h, 2),
                low=round(l, 2),
                close=round(c, 2),
            )
            for dt, o, h, l, c in zip(
                self.x_dates,
                self.data["open"],
                self.data["high"],
                self.data["low"],
                self.data["close"],
            )
            if pd.notna(o) and pd.notna(h) and pd.notna(l) and pd.notna(c)
        ]

    @staticmethod
    def get_axis_options() -> dict:
        """Shared axis configuration for all charts."""
        return {
            "rightPriceScale": {
                "borderVisible": True,
                "borderColor": "#9ca3af",
            },
            "timeScale": {
                "timeVisible": True,
                "secondsVisible": False,
                "borderVisible": True,
                "borderColor": "#9ca3af",
            },
        }

    def get_chart_options(self, height: int = 500) -> dict:
        """Build chart-level options dict for lightweight-charts."""
        axis = self.get_axis_options()
        opts = {
            "height": height,
            "layout": {
                "background": {"color": "#ffffff"},
                "textColor": "#333",
            },
            "grid": {
                "vertLines": {"color": "#eee"},
                "horzLines": {"color": "#eee"},
            },
            "crosshair": {"mode": 0},
            "timeScale": {
                **axis["timeScale"],
            },
            "rightPriceScale": axis["rightPriceScale"],
        }
        # overlay charts get extra timeScale tweaks
        if self.chart_type == "overlay":
            opts["timeScale"]["rightOffset"] = 0
            opts["timeScale"]["barSpacing"] = 30
        return opts

    # ── abstract interface ───────────────────────────────────────────────

    @property
    @abstractmethod
    def chart_type(self) -> str:
        """Return 'overlay' (renders on candlestick chart) or 'panel' (separate sub-chart)."""
        ...

    @abstractmethod
    def compute(self) -> None:
        """Run the algorithm on self.data and store computed results."""
        ...

    @abstractmethod
    def get_chart_data(self) -> list[dict]:
        """Return a list of {"chart": dict, "series": list} for renderLightweightCharts."""
        ...
