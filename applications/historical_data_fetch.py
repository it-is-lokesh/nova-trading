"""
Historical Data Fetch — Downloads 15-minute OHLCV data for all Nifty 200 stocks.

Features:
    - Resumes from existing cache (only downloads missing data)
    - Automatically retries failed stocks (up to MAX_RETRIES times)
    - Uses tqdm for progress tracking
    - Verbose mode can be toggled per run

Usage:
    python3 applications/historical_data_fetch.py
"""
import sys
import time
from pathlib import Path

# Add project root and angelone module to sys.path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "download_data" / "angelone"))

from tqdm import tqdm
from core.utils import get_nifty200_symbols
from fetch import get_data


# ── Configuration ──────────────────────────────────────────────
EXCHANGE = "NSE"
INTERVAL = "FIFTEEN_MINUTE"
FROM_DATE = "2016-04-01 09:15"
TO_DATE = "2026-04-24 15:30"

MAX_RETRIES = 3          # Number of retry passes for failed stocks
RETRY_DELAY = 5          # Seconds to wait before each retry pass
VERBOSE = False          # Set True to see per-chunk logs
# ───────────────────────────────────────────────────────────────


def fetch_all(symbols, all_success, verbose=False):
    """
    Attempts to download data for a list of symbols.
    Appends successful symbols to all_success in-place.
    Returns the list of (symbol, error) for failures.
    """
    failed = []
    interrupted = False

    pbar = tqdm(symbols, desc="Downloading", unit="stock", leave=True)
    try:
        for symbol in pbar:
            try:
                get_data(EXCHANGE, symbol, INTERVAL, FROM_DATE, TO_DATE, verbose=verbose)
                all_success.append(symbol)
            except KeyboardInterrupt:
                tqdm.write(f"\n⚠ Interrupted during {symbol}. Stopping...")
                interrupted = True
                break
            except Exception as e:
                tqdm.write(f"  ✗ {symbol}: {e}")
                failed.append((symbol, str(e)))
    finally:
        pbar.close()

    return failed, interrupted


def main():
    print("=" * 60)
    print("  Historical Data Fetch — Nifty 200 (15-min)")
    print(f"  Range: {FROM_DATE}  →  {TO_DATE}")
    print(f"  Max retries: {MAX_RETRIES}")
    print("=" * 60)

    symbols = get_nifty200_symbols()
    total = len(symbols)
    print(f"\nDownloading {INTERVAL} data for {total} stocks...\n")

    all_success = []
    all_failed = []

    # ── Pass 1: Initial fetch ──
    all_failed, interrupted = fetch_all(symbols, all_success, verbose=VERBOSE)

    # ── Retry passes ──
    if not interrupted:
        for attempt in range(1, MAX_RETRIES + 1):
            if not all_failed:
                break

            retry_symbols = [sym for sym, _ in all_failed]
            print(f"\n{'─' * 60}")
            print(f"  Retry {attempt}/{MAX_RETRIES}: {len(retry_symbols)} stocks to revisit")
            print(f"  Waiting {RETRY_DELAY}s before retrying...")
            print(f"{'─' * 60}\n")
            time.sleep(RETRY_DELAY)

            all_failed, interrupted = fetch_all(retry_symbols, all_success, verbose=VERBOSE)
            if interrupted:
                break

    # ── Final summary ──
    print("\n" + "=" * 60)
    print(f"  Results: {len(all_success)}/{total} stocks downloaded")
    if all_failed:
        print(f"  Still failed: {len(all_failed)}")
        for sym, err in all_failed:
            print(f"    • {sym}: {err}")
    elif not interrupted:
        print("  All stocks downloaded successfully! ✓")
    if interrupted:
        print("  (Run interrupted — resume anytime, cached data will be preserved)")
    print("=" * 60)


if __name__ == "__main__":
    main()
