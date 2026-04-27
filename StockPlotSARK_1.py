import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# ==============================================================================
# 1. 系統環境與側邊欄配置
# ==============================================================================

# 網頁配置
st.set_page_config(page_title="改良版 SAR 趨勢追蹤系統 (週K線版)", layout="wide")

# --- 側邊欄：參數設定 ---
st.sidebar.header("參數設定")

# 股票與日期輸入
stock_id = st.sidebar.text_input("股票代號(如2330.TW或AAPL)", "2330.TW")
start_date = st.sidebar.date_input("起始日期(YYYY/MM/DD)", datetime(2026, 1, 1))
end_date = st.sidebar.date_input("結束日期(YYYY/MM/DD)", datetime.now())

# 週線模式：自動將起始日期調整為當週週一
from datetime import timedelta
if start_date.weekday() != 0:
    start_date = start_date - timedelta(days=start_date.weekday())
    st.sidebar.info(f"起始日期已自動調整為當週週一：{start_date}")

# 圖表主題選擇：影響後續 CSS 渲染與 Plotly 模板
theme_choice = st.sidebar.radio("圖表主題(對應網頁背景)", ["亮色(白色背景)", "深色(深色背景)"])

# ==============================================================================
# 2. CSS 視覺樣式優化 (強制覆蓋各主題背景色)
# ==============================================================================

if theme_choice == "深色(深色背景)":
    chart_template = "plotly_dark"
    font_color = "white"
    bg_color = "#0E1117"
    st.markdown("""
        <style>
        /* 深色模式：設定側邊欄與背景為深黑色 (#0E1117)，文字為白色 */
        [data-testid="stSidebar"], .stApp, header { background-color: #0E1117 !important; color: white !important; }
        .stMarkdown, p, h1, h2, h3, span { color: white !important; }
        input { color: white !important; background-color: #262730 !important; }
        </style>
        """, unsafe_allow_html=True)
else:
    chart_template = "plotly_white"
    font_color = "black"
    bg_color = "#FFFFFF"
    st.markdown("""
        <style>
        /* 亮色模式：設定背景為純白，文字為純黑 */
        [data-testid="stSidebar"], .stApp, header { background-color: #FFFFFF !important; color: black !important; }
        .stMarkdown, p, h1, h2, h3, span { color: black !important; }
        
        /* 消除輸入框陰影，改用簡約淺灰色邊框 */
        div[data-baseweb="input"], div[data-baseweb="input"] > div, div[data-baseweb="input"] input {
            background-color: white !important;
            border-color: #dcdcdc !important;
            box-shadow: none !important;
        }

        /* 按鈕樣式：黑底白字，增加專業感 */
        div.stButton > button {
            background-color: #000000 !important;
            border: 1px solid #000000 !important;
            font-weight: bold !important;
        }
        div.stButton > button * {
            color: #FFFFFF !important;
        }
        div.stButton > button:hover {
            background-color: #333333 !important;
        }

        /* 側邊欄邊框調整 */
        [data-testid="stSidebar"] { border-right: 1px solid #f0f2f6; }
        input { color: black !important; background-color: white !important; }
        </style>
        """, unsafe_allow_html=True)

st.sidebar.markdown("---")
# SAR 核心參數：AF (加速因子)
af_start = st.sidebar.slider("AF 起始值", min_value=0.01, max_value=0.10, value=0.02, step=0.01)
af_max = st.sidebar.slider("AF 極限值", min_value=0.10, max_value=0.50, value=0.20, step=0.01)
st.sidebar.markdown("---")
# 收盤價容許度 (避免因盤中影線誤觸導致頻繁轉向)(收盤價確認機制參數)
tolerance_pct = st.sidebar.slider("誤差容忍值%(預設1%)", min_value=0.0, max_value=5.0, value=1.0, step=0.5, format="%.1f%%")
up_tol = 1 - tolerance_pct / 100    # e.g. 1% → 0.99
down_tol = 1 + tolerance_pct / 100  # e.g. 1% → 1.01

# 定義分析按鈕
analyze_btn = st.sidebar.button("開始分析")

# 自動處理台股代號 (.TW)
search_id = f"{stock_id}.TW" if stock_id.isdigit() else stock_id

st.title("🚀 改良版 SAR 趨勢追蹤系統 (週K線版)")

# ==============================================================================
# 3. 數據抓取與計算邏輯
# ==============================================================================
if not analyze_btn:
    st.info("💡 請點開左上角選單 [ >> ] 在左側面板設定參數後，按「開始分析」即可產出圖表")
