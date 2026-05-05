## Nova Trading

This repository contains scripts to download historical price data of Indian stocks (NSE), run trading algorithms on them, and visualize the output using interactive charts.

### TODO
1. Add Kite and TradingView data fetch pipeline codes.

---

### Repository Structure

```
nova-trading/
├── applications/                  # Runnable entry-point scripts
│   ├── visualize.py               # Streamlit dashboard — chart rendering
│   ├── historical_data_fetch.py   # Batch-download historical data
│   └── encrypt.py                 # Encrypt credentials into confidential/env.py
│
├── core/                          # Shared library code
│   ├── base_visualizer.py         # BaseVisualizer ABC (shared chart logic)
│   ├── algorithms/                # Trading algorithms (one package per algo)
│   │   ├── moving_averages.py     # MA primitives (SMA, EMA, HMA, JMA, etc.)
│   │   ├── ssl_hybrid/            # SSL Hybrid algorithm
│   │   │   ├── core.py            # Algorithm computation (ssl_hybrid_core)
│   │   │   ├── visualize.py       # SSLHybridVisualizer — overlay chart
│   │   │   └── __init__.py        # Re-exports ssl_hybrid_core
│   │   └── qqe_mod/               # QQE Mod algorithm
│   │       ├── core.py            # Algorithm computation (qqe_mod_core)
│   │       ├── visualize.py       # QQEModVisualizer — panel chart
│   │       └── __init__.py        # Re-exports qqe_mod_core
│   ├── download_data/             # Data fetchers by broker
│   │   └── angelone/              # AngelOne SmartAPI integration
│   │       ├── fetch.py           # Historical candle download
│   │       ├── get_authorization.py  # Auth + JWT management
│   │       └── symbol_id.py       # Symbol → token mapping
│   ├── credentials.py             # Runtime credential decryption
│   └── utils.py                   # NSE index constituent fetching
│
├── cache/                         # Downloaded data and computed caches
│   ├── min15/                     # 15-min OHLCV CSVs (SYMBOL.csv)
│   ├── ema/                       # Pre-computed EMA arrays (SYMBOL.npz)
│   └── ...                        # Other interval caches
│
├── confidential/                  # Encrypted secrets (git-ignored)
├── documentation/                 # Detailed module-level documentation
│   ├── project.md                 # This README (mirrored)
│   ├── algorithms.md              # Algorithm & visualization system design
│   ├── core.md                    # Core utilities documentation
│   └── angelone.md                # AngelOne data module documentation
│
└── requirements.txt
```

---

### Quick Start

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set up credentials (see [AngelOne docs](documentation/angelone.md)):
   ```bash
   cp .credentials.example .credentials
   # Fill in your AngelOne API fields
   python applications/encrypt.py
   ```

3. Download historical data:
   ```bash
   python applications/historical_data_fetch.py
   ```

4. Launch the visualization dashboard:
   ```bash
   streamlit run applications/visualize.py
   ```

---

### System Design Overview

The project separates concerns into three layers:

| Layer | Location | Responsibility |
|-------|----------|---------------|
| **Data** | `core/download_data/` | Fetch and cache OHLCV data from brokers |
| **Algorithms** | `core/algorithms/` | Compute trading signals from OHLCV data |
| **Visualization** | `core/base_visualizer.py` + per-algo `visualize.py` | Render algorithm output on interactive charts |
| **Applications** | `applications/` | Compose the above into runnable scripts |

Each algorithm lives in its own package under `core/algorithms/` and contains both its computation logic (`core.py`) and its visualization logic (`visualize.py`). See [Algorithm & Visualization System](documentation/algorithms.md) for the full design guide.

---

### Documentation Index

| Document | Contents |
|----------|----------|
| [Algorithm & Visualization System](documentation/algorithms.md) | How algorithms and visualizers are structured, the BaseVisualizer contract, and how to add new algorithms |
| [Core Utilities](documentation/core.md) | NSE index constituent fetching, cache system |
| [AngelOne Data Module](documentation/angelone.md) | Credential setup, authentication, historical data download |
