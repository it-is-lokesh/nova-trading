import pandas as pd

from core.base_visualizer import BaseVisualizer
from core.algorithms.ssl_hybrid.core import ssl_hybrid_core


class SSLHybridVisualizer(BaseVisualizer):
    """
    Visualizer for the SSL Hybrid algorithm.

    chart_type = "overlay" — the SSL signals (markers, lines) are rendered
    directly on the candlestick chart.
    """

    def __init__(self, symbol: str):
        super().__init__(symbol)
        self.ssl_df: pd.DataFrame | None = None

    # ── interface implementation ─────────────────────────────────────────

    @property
    def chart_type(self) -> str:
        return "overlay"

    def compute(self) -> None:
        """Run ssl_hybrid_core on the loaded data."""
        self.ssl_df = ssl_hybrid_core(self.data)

    def get_chart_data(self) -> list[dict]:
        """
        Return a single chart dict with:
          - Candlestick series (with cross-long / cross-short arrow markers)
          - SSL line series (commented out by default, same as original)
        """
        candles = self.get_candles()

        # Build markers from SSL cross signals
        markers = []
        for _, row in self.ssl_df.iterrows():
            if row["base_cross_long"] is True:
                markers.append({
                    "time": row["time"],
                    "position": "belowBar",
                    "color": "blue",
                    "shape": "arrowUp",
                    "size": 1,
                })
            elif row["base_cross_short"] is True:
                markers.append({
                    "time": row["time"],
                    "position": "aboveBar",
                    "color": "red",
                    "shape": "arrowDown",
                    "size": 1,
                })

        # Prepare SSL line series (available for toggling on)
        # BBMC = self.get_series(self.ssl_df["BBMC"])
        # upperk = self.get_series(self.ssl_df["upperk"])
        # lowerk = self.get_series(self.ssl_df["lowerk"])
        # ssl1 = self.get_series(self.ssl_df["ssl1"])
        # ssl2 = self.get_series(self.ssl_df["ssl2"])

        series = [
            {"type": "Candlestick", "data": candles, "markers": markers},
            # {"type": "Line", "data": lowerk, "options": {"color": "blue", "lineWidth": 1}},
            # {"type": "Line", "data": upperk, "options": {"color": "red", "lineWidth": 1}},
            # {"type": "Line", "data": BBMC, "options": {"color": "red", "lineWidth": 2}},
            # {"type": "Line", "data": ssl1, "options": {"color": "red", "lineWidth": 2}},
            # {"type": "Line", "data": ssl2, "options": {"color": "pink", "lineWidth": 1}},
        ]

        return [{"chart": self.get_chart_options(height=500), "series": series}]
