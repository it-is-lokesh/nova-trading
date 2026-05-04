import json
from urllib.request import urlopen
from pathlib import Path

SCRIP_MASTER_URL = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
PROJECT_ROOT = Path(__file__).resolve().parents[3]
CACHE_DIR = PROJECT_ROOT / "cache"
LOCAL_CACHE_PATH = CACHE_DIR / "symbol_tokens.json"

_token_cache = {}


def _load_cache():
    global _token_cache
    if LOCAL_CACHE_PATH.exists():
        try:
            with LOCAL_CACHE_PATH.open("r") as f:
                _token_cache.update(json.load(f))
        except (json.JSONDecodeError, IOError):
            pass


def _save_cache():
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with LOCAL_CACHE_PATH.open("w") as f:
            json.dump(_token_cache, f, indent=4)
    except IOError as e:
        print(f"Warning: Could not save cache to {LOCAL_CACHE_PATH}: {e}")


def get_symboltoken(symbol):
    """
    Returns the symbol token. Checks memory cache first, then local file cache.
    If absent, scrapes the AngelOne scrip master and updates the cache.
    """
    global _token_cache

    # 1. Check memory cache
    if symbol in _token_cache:
        return _token_cache[symbol]

    # 2. Check local file cache
    if not _token_cache:
        _load_cache()
        if symbol in _token_cache:
            return _token_cache[symbol]

    # 3. Scrape and update if still not found
    print(f"Token for {symbol} not found in cache. Fetching scrip master...")
    with urlopen(SCRIP_MASTER_URL, timeout=30) as response:
        instruments = json.load(response)

    for instrument in instruments:
        if instrument.get("exch_seg") != "NSE":
            continue

        inst_symbol = instrument.get("symbol", "")
        inst_name = instrument.get("name", "")
        inst_token = instrument.get("token")

        if inst_symbol.endswith("-EQ") and inst_token:
            _token_cache[inst_symbol.removesuffix("-EQ")] = inst_token

        if inst_name and inst_token:
            _token_cache.setdefault(inst_name, inst_token)

    _save_cache()
    return _token_cache.get(symbol)


if __name__ == "__main__":
    stock_symbols = ["ADANIGREEN", "ICICIBANK", "SBIN", "AXISBANK"]
    for stock_symbol in stock_symbols:
        token = get_symboltoken(stock_symbol)
        print(stock_symbol, token)
