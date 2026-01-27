import streamlit as st
import akshare as ak
import pandas as pd
from datetime import datetime

# =====================================================
# 1. 页面配置（必须第一行）
# =====================================================
st.set_page_config(
    page_title="Nova 穿透式投研系统 · 板块版",
    page_icon="🛡️",
    layout="wide"
)

# =====================================================
# 2. 核心审计引擎（板块优先）
# =====================================================
class NovaAuditEngine:

    # -------------------------------
    # 政策 / 新闻信号模块
    # -------------------------------
    @staticmethod
    @st.cache_data(ttl=600)
    def fetch_smart_news():
        """
        获取政策新闻并计算关键词权重
        """
        try:
            df = ak.stock_telegraph_cls()
            if df.empty:
                return pd.DataFrame()

            df = df.rename(columns={
                '标题': 'title',
                '内容': 'content',
                '发布时间': 'time'
            })

            key_words = [
                '降准', '回购', '注销', '并购重组',
                '新质生产力', '低空经济', '红利', '增持'
            ]

            def detect_keywords(text):
                found = [w for w in key_words if w in str(text)]
                return ", ".join(found) if found else None

            df['signal'] = df['content'].apply(detect_keywords)
            df = df.dropna(subset=['signal'])

            if df.empty:
                return pd.DataFrame()

            df['weight'] = df['signal'].str.count(',') + 1
            df = df.sort_values('weight', ascending=False)

            return df

        except Exception as e:
            print(f"新闻取数失败: {e}")
            return pd.DataFrame()

    # -------------------------------
    # 行业板块列表
    # -------------------------------
    @staticmethod
    @st.cache_data(ttl=3600)
    def get_industry_boards():
        """
        获取东方财富行业板块
        """
        try:
            df = ak.stock_board_industry_name_em()
            df = df.rename(columns={
                '板块名称': 'industry',
                '涨跌幅': 'change_pct',
                '成交额': 'amount'
            })

            df['change_pct'] = pd.to_numeric(df['change_pct'], errors='coerce')
            df['amount'] = pd.to_numeric(df['amount'], errors='coerce')

            return df.dropna()

        except Exception as e:
            print(f"板块取数失败: {e}")
            return pd.DataFrame()

    # -------------------------------
    # 行业 → 个股穿透
    # -------------------------------
    @staticmethod
    @st.cache_data(ttl=1800)
    def get_industry_stocks(industry_name):
        """
        获取指定行业板块的成分股
        """
        try:
            df = ak.stock_board_industry_cons_em(symbol=industry_name)
            df = df.rename(columns={
                '代码': 'code',
                '名称': 'name',
                '最新价': 'price',
                '市盈率': 'pe',
                '市净率': 'pb'
            })

            for col in ['price', 'pe', 'pb']:
                df[col] = pd.to_numeric(df[col], errors='coerce')

            return df.dropna(subset=['pe', 'pb'])

        except Exception as e:
            print(f"板块穿透失败: {e}")
            return pd.DataFrame()


# =====================================================
# 3. UI 渲染层
# =====================================================
def main():

    st.title("🛡️ Nova 穿透式投研系统 · 行业板块版")
    st.caption(
        f"系统时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ｜ "
        f"路径：政策 → 板块 → 个股"
    )

    # -------------------------------
    # 侧边栏（估值过滤）
    # -------------------------------
    st.sidebar.header("⚖️ 审计过滤条件")
    max_pe = st.sidebar.slider("最大 PE", 5.0, 50.0, 20.0)
    max_pb = st.sidebar.slider("最大 PB", 0.5, 5.0, 2.0)

    # =================================================
    # 第一部分：政策信号看板
    # =================================================
    st.subheader("🚩 高权重政策信号")

    with st.spinner("正在解析最新政策信号..."):
        news_df = NovaAuditEngine.fetch_smart_news()

    if not news_df.empty:
        for _, row in news_df.head(5).iterrows():
            with st.expander(
                f"强度 {row['weight']} ｜ {row['signal']} ｜ {row['time']}",
                expanded=True
            ):
                st.write(row['content'])
    else:
        st.info("当前暂无高权重政策信号。")

    st.divider()

    # =================================================
    # 第二部分：行业板块选择
    # =================================================
    st.subheader("🏭 行业板块扫描")

    boards_df = NovaAuditEngine.get_industry_boards()

    if boards_df.empty:
        st.error("❌ 无法获取行业板块数据（云端 IP 可能受限）")
        return

    # 板块排序逻辑：成交额 + 涨跌幅
    boards_df = boards_df.sort_values(
        ['amount', 'change_pct'],
        ascending=False
    )

    selected_board = st.selectbox(
        "请选择一个行业板块进行穿透分析",
        boards_df['industry'].head(20)
    )

    # =================================================
    # 第三部分：板块内个股穿透
    # =================================================
    if selected_board:
        st.subheader(f"🎯 {selected_board} 板块 · 低溢价标的")

        with st.spinner("正在穿透板块成分股..."):
            stocks_df = NovaAuditEngine.get_industry_stocks(selected_board)

        if stocks_df.empty:
            st.warning("该板块暂无可用成分股数据。")
        else:
            final_df = stocks_df[
                (stocks_df['pe'] > 0) &
                (stocks_df['pe'] <= max_pe) &
                (stocks_df['pb'] <= max_pb)
            ].sort_values('pe')

            if final_df.empty:
                st.info("该板块暂无符合安全边际的个股。")
            else:
                st.success(
                    f"在 {selected_board} 板块中筛选出 "
                    f"{len(final_df)} 只低溢价标的"
                )
                st.dataframe(
                    final_df,
                    use_container_width=True,
                    hide_index=True
                )

    # =================================================
    # 底部说明
    # =================================================
    st.divider()
    st.markdown(
        """
        <div style="text-align:center; font-size:0.8em; color:gray;">
        Nova 方法论：<br>
        政策信号 → 行业板块 → 板块内估值穿透<br>
        本系统仅用于投研辅助，不构成投资建议
        </div>
        """,
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
