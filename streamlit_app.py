import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ==========================================
# 0. 系統配置
# ==========================================
st.set_page_config(page_title="Sniper X V109 (V75核心)", layout="wide")

# ==========================================
# 1. V75 大師策略參數庫 (完整修復版)
# ==========================================
# 這是 Sniper X 的靈魂，針對不同股性的最佳化均線
MASTER_STRATEGIES = {
    '2330': 17,  # 台積電
    '2317': 18,  # 鴻海
    '2303': 21,  # 聯電
    '2454': 29,  # 聯發科
    '2382': 23,  # 廣達
    '3231': 26,  # 緯創
    '2301': 18,  # 光寶科
    '2308': 27,  # 台達電
    '2357': 21,  # 華碩
    '6669': 28,  # 緯穎
    '1519': 25,  # 華城
    '2603': 35,  # 長榮
    '3037': 24,  # 欣興 (V75 擴充)
    '3034': 22,  # 聯詠 (V75 擴充)
    '3008': 20   # 大立光
}

# ==========================================
# 2. 側邊欄與動態清單 (手機介面優化)
# ==========================================
st.sidebar.header("🕹️ 戰情控制台")
st.title("🚀 Sniper X V109 (V75核心)")

# 初始化關注清單 (Session State)
if 'watchlist' not in st.session_state:
    st.session_state.watchlist = ['2330', '2317', '2454', '3231', '2603']

# 功能 A: 新增股票到清單
new_input = st.sidebar.text_input("➕ 新增代號 (如 3081)", key="add_stock").strip().upper()
if st.sidebar.button("加入清單") and new_input:
    if new_input not in st.session_state.watchlist:
        st.session_state.watchlist.append(new_input)
        st.success(f"已加入 {new_input}")

# 功能 B: 清空清單
if st.sidebar.button("🗑️ 清空所有關注"):
    st.session_state.watchlist = []

# 功能 C: 選擇股票 (若清單為空，提供預設輸入框)
if st.session_state.watchlist:
    stock_id = st.sidebar.selectbox("📋 快速切換", st.session_state.watchlist)
else:
    stock_id = st.sidebar.text_input("輸入代號查詢", "2330").strip().upper()

# 功能 D: 圖表參數調整
days_show = st.sidebar.select_slider("📅 顯示天數", options=[60, 120, 240, 360], value=120)
chart_h = st.sidebar.slider("📱 圖表高度", 400, 800, 550, step=50)

# ==========================================
# 3. 核心數據邏輯
# ==========================================
def fetch_data_v75(sid):
    # 自動嘗試 .TW (上市) 與 .TWO (上櫃)
    for sfx in ['.TW', '.TWO']:
        ticker = f"{sid}{sfx}"
        try:
            t_obj = yf.Ticker(ticker)
            # 抓取歷史數據
            df = t_obj.history(period="2y")
            if not df.empty:
                # 嘗試抓取股票中文名稱 (若失敗則用代號)
                name = t_obj.info.get('longName', sid)
                return df, ticker, name
        except: continue
    return None, None, None

# ==========================================
# 4. 戰情室主畫面
# ==========================================
if stock_id:
    df, final_ticker, s_name = fetch_data_v75(stock_id)
    
    if df is not None:
        # --- A. 策略判定 ---
        # 檢查是否為大師股，決定均線參數
        if stock_id in MASTER_STRATEGIES:
            ma_days = MASTER_STRATEGIES[stock_id]
            strategy_name = f"👑 大師策略 ({ma_days}MA)"
        else:
            ma_days = 20
            strategy_name = f"🤖 AI 預設 ({ma_days}MA)"
            
        # 計算均線
        df['MA'] = df['Close'].rolling(window=ma_days).mean()
        
        # 裁切顯示範圍
        plot_df = df.tail(days_show)
        
        # --- B. 標題與即時狀態 ---
        curr_p = plot_df['Close'].iloc[-1]
        curr_ma = plot_df['MA'].iloc[-1]
        status = "🔥 強勢多頭" if curr_p > curr_ma else "❄️ 空頭修正"
        
        st.subheader(f"{s_name} ({stock_id})")
        st.caption(f"目前策略：{strategy_name} | 狀態：{status}")

        # --- C. 繪製專業圖表 (雙子圖: 價 + 量) ---
        fig = make_subplots(
            rows=2, cols=1, 
            shared_xaxes=True, 
            vertical_spacing=0.03, 
            row_width=[0.25, 0.75] # 上面 75% 價格，下面 25% 量
        )

        # 1. 價格線
        fig.add_trace(go.Scatter(
            x=plot_df.index, y=plot_df['Close'], name='收盤價',
            line=dict(color='#2962FF', width=2),
            hovertemplate='價: %{y:.2f}'
        ), row=1, col=1)

        # 2. 均線 (大師參數)
        fig.add_trace(go.Scatter(
            x=plot_df.index, y=plot_df['MA'], name=f'{ma_days}MA',
            line=dict(color='#FF6D00', width=2, dash='solid'), # V75 均線改為實線更清楚
            hovertemplate='均: %{y:.2f}'
        ), row=1, col=1)

        # 3. 成交量 (紅漲綠跌)
        colors = ['#D32F2F' if c >= o else '#00796B' for c, o in zip(plot_df['Close'], plot_df['Open'])]
        fig.add_trace(go.Bar(
            x=plot_df.index, y=plot_df['Volume'], name='成交量',
            marker_color=colors,
            hovertemplate='量: %{y:.2s}'
        ), row=2, col=1)

        # 4. 版面優化 (手機專用)
        fig.update_layout(
            template="plotly_white",
            height=chart_h,
            margin=dict(l=10, r=10, t=10, b=10),
            hovermode="x unified", # 十字查線
            dragmode=False, # 鎖定縮放防手滑
            showlegend=False
        )
        
        # 價格座標放右邊 (符合手機習慣)
        fig.update_yaxes(side="right", fixedrange=True)
        fig.update_xaxes(fixedrange=True, type='date')

        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

        # --- D. 數據儀表板 ---
        c1, c2, c3 = st.columns(3)
        c1.metric("收盤價", f"{curr_p:.1f}")
        c2.metric(f"生命線 ({ma_days})", f"{curr_ma:.1f}")
        
        # 計算乖離率
        bias = ((curr_p - curr_ma) / curr_ma) * 100
        c3.metric("乖離率", f"{bias:+.2f}%")

    else:
        st.error(f"❌ 查無代號 {stock_id}，請確認是否為台股代號。")
