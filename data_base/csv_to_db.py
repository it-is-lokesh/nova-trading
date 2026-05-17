"""
CSV to SQLite Importer
======================
Imports all 15-min candle CSVs from a folder into a single SQLite database.

Usage:
    1. Edit CSV_DIR below to point to your min15 folder
    2. Run: python csv_to_db.py
    3. Output: nifty200_15min.db in the same directory as this script
"""

import sqlite3
import csv
import os
import glob
import time

# ============ CONFIGURATION (edit this) ============
CSV_DIR = r"../cache/min15"  # path to your min15 folder
DB_PATH = "nifty200_15min.db"          # output database file
# ===================================================


def get_symbol(filepath):
    """Extract symbol from filename: /path/to/RELIANCE.csv -> RELIANCE"""
    return os.path.splitext(os.path.basename(filepath))[0].upper()


def clean_datetime(dt_string):
    """
    Normalize datetime to consistent format without timezone.
    '2019-09-19T09:30:00+05:30' -> '2019-09-19 09:30:00'
    All your data is IST anyway, so we strip the offset for cleaner queries.
    """
    # Split off the timezone part (+05:30)
    if "+" in dt_string:
        dt_string = dt_string.split("+")[0]
    elif dt_string.count("-") > 2:
        # Handle negative UTC offsets if any (unlikely for IST)
        pass
    return dt_string.replace("T", " ")


def main():
    start_time = time.time()

    # --- Step 1: Create database and table ---
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Enable WAL mode for better performance during bulk inserts
    cursor.execute("PRAGMA journal_mode=WAL")
    # Reduce fsync calls during import (safe for bulk loading)
    cursor.execute("PRAGMA synchronous=OFF")
    # Use more memory for faster imports
    cursor.execute("PRAGMA cache_size=-64000")  # 64MB cache

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS candles (
            symbol      TEXT    NOT NULL,
            datetime    TEXT    NOT NULL,
            open        REAL    NOT NULL,
            high        REAL    NOT NULL,
            low         REAL    NOT NULL,
            close       REAL    NOT NULL,
            volume      INTEGER NOT NULL,
            PRIMARY KEY (symbol, datetime)
        )
    """)
    conn.commit()

    # --- Step 2: Find all CSV files ---
    # check to ensure the directory exists and contains CSV files
    if not os.path.exists(CSV_DIR):
        print(f"ERROR: Directory '{CSV_DIR}' does not exist.")
        print(f"  Please check the path and try again.")
        conn.close()
        return
    csv_files = sorted(glob.glob(os.path.join(CSV_DIR, "*.csv")))
    total_files = len(csv_files)

    if total_files == 0:
        print(f"ERROR: No CSV files found in '{CSV_DIR}'")
        print(f"  Resolved path: {os.path.abspath(CSV_DIR)}")
        print(f"  Make sure the path is correct.")
        conn.close()
        return

    print(f"Found {total_files} CSV files in {os.path.abspath(CSV_DIR)}")
    print(f"Database: {os.path.abspath(DB_PATH)}")
    print("-" * 60)

    # --- Step 3: Import each CSV ---
    total_rows = 0
    errors = []

    for i, filepath in enumerate(csv_files, 1):
        symbol = get_symbol(filepath)
        file_rows = 0

        try:
            with open(filepath, "r") as f:
                reader = csv.DictReader(f)
                batch = []

                for row in reader:
                    batch.append((
                        symbol,
                        clean_datetime(row["datetime"]),
                        float(row["open"]),
                        float(row["high"]),
                        float(row["low"]),
                        float(row["close"]),
                        int(row["volume"]),
                    ))

                # Bulk insert entire file at once
                cursor.executemany(
                    "INSERT OR REPLACE INTO candles VALUES (?, ?, ?, ?, ?, ?, ?)",
                    batch
                )
                file_rows = len(batch)
                total_rows += file_rows

            print(f"  [{i:3d}/{total_files}]  {symbol:<20s}  {file_rows:>8,} rows")

        except Exception as e:
            errors.append((symbol, str(e)))
            print(f"  [{i:3d}/{total_files}]  {symbol:<20s}  ERROR: {e}")

    conn.commit()

    # --- Step 4: Create indexes ---
    print("-" * 60)
    print("Creating indexes (this may take a minute)...")

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_symbol ON candles(symbol)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_datetime ON candles(datetime)")
    # Composite index — most useful for typical queries
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sym_dt ON candles(symbol, datetime)")

    conn.commit()

    # --- Step 5: Reset PRAGMAs to safe defaults ---
    cursor.execute("PRAGMA synchronous=NORMAL")

    # --- Step 6: Summary ---
    cursor.execute("SELECT COUNT(DISTINCT symbol) FROM candles")
    unique_symbols = cursor.fetchone()[0]

    cursor.execute("SELECT MIN(datetime), MAX(datetime) FROM candles")
    min_dt, max_dt = cursor.fetchone()

    conn.close()

    elapsed = time.time() - start_time
    db_size_mb = os.path.getsize(DB_PATH) / (1024 * 1024)

    print("-" * 60)
    print(f"  DONE!")
    print(f"  Total rows   : {total_rows:,}")
    print(f"  Unique stocks : {unique_symbols}")
    print(f"  Date range    : {min_dt}  to  {max_dt}")
    print(f"  Database size : {db_size_mb:.1f} MB")
    print(f"  Time taken    : {elapsed:.1f} seconds")

    if errors:
        print(f"\n  {len(errors)} files had errors:")
        for sym, err in errors:
            print(f"    {sym}: {err}")

    print(f"\n  Your database is ready at: {os.path.abspath(DB_PATH)}")


if __name__ == "__main__":
    main()
