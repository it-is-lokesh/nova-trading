## Trading App

This repository contains necessary scripts to download historical price data of stocks and then use it for backtesting your custom algorithms.

### TODO
1. Add Kite and TradingView data fetch pipeline codes.

### Steps to use this repository

1. Install dependencies with `pip install -r requirements.txt`.
2. Copy `.credentials.example` to `.credentials` in the project root and fill the AngelOne fields:

```bash
API_KEY = "your_api_key"
CLIENT_CODE = "your_client_code"
CLIENT_PIN = "your_pin"
TOTP_CODE = ""
TOTP_SECRET = "your_totp_secret"
STATE_VARIABLE = "get_authorization"
JWT_TOKEN = ""
CLIENT_LOCAL_IP = "your_local_ip"
CLIENT_PUBLIC_IP = "your_public_ip"
MAC_ADDRESS = "your_mac_address"
```

3. Run `python applications/security.py`.
   - This creates or reuses `confidential/.key`.
   - This writes encrypted credential strings to `confidential/env.py`.
   - Keep `confidential/.key` private. If it is lost, the encrypted values in `confidential/env.py` cannot be decrypted.
4. You can clear `.credentials` after generating `confidential/env.py`, but do not rerun `applications/security.py` while `.credentials` is empty because it will overwrite the encrypted values with encrypted empty strings.
5. Run `python core/download_data/angelone/get_authorization.py` to generate and store an encrypted JWT token, or run `python applications/historical_data_fetch.py`; the fetch flow auto-refreshes missing or expired JWT tokens.
6. Run the data download scripts to download historical price data.

`confidential/env.py`, `confidential/.key`, and `.credentials` are ignored by git.


### Data Download Documentation

Folder structure:

```
core/
└── download_data/
    ├── angelone
    │   ├── fetch.py
    │   ├── get_authorization.py
    │   └── symbol_id.py
    ├── kite
    └── tradingview
```
