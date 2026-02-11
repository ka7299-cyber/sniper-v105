import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 頁面配置
st.set_page_config(page_title="Sniper X V130 (Global)", layout="wide")

# ==============================================
# 1. 資料庫：台股 (TW)
# ==============================================
TW_NAMES = {
    '2330':'台積電', '2317':'鴻海', '2454':'聯發科', '2303':'聯電', '2308':'台達電',
    '2382':'廣達', '3231':'緯創', '2357':'華碩', '2376':'技嘉', '3037':'欣興',
    '2603':'長榮', '2609':'陽明', '2615':'萬海', '3008':'大立光', '3081':'聯亞',
    '8069':'元太', '5536':'聖暉*', '3264':'欣銓', '2409':'友達', '3481':'群創',
    '3035':'智原', '3034':'聯詠', '6669':'緯穎', '3661':'世芯-KY', '3529':'力旺',
    '6770':'力積電', '3711':'日月光', '2327':'國巨', '2344':'華邦電', '2379':'瑞昱'
}

TW_STRATEGIES = {
    '2330': (17, 57), '2317': (18, 57), '2382': (23, 60), '2357': (21, 57),
    '2454': (29, 60), '2603': (35, 60), '3081': (20, 60), '3037': (35, 70),
    '3231': (26, 60), '8069': (22, 60), '3035': (25, 60), '2376': (24, 60),
    '3264': (18, 57)
}

# ==============================================
# 2. 資料庫：美股 (US) - 來自您的圖片
# ==============================================
US_NAMES = {
    'NVDA': '輝達', 'MSFT': '微軟', 'TSLA': '特斯拉', 'GOOGL': '谷歌', 'AMZN': '亞馬遜',
    'META': '臉書', 'AAPL': '蘋果', 'TSM': '台積電ADR', 'INTC': '英特爾', 'AMD': '超微',
    'ADBE': 'Adobe', 'ASML': '艾司摩爾', 'QCOM': '高通', 'NFLX': '奈飛', 'COST': '好市多',
    'MA': '萬事達卡', 'V': 'VISA', 'HD': '家得寶', 'ZTS': '碩騰疫苗', 'TTD': 'The Trade Desk',
    'JNJ': '嬌生', 'IBM': 'IBM', 'AVGO': '博通', 'UNH': '聯合健康', 'ULTA': 'Ulta美容',
    'NVO': '諾和諾德', 'BKNG': 'Booking', 'URI': '聯合租賃'
}

# 圖片中的大師參數 (部分缺長線者，暫補 60 以利運算)
US_STRATEGIES = {
    'NVDA': (19, 58), 'MSFT': (21, 53), 'TSLA': (17, 58), 'GOOGL': (26, 55),
    'AMZN': (19, 47), 'META': (24, 76), 'AAPL': (19, 58), 'TSM': (19, 64),
    'INTC': (27, 60), 'AMD': (22, 96),  'ADBE': (25, 63), 'ASML': (24, 51),
    'QCOM': (25, 64), 'NFLX': (23, 65), 'COST': (18, 56), 'MA': (33, 60),
    'V': (22, 56),    'HD': (17, 53),   'ZTS': (28, 56),  'TTD': (23, 60),
    'JNJ': (26, 60),  'IBM': (19, 60),  'AVGO': (24, 60), 'UNH': (26, 59),
    'ULTA': (26, 60), 'NVO': (26, 57),  'BKNG': (23, 60), 'URI': (22, 60),
    # 指數類
    '^DJI': (20, 45), '^GSPC': (19, 55), '^IXIC': (20, 60), '^SOX': (20, 60)
}

