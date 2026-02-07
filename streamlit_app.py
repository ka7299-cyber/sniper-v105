import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 頁面配置
st.set_page_config(page_title="Sniper X V112", layout="wide")

# ==============================================
# 1. 內建台股中英文對照庫 (可自行擴充) & 大師參數
# ==============================================
TW_NAMES = {
    '2330': '台積電', '2317': '鴻海', '2454': '聯發科', '2303': '聯電', 
    '2603': '長榮', '2609': '陽明', '2615': '萬海', '3008': '大立光',
    '3231': '緯創', '2382': '廣達', '2357': '華碩', '3037': '欣興',
    '3035': '智原', '3081': '聯亞', '8069': '元太', '5536': '聖暉*',
    '2308': '台達電', '3264': '欣銓'
}
MASTER_PARAMS = {'2330': 17, '2317': 18, '2303': 21, '2454': 29, '2603': 35}

# ==============================================
# 2. 狀態管理 (Session State)
# ==============================================
# 初始化清單 (優先讀取網址參數，若無則用預設)
if "list" in st.query_params:
    default_list = st.query_params["list"].split(",")
else:
    default_list = ['2330', '2317', '2454']

if 'my_list' not in st.session_state:
    st.session_state.my_list = default_list

# 輸入框的回調函數：加入後自動清空
def add_stock_callback():
    new_val = st.session_state.new_stock_input.strip().upper()
    if new_val:
        if new_val not in st.session_state.my_list:
            st.session_state.my_list.append(new_val)
            # 更新網址以便分享
            st.query_params["list"] = ",".join(st.session_state.my_list)
        st.session_state.new_stock_input = "" # 清空輸入框

# ==============================================
# 3. 側邊欄：控制中心
# ==============================================
st.sidebar.header("🕹️ 戰情控制中心")

# (A) 輸入與自動清空功能
st.sidebar.text_input("輸入代號 (例: 3081)", key="new_stock_input", on_change=add_stock_callback)
st.sidebar.caption("💡 輸入後按 Enter 即可自動加入並清空欄位")

# (B) 單檔刪除管理 (Multiselect)
# 這裡讓使用者可以直觀地看到所有股票，並按 'x' 移除個別股票
updated_list = st.sidebar.multiselect(
    "管理關注清單 (可單獨移除)", 
    options=st.session_state.my_list,
    default=st.session_state.my_list
)

# 如果清單有變動 (使用者刪除了某些股票)，更新 State 與網址
if updated_list != st.session_state.my_list:
    st.session_state.my_list = updated_list
    st.query_params["list"] = ",".join(updated_list)

# (C) 選擇要分析的股票
if st.session_state.my_list:
    stock_id = st.sidebar.selectbox("切換股票", st.session_state.my_list)
else:
    stock_id = None
    st.warning("清單為空，請輸入代號")

# (D) K線區間設定
days_to_show = st.sidebar.select_slider("K棒顯示數量", options=[60, 100, 150, 240], value=100)
chart_height = st.sidebar.slider("圖表高度", 400, 900, 600)

# ==============================================
# 4. 核心邏輯：抓取資料與 K 線繪圖
# ==============================================
st.title("🚀 Sniper X V112 (Pro K-Line)")

def get_stock_data(sid):
    # 嘗試上市或上櫃
    for sfx in ['.TW', '.TWO']:
        ticker = f"{sid}{sfx}"
        t = yf.Ticker(ticker)
        try:
            df = t.history(period="1y")
            if not df.empty:
                # 優先使用內建中文庫，否則嘗試抓取
                name = TW_NAMES.get(sid, t.info.get('shortName', sid))
                # 簡單修正：如果抓到的是英文且不在庫內，就顯示代號
                if name.isascii() and sid not in TW_NAMES: 
                     name = f"{sid} (名稱讀取中)"
                
                # 機構持股
                inst = t.info.get('heldPercentInstitutions', 0) * 100
                return df, ticker, name, inst
        except: continue
    return None, None, None, 0

if stock_id:
    with st.spinner(f"正在繪製 {stock_id} K線圖..."):
        df, ticker, name, inst_own = get_stock_data(stock_id)
        
        if df is not None:
            # 計算指標
            ma_days = MASTER_PARAMS.get(stock_id, 20)
            df['MA'] = df['Close'].rolling(window=ma_days).mean()
            
            # 判讀邏輯 (V75 核心)
            last_close = df['Close'].iloc[-1]
            last_ma = df['MA'].iloc[-1]
            bias = ((last_close - last_ma) / last_ma) * 100
            trend = "🔥 多頭格局" if last_close > last_ma else "❄️ 空頭格局"
            
            # 取出要繪圖的區間
            plot_df = df.tail(days_to_show)

            # --- 顯示 V75 風格戰報 ---
            st.subheader(f"{name} ({ticker})")
            
            # 使用 Columns 排版數據
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("收盤價", f"{last_close:.1f}")
            c2.metric(f"生命線 ({ma_days}MA)", f"{last_ma:.1f}")
            c3.metric("乖離率", f"{bias:+.2f}%", delta_color="off")
            c4.metric("法人籌碼", f"{inst_own:.1f}%")
            
            # 狀態條
            if last_close > last_ma:
                st.success(f"📈 判定：股價位於 {ma_days}MA 之上，維持 {trend}")
            else:
                st.error(f"📉 判定：股價位於 {ma_days}MA 之下，維持 {trend}")

            # --- 繪製專業 K 線圖 (Candlestick) ---
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                                vertical_spacing=0.03, row_width=[0.25, 0.75])

            # 1. K線圖 (Candlestick)
            fig.add_trace(go.Candlestick(
                x=plot_df.index,
                open=plot_df['Open'], high=plot_df['High'],
                low=plot_df['Low'], close=plot_df['Close'],
                name='K棒',
                increasing_line_color='#ef5350', # 台股漲是紅
                decreasing_line_color='#26a69a'  # 台股跌是綠
            ), row=1, col=1)

            # 2. 均線 (MA)
            fig.add_trace(go.Scatter(
                x=plot_df.index, y=plot_df['MA'], 
                name=f'{ma_days}MA',
                line=dict(color='#ff9800', width=1.5)
            ), row=1, col=1)

            # 3. 成交量 (Volume) - 顏色隨漲跌
            vol_colors = ['#ef5350' if c >= o else '#26a69a' 
                          for c, o in zip(plot_df['Close'], plot_df['Open'])]
            fig.add_trace(go.Bar(
                x=plot_df.index, y=plot_df['Volume'], 
                name='成交量', marker_color=vol_colors
            ), row=2, col=1)

            # --- 圖表設定 ---
            fig.update_layout(
                height=chart_height,
                template="plotly_white",
                xaxis_rangeslider_visible=False, # 隱藏下方醜醜的滑桿
                showlegend=False,
                margin=dict(l=5, r=5, t=10, b=5),
                hovermode="x unified",
                dragmode="pan" # 手機上允許拖動平移
            )
            
            # 價格軸在右側 (符合看盤習慣)
            fig.update_yaxes(side="right", row=1, col=1)
            fig.update_yaxes(side="right", row=2, col=1)

            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

        else:
            st.error(f"找不到 {stock_id} 的資料")
