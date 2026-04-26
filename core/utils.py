"""
Utility functions for fetching index constituents and other market data.
"""
import json
import time
from pathlib import Path

import requests

# Cache directory for storing fetched index data (project root / cache)
CACHE_DIR = Path(__file__).parent.parent / "cache"

# NSE configuration
NSE_BASE = "https://www.nseindia.com"
NSE_INDEX_API = NSE_BASE + "/api/equity-stockIndices?index={}"

# Browser-like headers required by NSE to not block us
_NSE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}


def _create_nse_session():
    """
    Creates a requests.Session with NSE cookies by visiting the homepage first.
    """
    session = requests.Session()
    session.headers.update(_NSE_HEADERS)
    # Visit homepage to get cookies
    session.get(NSE_BASE, timeout=10)
    return session


def _fetch_nse_index_data(index_name):
    """
    Fetches raw JSON data for an NSE index using the internal API.

    Args:
        index_name: e.g. "NIFTY 200", "NIFTY 50", "NIFTY NEXT 50"

    Returns:
        Parsed JSON dict from the NSE API.
    """
    encoded_name = index_name.replace(" ", "%20")
    url = NSE_INDEX_API.format(encoded_name)

    session = _create_nse_session()
    time.sleep(0.5)  # Brief pause to mimic browsing

    resp = session.get(url, timeout=10)
    if resp.status_code != 200:
        raise RuntimeError(
            f"NSE API returned HTTP {resp.status_code} for '{index_name}': "
            f"{resp.text[:300]}"
        )

    return resp.json()


def get_nifty200_symbols(use_cache=True):
    """
    Returns the list of stock symbols in the Nifty 200 index.

    Args:
        use_cache: If True, uses a cached file if it exists and was
                   fetched today. Set to False to force a fresh fetch.

    Returns:
        List of symbol strings, e.g. ["RELIANCE", "TCS", "SBIN", ...]
    """
    return get_index_symbols("NIFTY 200", use_cache=use_cache)


def get_index_symbols(index_name, use_cache=True):
    """
    Fetches the list of stock symbols for any NSE index.

    Args:
        index_name: e.g. "NIFTY 200", "NIFTY 50", "NIFTY NEXT 50"
        use_cache:  If True, uses a cached JSON file if it was
                    fetched today. Set to False to force a fresh fetch.

    Returns:
        List of symbol strings sorted alphabetically.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = index_name.replace(" ", "_").lower()
    cache_file = CACHE_DIR / f"{safe_name}_constituents.json"

    # Check cache
    if use_cache and cache_file.exists():
        cached = json.loads(cache_file.read_text())
        cached_date = cached.get("date", "")
        today = time.strftime("%Y-%m-%d")
        if cached_date == today:
            symbols = cached["symbols"]
            print(f"Loaded {len(symbols)} symbols for {index_name} from cache ({cached_date})")
            return symbols

    # Fetch fresh data
    print(f"Fetching {index_name} constituents from NSE...")
    data = _fetch_nse_index_data(index_name)

    # Parse the response — NSE returns a "data" array with stock objects
    stock_data = data.get("data", [])
    if not stock_data:
        raise RuntimeError(
            f"No constituent data found for '{index_name}'. "
            f"Check if the index name is correct."
        )

    # Extract symbols (skip the first entry which is the index summary row)
    symbols = []
    for entry in stock_data:
        symbol = entry.get("symbol", "")
        # The first row is usually the index summary (e.g. "NIFTY 200")
        # Real stock symbols don't have spaces
        if symbol and " " not in symbol:
            symbols.append(symbol)

    symbols.sort()

    # Save to cache
    cache_data = {
        "index": index_name,
        "date": time.strftime("%Y-%m-%d"),
        "count": len(symbols),
        "symbols": symbols,
    }
    cache_file.write_text(json.dumps(cache_data, indent=2))
    print(f"Fetched {len(symbols)} symbols for {index_name} (cached to {cache_file.name})")

    return symbols


if __name__ == "__main__":
    # Quick test
    symbols = get_nifty200_symbols(use_cache=False)
    print(f"\nNifty 200 ({len(symbols)} stocks):")
    # Print in columns
    cols = 5
    for i in range(0, len(symbols), cols):
        row = symbols[i : i + cols]
        print("  " + "  ".join(f"{s:<16}" for s in row))
