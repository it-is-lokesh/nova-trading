import os
import io
from tqdm import tqdm
import yfinance as yf
import pandas as pd
import streamlit as st
from streamlit_lightweight_charts import renderLightweightCharts
from datetime import datetime, timedelta
import numpy as np
import sys
import os

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if base_dir not in sys.path:
    sys.path.append(base_dir)

from core.algorithms.ssl_hybrid import ssl_hybrid_core
from core.algorithms.qqe_mod import qqe_mod_core
from core.algorithms.moving_averages import ema

class Process:
    def __init__(self, symbol):
        self.symbol = symbol
        self.data = None

        self.ema20_series = None
        self.ema50_series = None
        self.pivot_series = None
        self.ssl_baseline_series = None
        self.moving_avg_high_series = None
        self.moving_avg_low_series = None
        self.upper_atr_band_series = None
        self.lower_atr_band_series = None
        self.mid_atr_band_series = None
        self.moving_avg_band_area_series = None
        self.hist_series = None
        self.qqe_series = None

    def update_data(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        df = pd.read_csv(os.path.join(base_dir, "cache", "min15", f"{self.symbol}.csv"), parse_dates=True)
        df['datetime'] = pd.to_datetime(df['datetime'])

        # convert to unix seconds
        df['time'] = (df['datetime'].astype('int64') // 10**9).astype(int)

        # drop duplicate times to avoid lightweight-charts rendering failure
        df.drop_duplicates(subset=['time'], keep='last', inplace=True)

        self.data = df
        self.x_dates = df['time'].tolist()
    
    def update_ema(self):
        self.data['ema_9'] = ema(self.data['close'], 9)
        self.data['ema_20'] = ema(self.data['close'], 20)
        self.data['ema_50'] = ema(self.data['close'], 50)
        self.data['ema_200'] = ema(self.data['close'], 200)

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        archive_dir = os.path.join(base_dir, "cache", "ema")
        os.makedirs(archive_dir, exist_ok=True)
        np.savez(os.path.join(archive_dir, f"{self.symbol}.npz"), ema_9=self.data['ema_9'], ema_20=self.data['ema_20'], ema_50=self.data['ema_50'], ema_200=self.data['ema_200'])

        self.ema20_series = [{"time": dt, "value": round(v,2)} for dt,v in zip(self.x_dates, self.data['ema_20'])]
        self.ema50_series = [{"time": dt, "value": round(v,2)} for dt,v in zip(self.x_dates, self.data['ema_50'])]

    def update_ssl_hybrid(self):
        self.ssl_df: pd.DataFrame = ssl_hybrid_core(self.data)
        self.ssl_df.to_csv('hindistan unilever.csv')

    def update_qqe_mod(self):
        self.qqe_df = qqe_mod_core(self.data)
    
    def get_series(self, column: pd.Series, color=None):
        series = []
        for dt, v in zip(self.x_dates, column):
            if pd.notna(v):
                item = {"time": dt, "value": round(float(v), 2)}
                if color is not None:
                    item["color"] = color
                series.append(item)
        return series

    def visualize(self):

        candles = [
            dict(
                time=dt,
                open=round(o, 2),
                high=round(h, 2),
                low=round(l, 2),
                close=round(c, 2),
                # color="blue" if c >= o else "red"
            )
            for dt, o, h, l, c in zip(
                # self.x_dates, self.data["Open"], self.data["high"], self.data["low"], self.data["close"]
                self.x_dates,
                self.data["open"],
                self.data["high"],
                self.data["low"],
                self.data["close"]
            )
            if pd.notna(o) and pd.notna(h) and pd.notna(l) and pd.notna(c)
        ]

        # Chart configuration
        chart_options = {
            "height": 500,
            "width": 1500,
            "layout": {
                "background": {"color": "#ffffff"},
                "textColor": "#333",
            },
            "grid": {
                "vertLines": {"color": "#eee"},
                "horzLines": {"color": "#eee"},
            },
            "crosshair": {"mode": 0},
            "timeScale": {
                "timeVisible": True, 
                "secondsVisible": False,
                "rightOffset": 0,  # align last candle to right
                "barSpacing": 30,   # adjust zoom
            },
        }

        print(self.data.columns)

        markers = []
        for index, row in self.ssl_df.iterrows():
            if row['base_cross_long'] is True:
                markers.append({
                    "time": row['time'],
                    "position": 'belowBar',
                    "color": 'blue',
                    'shape': 'arrowUp',
                    "size": 1
                })
            elif row['base_cross_short'] is True:
                markers.append({
                    "time": row['time'],
                    "position": 'aboveBar',
                    "color": 'red',
                    'shape': 'arrowDown',
                    "size": 1
                })

        BBMC = self.get_series(self.ssl_df['BBMC'])
        upperk = self.get_series(self.ssl_df['upperk'])
        lowerk = self.get_series(self.ssl_df['lowerk'])
        base_cross_long = self.get_series(self.ssl_df['base_cross_short'])
        ssl1 = self.get_series(self.ssl_df['ssl1'])
        sslDown2 = self.get_series(self.ssl_df['ssl2'])
        upper_band = self.get_series(self.ssl_df['upper_band'])

        ssl_down_markers = []
        for point in sslDown2:
            ssl_down_markers.append({
                "time": point["time"],
                "position": "belowBar",  # or 'aboveBar' / 'inBar' if you prefer
                "color": "purple",
                "shape": "circle",
                "text": "",  # optional label next to the dot
            })

        series = [
            {"type": "Candlestick", "data": candles, "markers": markers},
            # {"type": "Line", "data": lowerk, "options": {"color": "blue", "lineWidth": 1}},
            # {"type": "Line", "data": upperk, "options": {"color": "red", "lineWidth": 1}},
            # {"type": "Line", "data": BBMC, "options": {"color": "red", "lineWidth": 2}},
            # {"type": "Line", "data": ssl1, "options": {"color": "red", "lineWidth": 2}},
            # {"type": "Line", "data": sslDown2, "options": {"color": "pink", "lineWidth": 1}},
            
        ]

        chart_options_qqe_mod = {
            "height": 200,
            "width": 1500,
            "layout": {
                "background": {"color": "#ffffff"},
                "textColor": "#333",
            },
            "grid": {
                "vertLines": {"color": "#eee"},
                "horzLines": {"color": "#eee"},
            },
            "crosshair": {"mode": 0},
            "timeScale": {"timeVisible": True, "secondsVisible": False},
        }

        hist_series_up = self.get_series(self.qqe_df['qqe_up_signal'], color="green")
        hist_series_down = self.get_series(self.qqe_df['qqe_down_signal'], color="red")

        series_qqe_mod = [
            {"type":"Histogram", "data": hist_series_up},
            {"type":"Histogram", "data": hist_series_down},

        ]

        # print(self.qqe_df['qqe_up_signal'])

        # st.write("Candles sample:", candles[:5])
        # st.write("Total candles:", len(candles))

        renderLightweightCharts([{"chart": chart_options, "series": series}, {"chart": chart_options_qqe_mod, "series": series_qqe_mod}], key="chart")


