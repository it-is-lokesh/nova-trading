import pandas as pd

from core.base_visualizer import BaseVisualizer
from core.algorithms.qqe_mod.core import qqe_mod_core


class QQEModVisualizer(BaseVisualizer):
    """
    Visualizer for the QQE Mod algorithm.

    chart_type = "panel" — the QQE histogram is rendered as a separate
    sub-chart below the main candlestick chart.
    """

    def __init__(self, symbol: str):
        super().__init__(symbol)
        self.qqe_df: pd.DataFrame | None = None

    # ── interface implementation ─────────────────────────────────────────

    @property
    def chart_type(self) -> str:
        return "panel"

    def compute(self) -> None:
        """Run qqe_mod_core on the loaded data."""
        self.qqe_df = qqe_mod_core(self.data)

    def get_chart_data(self) -> list[dict]:
        """
        Return a single chart dict with:
          - Up histogram (green) for bullish QQE signals
          - Down histogram (red) for bearish QQE signals
        """
        hist_series_up = self.get_series(
            self.qqe_df["qqe_up_signal"], color="green"
        )
        hist_series_down = self.get_series(
            self.qqe_df["qqe_down_signal"], color="red"
        )

        series = [
            {"type": "Histogram", "data": hist_series_up},
            {"type": "Histogram", "data": hist_series_down},
        ]

        return [{"chart": self.get_chart_options(height=200), "series": series}]
