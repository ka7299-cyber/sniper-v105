import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 頁面配置
st.set_page_config(page_title="Sniper X V126", layout="wide")

# ==============================================
# 1. 內建中文庫
# ==============================================
TW_NAMES = {
    '2330':'台積電', '2317':'鴻海', '2454':'聯發科', '2303':'聯電', '2308':'台達電',
    '2382':'廣達', '3231':'緯創', '2357':'華碩', '2376':'技嘉', '3037':'欣興',
    '2603':'長榮', '2609':'陽明', '2615':'萬海', '3008':'大立光', '3081':'聯亞',
    '8069':'元太', '5536':'聖暉*', '3264':'欣銓', '2409':'友達', '3481':'群創',
    '3035':'智原', '3034':'聯詠', '6669':'緯穎', '3661':'世芯-KY', '3529':'力旺',
    '6770':'力積電', '3711':'日月光', '2327':'國巨', '2344':'華邦電', '2379':'瑞昱'
}

# ==============================================
# 2. 大師策略參數庫 (絕對優先)
# ==============================================
MASTER_STRATEGIES = {
    '2330': (17, 57), '2317': (18, 57), '2382': (23, 60), '2357': (21, 57),
    '2454': (29, 60), '2603': (35, 60), '3081': (20, 60), '3037': (35, 70),
    '3231': (26, 60), '8069': (22, 60), '3035': (25, 60), '2376': (24, 60),
    '3264': (18, 57)
}

# ==============================================
# 3. AI 回測核心 (計算勝率)
# ==============================================
def backtest_strategy(df, ma_days):
    """
    模擬交易：
    1. 站上均線 -> 買入
    2. 跌破均線 -> 賣出
    回傳：(總報酬率, 勝率, 交易次數)
    """
    ma = df['Close'].rolling(window=ma_days).mean()
    
    # 產生訊號: 1=持有, 0=空手
    signals = (df['Close'] > ma).astype(int)
    
    # 找出買賣點 (diff=1 買, diff=-1 賣)
    actions = signals.diff()
    
    entry_price = 0
    wins = 0
    total_trades = 0
    total_return = 0.0
    holding = False
    
    # 逐日模擬 (為了準確計算次數與勝率)
    for i in range(1, len(df)):
        price = df['Close'].iloc[i]
        act = actions.iloc[i]
        
        if act == 1 and not holding: # 買入
            entry_price = price
            holding = True
        elif act == -1 and holding: # 賣出
            profit = (price - entry_price) / entry_price
            total_return += profit
            if profit > 0:
                wins += 1
            total_trades += 1
            holding = False
            
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
    return total_return, win_rate, total_trades

def find_best_ma_with_stats(df, min_days, max_days):
    """
    尋找區間內獲利最高的均線，並回傳其統計數據
    """
    best_ma = min_days
    best_ret = -float('inf')
    best_stats = (0, 0, 0) # ret, win_rate, trades
    
    for d in range(min_days, max_days + 1):
        ret, rate, trades = backtest_strategy(df, d)
        # 這裡以「總報酬」為優化目標，但也可以改為勝率優先
        if ret > best_ret:
            best_ret = ret
            best_ma = d
            best_stats = (ret, rate, trades)
            
    return best_ma, best_stats

# ==============================================
# 4. 狀態與清單管理
# ==============================================
if "list" in st.query_params:
    default_list = st.query_params["list"].split(",")
else:
    default_list = ['2330', '2317', '3081']

if 'my_list' not in st.session_state:
    st.session_state.my_list = default_list

def add_stock_callback():
    new_val = st.session_state.new_stock_input.strip().upper()
    if new_val:
        if new_val not in st.session_state.my_list:
            st.session_state.my_list.append(new_val)
            st.query_params["list"] = ",".join(st.session_state.my_list)
        st.session_state.new_stock_input = "" 

# ==============================================
# 5. 側邊欄控制
# ==============================================
st.sidebar.header("🕹️ V126 戰情中心")
st.sidebar.text_input("輸入代號 (自動清空)", key="new_stock_input", on_change=add_stock_callback)

updated_list = st.sidebar.multiselect("管理清單", options=st.session_state.my_list, default=st.session_state.my_list)
if updated_list != st.session_state.my_list:
    st.session_state.my_list = updated_list
    st.query_params["list"] = ",".join(updated_list)

if st.session_state.my_list:
    stock_id = st.sidebar.selectbox("切換股票", st.session_state.my_list)
else:
    stock_id = None

days_to_show = st.sidebar.select_slider("K棒數量", options=[30, 60, 100, 150, 240], value=60)

# ==============================================
# 6. 主程式邏輯
# ==============================================
st.title("🚀 Sniper X V126 (Win Rate)")

def get_stock_data(sid):
    for sfx in ['.TW', '.TWO']:
        ticker = f"{sid}{sfx}"
        t = yf.Ticker(ticker)
        try:
            df = t.history(period="1y") # 抓1年來回測
            if not df.empty:
                name = TW_NAMES.get(sid, t.info.get('shortName', sid))
                inst = t.info.get('heldPercentInstitutions', 0) * 100
                return df, ticker, name, inst
        except: continue
    return None, None, None, 0

