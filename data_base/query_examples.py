"""
Example Queries for nifty200_15min.db
=====================================
Run this after csv_to_db.py to test your database.

Usage: python query_examples.py
"""

import sqlite3

DB_PATH = "nifty200_15min.db"
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()


# --- 1. Basic stats ---
print("=" * 50)
print("DATABASE OVERVIEW")
print("=" * 50)

cursor.execute("SELECT COUNT(*) FROM candles")
print(f"Total rows: {cursor.fetchone()[0]:,}")

cursor.execute("SELECT COUNT(DISTINCT symbol) FROM candles")
print(f"Unique stocks: {cursor.fetchone()[0]}")

cursor.execute("SELECT MIN(datetime), MAX(datetime) FROM candles")
mn, mx = cursor.fetchone()
print(f"Date range: {mn} to {mx}")


# --- 2. List all symbols ---
print("\n" + "=" * 50)
print("ALL SYMBOLS")
print("=" * 50)

cursor.execute("SELECT DISTINCT symbol FROM candles ORDER BY symbol")
symbols = [row[0] for row in cursor.fetchall()]
print(", ".join(symbols))


# --- 3. Get candles for a specific stock and date ---
print("\n" + "=" * 50)
print("SAMPLE: First 5 candles of ADANIENT")
print("=" * 50)

cursor.execute("""
    SELECT datetime, open, high, low, close, volume
    FROM candles
    WHERE symbol = 'ADANIENT'
    ORDER BY datetime
    LIMIT 5
""")
for row in cursor.fetchall():
    print(f"  {row[0]}  O:{row[1]:>10.2f}  H:{row[2]:>10.2f}  L:{row[3]:>10.2f}  C:{row[4]:>10.2f}  V:{row[5]:>10,}")


# --- 4. Top volume candles across all stocks on a date ---
print("\n" + "=" * 50)
print("TOP 5 VOLUME CANDLES (latest date in DB)")
print("=" * 50)

cursor.execute("SELECT MAX(substr(datetime, 1, 10)) FROM candles")
latest_date = cursor.fetchone()[0]

cursor.execute("""
    SELECT symbol, datetime, close, volume
    FROM candles
    WHERE datetime LIKE ?
    ORDER BY volume DESC
    LIMIT 5
""", (f"{latest_date}%",))
for row in cursor.fetchall():
    print(f"  {row[0]:<15s}  {row[1]}  Close:{row[2]:>10.2f}  Vol:{row[3]:>12,}")


# --- 5. Daily OHLCV aggregation from 15-min candles ---
print("\n" + "=" * 50)
print("DAILY OHLCV (last 5 days of RELIANCE)")
print("=" * 50)

cursor.execute("""
    SELECT
        substr(datetime, 1, 10) as date,
        -- First candle's open (9:15 candle)
        (SELECT c2.open FROM candles c2 
         WHERE c2.symbol = c.symbol 
           AND substr(c2.datetime, 1, 10) = substr(c.datetime, 1, 10)
         ORDER BY c2.datetime ASC LIMIT 1) as day_open,
        MAX(high) as day_high,
        MIN(low) as day_low,
        -- Last candle's close (3:15 candle)
        (SELECT c3.close FROM candles c3 
         WHERE c3.symbol = c.symbol 
           AND substr(c3.datetime, 1, 10) = substr(c.datetime, 1, 10)
         ORDER BY c3.datetime DESC LIMIT 1) as day_close,
        SUM(volume) as day_volume
    FROM candles c
    WHERE symbol = 'RELIANCE'
    GROUP BY symbol, substr(datetime, 1, 10)
    ORDER BY date DESC
    LIMIT 5
""")
for row in cursor.fetchall():
    print(f"  {row[0]}  O:{row[1]:>10.2f}  H:{row[2]:>10.2f}  L:{row[3]:>10.2f}  C:{row[4]:>10.2f}  V:{row[5]:>12,}")


# --- 6. Using with pandas ---
print("\n" + "=" * 50)
print("PANDAS INTEGRATION")
print("=" * 50)

try:
    import pandas as pd
    df = pd.read_sql_query("""
        SELECT * FROM candles 
        WHERE symbol = 'TCS' 
        ORDER BY datetime DESC
        LIMIT 5
    """, conn)
    print(df.to_string(index=False))
except ImportError:
    print("  (install pandas to use: pip install pandas)")


conn.close()
print("\nDone!")
