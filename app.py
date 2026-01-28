import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
from xml.etree import ElementTree

# -----------------------------
# 1️⃣ 页面配置
# -----------------------------
st.set_page_config(page_title="Nova 投行级穿透看板", page_icon="🛡️", layout="wide")
st.title("🛡️ 投行级新闻板块穿透系统")
st.caption(f"系统时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 模式: 官方 RSS + 手动关键词穿透")

# -----------------------------
# 2️⃣ 核心数据字典
# -----------------------------
SECTOR_CONFIG = {
    "医药": {"keywords": "医药+生物+创新药+集采", "stocks": ["600276", "300760", "603259"]},
    "新能源": {"keywords": "锂电+宁德时代+储能+光伏", "stocks": ["300750", "002594", "300274"]},
    "科技": {"keywords": "半导体+芯片+华为+AI", "stocks": ["603501", "688981", "002415"]},
    "低空经济": {"keywords": "无人机+飞行汽车+eVTOL", "stocks": ["002085", "000099", "600677"]},
    "化工": {"keywords": "化工+涨价+材料+产能", "stocks": ["600309", "002493", "600096"]},
    "综合/重组": {"keywords": "并购+重组+股权转让", "stocks": ["600104", "000157", "600606"]},
    "地产": {"keywords": "房地产+收储+存量房+房贷", "stocks": ["600048", "000002", "601155"]}
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
# 4️⃣ 官方 RSS 新闻抓取（支持一周内）
# -----------------------------
OFFICIAL_RSS = [
    # 交易所公告
    "http://www.sse.com.cn/rss/announcement/",
    "http://www.szse.cn/rss/news/",
    # 证监会新闻
    "http://www.csrc.gov.cn/pub/newsite/rss/news.xml",
    # 新华社财经
    "http://www.xinhuanet.com/finance/rss.xml"
]

@st.cache_data(ttl=300)
def fetch_official_news(query="", days=7):
    records = []
    cutoff = datetime.utcnow() - timedelta(days=days)
    for rss_url in OFFICIAL_RSS:
        try:
            res = requests.get(rss_url, timeout=10)
            root = ElementTree.fromstring(res.content)
            for item in root.findall('.//item')[:50]:  # 取最新50条
                title = item.find('title').text or ""
                link = item.find('link').text or ""
                pub_date = item.find('pubDate').text or ""
                try:
                    pub_dt = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %Z")
                except:
                    pub_dt = datetime.utcnow()
                # 仅保留指定天数内
                if pub_dt < cutoff:
                    continue
                # 关键词过滤
                if query.lower() in title.lower():
                    records.append({"title": title, "time": pub_date, "link": link})
        except Exception as e:
            print(f"抓取 {rss_url} 失败:", e)
    return pd.DataFrame(records)

# =========================
# 5️⃣ Streamlit UI 交互
# =========================
st.sidebar.header("🔍 审计搜索控制台")
manual_key = st.sidebar.text_input("注入手动关键词", placeholder="如：市值管理 / 固态电池")
probe_trigger = st.sidebar.button("🚀 执行穿透探测", use_container_width=True)
st.sidebar.divider()

# 主屏逻辑
if probe_trigger and manual_key:
    st.subheader(f"🚀 专项搜索：{manual_key}")
    with st.spinner(f"抓取 '{manual_key}' 相关官方线索..."):
        news_df = fetch_official_news(manual_key)
    if not news_df.empty:
        for _, row in news_df.iterrows():
            c1, c2 = st.columns([5, 1])
            with c1:
                st.markdown(f"**{row['title']}**")
                st.caption(f"⏳ {row['time']}")
            with c2:
                st.link_button("穿透全文", row['link'], use_container_width=True)
            st.divider()
    else:
        st.warning(f"未发现与 '{manual_key}' 相关的官方线索。")
else:
    # 板块默认看板
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
        st.write(f"📰 **{selected_sector}** 官方新闻/公告（7天）:")
        q_words = SECTOR_CONFIG[selected_sector]["keywords"]
        sector_news = fetch_official_news(q_words, days=7)
        if not sector_news.empty:
            for _, row in sector_news.iterrows():
                nc1, nc2 = st.columns([4, 1])
                with nc1:
                    st.write(f"● {row['title']}")
                    st.caption(f"_{row['time']}_")
                with nc2:
                    st.link_button("🚀 穿透", row['link'], use_container_width=True)
        else:
            st.warning(f"💡 暂未发现与 {selected_sector} 相关的一周官方线索。")

st.divider()
st.markdown("---")
st.caption("Nova 审计脚注：使用官方 RSS 来源（交易所公告 + 证监会 + 新华社财经），支持 7 天新闻穿透。")
