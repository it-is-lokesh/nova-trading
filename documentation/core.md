## Core Module — API Documentation

This module provides the shared library code for the trading application: algorithm computation, chart visualization, data fetching utilities, and credential management.

> **Note:** The NSE API is undocumented and may change without notice.

---

### Module Structure

```
core/
├── base_visualizer.py         # BaseVisualizer ABC (shared chart logic)
├── algorithms/                # Trading algorithms
│   ├── moving_averages.py     # MA primitives (SMA, EMA, HMA, JMA, etc.)
│   ├── ssl_hybrid/            # SSL Hybrid algorithm + visualizer
│   │   ├── core.py
│   │   ├── visualize.py
│   │   └── __init__.py
│   └── qqe_mod/               # QQE Mod algorithm + visualizer
│       ├── core.py
│       ├── visualize.py
│       └── __init__.py
├── download_data/             # Data fetchers by broker
│   └── angelone/              # AngelOne SmartAPI integration
├── credentials.py             # Runtime credential decryption
└── utils.py                   # NSE index constituent fetching
```

---

### Algorithms & Visualization

Each algorithm is a self-contained Python package under `core/algorithms/` containing:

- **`core.py`** — Pure computation. Takes a DataFrame, adds signal columns, returns the enriched DataFrame. No UI code.
- **`visualize.py`** — A `BaseVisualizer` subclass. Calls the core function, then converts results to chart-renderable data.
- **`__init__.py`** — Re-exports the core function for convenient imports.

The `BaseVisualizer` ABC in `core/base_visualizer.py` provides shared logic: CSV data loading, timestamp formatting, candlestick building, chart options, and series conversion. Each subclass declares a `chart_type` (`"overlay"` or `"panel"`) and implements `compute()` and `get_chart_data()`.

For full details, see [Algorithm & Visualization System](algorithms.md).

#### Current Algorithms

| Algorithm | Package | Chart Type | Description |
|-----------|---------|------------|-------------|
| SSL Hybrid | `core.algorithms.ssl_hybrid` | `overlay` | Multi-MA trend/crossover system — renders buy/sell arrow markers on the candlestick chart |
| QQE Mod | `core.algorithms.qqe_mod` | `panel` | Dual-QQE oscillator — renders green/red histogram in a separate sub-chart |

#### Quick Import Examples

```python
# Import algorithm core functions directly
from core.algorithms.ssl_hybrid import ssl_hybrid_core
from core.algorithms.qqe_mod import qqe_mod_core

# Import visualizer classes
from core.algorithms.ssl_hybrid.visualize import SSLHybridVisualizer
from core.algorithms.qqe_mod.visualize import QQEModVisualizer
```

---

### NSE Utilities (`utils.py`)

#### Cache

All cache files are stored in the top-level `cache/` directory at the project root:

| File | Source | Contents |
|---|---|---|
| `cache/symbol_tokens.json` | AngelOne Scrip Master | Maps stock symbols → AngelOne token IDs |
| `cache/nifty_200_constituents.json` | NSE India API | Current Nifty 200 index constituents |
| `cache/nifty_50_constituents.json` | NSE India API | Current Nifty 50 index constituents |

- **Index constituent caches** are valid for one day (auto-refreshed daily).
- **Symbol token cache** persists indefinitely and grows as new symbols are looked up.

#### Key Functions

*   `get_nifty200_symbols(use_cache=True)`
    - Returns a sorted list of stock symbols in the NIFTY 200 index.
    - Uses daily caching — fetches fresh data only once per day.

*   `get_index_symbols(index_name, use_cache=True)`
    - Generic function that works for any NSE index.
    - Examples: `"NIFTY 50"`, `"NIFTY 200"`, `"NIFTY NEXT 50"`

#### Usage Example

```python
from core.utils import get_nifty200_symbols, get_index_symbols

# Fetch Nifty 200 symbols (cached daily)
nifty200 = get_nifty200_symbols()

# Fetch any other index
nifty50 = get_index_symbols("NIFTY 50")

print(f"NIFTY 200: {len(nifty200)} stocks")
print(f"NIFTY 50:  {len(nifty50)} stocks")
```

#### Important Notes

*   The NSE API requires browser-like session cookies. The script handles this automatically by visiting the NSE homepage before making API calls.
*   If NSE changes their API structure or adds new anti-bot measures, this script may break.
*   Index constituents change infrequently (quarterly rebalancing), so daily caching is more than sufficient.