# ==============================================
# 3. 核心函數：回測與搜尋
# ==============================================
def backtest_strategy(df, ma_days):
    ma = df['Close'].rolling(window=ma_days).mean()
    signals = (df['Close'] > ma).astype(int)
    actions = signals.diff()
    
    entry_price = 0
    wins = 0
    total_trades = 0
    total_return = 0.0
    holding = False
    
    for i in range(1, len(df)):
        price = df['Close'].iloc[i]
        act = actions.iloc[i]
        if act == 1 and not holding:
            entry_price = price
            holding = True
        elif act == -1 and holding:
            profit = (price - entry_price) / entry_price
            total_return += profit
            if profit > 0: wins += 1
            total_trades += 1
            holding = False
            
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
    return total_return, win_rate, total_trades

def find_best_ma_with_stats(df, min_days, max_days):
    best_ma = min_days
    best_ret = -float('inf')
    best_stats = (0, 0, 0)
    
    for d in range(min_days, max_days + 1):
        ret, rate, trades = backtest_strategy(df, d)
        if ret > best_ret:
            best_ret = ret
            best_ma = d
            best_stats = (ret, rate, trades)
    return best_ma, best_stats

# ==============================================
# 4. 介面與邏輯
# ==============================================
st.sidebar.header("🕹️ Sniper X 戰情中心")

# ★ 市場切換開關
market_mode = st.sidebar.radio("選擇市場", ["🇹🇼 台股 (TW)", "🇺🇸 美股 (US)"], horizontal=True)

# 根據市場選擇預設清單與輸入範例
if "TW" in market_mode:
    current_strategies = TW_STRATEGIES
    current_names = TW_NAMES
    default_list = ['2330', '2317', '3081']
    input_ph = "例: 2330"
else:
    current_strategies = US_STRATEGIES
    current_names = US_NAMES
    default_list = ['NVDA', 'TSLA', 'AAPL', 'AMD']
    input_ph = "例: NVDA"

# 清單管理 (Session State)
state_key = "tw_list" if "TW" in market_mode else "us_list"
if state_key not in st.session_state:
    st.session_state[state_key] = default_list

def add_stock_callback():
    new_val = st.session_state.new_stock_input.strip().upper()
    if new_val:
        if new_val not in st.session_state[state_key]:
            st.session_state[state_key].append(new_val)
        st.session_state.new_stock_input = "" 

st.sidebar.text_input(f"輸入代號 ({input_ph})", key="new_stock_input", on_change=add_stock_callback)
selected_list = st.sidebar.multiselect("關注清單", st.session_state[state_key], st.session_state[state_key])
st.session_state[state_key] = selected_list # 更新狀態

stock_id = st.sidebar.selectbox("切換股票", selected_list) if selected_list else None
days_to_show = st.sidebar.select_slider("K棒數量", options=[30, 60, 100, 150, 240], value=60)

# ==============================================
# 5. 主程式
# ==============================================
st.title(f"🚀 Sniper X V130 ({'台股' if 'TW' in market_mode else '美股'})")

def get_data(sid, market):
    ticker = sid
    # 台股需加後綴，美股通常不用 (除了少數如 BRK.B)
    if "TW" in market:
        tickers_to_try = [f"{sid}.TW", f"{sid}.TWO"]
    else:
        tickers_to_try = [sid, f"{sid}"] # 美股直接用代號

    for t_symbol in tickers_to_try:
        t = yf.Ticker(t_symbol)
        try:
            df = t.history(period="1y")
            if not df.empty:
                name = current_names.get(sid, t.info.get('shortName', sid))
                inst = t.info.get('heldPercentInstitutions', 0) * 100
                return df, t_symbol, name, inst
        except: continue
    return None, None, None, 0

