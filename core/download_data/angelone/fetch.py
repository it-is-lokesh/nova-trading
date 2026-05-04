import http.client
import csv
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to sys.path to import confidential.env
PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

import confidential.env as env
from core.credentials import decrypt_env_credential
try:
    from .symbol_id import get_symboltoken
    from .get_authorization import get_fresh_token, update_env_file
except ImportError:
    from symbol_id import get_symboltoken
    from get_authorization import get_fresh_token, update_env_file


# Maximum number of days allowed per API call for each interval
INTERVAL_MAX_DAYS = {
    "ONE_MINUTE": 30,
    "THREE_MINUTE": 60,
    "FIVE_MINUTE": 100,
    "TEN_MINUTE": 100,
    "FIFTEEN_MINUTE": 200,
    "THIRTY_MINUTE": 200,
    "ONE_HOUR": 400,
    "ONE_DAY": 2000,
}

# Short labels for output directory naming
INTERVAL_DIR_NAME = {
    "ONE_MINUTE": "min1",
    "THREE_MINUTE": "min3",
    "FIVE_MINUTE": "min5",
    "TEN_MINUTE": "min10",
    "FIFTEEN_MINUTE": "min15",
    "THIRTY_MINUTE": "min30",
    "ONE_HOUR": "hour1",
    "ONE_DAY": "day1",
}

DATA_ROOT = PROJECT_ROOT / "cache"
DATE_FMT = "%Y-%m-%d %H:%M"
TOKEN_REFRESH_ERROR_CODES = {"AG8001", "AG8003"}


def credential(name):
    return decrypt_env_credential(env, name)


def refresh_jwt_token(reason):
    print(f"  JWT Token {reason}. Refreshing...")
    new_token = get_fresh_token()
    update_env_file(new_token)
    print("  Token refreshed.")
    return new_token


def get_jwt_token():
    jwt_token = credential("JWT_TOKEN")
    if jwt_token:
        return jwt_token
    return refresh_jwt_token("missing")


def make_headers():
    return {
        "X-PrivateKey": credential("API_KEY"),
        "Accept": "application/json",
        "X-SourceID": "WEB",
        "X-ClientLocalIP": credential("CLIENT_LOCAL_IP"),
        "X-ClientPublicIP": credential("CLIENT_PUBLIC_IP"),
        "X-MACAddress": credential("MAC_ADDRESS"),
        "X-UserType": "USER",
        "Authorization": f"Bearer {get_jwt_token()}",
        "Content-Type": "application/json",
    }


def fetch_chunk(exchange, symbol, interval, from_date, to_date, retry=True):
    """
    Fetches a single chunk of candle data from the SmartAPI.
    Returns a list of candle rows, or raises on failure.
    """
    try:
        conn = http.client.HTTPSConnection("apiconnect.angelone.in", timeout=30)
        payload = {
            "exchange": exchange,
            "symboltoken": get_symboltoken(symbol),
            "interval": interval,
            "fromdate": from_date,
            "todate": to_date,
        }

        conn.request(
            "POST",
            "/rest/secure/angelbroking/historical/v1/getCandleData",
            json.dumps(payload),
            make_headers(),
        )

        res = conn.getresponse()
        data = res.read()
        conn.close()
        response = json.loads(data.decode("utf-8"))
    except (OSError, TimeoutError, http.client.HTTPException) as e:
        raise RuntimeError(f"Network error: {e}")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid response from API: {e}")

    if not response.get("status"):
        error_code = response.get("errorCode", "")

        if error_code in TOKEN_REFRESH_ERROR_CODES and retry:
            try:
                reason = "expired" if error_code == "AG8001" else "missing"
                refresh_jwt_token(reason)
                print("  Retrying chunk...")
                return fetch_chunk(exchange, symbol, interval, from_date, to_date, retry=False)
            except Exception as e:
                raise RuntimeError(f"Failed to refresh token: {e}")

        raise RuntimeError(
            f"SmartAPI error: {response.get('message', 'Unknown')} "
            f"(code: {error_code})"
        )

    return response.get("data") or []


def _get_output_path(symbol, interval):
    """Returns the output CSV path for a given symbol and interval."""
    dir_name = INTERVAL_DIR_NAME[interval]
    output_dir = DATA_ROOT / dir_name
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / f"{symbol}.csv"


def _read_cached_data(csv_path):
    """
    Reads an existing CSV cache file and returns (rows, last_datetime).
    rows: list of [datetime, open, high, low, close, volume]
    last_datetime: datetime object of the last row, or None if empty.
    """
    if not csv_path.exists():
        return [], None

    rows = []
    last_dt = None
    try:
        with csv_path.open("r") as f:
            reader = csv.reader(f)
            header = next(reader, None)  # skip header
            for row in reader:
                if row:
                    rows.append(row)
        if rows:
            # The datetime column is the first field, e.g. "2024-10-07T09:15:00+05:30"
            last_dt_str = rows[-1][0]
            # Parse ISO format from SmartAPI (with timezone info)
            # Strip timezone suffix for parsing
            clean_dt = last_dt_str.split("+")[0].split("T")
            if len(clean_dt) == 2:
                last_dt = datetime.strptime(f"{clean_dt[0]} {clean_dt[1][:5]}", DATE_FMT)
    except (IOError, ValueError, IndexError):
        return [], None

    return rows, last_dt


