import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
from xml.etree import ElementTree
from email.utils import parsedate_to_datetime

# -----------------------------
# 1️⃣ 页面配置
# -----------------------------
st.set_page_config(page_title="Nova 投行级穿透看板", page_icon="🛡️", layout="wide")
st.title("🛡️ 投行级新闻板块穿透系统")
st.caption(f"系统时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 模式: 自动穿透板块关键词")

# -----------------------------
# 2️⃣ 核心数据字典
# -----------------------------
SECTOR_CONFIG = {
    "医药": {"keywords": ["医药", "生物", "创新药", "集采"], "stocks": ["600276", "300760", "603259"]},
    "新能源": {"keywords": ["锂电", "宁德时代", "储能", "光伏"], "stocks": ["300750", "002594", "300274"]},
    "科技": {"keywords": ["半导体", "芯片", "华为", "AI"], "stocks": ["603501", "688981", "002415"]},
    "低空经济": {"keywords": ["无人机", "飞行汽车", "eVTOL"], "stocks": ["002085", "000099", "600677"]},
    "化工": {"keywords": ["化工", "涨价", "材料", "产能"], "stocks": ["600309", "002493", "600096"]},
    "综合/重组": {"keywords": ["并购", "重组", "股权转让"], "stocks": ["600104", "000157", "600606"]},
    "地产": {"keywords": ["房地产", "收储", "存量房", "房贷"], "stocks": ["600048", "000002", "601155"]}
}

# -----------------------------
# 3️⃣ 不限流个股行情接口
# -----------------------------
@st.cache_data(ttl=60)
def get_realtime_stocks(sector_name):
    stock_ids = SECTOR_CONFIG.get(sector_name, {}).get("stocks", ["600519"])
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
                    name, price, prev_close = p[0], float(p[3]), float(p[2])
                    change = (price - prev_close) / prev_close * 100
                    data.append({"名称": name, "最新价": f"{price:.2f}", "涨跌幅": f"{change:+.2f}%"})
        return pd.DataFrame(data)
    except:
        return pd.DataFrame()

# -----------------------------
# 4️⃣ 自动抓取板块新闻（最近7天）
# -----------------------------
@st.cache_data(ttl=300)
def fetch_news_for_sector(sector_name, days=7):
    try:
        keywords = SECTOR_CONFIG.get(sector_name, {}).get("keywords", [])
        if not keywords:
            return pd.DataFrame()
        
        records = []
        # 针对每个关键词抓取
        for kw in keywords:
            search_query = f"财联社 {kw}"
            url = f"https://news.google.com/rss/search?q={search_query}&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"
            res = requests.get(url, timeout=10)
            root = ElementTree.fromstring(res.content)
            for item in root.findall('.//item')[:50]:
                title = item.find('title').text
                pub_date = item.find('pubDate').text
                link = item.find('link').text
                try:
                    pub_dt = parsedate_to_datetime(pub_date)
                except:
                    pub_dt = datetime.utcnow()
                if datetime.utcnow() - pub_dt <= timedelta(days=days):
                    records.append({"title": title, "time": pub_dt, "link": link})
        
        # 去重标题并按时间排序
        df = pd.DataFrame(records)
        if not df.empty:
            df.drop_duplicates(subset=['title'], inplace=True)
            df.sort_values(by='time', ascending=False, inplace=True)
        return df
    except Exception as e:
        print("抓取失败:", e)
        return pd.DataFrame()

# =========================
# 5️⃣ Streamlit UI 交互
# =========================
st.sidebar.header("🔍 审计搜索控制台")
probe_trigger = st.sidebar.button("🚀 执行板块自动穿透", use_container_width=True)
st.sidebar.divider()

# B模式：板块默认看板
st.subheader("🏭 板块深度穿透")
selected_sector = st.selectbox("选择审计板块", list(SECTOR_CONFIG.keys()))
col1, col2 = st.columns([1, 2])

with col1:
    st.write(f"📊 **{selected_sector}** 实时行情：")
    stock_df = get_realtime_stocks(selected_sector)
    if not stock_df.empty:
        st.table(stock_df)
    else:
        st.info("行情接口同步中...")

with col2:
    st.write(f"📰 **{selected_sector}** 板块关联动态：")
    if probe_trigger:
        sector_news = fetch_news_for_sector(selected_sector)
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
main_news = fetch_news_for_sector("综合/重组")
if not main_news.empty:
    for _, row in main_news.head(10).iterrows():
        mc1, mc2 = st.columns([5, 1])
        with mc1:
            st.write(f"📌 {row['title']} (_{row['time'].strftime('%Y-%m-%d %H:%M')}_)")
        with mc2:
            st.link_button("原文", row['link'])
else:
    st.error("数据流受阻或近期无新新闻。")

st.markdown("---")
st.caption("Nova 审计脚注：新闻自动提取板块关键词，最近7天内，已去重并按时间排序。")
