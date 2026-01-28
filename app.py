import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
from xml.etree import ElementTree
from email.utils import parsedate_to_datetime
import urllib.parse

# -----------------------------
# 1️⃣ 页面配置
# -----------------------------
st.set_page_config(page_title="Nova 投行级穿透看板", page_icon="🛡️", layout="wide")
st.title("🛡️ 投行级新闻板块穿透系统")
st.caption(f"系统时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 模式: 自动穿透板块关键词（中英文 Google News）")

# -----------------------------
# 2️⃣ 核心数据字典
# -----------------------------
SECTOR_CONFIG = {
    "医药": {"keywords": ["医药", "生物", "创新药", "集采", "pharma", "biotech", "drug"], "stocks": ["600276", "300760", "603259"]},
    "新能源": {"keywords": ["锂电", "宁德时代", "储能", "光伏", "lithium", "battery", "solar"], "stocks": ["300750", "002594", "300274"]},
    "科技": {"keywords": ["半导体", "芯片", "华为", "AI", "semiconductor", "chip", "Huawei", "artificial intelligence"], "stocks": ["603501", "688981", "002415"]},
    "低空经济": {"keywords": ["无人机", "飞行汽车", "eVTOL", "drone", "flying car"], "stocks": ["002085", "000099", "600677"]},
    "化工": {"keywords": ["化工", "涨价", "材料", "产能", "chemical", "materials"], "stocks": ["600309", "002493", "600096"]},
    "综合/重组": {"keywords": ["并购", "重组", "股权转让", "merger", "acquisition", "restructuring"], "stocks": ["600104", "000157", "600606"]},
    "地产": {"keywords": ["房地产", "收储", "存量房", "房贷", "real estate", "housing"], "stocks": ["600048", "000002", "601155"]}
}

# -----------------------------
# 3️⃣ 不限流个股行情（新浪）
# -----------------------------
@st.cache_data(ttl=60)
def get_realtime_stocks_sina(sector_name):
    stock_ids = SECTOR_CONFIG.get(sector_name, {}).get("stocks", [])
    if not stock_ids:
        return pd.DataFrame()
    formatted_ids = ",".join([f"sh{s}" if s.startswith('6') else f"sz{s}" for s in stock_ids])
    url = f"http://hq.sinajs.cn/list={formatted_ids}"
    try:
        headers = {"Referer": "http://finance.sina.com.cn", "User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=5).text
        data = []
        for line in res.splitlines():
            if '"' in line:
                p = line.split('"')[1].split(',')
                if len(p) > 4:
                    name = p[0]
                    price = float(p[3])
                    prev_close = float(p[2])
                    change = (price - prev_close) / prev_close * 100 if prev_close != 0 else 0
                    data.append({"名称": name, "最新价": f"{price:.2f}", "涨跌幅": f"{change:+.2f}%"})
        return pd.DataFrame(data)
    except:
        return pd.DataFrame()

# -----------------------------
# 4️⃣ Google News RSS 抓取（支持中英文）
# -----------------------------
@st.cache_data(ttl=300)
def fetch_news_google(keywords, days=7):
    records = []
    for kw in keywords:
        query = urllib.parse.quote(kw)
        rss_url = f"https://news.google.com/rss/search?q={query}&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"
        try:
            res = requests.get(rss_url, timeout=10)
            root = ElementTree.fromstring(res.content)
            for item in root.findall('.//item'):
                title = item.find('title').text
                link = item.find('link').text
                pub_date = item.find('pubDate')
                if pub_date is not None:
                    try:
                        pub_dt = parsedate_to_datetime(pub_date.text)
                    except:
                        pub_dt = datetime.utcnow()
                else:
                    pub_dt = datetime.utcnow()
                if datetime.utcnow() - pub_dt <= timedelta(days=days):
                    records.append({"title": title, "time": pub_dt, "link": link})
        except:
            continue
    df = pd.DataFrame(records)
    if not df.empty:
        df.drop_duplicates(subset=['title'], inplace=True)
        df.sort_values(by='time', ascending=False, inplace=True)
    return df

# =========================
# 5️⃣ Streamlit UI
# =========================
st.sidebar.header("🔍 审计搜索控制台")
manual_key = st.sidebar.text_input("注入手动关键词", placeholder="如：市值管理 / solid state battery")
probe_trigger = st.sidebar.button("🚀 执行穿透探测", use_container_width=True)
st.sidebar.divider()

# A模式：手动关键词穿透
if probe_trigger and manual_key:
    st.subheader(f"🚀 专项搜索：{manual_key}")
    with st.spinner(f"正在抓取 '{manual_key}' 相关线索..."):
        manual_news = fetch_news_google([manual_key])
    if not manual_news.empty:
        for _, row in manual_news.iterrows():
            c1, c2 = st.columns([5, 1])
            with c1:
                st.markdown(f"**{row['title']}**")
                st.caption(f"⏳ {row['time'].strftime('%Y-%m-%d %H:%M')}")
            with c2:
                st.link_button("穿透全文", row['link'], use_container_width=True)
        if st.button("⬅️ 重置看板视图"):
            st.rerun()
    else:
        st.warning(f"未发现与 '{manual_key}' 相关的最新线索。")

# B模式：板块自动穿透
st.subheader("🏭 板块深度穿透")
selected_sector = st.selectbox("选择审计板块", list(SECTOR_CONFIG.keys()))
col1, col2 = st.columns([1, 2])

with col1:
    st.write(f"📊 **{selected_sector}** 实时行情：")
    stock_df = get_realtime_stocks_sina(selected_sector)
    if not stock_df.empty:
        st.table(stock_df)
    else:
        st.info("行情接口同步中...")

with col2:
    st.write(f"📰 **{selected_sector}** 板块关联动态：")
    sector_news = fetch_news_google(SECTOR_CONFIG[selected_sector]["keywords"])
    if not sector_news.empty:
        for _, row in sector_news.iterrows():
            nc1, nc2 = st.columns([4, 1])
            with nc1:
                st.write(f"● {row['title']}")
                st.caption(f"_{row['time'].strftime('%Y-%m-%d %H:%M')}_")
            with nc2:
                st.link_button("🚀 穿透", row['link'], use_container_width=True)
    else:
        st.warning(f"💡 暂未发现与 {selected_sector} 相关的最新线索。")

st.divider()

# 全量流
st.subheader("🔥 实时早盘全量流")
all_news = fetch_news_google([kw for sector in SECTOR_CONFIG.values() for kw in sector["keywords"]])
if not all_news.empty:
    for _, row in all_news.head(10).iterrows():
        mc1, mc2 = st.columns([5, 1])
        with mc1:
            st.write(f"📌 {row['title']} (_{row['time'].strftime('%Y-%m-%d %H:%M')}_)")
        with mc2:
            st.link_button("原文", row['link'])
else:
    st.error("数据流受阻或近期无新新闻。")

st.markdown("---")
st.caption("Nova 审计脚注：新闻自动提取板块关键词（中英文 Google News），最近7天内，已去重并按时间排序。")
