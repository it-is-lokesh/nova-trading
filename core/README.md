## Core Module — API Documentation

This module provides utility functions for fetching index constituent data from the NSE (National Stock Exchange) website.

> **Note:** The NSE API is undocumented and may change without notice.

### Cache

All cache files are stored in the top-level `cache/` directory at the project root:

| File | Source | Contents |
|---|---|---|
| `cache/symbol_tokens.json` | AngelOne Scrip Master | Maps stock symbols → AngelOne token IDs |
| `cache/nifty_200_constituents.json` | NSE India API | Current Nifty 200 index constituents |
| `cache/nifty_50_constituents.json` | NSE India API | Current Nifty 50 index constituents |

- **Index constituent caches** are valid for one day (auto-refreshed daily).
- **Symbol token cache** persists indefinitely and grows as new symbols are looked up.

### Key Functions

*   `get_nifty200_symbols(use_cache=True)`
    - Returns a sorted list of stock symbols in the NIFTY 200 index.
    - Uses daily caching — fetches fresh data only once per day.

*   `get_index_symbols(index_name, use_cache=True)`
    - Generic function that works for any NSE index.
    - Examples: `"NIFTY 50"`, `"NIFTY 200"`, `"NIFTY NEXT 50"`

### Usage Example

```python
from core.utils import get_nifty200_symbols, get_index_symbols

# Fetch Nifty 200 symbols (cached daily)
nifty200 = get_nifty200_symbols()

# Fetch any other index
nifty50 = get_index_symbols("NIFTY 50")

print(f"NIFTY 200: {len(nifty200)} stocks")
print(f"NIFTY 50:  {len(nifty50)} stocks")
```

### Important Notes

*   The NSE API requires browser-like session cookies. The script handles this automatically by visiting the NSE homepage before making API calls.
*   If NSE changes their API structure or adds new anti-bot measures, this script may break.
*   Index constituents change infrequently (quarterly rebalancing), so daily caching is more than sufficient.
