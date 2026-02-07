import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 頁面基本設定
st.set_page_config(page_title="Sniper X V109 Full", layout="wide")

# ==========================================
# 1. 大師參數庫 (完整移植自 V75 核心)
# ==========================================
# 包含您開發的 Sniper_X, V62, V72 核心邏輯
MASTER_PARAMS = {
    '2330': {'s': 17, 'l': 72}, # 台積電: 短線 17MA
    '2317': {'s': 18, 'l': 72}, # 鴻海: 短線 18MA
    '2303': {'s': 21, 'l': 72}, # 聯電
    '2454': {'s': 29, 'l': 72}, # 聯發科
    '2382': {'s': 23, 'l': 72}, # 廣達
    '3231': {'s': 26, 'l': 72}, # 緯創
    '2301': {'s': 18, 'l': 72}, # 光寶科
    '2308': {'s': 27, 'l': 72}, # 台達電
    '2357': {'s': 21, 'l': 72}, # 華碩
    '6669': {'s': 28, 'l': 72}, # 緯穎
    '1519': {'s': 25, 'l': 72}, # 華城
    '2603': {'s': 35, 'l': 72}, # 長榮 (大師策略)
    '3081': {'s': 20, 'l': 72}  # 譜瑞
}

# 預設關注清單
MY_WATCHLIST = ['2330', '2317', '2454', '2382', '3231', '5536', '3081']

# --- 側邊欄控制 ---
st.sidebar.title("🎮 Sniper X V109")
mode = st.sidebar.radio("切換功能：", ["單檔詳細分析", "我的關注清單"])

# 顯示設定
range_options = {"3個月": 60, "半年": 120, "1年": 240}
selected_range = st.sidebar.selectbox("顯示時間區間", list(range_options.keys()), index=1)
days_to_show = range_options[selected_range]
chart_height = st.sidebar.slider("圖表高度", 300, 1000, 550, 50)

def get_full_data(sid):
    """抓取股價與籌碼比例"""
    for sfx in [".TW", ".TWO"]:
        ticker_id = f"{sid}{sfx}"
        try:
            t_obj = yf.Ticker(ticker_id)
            # 抓取較長歷史確保長均線 72MA 計算正確
            df = t_obj.history(period="2y") 
            if not df.empty:
                # 抓取機構持股比例 (Inst. Own)
                inst_own = t_obj.info.get('heldPercentInstitutions', 0) * 100
                return df, ticker_id, inst_own
        except: continue
    return pd.DataFrame(), sid, 0

# ==========================================
# 模式 A：單檔詳細分析 (雙均線系統)
# ==========================================
if mode == "單檔詳細分析":
    stock_id = st.sidebar.text_input("輸入股票代號", value="2330").upper().strip()
    
    if stock_id:
        df, final_ticker, inst_own = get_full_data(stock_id)
        
        if not df.empty:
            # 取得該股大師參數，無對應則預設 20MA
            params = MASTER_PARAMS.get(stock_id, {'s': 20, 'l': 72})
            df['SMA'] = df['Close'].rolling(window=params['s']).mean() # 短期大師線
            df['LMA'] = df['Close'].rolling(window=params['l']).mean() # 長期支撐線
            
            plot_df = df.tail(days_to_show).copy()
            
            # 1. 頂部數據面板 (數值摘要)
            last_p = plot_df['Close'].iloc[-1]
            last_sma = plot_df['SMA'].iloc[-1]
            status = "🔥 多頭" if last_p > last_sma else "❄️ 空頭"
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("目前價格", f"{last_p:.1f}")
            c2.metric(f"短期 ({params['s']}MA)", f"{last_sma:.1f}", f"{last_p-last_sma:+.1f}")
            c3.metric("機構持股", f"{inst_own:.1f}%")
            c4.metric("趨勢狀態", status)
            
            # 2. 繪製上下分離圖表 (價格 + 成交量)
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                                vertical_spacing=0.03, row_width=[0.25, 0.75])
            
            # 主圖：收盤價 + 雙均線
            fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df['Close'], name='價格', line=dict(color='#1f77b4', width=2)), row=1, col=1)
            fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df['SMA'], name=f'短線{params["s"]}MA', line=dict(color='#ff7f0e', width=2, dash='dash')), row=1, col=1)
            fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df['LMA'], name='長線72MA', line=dict(color='#2ca02c', width=1.5)), row=1, col=1)
            
            # 副圖：成交量 (紅跌綠漲著色)
            colors = ['#ef5350' if c >= o else '#26a69a' for c, o in zip(plot_df['Close'], plot_df['Open'])]
            fig.add_trace(go.Bar(x=plot_df.index, y=plot_df['Volume'], name='成交量', marker_color=colors, opacity=0.8), row=2, col=1)
            
            # 佈局美化
            fig.update_layout(height=chart_height, template="plotly_white", hovermode="x unified", dragmode=False, showlegend=True, margin=dict(l=5, r=5, t=10, b=5))
            fig.update_yaxes(side="right", fixedrange=True)
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            
        else:
            st.error(f"❌ 無法讀取 {stock_id}")

# ==========================================
# 模式 B：我的關注清單 (籌碼雷達)
# ==========================================
elif mode == "我的關注清單":
    st.header("🔍 完整參數雷達掃描")
    scan_results = []
    with st.spinner('同步大師參數中...'):
        for sid in MY_WATCHLIST:
            temp_df, _, i_own = get_full_data(sid)
            if not temp_df.empty:
                p = MASTER_PARAMS.get(sid, {'s': 20, 'l': 72})
                curr_p = temp_df['Close'].iloc[-1]
                m_val = temp_df['Close'].rolling(window=p['s']).mean().iloc[-1]
                scan_results.append({
                    "代號": sid, "現價": f"{curr_p:.1f}", 
                    "大師均線": f"{p['s']}MA", "機構比例": f"{i_own:.1f}%",
                    "狀態": "🔥多頭" if curr_p > m_val else "❄️空頭"
                })
    st.table(pd.DataFrame(scan_results))
