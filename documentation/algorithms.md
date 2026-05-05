## Algorithm & Visualization System — Design Documentation

This document explains how trading algorithms and their chart visualizations are structured in this project. It covers the base class contract, the two built-in algorithms, how the application layer composes them, and how to add new algorithms.

---

### Architecture Overview

```
core/
├── base_visualizer.py              # BaseVisualizer ABC — shared chart logic
├── algorithms/
│   ├── moving_averages.py          # Shared MA primitives (SMA, EMA, HMA, etc.)
│   ├── ssl_hybrid/                 # Algorithm package
│   │   ├── __init__.py             # Re-exports ssl_hybrid_core
│   │   ├── core.py                 # Pure computation: ssl_hybrid_core(df) → df
│   │   └── visualize.py            # SSLHybridVisualizer(BaseVisualizer)
│   └── qqe_mod/                    # Algorithm package
│       ├── __init__.py             # Re-exports qqe_mod_core
│       ├── core.py                 # Pure computation: qqe_mod_core(df) → df
│       └── visualize.py            # QQEModVisualizer(BaseVisualizer)

applications/
└── visualize.py                    # Composes visualizers → Streamlit dashboard
```

Each algorithm is a self-contained **package** under `core/algorithms/` containing:

| File | Purpose |
|------|---------|
| `core.py` | Pure computation — takes a DataFrame of OHLCV data, adds signal columns, returns the enriched DataFrame. No UI or chart logic. |
| `visualize.py` | A `BaseVisualizer` subclass that calls `core.py`, then converts the results into chart-renderable data structures. |
| `__init__.py` | Re-exports the core function (e.g. `ssl_hybrid_core`) so external code can import directly from the package name. |

This separation means the algorithm logic (`core.py`) can be used independently of charts — for backtesting, signal generation, or any other downstream consumer — while the visualizer adds the chart rendering layer on top.

---

### BaseVisualizer — The Shared Contract

**File:** `core/base_visualizer.py`

`BaseVisualizer` is an abstract base class (ABC) that all algorithm visualizers inherit from. It provides shared data loading, chart configuration, and series-building helpers, while requiring each subclass to implement the algorithm-specific parts.

#### Constructor

```python
def __init__(self, symbol: str)
```

Stores the stock symbol and initializes `self.data` (DataFrame) and `self.x_dates` (list of chart timestamps) to `None`. These are populated by `update_data()`.

#### Shared Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `update_data` | `(show_caption: bool = True) → None` | Loads OHLCV CSV from `cache/min15/{symbol}.csv`, parses datetimes, creates integer UTC timestamps for Lightweight Charts, deduplicates, and optionally displays a Streamlit caption with the first candle's timestamp. Set `show_caption=False` to suppress duplicate captions when multiple visualizers load the same symbol. |
| `get_series` | `(column: pd.Series, color: str = None) → list[dict]` | Converts a pandas column to a list of `{"time": int, "value": float}` dicts, skipping NaN values. Optionally adds a `"color"` key to each point. |
| `get_candles` | `() → list[dict]` | Builds the candlestick data list from `self.data`, returning dicts with `time`, `open`, `high`, `low`, `close` keys. Skips rows with any NaN OHLC values. |
| `get_axis_options` | `() → dict` (static) | Returns shared axis configuration (right price scale border, time scale visibility settings). |
| `get_chart_options` | `(height: int = 500) → dict` | Builds a complete chart options dict for `renderLightweightCharts`. Overlay-type charts automatically get extra time scale tweaks (`rightOffset`, `barSpacing`). |

#### Abstract Interface (Must Be Implemented by Subclasses)

| Member | Type | Description |
|--------|------|-------------|
| `chart_type` | `@property → str` | Returns `"overlay"` if the algorithm renders on top of the candlestick chart (e.g. signal markers, trend lines), or `"panel"` if it needs a separate sub-chart (e.g. histograms, oscillators). |
| `compute` | `() → None` | Runs the algorithm on `self.data` and stores computed results (e.g. `self.ssl_df`, `self.qqe_df`). Must be called after `update_data()`. |
| `get_chart_data` | `() → list[dict]` | Returns a list of `{"chart": dict, "series": list}` dicts, ready to be passed to `renderLightweightCharts`. Each dict represents one chart pane. |

