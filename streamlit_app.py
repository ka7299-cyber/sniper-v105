import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 頁面基本設定
st.set_page_config(page_title="Sniper X V105", layout="wide")

# ==========================================
# 1. 核心參數庫 (移植自 V75)
# ==========================================
# 大師策略：[短期MA, 長期MA]
MASTER_STRATEGY = {
    '2330': [17, 72], '2317': [18, 62], '2454': [29, 65],
    '2303': [21, 55], '2382': [23, 70], '3231': [26, 60]
}

def get_full_data(sid):
    ticker_tw = f"{sid}.TW"
    df = yf.download(ticker_tw, period="2y", progress=False)
    if df.empty:
        ticker_two = f"{sid}.TWO"
        df = yf.download(ticker_two, period="2y", progress=False)
        return df, ticker_two
    return df, ticker_tw

# ==========================================
# 2. 型態偵測邏輯 (簡化移植)
# ==========================================
def detect_pattern(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]
    # 簡單範例：紅三兵、吞噬等
    if last['Close'] > last['Open'] and prev['Close'] > prev['Open'] and last['Close'] > prev['Close']:
        return "☀️ 多頭排列 (連漲)"
    if last['Close'] > prev['Open'] and last['Open'] < prev['Close'] and last['Close'] > prev['Close']:
        return "⚡ 多頭吞噬"
    return "⚖️ 區間震盪"

# ==========================================
# 3. 主介面開發
# ==========================================
st.title("🚀 Sniper X 全能戰情室 V105")
stock_id = st.sidebar.text_input("輸入股票代號", value="2330").upper().strip()
chart_height = st.sidebar.slider("圖表高度", 400, 1000, 550)

if stock_id:
    df, final_ticker = get_full_data(stock_id)
    if not df.empty:
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # --- 計算均線 ---
        short_p, long_p = MASTER_STRATEGY.get(stock_id, [20, 60]) # 若無大師參數則用 AI 20/60
        df['Short_MA'] = df['Close'].rolling(window=short_p).mean()
        df['Long_MA'] = df['Close'].rolling(window=long_p).mean()
        
        # --- 戰情報告區 ---
        pattern = detect_pattern(df)
        last_p = float(df['Close'].iloc[-1])
        
        tab1, tab2, tab3 = st.tabs(["📈 技術分析", "📊 籌碼數據", "🧠 型態判讀"])
        
        with tab1:
            # 建立子圖：上方 K 線，下方成交量
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                               vertical_spacing=0.05, row_heights=[0.7, 0.3])
            
            # 收盤價線
            fig.add_trace(go.Scatter(x=df.index, y=df['Close'], name='收盤價', line=dict(color='#1f77b4', width=2)), row=1, col=1)
            # 短期均線
            fig.add_trace(go.Scatter(x=df.index, y=df['Short_MA'], name=f'短期({short_p}MA)', line=dict(color='#ff7f0e', dash='dash')), row=1, col=1)
            # 長期均線
            fig.add_trace(go.Scatter(x=df.index, y=df['Long_MA'], name=f'長期({long_p}MA)', line=dict(color='#2ca02c')), row=1, col=1)
            
            # 成交量柱狀圖
            colors = ['red' if df['Close'].iloc[i] >= df['Open'].iloc[i] else 'green' for i in range(len(df))]
            fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name='成交量', marker_color=colors, opacity=0.7), row=2, col=1)
            
            fig.update_layout(height=chart_height, template="plotly_white", hovermode="x unified",
                              margin=dict(l=10, r=10, t=20, b=10), dragmode=False)
            fig.update_xaxes(fixedrange=True, nticks=8)
            fig.update_yaxes(fixedrange=True, side="right")
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

        with tab2:
            st.subheader("三大法人與信用交易 (估算)")
            # 這裡可以整合 yf.Ticker(final_ticker).info 的籌碼數據
            st.info("⚠️ 網頁版籌碼數據由 Yahoo Finance 延遲提供，詳細券商分點建議參考 V75 電腦版。")
            c1, c2 = st.columns(2)
            c1.metric("機構持股比", f"{yf.Ticker(final_ticker).info.get('heldPercentInstitutions', 0)*100:.1f}%")
            c2.metric("空單佔比 (Short Ratio)", f"{yf.Ticker(final_ticker).info.get('shortPercentOfFloat', 0)*100:.2f}%")

        with tab3:
            st.header(f"型態偵測結果：{pattern}")
            st.write(f"目前股價 {last_p} 相對於短期均線之乖離率：{((last_p - df['Short_MA'].iloc[-1])/df['Short_MA'].iloc[-1]*100):.2f}%")

    else:
        st.error("查無資料")
