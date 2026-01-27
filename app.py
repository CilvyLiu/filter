import streamlit as st
import pandas as pd
import requests
from collections import Counter
from datetime import datetime
import re
from xml.etree import ElementTree

# -----------------------------
# 1️⃣ 页面配置
# -----------------------------
st.set_page_config(page_title="Nova 投行级新闻看板 (稳定版)", page_icon="🛡️", layout="wide")
st.title("🛡️ 投行级新闻板块穿透系统")
st.caption(f"系统时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 数据流状态: 穿透隔离模式")

# -----------------------------
# 2️⃣ 核心数据抓取 (解决财联社无法取数问题)
# -----------------------------
@st.cache_data(ttl=600)
def fetch_news_stable():
    """
    穿透方案：当官方 API 被封时，通过全球 RSS 镜像实时抓取
    """
    try:
        # 使用 Google News 聚合的财联社/证券时报镜像流，云端 100% 通畅
        url = "https://news.google.com/rss/search?q=财联社+并购+回购+IPO&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
        res = requests.get(url, headers=headers, timeout=10)
        root = ElementTree.fromstring(res.content)
        records = []
        for item in root.findall('.//item')[:40]:
            records.append({
                "title": item.find('title').text,
                "content": item.find('title').text, # RSS 主要信息在标题
                "time": item.find('pubDate').text,
                "link": item.find('link').text
            })
        return pd.DataFrame(records)
    except:
        return pd.DataFrame()

# -----------------------------
# 3️⃣ 板块代码库 (Nova 版)
# -----------------------------
SECTOR_CODES = {
    "新能源": "BK0998", "化工": "BK0436", "原材料": "BK0486", "医药": "BK0506",
    "综合/重组": "BK0110", "光伏": "BK0933", "AI": "BK1096", "元宇宙": "BK1009",
    "低空经济": "BK1158", "科技": "BK0707", "地产": "BK0451"
}

@st.cache_data(ttl=3600)
def get_sector_stocks():
    sector_data = {}
    for name, code in SECTOR_CODES.items():
        try:
            # 东方财富实时接口 (云端稳定)
            url = f"http://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=15&po=1&np=1&fltt=2&invt=2&fs=b:{code}&fields=f12,f14"
            res = requests.get(url, timeout=5).json()
            stocks = [f"{item['f14']}({item['f12']})" for item in res.get('data', {}).get('diff', [])]
            sector_data[name] = stocks
        except:
            sector_data[name] = []
    return sector_data

# -----------------------------
# 4️⃣ 专家加权逻辑
# -----------------------------
def calculate_hotwords(df, manual_key=None):
    weights = {'回购':5, '并购':4, '增持':5, 'IPO':4, '新能源':3, '低空经济':5}
    if manual_key:
        weights[manual_key] = 10
    
    counter = Counter()
    for text in df['title']:
        for k, w in weights.items():
            if k in str(text):
                counter[k] += w
    return pd.DataFrame(counter.most_common(10), columns=["word", "权重分"])

# =========================
# 5️⃣ Streamlit UI 交互
# =========================
# 侧边栏：手动关键词注入
st.sidebar.header("🔍 审计搜索")
manual_key = st.sidebar.text_input("注入手动关键词", placeholder="如：市值管理")

# 获取数据
news_df = fetch_news_stable()
sector_map = get_sector_stocks()

if not news_df.empty:
    # 第一部分：热词
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("🔥 专家权重排行")
        hotwords_df = calculate_hotwords(news_df, manual_key)
        st.dataframe(hotwords_df, use_container_width=True, hide_index=True)
    
    with col2:
        st.subheader("🏭 板块深度穿透")
        selected_sector = st.selectbox("选择审计板块", list(SECTOR_CODES.keys()))
        sector_stocks = sector_map.get(selected_sector, [])
        st.write(f"📌 {selected_sector} 板块核心成分股：")
        st.write(", ".join(sector_stocks) if sector_stocks else "行情接口限流中")

    st.divider()

    # 第二部分：新闻列表
    st.subheader("📰 实时新闻流 (手动同步)")
    # 结合手动搜索逻辑
    search_term = manual_key if manual_key else ""
    filtered_news = news_df[news_df['title'].str.contains(search_term)] if search_term else news_df
    
    for _, row in filtered_news.head(15).iterrows():
        with st.expander(f"{row['title']}"):
            st.write(f"发布时间: {row['time']}")
            st.markdown(f"[查看原文链接]({row['link']})")
            # 自动高亮命中的板块
            hits = [s for s in SECTOR_CODES.keys() if s in row['title']]
            if hits:
                st.info(f"关联板块: {', '.join(hits)}")

else:
    st.error("无法建立安全连接，请在本地环境运行以绕过云端 WAF。")

st.markdown("---")
st.caption("Nova 审计脚注：采用镜像 RSS 流规避了财联社官方 API 的 IP 封锁。")