#### Lifecycle

```
1. visualizer = SomeVisualizer(symbol)     # construct
2. visualizer.update_data()                # load CSV → self.data, self.x_dates
3. visualizer.compute()                    # run algorithm → store signals
4. chart_data = visualizer.get_chart_data() # build renderable chart dicts
```

---

### Built-in Algorithms

#### SSL Hybrid

**Package:** `core/algorithms/ssl_hybrid/`

**Algorithm (`core.py`):**

`ssl_hybrid_core(df, ...)` adds the following columns to the DataFrame:

| Column | Type | Description |
|--------|------|-------------|
| `BBMC` | float | Baseline moving average (configurable MA type, default HMA-60) |
| `upperk`, `lowerk` | float | Keltner-style channel bands around the baseline |
| `atr` | float | Average True Range (Wilder/RMA smoothing) |
| `upper_band`, `lower_band` | float | ATR-based price bands |
| `ssl1` | float | Primary SSL line (baseline MA applied to high/low) |
| `ssl2` | float | Continuation SSL line (JMA-5 by default) |
| `sslExit` | float | Exit SSL line (HMA-15) |
| `buy_atr`, `sell_atr` | bool | ATR-confirmed continuation signals |
| `ssl2_buy_signal`, `ssl2_sell_signal` | bool | Edge-triggered buy/sell signals (False→True transitions) |
| `base_cross_long`, `base_cross_short` | bool | Crossover signals (price crosses sslExit) |
| `exit_long`, `exit_short` | bool | Exit signals |

**Visualizer (`visualize.py`):**

`SSLHybridVisualizer` — `chart_type = "overlay"`

Renders directly on the candlestick chart:
- Blue up-arrows below bars on `base_cross_long` signals
- Red down-arrows above bars on `base_cross_short` signals
- SSL lines (BBMC, upperk, lowerk, ssl1, ssl2) are computed but currently commented out in the series list — uncomment to enable

Returns one chart dict: the candlestick chart with overlaid markers.

---

#### QQE Mod

**Package:** `core/algorithms/qqe_mod/`

**Algorithm (`core.py`):**

`qqe_mod_core(df)` computes a dual-QQE oscillator and adds the following columns:

| Column | Type | Description |
|--------|------|-------------|
| `qqe_up_signal` | float | Bullish signal strength (positive values when both primary and secondary QQE agree on up) |
| `qqe_down_signal` | float | Bearish signal strength (negative values when both agree on down) |

The algorithm internally:
1. Computes two QQE trend lines with different factors (primary: 3.0, secondary: 1.61)
2. Applies Bollinger Bands to the primary QQE difference from 50
3. Generates confluence signals only when both QQE lines agree on direction

**Visualizer (`visualize.py`):**

`QQEModVisualizer` — `chart_type = "panel"`

Renders as a separate sub-chart below the candlestick:
- Green histogram bars for `qqe_up_signal` (bullish)
- Red histogram bars for `qqe_down_signal` (bearish)
- Chart height: 200px (shorter panel)

Returns one chart dict: the histogram panel.

---

### Moving Averages — Shared Primitives

**File:** `core/algorithms/moving_averages.py`

This file provides the moving average functions used by the algorithms. It is not an algorithm package itself — it is a shared utility module.

| Function | Description |
|----------|-------------|
| `sma(s, n)` | Simple Moving Average |
| `ema(s, n)` | Exponential Moving Average |
| `rma(s, n)` | Wilder's Moving Average (alpha = 1/n) |
| `wma(s, n)` | Weighted Moving Average (weights 1..n) |
| `tema(s, n)` | Triple Exponential Moving Average |
| `hma(s, n)` | Hull Moving Average |
| `jurik_moving_average(s, length, phase, power)` | Jurik Moving Average approximation |
| `ma_dispatch(ma_type, series, length)` | Dispatcher — selects MA function by name string (e.g. `"HMA"`, `"JMA"`, `"EMA"`) |

