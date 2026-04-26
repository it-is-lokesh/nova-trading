## Trading App

This repository contains necessary scripts to download historical price data of stocks and then use it for backtesting your custom algorithms.

### TODO
1. Add Kite and TradingView data fetch pipeline codes.

### Steps to use this repository

1. First get API key, client code, client pin, totp code, state variable, client local IP, client public IP and MAC address from AngelOne platform.
2. Get the JWT token from AngelOne platform by running the get_authorization.py script.
3. Then create a ./confidential/env.py file and paste the credentials in it. Refer to ./confidential/env_example.py for the structure of the file.
4. Then run the download_data.py script to download the historical price data of stocks.


### Data Download Documentation

Folder structure:

```
download_data/
├── angelone
│   ├── fetch.py
│   ├── get_authorization.py
│   └── symbol_id.py
├── kite
└── tradingview
```

