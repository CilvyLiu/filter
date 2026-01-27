import streamlit as st
import pandas as pd
import requests
from xml.etree import ElementTree
from collections import Counter
from datetime import datetime
import akshare as ak

# ------------------------
# 1️⃣ 页面配置
# ------------------------
st.set_page_config(
    page_title="Nova A股投行+行业决策看板",
    page_icon="🛡️",
    layout="wide"
)

# ------------------------
# 2️⃣ 配置字典 (由 Nova 提供并优化对齐)
# ------------------------
KEY_WEIGHTS = {
    # 投行及政策类
    '回购': 5, '增持': 5, '并购': 4, 'IPO': 4, '限售解禁': 4, '分红': 3, '降准': 3, '注册制': 3, '融资融券': 2,
    # 行业及板块类
    '化工': 4, '原材料': 4, '新能源': 4, '医药': 4, '科技': 4, '地产': 3, '能源': 4, '钢铁': 3, '电池': 3, '光伏': 3
}

# 映射字典：确保与 AkShare/同花顺标准名对齐
KEYWORD_TO_SECTOR = {
    '新能源': '电力设备',
    '化工': '基础化工',
    '原材料': '建筑材料',
    '医药': '医药生物',
    '科技': '半导体及元件',
    '地产': '房地产开发',
    '能源': '石油加工贸易',
    '钢铁': '钢铁',
    '电池': '电力设备',
    '光伏': '光伏设备',
    '回购': '中字头',
    '增持': '沪深300',
    '并购': '资产重组',
    'IPO': '次新股'
}

# ------------------------
# 3️⃣ 数据抓取 (不封 IP 版)
# ------------------------
@st.cache_data(ttl=600)
def fetch_ib_news(limit=35):
    """通过 RSS 抓取投行及行业政策新闻"""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        # 搜索组合：合并了你提供的所有核心热词
        search_query = "投资银行+并购+回购+IPO+化工+原材料+新能源+医药"
        url = f"https://news.google.com/rss/search?q={search_query}&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"
        res = requests.get(url, headers=headers, timeout=10)
        root = ElementTree.fromstring(res.content)
        records = []
        for item in root.findall('.//item')[:limit]:
            records.append({
                "title": item.find('title').text,
                "link": item.find('link').text,
                "time": item.find('pubDate').text,
                "content": item.find('title').text
            })
        return pd.DataFrame(records)
    except Exception as e:
        return pd.DataFrame()

# ------------------------
# 4️⃣ 核心处理逻辑
# ------------------------
def calculate_hotwords(df, manual_key=None):
    """应用 Nova 专家权重字典"""
    current_weights = KEY_WEIGHTS.copy()
    if manual_key:
        current_weights[manual_key] = 10  # 手动干预设为最高权重

    counter = Counter()
    for text in df['content']:
        for k, w in current_weights.items():
            if k in str(text):
                counter[k] += w
    
    res_df = pd.DataFrame(counter.most_common(20), columns=["word", "权重分"])
    res_df['板块'] = res_df['word'].apply(lambda x: KEYWORD_TO_SECTOR.get(x, '其他/综合'))
    return res_df

@st.cache_data(ttl=1800)
def get_sector_stocks(sector_name):
    """下钻获取 A 股成分股行情"""
    if sector_name in ['其他/综合', '综合']: return pd.DataFrame()
    try:
        # 路径 A: 同花顺行业成分 (本地运行成功率极高)
        df = ak.stock_board_cons_ths(symbol=sector_name)
        return df[['股票代码', '股票名称', '最新价', '涨跌幅']].head(20)
    except:
        return pd.DataFrame()

# ------------------------
# 5️⃣ UI 渲染层
# ------------------------
st.title("🛡️ Nova A股投行+行业决策看板")
st.caption(f"系统时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 数据流模式: RSS 穿透隔离")

# 7.1 侧边栏
st.sidebar.header("🔍 审计干预")
manual_key = st.sidebar.text_input("注入临时关键词", placeholder="如：市值管理")

# 获取数据
news_df = fetch_ib_news()

if not news_df.empty:
    # 7.2 热词排行榜
    st.subheader("🔥 实时热度权重榜")
    hotwords_df = calculate_hotwords(news_df, manual_key)
    st.dataframe(hotwords_df, use_container_width=True, hide_index=True)

    # 布局展示
    col1, col2 = st.columns([2, 3])

    with col1:
        st.subheader("📰 最新政策快讯")
        for _, row in news_df.head(10).iterrows():
            with st.expander(f"{row['title']}", expanded=False):
                st.write(f"发布时间: {row['time']}")
                st.markdown(f"[原文链接]({row['link']})")

    with col2:
        st.subheader("🏭 行业穿透行情")
        # 联动：根据热度榜选择板块
        sector_options = [s for s in hotwords_df['板块'].unique() if s != '其他/综合']
        if sector_options:
            selected_sector = st.selectbox("选择热点板块查看成分股", sector_options)
            if selected_sector:
                stocks = get_sector_stocks(selected_sector)
                if not stocks.empty:
                    st.success(f"已锁定 {selected_sector} 核心成分股行情")
                    st.dataframe(stocks, use_container_width=True, hide_index=True)
                else:
                    st.info(f"云端接口暂无法直接穿透 {selected_sector} 行情，建议本地运行。")
        else:
            st.info("当前热词暂无特定行业映射，请查看宏观快讯。")

    # 7.3 搜索功能
    st.divider()
    st.subheader("🔍 深度穿透搜索")
    search_key = st.text_input("搜索新闻全文", placeholder="输入关键词...")
    if search_key:
        search_res = news_df[news_df['content'].str.contains(search_key)]
        st.write(f"共发现 {len(search_res)} 条关联信息：")
        st.dataframe(search_res[['time', 'title']], use_container_width=True)

else:
    st.error("❌ 数据源连接受阻。请检查 AkShare 是否更新到最新版本，或在本地网络环境下运行。")

# 7.4 审计脚注
st.markdown("---")
st.markdown("""
<div style='text-align:center; color:gray; font-size:0.8em;'>
逻辑：[RSS抓取] -> [词权加分] -> [行业映射] -> [行情下钻]<br>
Nova，当前系统已集成你提供的所有行业映射，实现了从政策到个股的穿透审计。
</div>
""", unsafe_allow_html=True)