if stock_id:
    df, ticker, name, inst_own = get_stock_data(stock_id)
    
    if df is not None:
        # --- 參數與回測 ---
        st.sidebar.markdown("---")
        
        if stock_id in MASTER_STRATEGIES:
            # 情況 A: 大師參數
            final_short, final_long = MASTER_STRATEGIES[stock_id]
            st.sidebar.info(f"👑 **大師策略**\n\n短線: {final_short} MA\n長線: {final_long} MA")
            # 即使是大師參數，也可以偷算一下勝率給使用者看 (選擇性)
            _, s_win, s_trades = backtest_strategy(df, final_short)
            st.sidebar.caption(f"(大師短線回測: 勝率 {s_win:.0f}% / {s_trades}次)")
            
        else:
            # 情況 B: AI 自動運算 + 勝率報告
            with st.spinner('🤖 AI 正在進行勝率回測...'):
                # 搜尋最佳短線 (16-25)
                ai_short, (s_ret, s_win, s_trades) = find_best_ma_with_stats(df, 16, 25)
                # 搜尋最佳長線 (45-70)
                ai_long, (l_ret, l_win, l_trades) = find_best_ma_with_stats(df, 45, 70)
            
            final_short, final_long = ai_short, ai_long
            
            st.sidebar.warning(f"🤖 **AI 最佳參數**")
            
            # 顯示短線數據
            st.sidebar.markdown(f"**短線攻擊 ({final_short}MA)**")
            c1, c2 = st.sidebar.columns(2)
            c1.metric("勝率", f"{s_win:.0f}%")
            c2.metric("次數", f"{s_trades}")
            
            # 顯示長線數據
            st.sidebar.markdown(f"**長線防守 ({final_long}MA)**")
            c3, c4 = st.sidebar.columns(2)
            c3.metric("勝率", f"{l_win:.0f}%")
            c4.metric("次數", f"{l_trades}")
            
            if s_win < 50:
                st.sidebar.error("⚠️ 警告：此股短線股性雜亂，AI 算出的勝率偏低，請謹慎參考。")

        # 計算指標
        df['MA_Short'] = df['Close'].rolling(window=final_short).mean()
        df['MA_Long'] = df['Close'].rolling(window=final_long).mean()
        df['Vol_MA5'] = df['Volume'].rolling(window=5).mean()
        
        plot_df = df.tail(days_to_show)
        last_close = plot_df['Close'].iloc[-1]
        last_short = plot_df['MA_Short'].iloc[-1]
        last_long = plot_df['MA_Long'].iloc[-1]
        
        bias_short = ((last_close - last_short) / last_short) * 100
        
        st.subheader(f"{name} ({ticker})")
        
        # 數據儀表板
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("收盤", f"{last_close:.1f}")
        c2.metric(f"短線({final_short})", f"{last_short:.1f}", f"乖離 {bias_short:+.1f}%")
        c3.metric(f"長線({final_long})", f"{last_long:.1f}")
        
        # 多空判定
        if last_close > last_short and last_short > last_long:
            trend_str = "🔥 強勢多頭"
        elif last_close > last_short:
            trend_str = "📈 短多格局"
        elif last_close < last_short and last_short < last_long:
            trend_str = "❄️ 絕對空頭"
        else:
            trend_str = "⚠️ 整理中"
        c4.metric("法人", f"{inst_own:.1f}%", trend_str)

        # --- 繪圖 ---
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                            vertical_spacing=0.02, row_width=[0.25, 0.75])

        # K棒
        fig.add_trace(go.Candlestick(
            x=plot_df.index, open=plot_df['Open'], high=plot_df['High'],
            low=plot_df['Low'], close=plot_df['Close'], name='K棒',
            increasing_line_color='#ef5350', decreasing_line_color='#26a69a'
        ), row=1, col=1)

        # 短線
        fig.add_trace(go.Scatter(
            x=plot_df.index, y=plot_df['MA_Short'], name=f'短線{final_short}MA',
            line=dict(color='#ff9800', width=1.5)
        ), row=1, col=1)

        # 長線
        fig.add_trace(go.Scatter(
            x=plot_df.index, y=plot_df['MA_Long'], name=f'長線{final_long}MA',
            line=dict(color='#9c27b0', width=1.5)
        ), row=1, col=1)

        # 成交量
        vol_colors = ['#ef5350' if c >= o else '#26a69a' for c, o in zip(plot_df['Close'], plot_df['Open'])]
        fig.add_trace(go.Bar(
            x=plot_df.index, y=plot_df['Volume'], name='量', marker_color=vol_colors
        ), row=2, col=1)
        
        fig.add_trace(go.Scatter(
            x=plot_df.index, y=plot_df['Vol_MA5'], name='5日均量',
            line=dict(color='#29b6f6', width=1)
        ), row=2, col=1)

        # 手機體驗設定
        fig.update_layout(
            height=400, template="plotly_white",
            xaxis_rangeslider_visible=False, showlegend=False,
            margin=dict(l=0, r=0, t=5, b=0),
            hovermode="x unified", dragmode=False
        )
        
        fig.update_xaxes(fixedrange=True)
        fig.update_yaxes(side="right", fixedrange=True, row=1, col=1)
        fig.update_yaxes(side="right", fixedrange=True, row=2, col=1)

        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    else:
        st.error(f"查無資料 {stock_id}")
