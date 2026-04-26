## AngelOne Data Module — API Documentation

This module handles authentication, symbol mapping, and historical data download from the AngelOne SmartAPI.

> **Note:** Requires credentials in `confidential/env.py`. See `confidential/env_example.py` for the template.

---

### Files Overview

| File | Purpose |
|---|---|
| `get_authorization.py` | TOTP generation, login, JWT token management |
| `symbol_id.py` | Maps stock symbols (e.g. `SBIN`) to AngelOne token IDs (e.g. `3045`) |
| `fetch.py` | Downloads historical candle data with chunked fetching |

---

### `get_authorization.py` — Authentication

Handles the full login lifecycle: TOTP generation → login → JWT token refresh.

#### Functions

*   `generate_totp()` → `str`
    - Generates a fresh 6-digit TOTP code using `TOTP_SECRET` from `env.py`.
    - Uses the `pyotp` library (RFC 6238 standard).
    - Raises `RuntimeError` if `TOTP_SECRET` is not set.

*   `ensure_credentials()`
    - Validates that `API_KEY`, `CLIENT_CODE`, `CLIENT_PIN`, and `TOTP_SECRET` are all set in `env.py`.
    - Raises `RuntimeError` listing any missing values.

*   `get_fresh_token()` → `str`
    - Performs a full login to AngelOne SmartAPI and returns a fresh JWT token.
    - Calls `generate_totp()` and `ensure_credentials()` internally.
    - Raises `RuntimeError` on login failure.

*   `update_env_file(new_jwt_token)`
    - Writes the new JWT token to `confidential/env.py` on disk (regex-based replacement).
    - Also updates `env.JWT_TOKEN` in memory so the current process uses it immediately.

#### Usage

```python
from get_authorization import get_fresh_token, update_env_file

token = get_fresh_token()    # Logs in, returns JWT
update_env_file(token)       # Saves to env.py
```

---

### `symbol_id.py` — Symbol Token Mapping

Maps human-readable stock symbols to AngelOne's internal numeric token IDs.

#### Functions

*   `get_symboltoken(symbol)` → `str | None`
    - Returns the AngelOne token ID for a given stock symbol.
    - **Lookup order:** memory cache → file cache (`cache/symbol_tokens.json`) → AngelOne Scrip Master API.
    - On first miss, downloads the full Scrip Master (~200K+ instruments) and caches all NSE equity tokens locally.
    - Returns `None` if the symbol is not found even after fetching.

#### Cache Behavior

| Layer | Location | Lifetime |
|---|---|---|
| Memory | `_token_cache` dict | Current process only |
| File | `cache/symbol_tokens.json` | Persistent (grows over time) |

#### Usage

```python
from symbol_id import get_symboltoken

token = get_symboltoken("SBIN")       # "3045"
token = get_symboltoken("RELIANCE")   # "2885"
```

---

### `fetch.py` — Historical Data Download

Downloads OHLCV candle data from the AngelOne SmartAPI with automatic chunking.

#### Functions

*   `fetch_chunk(exchange, symbol, interval, from_date, to_date)` → `list`
    - Fetches a single chunk of candle data (within SmartAPI limits).
    - Auto-refreshes the JWT token on `AG8001` (Invalid Token) errors.
    - Returns a list of `[datetime, open, high, low, close, volume]` rows.

*   `get_data(exchange, symbol, interval, from_date, to_date)` → `list`
    - **Main function.** Downloads data across any date range by splitting into chunks.
    - Saves the combined result as a CSV to `data/<interval>/SYMBOL.csv`.
    - Raises `RuntimeError` if no data is available for the requested range.
    - Prints progress: `[1/10] 2020-04-23 → 2020-11-09 ... 3476 candles`

#### Parameters

| Parameter | Type | Example | Description |
|---|---|---|---|
| `exchange` | `str` | `"NSE"` | Exchange segment |
| `symbol` | `str` | `"SBIN"` | Stock symbol |
| `interval` | `str` | `"FIFTEEN_MINUTE"` | Candle interval (see table below) |
| `from_date` | `str` | `"2020-04-23 09:15"` | Start date (`YYYY-MM-DD HH:MM`) |
| `to_date` | `str` | `"2025-04-23 15:30"` | End date (`YYYY-MM-DD HH:MM`) |

#### Supported Intervals & Chunk Limits

| Interval | Max Days/Request | Output Directory |
|---|---|---|
| `ONE_MINUTE` | 30 | `data/min1/` |
| `THREE_MINUTE` | 60 | `data/min3/` |
| `FIVE_MINUTE` | 100 | `data/min5/` |
| `TEN_MINUTE` | 100 | `data/min10/` |
| `FIFTEEN_MINUTE` | 200 | `data/min15/` |
| `THIRTY_MINUTE` | 200 | `data/min30/` |
| `ONE_HOUR` | 400 | `data/hour1/` |
| `ONE_DAY` | 2000 | `data/day1/` |

#### Output CSV Format

```
datetime,open,high,low,close,volume
2024-10-07T09:15:00+05:30,799.95,804.0,798.1,799.55,884521
2024-10-07T09:30:00+05:30,799.4,800.0,796.65,797.65,416034
```

#### Usage

```python
from fetch import get_data

# Fetch 5 years of 15-minute data for SBIN
get_data("NSE", "SBIN", "FIFTEEN_MINUTE", "2020-04-23 09:15", "2025-04-23 15:30")
# → Saved 30913 total candles to data/min15/SBIN.csv

# Fetch daily data
get_data("NSE", "RELIANCE", "ONE_DAY", "2015-01-01 09:15", "2025-04-23 15:30")
```

#### Error Handling

| Scenario | Behavior |
|---|---|
| JWT token expired | Auto-refreshes via `get_fresh_token()` and retries |
| No data for entire range | Raises `RuntimeError` |
| Some chunks empty | Prints warning, saves available data |
| Invalid interval | Raises `ValueError` with valid options |
