import streamlit as st
import pandas as pd
import requests
from collections import Counter
from datetime import datetime
from xml.etree import ElementTree

# -----------------------------
# 1️⃣ 页面配置
# -----------------------------
st.set_page_config(page_title="Nova 投行级穿透看板 (稳定版)", page_icon="🛡️", layout="wide")
st.title("🛡️ 投行级新闻板块穿透系统")
st.caption(f"系统时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 模式: 镜像流+不限流行情")

# -----------------------------
# 2️⃣ 核心数据字典 (关联词簇 + 核心权重股)
# -----------------------------
# 增加 keywords 用于主动搜索镜像，增加 stocks 用于不限流行情展示
SECTOR_CONFIG = {
    "医药": {"keywords": "医药+生物+创新药+集采", "stocks": ["600276", "300760", "603259"]},
    "新能源": {"keywords": "锂电+宁德时代+储能+光伏", "stocks": ["300750", "002594", "300274"]},
    "科技": {"keywords": "半导体+芯片+华为+AI", "stocks": ["603501", "688981", "002415"]},
    "低空经济": {"keywords": "无人机+飞行汽车+eVTOL+空管", "stocks": ["002085", "000099", "600677"]},
    "化工": {"keywords": "化工+涨价+材料+产能", "stocks": ["600309", "002493", "600096"]},
    "综合/重组": {"keywords": "并购+重组+重组+股权转让", "stocks": ["600104", "000157", "600606"]}
}

# -----------------------------
# 3️⃣ 不限流个股行情接口 (新浪财经保底)
# -----------------------------
@st.cache_data(ttl=60)
def get_realtime_stocks(sector_name):
    """利用新浪财经 HTML 接口，规避东财 JSON 限流"""
    stock_ids = SECTOR_CONFIG.get(sector_name, {}).get("stocks", ["600519"])
    # 构造新浪格式 sh600276,sz300760
    formatted_ids = ",".join([f"sh{s}" if s.startswith('6') else f"sz{s}" for s in stock_ids])
    url = f"http://hq.sinajs.cn/list={formatted_ids}"
    
    try:
        # 新浪需要 Referer 伪装
        headers = {"Referer": "http://finance.sina.com.cn", "User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=5).text
        
        data = []
        for line in res.splitlines():
            if '"' in line:
                parts = line.split('"')[1].split(',')
                if len(parts) > 4:
                    name, price, prev_close = parts[0], float(parts[3]), float(parts[2])
                    change = (price - prev_close) / prev_close * 100
                    data.append({"名称": name, "最新价": f"{price:.2f}", "涨跌幅": f"{change:+.2f}%"})
        return pd.DataFrame(data)
    except:
        return pd.DataFrame()

# -----------------------------
# 4️⃣ 主动联动抓取新闻 (解决“没新闻”问题)
# -----------------------------
@st.cache_data(ttl=300)
def fetch_news_via_mirror(query=""):
    """
    联动逻辑：不再被动等待，而是根据板块 query 主动请求 Google/镜像 RSS
    """
    try:
        # 搜索组合：财联社 + 板块核心词
        search_query = f"财联社+{query}"
        url = f"https://news.google.com/rss/search?q={search_query}&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        root = ElementTree.fromstring(res.content)
        records = []
        for item in root.findall('.//item')[:15]:
            records.append({
                "title": item.find('title').text,
                "time": item.find('pubDate').text,
                "link": item.find('link').text
            })
        return pd.DataFrame(records)
    except:
        return pd.DataFrame()

# =========================
# 5️⃣ Streamlit UI 交互
# =========================
# 侧边栏
st.sidebar.header("🔍 审计搜索")
manual_key = st.sidebar.text_input("注入手动关键词", placeholder="如：回购")

# 全量早盘流 (默认加载)
all_news = fetch_news_via_mirror("并购+回购+IPO")

# UI 第一部分：板块深度穿透
st.subheader("🏭 板块深度穿透")
selected_sector = st.selectbox("选择审计板块", list(SECTOR_CONFIG.keys()))

col1, col2 = st.columns([1, 2])

with col1:
    st.write(f"📊 **{selected_sector}** 不限流权重表现：")
    stock_df = get_realtime_stocks(selected_sector)
    if not stock_df.empty:
        st.table(stock_df)
    else:
        st.info("数据接口同步中...")

with col2:
    st.write(f"📰 **{selected_sector}** 联动镜像新闻：")
    # 获取该板块对应的搜索关键词
    q = SECTOR_CONFIG[selected_sector]["keywords"]
    sector_news = fetch_news_via_mirror(q)
    
    if not sector_news.empty:
        for _, row in sector_news.iterrows():
            with st.expander(f"{row['title']}"):
                st.caption(f"发布时间: {row['time']}")
                st.markdown(f"[查看穿透原文]({row['link']})")
    else:
        st.warning(f"当前镜像流暂未发现与 {selected_sector} 相关的强特征线索。")

st.divider()

# UI 第二部分：热词与全量流
st.subheader("🔥 实时早盘审计流")
if not all_news.empty:
    for _, row in all_news.head(10).iterrows():
        st.write(f"● {row['title']} (_{row['time']}_)")
else:
    st.error("无法建立安全连接，镜像流受限。")

st.markdown("---")
st.caption("Nova 审计脚注：个股行情采用新浪 HTML 通道，新闻采用主动式关键词联动镜像。")
