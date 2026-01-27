import streamlit as st
import akshare as ak
import pandas as pd
from datetime import datetime

# --- 1. 页面配置 (必须是第一行) ---
st.set_page_config(
    page_title="Nova 穿透式投研系统",
    page_icon="🛡️",
    layout="wide"
)

# --- 2. 核心逻辑引擎 ---
class NovaAuditEngine:
    @staticmethod
    @st.cache_data(ttl=600)
    def fetch_smart_news():
        """第一：获取最新政策电报并进行关键词权重计算"""
        try:
            # 使用财联社电报接口，稳定性较高
            df = ak.stock_telegraph_cls()
            if df.empty:
                return pd.DataFrame()

            df = df.rename(columns={'标题': 'title', '内容': 'content', '发布时间': 'time'})
            
            # 设定审计关注关键词
            key_words = ['增持', '回购', '并购重组', '新质生产力', '低空经济', '红利', '注销', '降准']

            def detect_keywords(text):
                found = [w for w in key_words if w in str(text)]
                return ", ".join(found) if found else "常规监测"

            # Nova 的权重算法实现
            df['signal'] = df['content'].apply(detect_keywords)
            # 过滤掉常规噪音，仅保留含关键词的信号
            signal_df = df[df['signal'] != "常规监测"].copy()
            
            if not signal_df.empty:
                # 计算权重：关键词数量 + 1
                signal_df['weight'] = signal_df['signal'].str.count(',') + 1
                # 按权重降序排列
                signal_df = signal_df.sort_values('weight', ascending=False)
                return signal_df
            return pd.DataFrame()
        except Exception as e:
            # 打印错误到后台日志，不打断前端渲染
            print(f"新闻取数异常: {e}")
            return pd.DataFrame()

    @staticmethod
    @st.cache_data(ttl=3600)
    def get_market_data():
        """次之：获取全市场行情并剥离溢价"""
        try:
            # A股实时行情快照
            df = ak.stock_zh_a_spot_em()
            if df.empty:
                return pd.DataFrame()

            cols = {
                '代码': 'code', '名称': 'name', '最新价': 'price',
                '市盈率-动态': 'pe', '市净率': 'pb', '成交额': 'amount'
            }
            df = df[list(cols.keys())].rename(columns=cols)

            # 强制数值转换，排除非数值噪音
            for col in ['price', 'pe', 'pb', 'amount']:
                df[col] = pd.to_numeric(df[col], errors='coerce')

            return df.dropna(subset=['pe', 'pb'])
        except Exception as e:
            print(f"行情取数异常: {e}")
            return pd.DataFrame()

# --- 3. UI 渲染层 ---
def main():
    st.title("🛡️ Nova 穿透式投研决策系统")
    st.caption(f"当前系统时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 数据源: 开源权威口径")

    # 侧边栏配置
    st.sidebar.header("⚖️ 审计降噪配置")
    target_pe = st.sidebar.slider("最大 PE 阈值 (撇掉表面溢价)", 5.0, 40.0, 15.0)
    target_pb = st.sidebar.slider("最大 PB 阈值 (防范估值泡沫)", 0.5, 5.0, 1.8)
    min_liquidity = st.sidebar.number_input("最小成交额 (过滤流动性陷阱)", value=80000000)

    # 第一部分：高权重政策信号侦测
    st.subheader("🚩 核心政策信号权重看板")
    with st.spinner("正在穿透最新政策动态..."):
        news_df = NovaAuditEngine.fetch_smart_news()
        
        if not news_df.empty:
            # 展示前 5 条最高权重信号
            display_news = news_df.head(5)
            for _, row in display_news.iterrows():
                with st.expander(f"强度 {row['weight']} | 关键词: {row['signal']} | {row['time']}", expanded=True):
                    st.write(row['content'])
        else:
            st.info("💡 当前暂无符合高权重关键词的政策异动。")

    st.divider()

    # 第二部分：全市场价值洼地扫描
    st.subheader("🎯 潜力资产筛选 (已撇掉溢价)")
    if st.button("🚀 执行全市场实时扫描", type="primary"):
        with st.spinner("正在执行多维审计过滤..."):
            market_df = NovaAuditEngine.get_market_data()
            
            if not market_df.empty:
                # 执行 Nova 过滤算法
                final_df = market_df[
                    (market_df['pe'] > 0) & (market_df['pe'] < target_pe) & 
                    (market_df['pb'] < target_pb) & (market_df['amount'] >= min_liquidity)
                ].sort_values('pe')

                if not final_df.empty:
                    st.success(f"审计完成！在全市场 5000+ 标的中锁定 {len(final_df)} 只低溢价资产。")
                    # 美化展示表格
                    st.dataframe(
                        final_df.style.background_gradient(subset=['pe'], cmap='RdYlGn_r'),
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.warning("当前筛选条件下未发现符合审计安全边际的资产。")
            else:
                st.error("❌ 无法获取实时行情。原因可能是云端服务器 IP 访问受限，请尝试在本地运行。")

    # 底部说明
    st.divider()
    st.markdown("""
    <div style='text-align: center; color: gray; font-size: 0.8em;'>
        系统逻辑：第一获取权威政策 -> 次之计算权重 -> 最后剥离财务溢价<br>
        本系统仅供 Nova 投研参考，不构成投资建议。
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
