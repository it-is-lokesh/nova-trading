# Database Setup & Usage

## Overview
This directory contains scripts to import 15-minute candle data from CSV files into a SQLite database. The database (`nifty200_15min.db`) is **not included** in the repository due to its large size (~2GB).

## ⚠️ Important: Database File Not in Repository

The `nifty200_15min.db` file is **2GB** and cannot be pushed to GitHub. You must **generate it locally** by running the setup script.

## Quick Start

### Step 1: Ensure CSV Data is Available
Verify that the min15 CSV files exist in:
```
nova-trading/cache/min15/
```

Expected structure:
```
cache/
└── min15/
    ├── ADANIENT.csv
    ├── RELIANCE.csv
    ├── INFY.csv
    └── ... (200+ symbols)
```

### Step 2: Generate the Database
Run the importer script from this directory:
```bash
python csv_to_db.py
```

**What it does:**
- Scans all CSV files in `../cache/min15/`
- Creates a new SQLite database: `nifty200_15min.db`
- Imports all 15-minute candle data into a single table
- Normalizes datetime and data formats
- Shows progress and final statistics

**Output:**
```
Imported 200 symbols
Total rows: 4,521,843
Time taken: ~1-2 minutes (depending on system)
```

### Step 3: Test the Database
Verify the database works correctly:
```bash
python query_examples.py
```

**Output shows:**
- Total number of candles
- Unique symbols in database
- Date range of data
- Sample queries for specific stocks

## Files Description

| File | Purpose |
|------|---------|
| `csv_to_db.py` | **Main script** - Imports CSV files into SQLite |
| `query_examples.py` | Test/demo script - Shows how to query the database |
| `README.md` | This file |

## Configuration

### csv_to_db.py
Edit these lines if your paths differ:
```python
CSV_DIR = r"../cache/min15"      # Path to CSV folder
DB_PATH = "nifty200_15min.db"    # Output database filename
```

### query_examples.py
Edit this line if you rename the database:
```python
DB_PATH = "nifty200_15min.db"
```

## Database Schema

**Table: `candles`**
```sql
CREATE TABLE candles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    datetime TEXT NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume INTEGER,
    UNIQUE(symbol, datetime)
);
```

## Usage Examples

### Query single stock data
```python
import sqlite3

conn = sqlite3.connect('nifty200_15min.db')
cursor = conn.cursor()

cursor.execute("""
    SELECT datetime, open, close, volume
    FROM candles
    WHERE symbol = 'RELIANCE'
    LIMIT 10
""")
for row in cursor.fetchall():
    print(row)
```

### Get all symbols
```python
cursor.execute("SELECT DISTINCT symbol FROM candles ORDER BY symbol")
symbols = [row[0] for row in cursor.fetchall()]
print(symbols)
```

### Date range query
```python
cursor.execute("""
    SELECT MIN(datetime), MAX(datetime)
    FROM candles
    WHERE symbol = 'INFY'
""")
min_date, max_date = cursor.fetchone()
print(f"INFY data: {min_date} to {max_date}")
```

## Troubleshooting

### "CSV files not found"
- Verify `CSV_DIR` path is correct
- Check that CSV files exist in `nova-trading/cache/min15/`

### Database file is slow to create
- This is normal for 4M+ rows
- Allow 5-15 minutes depending on disk speed
- No need to interrupt the process

### "Database is locked" error
- Close any other programs accessing the database
- Restart Python interpreter
- Delete `nifty200_15min.db` and regenerate

### Import completes but no data
- Verify CSV file format is correct (datetime, open, high, low, close, volume)
- Check that `symbol` names match filename

## For Collaborators

1. Clone the repository
2. Ensure you have Python 3.6+ with `sqlite3` (built-in)
3. Run `python csv_to_db.py` to generate the local database
4. Use `query_examples.py` as a reference for queries

The database is **auto-generated locally** — no download needed.

## Git Configuration

The `nifty200_15min.db` file is likely in `.gitignore` to prevent accidental commits. If you need to share database dumps, consider:
- Exporting specific symbol data as CSV
- Using compressed database backups
- Sharing via cloud storage (Dropbox, Google Drive, etc.)

---

**Last Updated:** 2026-05-18  
**Branch:** `nitish_exp_db`
