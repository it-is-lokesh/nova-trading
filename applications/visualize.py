import pandas as pd
import streamlit as st
import sys
import os

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from core.visualize import Process


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

    obj = Process(symbol)
    obj.update_data()
    obj.update_ema()
    obj.update_ssl_hybrid()
    obj.update_qqe_mod()
    obj.visualize()

if __name__ == "__main__":
    main()
