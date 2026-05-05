import pandas as pd
import streamlit as st
from streamlit_lightweight_charts import renderLightweightCharts
import sys
import os

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from core.algorithms.ssl_hybrid.visualize import SSLHybridVisualizer
from core.algorithms.qqe_mod.visualize import QQEModVisualizer


def main():
    BANKS = ["HDFCBANK", "ICICIBANK", "SBIN", "AXISBANK", "KOTAKBANK", "INDUSINDBK", "PNB", "BANKBARODA"]
    IT = ["INFY", "TCS", "HCLTECH", "TECHM", "LTIM", "PERSISTENT", "TATAELXSI", "TATATECH"] # "WIPRO"
    PHARMA = ["SUNPHARMA", "DRREDDY", "CIPLA", "DIVISLAB", "AUROPHARMA", "BIOCON", "LUPIN", "BROOKS"]
    FMCG = ["HINDUNILVR", "NESTLEIND", "ITC", "DABUR", "BRITANNIA", "GODREJCP", "MARICO", "COLPAL", "TATACONSUM"]
    AUTO = ["TATAMOTORS", "M&M", "MARUTI", "EICHERMOT", "HEROMOTOCO", "BAJAJ-AUTO", "TVSMOTOR"]
    METALS_MINING = ["TATASTEEL", "JSWSTEEL", "HINDALCO", "JINDALSTEL", "NMDC", "NATIONALUM", "SAIL", "ADANIENT", "TATACHEM", "TATAGOLD"]
    ENERGY = ["RELIANCE", "ONGC", "IOC", "BPCL", "HINDPETRO", "GAIL", "POWERGRID", "NTPC", "ADANIENSOL", "ADANIGREEN", "ADANIPOWER", "TATAPOWER"]
    CONSTRUCTION = ["ADANIPORTS", "DLF", "GODREJPROP", "OBEROIRLTY", "CONCOR", "NBCC"] # "L&T"
    TELECOM = ["BHARTIARTL", "IDEA", "SUNTV", "DISHTV", "TATACOMM"] # "RELCOM", "ZEEL"
    ELECTRONICS = ["BHEL"]
    DEFENCE = ["HAL", "BDL", "PARAS"]

    symbol = 'BANKBARODA'

    st.set_page_config(layout="wide")
    # st.title("📈 TradingView-style Chart in Streamlit")

    # ticker = st.sidebar.text_input("Enter Stock Ticker (NSE/BSE)", f"{symbol}.NS")
    # start_date = st.sidebar.date_input("Start Date", value=pd.to_datetime("2025-08-01"))
    # end_date = st.sidebar.date_input("End Date", value=pd.to_datetime("2025-09-28"))

    # --- SSL Hybrid (overlay on candlestick chart) ---
    ssl_viz = SSLHybridVisualizer(symbol)
    ssl_viz.update_data()
    ssl_viz.compute()

    # --- QQE Mod (separate panel below) ---
    qqe_viz = QQEModVisualizer(symbol)
    qqe_viz.update_data(show_caption=False)
    qqe_viz.compute()

    # Compose both charts: SSL overlay first, QQE panel below
    all_charts = ssl_viz.get_chart_data() + qqe_viz.get_chart_data()
    chart_key = f"chart-{symbol}-{ssl_viz.x_dates[0]}-{ssl_viz.x_dates[-1]}-{len(ssl_viz.x_dates)}"
    renderLightweightCharts(all_charts, key=chart_key)

if __name__ == "__main__":
    main()