def get_data(exchange, symbol, interval, from_date, to_date, verbose=True):
    """
    Downloads historical candle data in chunks and saves to CSV.
    Resumes from existing cache — only fetches data after the last
    cached timestamp.

    Args:
        exchange:   e.g. "NSE", "BSE", "NFO"
        symbol:     e.g. "SBIN", "RELIANCE"
        interval:   e.g. "ONE_MINUTE", "FIFTEEN_MINUTE", "ONE_DAY"
        from_date:  start date string "YYYY-MM-DD HH:MM"
        to_date:    end date string   "YYYY-MM-DD HH:MM"
        verbose:    If True, prints per-chunk progress logs.
                    If False, only prints the final summary line.
    """
    # Validate interval
    if interval not in INTERVAL_MAX_DAYS:
        raise ValueError(
            f"Unknown interval '{interval}'. "
            f"Valid options: {', '.join(INTERVAL_MAX_DAYS.keys())}"
        )

    end_dt = datetime.strptime(to_date, DATE_FMT)
    output_file = _get_output_path(symbol, interval)

    # ── Check existing cache ──
    cached_rows, last_cached_dt = _read_cached_data(output_file)

    if last_cached_dt and last_cached_dt >= end_dt:
        if verbose:
            print(f"{symbol}: already up to date ({len(cached_rows)} candles cached)")
        return cached_rows

    # Determine effective start date
    if last_cached_dt:
        # Start from 1 minute after the last cached candle
        effective_start = last_cached_dt + timedelta(minutes=1)
        effective_from = effective_start.strftime(DATE_FMT)
        if verbose:
            print(f"{symbol}: cache has data until {last_cached_dt.strftime(DATE_FMT)}, "
                  f"fetching remaining from {effective_from}")
    else:
        effective_from = from_date
        if verbose:
            print(f"{symbol}: no cache found, fetching from {from_date}")

    max_days = INTERVAL_MAX_DAYS[interval]
    start_dt = datetime.strptime(effective_from, DATE_FMT)

    if start_dt >= end_dt:
        if verbose:
            print(f"{symbol}: already up to date")
        return cached_rows

    # Split the remaining range into chunks
    total_days = (end_dt - start_dt).days
    chunks = []
    chunk_start = start_dt
    while chunk_start < end_dt:
        chunk_end = min(chunk_start + timedelta(days=max_days), end_dt)
        chunks.append((chunk_start, chunk_end))
        chunk_start = chunk_end + timedelta(seconds=1)

    num_chunks = len(chunks)
    if verbose:
        print(f"  Remaining: {total_days} days → {num_chunks} chunk(s)")

    new_candles = []
    empty_chunks = 0

    for i, (c_start, c_end) in enumerate(chunks, 1):
        c_start_str = c_start.strftime(DATE_FMT)
        c_end_str = c_end.strftime(DATE_FMT)
        if verbose:
            print(f"  [{i}/{num_chunks}] {c_start_str} → {c_end_str} ... ", end="", flush=True)

        try:
            candles = fetch_chunk(exchange, symbol, interval, c_start_str, c_end_str)
            if candles:
                new_candles.extend(candles)
                if verbose:
                    print(f"{len(candles)} candles")
            else:
                empty_chunks += 1
                if verbose:
                    print("0 candles (no data)")
        except RuntimeError as e:
            if verbose:
                print(f"FAILED: {e}")
            raise

        # Brief pause between API calls to avoid rate limiting
        if i < num_chunks:
            time.sleep(0.5)

    # Combine cached + new data
    all_candles = cached_rows + new_candles

    # Validate: error if nothing at all (no cache and no new data)
    if not all_candles:
        raise RuntimeError(
            f"No data returned for {symbol} ({interval}) across the entire "
            f"requested range ({from_date} to {to_date}). "
            f"The data may not be available this far back for this interval."
        )

    if empty_chunks > 0 and verbose:
        print(
            f"\n  WARNING: {empty_chunks}/{num_chunks} chunks returned no data. "
            f"Data may not be available for the full requested timeframe."
        )

    # Write combined CSV (cached + new)
    with output_file.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["datetime", "open", "high", "low", "close", "volume"])
        writer.writerows(all_candles)

    if verbose:
        new_count = len(new_candles)
        total_count = len(all_candles)
        if cached_rows:
            print(f"  +{new_count} new candles → {total_count} total in {output_file.name}")
        else:
            print(f"\nSaved {total_count} candles to {output_file}")
    return all_candles


def main():
    exchange = "NSE"
    symbol = "SBIN"
    interval = "FIFTEEN_MINUTE"
    from_date = "2016-04-01 09:15"
    to_date = "2026-04-23 15:30"

    try:
        get_data(exchange, symbol, interval, from_date, to_date)
    except (ValueError, RuntimeError) as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
