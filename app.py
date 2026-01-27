import streamlit as st
import akshare as ak
import pandas as pd
from datetime import datetime

# --- 页面配置 ---
st.set_page_config(page_title="Nova 穿透式投研系统", layout="wide", initial_sidebar_state="collapsed")

class NovaAuditEngine:
    @st.cache_data(ttl=3600)
    def fetch_macro_news():
        """第一：获取最新权威宏观动态"""
        try:
            # 财联社电报数据，实时性极强，适合政治经济动向监控
            news_df = ak.js_news(src="mainstream") 
            return news_df[['datetime', 'content']].head(15)
        except:
            # 备选方案：新浪财经
            try:
                return ak.stock_info_global_news().head(10)
            except:
                return pd.DataFrame({"content": ["宏观接口流受限，请稍后刷新"]})

    @st.cache_data(ttl=600) # 行情数据缓存10分钟
    def get_market_snapshot():
        """次之：获取全A股实时行情及估值指标"""
        try:
            # 东方财富接口，响应速度快且稳定
            df = ak.stock_zh_a_spot_em()
            # 字段对齐：代码, 名称, 最新价, 涨跌额, 市盈率-动态, 市净率, 成交额
            # 对应原始列：'代码', '名称', '最新价', '涨跌额', '市盈率-动态', '市净率', '成交额'
            cols_map = {
                '代码': 'code', '名称': 'name', '最新价': 'price', 
                '涨跌额': 'change', '市盈率-动态': 'pe', '市净率': 'pb', '成交额': 'amount'
            }
            df = df[list(cols_map.keys())].rename(columns=cols_map)
            # 数据类型清洗
            df[['price', 'pe', 'pb', 'amount']] = df[['price', 'pe', 'pb', 'amount']].apply(pd.to_numeric, errors='coerce')
            return df
        except Exception as e:
            st.error(f"行情获取失败: {e}")
            return pd.DataFrame()

    @staticmethod
    def audit_filter(df, pe_threshold, pb_threshold, min_amount=50_000_000):
        """最后：统一的审计降噪过滤逻辑"""
        if df.empty:
            return df
        
        # 1. 估值剥离：剔除亏损(PE<=0)及高溢价
        # 2. 流动性过滤：成交额小于 min_amount (默认5000万) 的视为市场噪音，不具操作性
        mask = (
            (df['pe'] > 0) & 
            (df['pe'] < pe_threshold) & 
            (df['pb'] < pb_threshold) & 
            (df['pb'] > 0) &
            (df['amount'] >= min_amount)
        )
        filtered = df[mask].copy()
        
        # 排序：按 PE 升序，寻找估值洼地
        return filtered.sort_values('pe', ascending=True)

# --- 系统实例化 ---
engine = NovaAuditEngine

# --- UI 界面 ---
st.title("🛡️ Nova 顶级投研决策系统")
st.markdown("---")

# 1. 宏观对齐 (权威消息流)
st.subheader("📡 宏观政治经济动向 (Real-time Signal)")
news_data = engine.fetch_macro_news()
if not news_data.empty:
    with st.container():
        # 滚动展示或展示前3条最重要信息
        for i in range(3):
            content = news_data.iloc[i]['content']
            st.info(f"**[{datetime.now().strftime('%H:%M')}]** {content[:200]}...")

# 2. 参数与筛选
st.sidebar.header("📊 审计过滤参数")
target_pe = st.sidebar.slider("最大允许 PE (溢价控制)", 5, 50, 15)
target_pb = st.sidebar.slider("最大允许 PB (资产溢价)", 0.5, 5.0, 1.5)
min_liquidity = st.sidebar.number_input("最低成交额 (流动性过滤)", value=50000000, step=10000000)

if st.button("🚀 执行全市场穿透扫描"):
    raw_data = engine.get_market_snapshot()
    
    if not raw_data.empty:
        # 执行审计降噪
        final_df = engine.audit_filter(raw_data, target_pe, target_pb, min_liquidity)
        
        # 统计摘要
        c1, c2, c3 = st.columns(3)
        c1.metric("扫描标的总数", f"{len(raw_data)}")
        c2.metric("通过初筛标的", f"{len(final_df)}")
        c3.metric("筛选率", f"{round(len(final_df)/len(raw_data)*100, 2)}%")

        # 结果呈现
        st.subheader("🎯 穿透后高潜力标的清单 (已剔除表面溢价)")
        st.dataframe(
            final_df.style.background_gradient(subset=['pe'], cmap='RdYlGn_r'),
            use_container_width=True,
            hide_index=True
        )
        
        st.success("扫描完成。建议下一步：对上述标的进行『现金流/利润』质量穿透。")
    else:
        st.error("无法获取实时行情，请检查网络连接或接口状态。")

# --- 底部审计逻辑说明 ---
st.markdown("---")
st.caption("🔍 **审计专家系统逻辑说明：** 本程序已自动执行 $PE \in (0, PE_{max})$ 及 $Liquidity > Threshold$ 的强校验，有效规避僵尸股及博傻溢价。")
