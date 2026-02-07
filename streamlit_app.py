import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 頁面基本設定
st.set_page_config(page_title="Sniper X V106", layout="wide")

# 移植大師參數
MASTER_PARAMS = {'2330': 17, '2317': 18, '2303': 21, '2454': 29, '2603': 35}

st.title("🚀 Sniper X 戰情室 V106")

# --- 側邊欄控制 ---
st.sidebar.header("控制面板")
stock_id = st.sidebar.text_input("輸入股票代號", value="2330").upper().strip()

range_options = {"3個月": 60, "半年": 120, "1年": 240}
selected_range = st.sidebar.selectbox("顯示時間區間", list(range_options.keys()), index=1)
days_to_show = range_options[selected_range]

# 讓使用者在手機橫屏時可調大高度
chart_height = st.sidebar.slider("調整圖表高度", 300, 800, 500, 50)

def get_data_with_fallback(sid):
    ticker_tw = f"{sid}.TW"
    df = yf.download(ticker_tw, period="2y", progress=False)
    if df.empty:
        ticker_two = f"{sid}.TWO"
        df = yf.download(ticker_two, period="2y", progress=False)
        return df, ticker_two
    return df, ticker_tw

if stock_id:
    with st.spinner('數據計算中...'):
        df, final_ticker = get_data_with_fallback(stock_id)
        
        if not df.empty:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
                
            # 計算均線
            ma_days = MASTER_PARAMS.get(stock_id, 20)
            df['MA'] = df['Close'].rolling(window=ma_days).mean()
            
            # 準備繪圖數據
            plot_df = df.tail(days_to_show).copy()
            
            # --- 核心：建立上下分離子圖 ---
            # row_width 設定比例：[0.3, 0.7] 表示下方佔30%，上方佔70%
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                                vertical_spacing=0.05, 
                                row_width=[0.3, 0.7])

            # 1. 上方圖層：收盤價
            fig.add_trace(go.Scatter(
                x=plot_df.index, y=plot_df['Close'], name='收盤價',
                line=dict(color='#1f77b4', width=2),
                hovertemplate='價格: %{y:.1f}'
            ), row=1, col=1)
            
            # 2. 上方圖層：大師均線
            fig.add_trace(go.Scatter(
                x=plot_df.index, y=plot_df['MA'], name=f'{ma_days}MA',
                line=dict(color='#ff7f0e', width=2, dash='dash'),
                hovertemplate='均線: %{y:.1f}'
            ), row=1, col=1)

            # 3. 下方圖層：成交量 (使用長條圖)
            # 根據漲跌自動著色 (漲紅跌綠)
            colors = ['#ef5350' if c >= o else '#26a69a' 
                      for c, o in zip(plot_df['Close'], plot_df['Open'])]
            
            fig.add_trace(go.Bar(
                x=plot_df.index, y=plot_df['Volume'], name='成交量',
                marker_color=colors, opacity=0.8,
                hovertemplate='量: %{y:,.0f}'
            ), row=2, col=1)

            # 圖表佈局優化
            fig.update_layout(
                title=f"{stock_id} ({final_ticker}) 戰情分析",
                template="plotly_white",
                height=chart_height,
                margin=dict(l=5, r=5, t=50, b=5),
                hovermode="x unified",
                dragmode=False,
                showlegend=False # 手機空間有限，隱藏圖例
            )

            # 座標軸設定
            fig.update_yaxes(title_text="價格", side="right", row=1, col=1, fixedrange=True)
            fig.update_yaxes(title_text="量", side="right", row=2, col=1, fixedrange=True)
            fig.update_xaxes(fixedrange=True, nticks=6)

            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            
            # 下方顯示數值摘要 (Metric)
            last_p = plot_df['Close'].iloc[-1]
            last_ma = plot_df['MA'].iloc[-1]
            c1, c2 = st.columns(2)
            c1.metric("現價", f"{last_p:.1f}")
            c2.metric(f"{ma_days}MA", f"{last_ma:.1f}", f"{last_p - last_ma:+.1f}")

        else:
            st.error("查無代號資料")