All functions accept a `pd.Series` and an integer period, and return a `pd.Series`.

---

### Application Layer — Composing Visualizers

**File:** `applications/visualize.py`

This is the runnable Streamlit dashboard. It creates one visualizer instance per algorithm, loads data into each, runs the computation, and then composes their chart outputs into a single `renderLightweightCharts` call.

```python
from core.algorithms.ssl_hybrid.visualize import SSLHybridVisualizer
from core.algorithms.qqe_mod.visualize import QQEModVisualizer

# Create separate instances
ssl_viz = SSLHybridVisualizer(symbol)
ssl_viz.update_data()
ssl_viz.compute()

qqe_viz = QQEModVisualizer(symbol)
qqe_viz.update_data(show_caption=False)  # suppress duplicate caption
qqe_viz.compute()

# Compose: overlay chart on top, panel chart below
all_charts = ssl_viz.get_chart_data() + qqe_viz.get_chart_data()
renderLightweightCharts(all_charts, key=chart_key)
```

The `renderLightweightCharts` function from `streamlit-lightweight-charts` accepts a list of chart dicts. Overlay-type charts include the candlestick series with markers/lines, while panel-type charts are separate panes rendered below. The order of charts in the list determines the top-to-bottom rendering order.

**To run:**

```bash
streamlit run applications/visualize.py
```

---

### How to Add a New Algorithm

Follow this step-by-step guide to add a new algorithm to the system.

#### 1. Create the package directory

```
core/algorithms/your_algo/
├── __init__.py
├── core.py
└── visualize.py
```

#### 2. Implement the algorithm in `core.py`

Write a function that takes a DataFrame with OHLCV columns and returns it with added signal columns:

```python
import pandas as pd
import numpy as np

def your_algo_core(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute your algorithm signals.
    
    Expects columns: open, high, low, close, volume, time
    Adds columns: your_signal_1, your_signal_2, ...
    Returns the same DataFrame with added columns.
    """
    # Your computation here
    df['your_signal'] = ...
    return df
```

**Rules:**
- The function receives a DataFrame that already has `time` (int timestamps), `open`, `high`, `low`, `close` columns.
- Add your computed columns directly to the DataFrame.
- Return the DataFrame.
- Do not import any UI/chart libraries here — keep it pure computation.

#### 3. Create `__init__.py` for backward-compatible imports

```python
from core.algorithms.your_algo.core import your_algo_core

__all__ = ["your_algo_core"]
```

#### 4. Implement the visualizer in `visualize.py`

```python
import pandas as pd
from core.base_visualizer import BaseVisualizer
from core.algorithms.your_algo.core import your_algo_core


class YourAlgoVisualizer(BaseVisualizer):
    """Visualizer for Your Algorithm."""

    def __init__(self, symbol: str):
        super().__init__(symbol)
        self.result_df: pd.DataFrame | None = None

    @property
    def chart_type(self) -> str:
        # "overlay" → renders on the candlestick chart (markers, lines)
        # "panel"   → renders as a separate sub-chart (histograms, oscillators)
        return "overlay"  # or "panel"

    def compute(self) -> None:
        self.result_df = your_algo_core(self.data)

    def get_chart_data(self) -> list[dict]:
        if self.chart_type == "overlay":
            # Include candles + your overlay series
            candles = self.get_candles()
            your_line = self.get_series(self.result_df["your_signal"])
            series = [
                {"type": "Candlestick", "data": candles},
                {"type": "Line", "data": your_line, "options": {"color": "blue", "lineWidth": 2}},
            ]
            return [{"chart": self.get_chart_options(height=500), "series": series}]
        else:
            # Panel-type: separate chart, no candles
            hist_data = self.get_series(self.result_df["your_signal"], color="green")
            series = [{"type": "Histogram", "data": hist_data}]
            return [{"chart": self.get_chart_options(height=200), "series": series}]
```