else:
    # 顯示股票代碼
    st.markdown(f"<h3 style='color: {font_color};'>{search_id}</h3>", unsafe_allow_html=True)
    
    data = yf.download(search_id, start=start_date, end=end_date, interval='1wk', auto_adjust=True)
    
    if not data.empty:
        df = data.copy().reset_index()
        # 格式化日期(用於 X 軸顯示)：移除 X 軸非交易日空隙的關鍵，先將日期轉為字串
        # 這樣會顯示成：Nov 02 2022
        df['Date_Str'] = df['Date'].dt.strftime('%b %d %Y')

        # 處理 yfinance 可能產生的多層欄位
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        # 展平數據確保計算穩定
        df['Close_1D'] = df['Close'].values.flatten()
        df['High_1D'] = df['High'].values.flatten()
        df['Low_1D'] = df['Low'].values.flatten()
        df['Open_1D'] = df['Open'].values.flatten()

        # --- 請刪除這一段 ---
        # psar = df.ta.psar(high='High_1D', low='Low_1D', close='Close_1D', 
        #                   af0=af_start, af=af_start, max_af=af_max)
        
        # if psar is not None:
        #     df['SAR_Long'] = psar.iloc[:, 0]
        #     df['SAR_Short'] = psar.iloc[:, 1]
        # else:
        #     df['SAR_Long'] = np.nan
        #     df['SAR_Short'] = np.nan

        # --- [取代為此段] 改良版 SAR 核心計算法 ---
        df['SAR'] = np.nan
        df['Trend'] = 0  # 趨勢標記：1 為多頭, -1 為空頭
        
        # 初始趨勢判斷：若第一天收紅則初步看多
        initial_trend = 1 if df['Close_1D'].iloc[0] > df['Open_1D'].iloc[0] else -1
        curr_trend = initial_trend
        curr_af = af_start
        # 初始 SAR 位在低點(多)或高點(空)
        curr_sar = df['Low_1D'].iloc[0] if initial_trend == 1 else df['High_1D'].iloc[0]
        # EP (極值點)：多頭為最高價，空頭為最低價
        ep = df['High_1D'].iloc[0] if initial_trend == 1 else df['Low_1D'].iloc[0]

        for i in range(len(df)):
            c_high, c_low, c_close = df['High_1D'].iloc[i], df['Low_1D'].iloc[i], df['Close_1D'].iloc[i]
            df.iat[i, df.columns.get_loc('SAR')] = curr_sar
            df.iat[i, df.columns.get_loc('Trend')] = curr_trend
            
            next_trend, next_af = curr_trend, curr_af
            
            # --- 多頭趨勢判斷 ---
            if curr_trend == 1: # 上升趨勢(創新高)
                if c_high > ep:
                    ep = c_high
                    next_af = min(curr_af + af_start, af_max) # 增加加速因子
                
                if c_low <= curr_sar: # 觸碰點位(盤中跌破 SAR)
                    # [改良邏輯] 若收盤價仍高於 SAR*容許比例，則不轉向，僅重置 AF 並調整 SAR 位置
                    if c_close > curr_sar * up_tol:
                        next_af, ep = af_start, c_high
                        next_sar = c_low # 重置為當日低點
                    else: # 未能守住，標準反轉(真正收破：轉向為空頭)
                        next_trend, next_af, next_sar, ep = -1, af_start, ep, c_low
                else: # 正常上升(沒觸碰)
                    next_sar = curr_sar + curr_af * (ep - curr_sar)
                    # 確保 SAR 不會高於前兩日低點
                    if i > 0: next_sar = min(next_sar, c_low, df['Low_1D'].iloc[i-1])
            
            # --- 空頭趨勢判斷 ---
            else: # 下降趨勢(創新低)
                if c_low < ep:
                    ep = c_low
                    next_af = min(curr_af + af_start, af_max)
                
                if c_high >= curr_sar: # 觸碰點位(盤中突破 SAR)
                    # [改良邏輯] 若收盤價仍低於 SAR*容許比例，不轉向
                    if c_close < curr_sar * down_tol:
                        next_af, ep = af_start, c_low
                        next_sar = c_high # 重置為當日高點
                    else: # 未能守住，標準反轉(真正收過：轉向為多頭)
                        next_trend, next_af, next_sar, ep = 1, af_start, ep, c_high
                else: # 正常下降(沒觸碰)
                    next_sar = curr_sar + curr_af * (ep - curr_sar)
                    # 確保 SAR 不會低於前兩日高點
                    if i > 0: next_sar = max(next_sar, c_high, df['High_1D'].iloc[i-1])

            curr_sar, curr_trend, curr_af = next_sar, next_trend, next_af

        # 將 SAR 分拆為多空兩欄，方便 Plotly 著色（紅點與綠點）
        df['SAR_Long'] = df.apply(lambda x: x['SAR'] if x['Trend'] == 1 else np.nan, axis=1)
        df['SAR_Short'] = df.apply(lambda x: x['SAR'] if x['Trend'] == -1 else np.nan, axis=1)


        # ==============================================================================
        # 4. 繪圖與互動優化
        # ==============================================================================
        fig = go.Figure()

        # 使用 Date_Str (字串日期) 當 X 軸，避開假日空隙
        fig.add_trace(go.Candlestick(
            x=df['Date_Str'], open=df['Open_1D'], high=df['High_1D'], low=df['Low_1D'], close=df['Close_1D'],
            name='K線', increasing_line_color='#FF4136', decreasing_line_color='#2ECC40'
        ))

        # 多頭支撐點 (紅色)
        fig.add_trace(go.Scatter(
            x=df['Date_Str'], y=df['SAR_Long'], name='多頭支撐', mode='markers',
            marker=dict(size=4, color='#FF4136', symbol='circle')
        ))

        # 空頭壓力點 (綠色)
        fig.add_trace(go.Scatter(
            x=df['Date_Str'], y=df['SAR_Short'], name='空頭壓力', mode='markers',
            marker=dict(size=4, color='#2ECC40', symbol='circle')
        ))

        # 新增 rangebreaks 或將 xaxis 類型改為 category 以消除缺口
        fig.update_layout(
            height=700,
            template=chart_template,
            xaxis_rangeslider_visible=False, # 隱藏滑動條讓圖表乾淨
            hovermode='x unified',
            font=dict(color=font_color),
            # 關鍵修正：將 xaxis 類型設為 category，配合 Date_Str 使用以忽略非交易日
            xaxis=dict(
                type='category', 
                color=font_color, 
                tickfont=dict(color=font_color),
                nticks=8  # 限制顯示的座標標籤數量，避免字體重疊
            ),
            yaxis=dict(color=font_color, tickfont=dict(color=font_color)),
            legend=dict(
                orientation="h", 
                yanchor="bottom", 
                y=1.02, 
                xanchor="center", 
                x=0.5,
                font=dict(color=font_color)
            ),
            paper_bgcolor=bg_color,
            plot_bgcolor=bg_color 
        )
        
        st.plotly_chart(fig, use_container_width=True)

        # ==============================================================================
        # 5. 數據摘要指標
        # ==============================================================================
        st.header("📊 最新狀態")
        valid_df = df.dropna(subset=['Close_1D'])
        
        if not valid_df.empty:
            last_price = valid_df['Close_1D'].iloc[-1]
            col1, col2, col3 = st.columns(3)
            
            is_long = not pd.isna(df['SAR_Long'].iloc[-1])
            trend_text = "看漲 (多頭)" if is_long else "看跌 (空頭)"
            trend_icon = "📈" if is_long else "📉"
            sar_val = df['SAR_Long'].iloc[-1] if is_long else df['SAR_Short'].iloc[-1]
            sar_label = "SAR 支撐位置" if is_long else "SAR 壓力位置"

            with col1:
                st.subheader("目前趨勢")
                st.markdown(f"### {trend_icon} {trend_text}")
            with col2:
                st.subheader("收盤價")
                st.markdown(f"### {last_price:.2f}")
            with col3:
                st.subheader(sar_label)
                st.markdown(f"### {sar_val:.2f}")
                
    else:
        st.error("找不到股票資料，請檢查代號是否正確。")

# 1.收盤價容許區間：
#     在上升趨勢中，判斷條件改為 c_close > curr_sar * 0.99。即使盤中低價穿過 SAR，只要收盤沒跌破 SAR 的 99%，趨勢就不會反轉，而是重置計算。
#     在下降趨勢中，則為 c_close < curr_sar * 1.01。
# 2.重置機制：
#     當觸發改良邏輯時，程式碼會執行 next_af = af_start（重置加速因子）以及 next_sar = c_low (或 c_high)，這能讓 SAR 點位更緊貼當日的影線。
# 3.繪圖銜接：
#     最後兩行將計算出的 SAR 根據 Trend 拆分回 SAR_Long 與 SAR_Short，這樣您後續的 Plotly 繪圖程式碼（紅點與綠點）完全不需要更動即可直接使用。