if stock_id:
    df, ticker, name, inst_own = get_data(stock_id, market_mode)
    
    if df is not None:
        st.sidebar.markdown("---")
        
        # --- 策略分流 ---
        if stock_id in current_strategies:
            # 👑 大師策略 (強制使用圖片數據)
            final_short, final_long = current_strategies[stock_id]
            st.sidebar.info(f"👑 **大師策略 ({stock_id})**\n\n短線: {final_short} MA\n長線: {final_long} MA")
            
            # 順便算勝率給使用者看
            _, s_win, s_trades = backtest_strategy(df, final_short)
            st.sidebar.caption(f"(短線回測: 勝率 {s_win:.0f}% / {s_trades}次)")
            
        else:
            # 🤖 AI 自動運算 (未知股票)
            with st.spinner('🤖 AI 正在掃描美股最佳參數...'):
                ai_short, (s_ret, s_win, s_trades) = find_best_ma_with_stats(df, 16, 25)
                ai_long, (l_ret, l_win, l_trades) = find_best_ma_with_stats(df, 45, 70)
            
            final_short, final_long = ai_short, ai_long
            
            st.sidebar.warning(f"🤖 **AI 最佳參數**")
            c1, c2 = st.sidebar.columns(2)
            c1.metric(f"短 ({final_short})", f"{s_win:.0f}%")
            c2.metric("次數", f"{s_trades}")
            c3, c4 = st.sidebar.columns(2)
            c3.metric(f"長 ({final_long})", f"{l_win:.0f}%")
            c4.metric("次數", f"{l_trades}")

        # 計算
        df['MA_Short'] = df['Close'].rolling(window=final_short).mean()
        df['MA_Long'] = df['Close'].rolling(window=final_long).mean()
        df['Vol_MA5'] = df['Volume'].rolling(window=5).mean()
        
        plot_df = df.tail(days_to_show)
        last_close = plot_df['Close'].iloc[-1]
        last_short = plot_df['MA_Short'].iloc[-1]
        last_long = plot_df['MA_Long'].iloc[-1]
        bias_short = ((last_close - last_short) / last_short) * 100
        
        st.subheader(f"{name} ({ticker})")
        
        # 數據面板
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("收盤", f"{last_close:.2f}") # 美股小數點2位
        c2.metric(f"短線({final_short})", f"{last_short:.2f}", f"{bias_short:+.1f}%")
        c3.metric(f"長線({final_long})", f"{last_long:.2f}")
        
        # 多空
        if last_close > last_short and last_short > last_long:
            trend_str = "🔥 強勢多頭"
        elif last_close > last_short:
            trend_str = "📈 短多格局"
        elif last_close < last_short and last_short < last_long:
            trend_str = "❄️ 絕對空頭"
        else:
            trend_str = "⚠️ 震盪整理"
        c4.metric("法人持股", f"{inst_own:.1f}%", trend_str)

        # 繪圖
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.02, row_width=[0.25, 0.75])

        # K棒
        fig.add_trace(go.Candlestick(
            x=plot_df.index, open=plot_df['Open'], high=plot_df['High'],
            low=plot_df['Low'], close=plot_df['Close'], name='K棒',
            increasing_line_color='#ef5350', decreasing_line_color='#26a69a'
        ), row=1, col=1)

        fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df['MA_Short'], name=f'短線{final_short}', line=dict(color='#ff9800', width=1.5)), row=1, col=1)
        fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df['MA_Long'], name=f'長線{final_long}', line=dict(color='#9c27b0', width=1.5)), row=1, col=1)

        vol_colors = ['#ef5350' if c >= o else '#26a69a' for c, o in zip(plot_df['Close'], plot_df['Open'])]
        fig.add_trace(go.Bar(x=plot_df.index, y=plot_df['Volume'], name='量', marker_color=vol_colors), row=2, col=1)
        fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df['Vol_MA5'], name='5日均量', line=dict(color='#29b6f6', width=1)), row=2, col=1)

        fig.update_layout(height=400, template="plotly_white", xaxis_rangeslider_visible=False, showlegend=False, margin=dict(l=0,r=0,t=5,b=0), hovermode="x unified", dragmode=False)
        fig.update_xaxes(fixedrange=True)
        fig.update_yaxes(side="right", fixedrange=True, row=1, col=1)
        fig.update_yaxes(side="right", fixedrange=True, row=2, col=1)

        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    else:
        st.error(f"查無 {stock_id} 資料")