#### 5. Add it to `applications/visualize.py`

```python
from core.algorithms.your_algo.visualize import YourAlgoVisualizer

# In main():
your_viz = YourAlgoVisualizer(symbol)
your_viz.update_data(show_caption=False)
your_viz.compute()

# Add to the composed chart list
all_charts = (
    ssl_viz.get_chart_data()
    + qqe_viz.get_chart_data()
    + your_viz.get_chart_data()
)
renderLightweightCharts(all_charts, key=chart_key)
```

---

### Chart Type Reference

| `chart_type` | Behavior | Use For |
|-------------|----------|---------|
| `"overlay"` | Renders on the main candlestick chart. `get_chart_data()` should include a `Candlestick` series plus any overlaid `Line`/`Area` series and markers. `get_chart_options()` automatically adds `barSpacing` and `rightOffset` tweaks. | Moving averages, Bollinger Bands, support/resistance lines, buy/sell signal markers |
| `"panel"` | Renders as a separate pane below the main chart. `get_chart_data()` should NOT include candles — only the indicator series (histograms, lines, areas). Typically uses a shorter chart height (e.g. 200px). | RSI, MACD, QQE oscillators, volume histograms, any indicator with a different Y-axis scale |

---

### Series Type Reference

These are the series types supported by `streamlit-lightweight-charts`:

| Type | Usage | Example |
|------|-------|---------|
| `"Candlestick"` | OHLC bars | `{"type": "Candlestick", "data": candles, "markers": markers}` |
| `"Line"` | Continuous line | `{"type": "Line", "data": series, "options": {"color": "blue", "lineWidth": 2}}` |
| `"Histogram"` | Vertical bars from zero | `{"type": "Histogram", "data": series}` |
| `"Area"` | Filled area under a line | `{"type": "Area", "data": series, "options": {"topColor": "rgba(0,150,136,0.5)", "bottomColor": "rgba(0,150,136,0.05)"}}` |
| `"Bar"` | OHLC bars (no candle fill) | `{"type": "Bar", "data": candles}` |

Each series data point is a dict: `{"time": int_timestamp, "value": float}` for Line/Histogram/Area, or `{"time": int_timestamp, "open": float, "high": float, "low": float, "close": float}` for Candlestick/Bar.

Markers can be attached to Candlestick/Bar series: `{"time": int, "position": "aboveBar"|"belowBar"|"inBar", "color": str, "shape": "arrowUp"|"arrowDown"|"circle"|"square", "size": int}`.

---

### Data Flow Diagram

```
   cache/min15/SYMBOL.csv
            │
            ▼
  ┌─────────────────────┐
  │  BaseVisualizer      │
  │  update_data()       │  ← Loads CSV, parses timestamps
  │  self.data           │  ← DataFrame with time, open, high, low, close
  │  self.x_dates        │  ← List of int timestamps for chart X-axis
  └──────────┬──────────┘
             │
     ┌───────┴────────┐
     ▼                ▼
┌──────────┐   ┌──────────┐
│ SSL      │   │ QQE Mod  │
│ Hybrid   │   │          │
│ compute()│   │ compute()│  ← Calls core.py algorithm
│          │   │          │
│ get_     │   │ get_     │
│ chart_   │   │ chart_   │
│ data()   │   │ data()   │  ← Builds chart dicts
└────┬─────┘   └────┬─────┘
     │               │
     └───────┬───────┘
             ▼
  ┌─────────────────────┐
  │ applications/       │
  │ visualize.py        │
  │                     │
  │ all_charts =        │
  │   ssl.get_chart_data()
  │ + qqe.get_chart_data()
  │                     │
  │ renderLightweight   │
  │   Charts(all_charts)│  ← Streamlit renders the composed charts
  └─────────────────────┘
```
