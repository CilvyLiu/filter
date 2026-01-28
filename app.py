import streamlit as st
import pandas as pd
import requests
from collections import Counter
from datetime import datetime, timedelta
from xml.etree import ElementTree

# -----------------------------
# 1️⃣ 页面配置
# -----------------------------
st.set_page_config(page_title="Nova 投行级穿透看板", page_icon="🛡️", layout="wide")
st.title("🛡️ 投行级新闻板块穿透系统")
st.caption(f"系统时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 模式: 7天深度穿透 + 社交舆情矩阵")

# -----------------------------
# 2️⃣ 核心数据字典 (热词优化：采用 OR 逻辑提高命中率)
# -----------------------------
SECTOR_CONFIG = {
    "医药": {"keywords": "(医药 OR 生物 OR 创新药 OR 集采 OR 医疗器械)", "stocks": ["600276", "300760", "603259"]},
    "新能源": {"keywords": "(锂电 OR 宁德时代 OR 储能 OR 光伏 OR 固态电池)", "stocks": ["300750", "002594", "300274"]},
    "科技": {"keywords": "(半导体 OR 芯片 OR 华为 OR AI OR 算力)", "stocks": ["603501", "688981", "002415"]},
    "低空经济": {"keywords": "(无人机 OR 飞行汽车 OR eVTOL OR 商业航天)", "stocks": ["002085", "000099", "600677"]},
    "化工": {"keywords": "(化工 OR 涨价 OR 材料 OR 产能 OR 磷化工)", "stocks": ["600309", "002493", "600096"]},
    "综合/重组": {"keywords": "(并购 OR 重组 OR 股权转让 OR 借壳 OR 市值管理)", "stocks": ["600104", "000157", "600606"]},
    "地产": {"keywords": "(房地产 OR 收储 OR 存量房 OR 房贷 OR 城中村)", "stocks": ["600048", "000002", "601155"]}
}

# -----------------------------
# 3️⃣ 行情引擎 (新浪HTML通道)
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
# 4️⃣ 核心探测引擎 (新闻+情绪)
# -----------------------------
@st.cache_data(ttl=300) # 7天数据量大，增加缓存时间
def fetch_nova_engine(query="", is_social=False):
    """
    Nova 引擎：支持 7天 强制新闻探测或社交情绪探测
    """
    try:
        if is_social:
            # 情绪探测：扩充至 7 天，覆盖周末和深度讨论
            search_query = f"(雪球 OR 股吧 OR 讨论)+{query}+after:7d"
        else:
            # 官方新闻：盯防主流财经媒体 7 天内动态
            search_query = f"(财联社 OR 证券时报 OR 界面新闻 OR 第一财经)+{query}+after:7d"
            
        url = f"https://news.google.com/rss/search?q={search_query}&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"
        res = requests.get(url, timeout=10)
        root = ElementTree.fromstring(res.content)
        records = []
        for item in root.findall('.//item')[:15]:
            title = item.find('title').text
            # 过滤陈旧年份标题
            if any(yr in title for yr in ["2023", "2022"]): continue
            records.append({
                "title": title.split('-')[0].strip(),
                "time": item.find('pubDate').text,
                "link": item.find('link').text,
                "source": "🔥 社交/异动" if is_social else "📰 官方信源"
            })
        return pd.DataFrame(records)
    except:
        return pd.DataFrame()

# =========================
# 5️⃣ Streamlit UI 交互
# =========================

# 侧边栏：探测控制
st.sidebar.header("🔍 审计搜索控制台")
manual_key = st.sidebar.text_input("注入手动关键词", placeholder="如：固态电池 / 机器人")
probe_trigger = st.sidebar.button("🚀 执行 7天 全量穿透", use_container_width=True)
st.sidebar.divider()

if probe_trigger and manual_key:
    # A模式：主动搜索
    st.subheader(f"⚡ 7D 专项探测：{manual_key}")
    c1, c2 = st.columns(2)
    with c1:
        st.write("📖 **官方信源周报**")
        m_news = fetch_nova_engine(manual_key, is_social=False)
        if not m_news.empty:
            for _, r in m_news.iterrows():
                st.write(f"● {r['title']}")
                st.link_button("原文", r['link'], key=f"n_{r['link']}")
        else: st.info("本周暂无相关官方报道")
    with c2:
        st.write("🧠 **社交情绪周报**")
        s_news = fetch_nova_engine(manual_key, is_social=True)
        if not s_news.empty:
            for _, r in s_news.iterrows():
                st.write(f"● {r['title']}")
                st.link_button("讨论区", r['link'], key=f"s_{r['link']}")
        else: st.info("本周讨论热度较低")
    if st.button("⬅️ 重置看板"): st.rerun()

else:
    # B模式：默认看板模式
    st.subheader("🏭 板块深度穿透 (7天动态)")
    selected_sector = st.selectbox("选择审计板块", list(SECTOR_CONFIG.keys()))
    col1, col2 = st.columns([1, 2])

    with col1:
        st.write(f"📊 **{selected_sector}** 实时行情：")
        stock_df = get_realtime_stocks(selected_sector)
        if not stock_df.empty:
            st.table(stock_df)
        else: st.info("行情同步中...")

    with col2:
        st.write(f"📰 **{selected_sector}** 周内关联动态：")
        q_words = SECTOR_CONFIG[selected_sector]["keywords"]
        sector_news = fetch_nova_engine(q_words, is_social=False)
        if not sector_news.empty:
            for _, row in sector_news.iterrows():
                nc1, nc2 = st.columns([4, 1])
                with nc1:
                    st.write(f"● {row['title']}")
                    st.caption(f"_{row['time']}_")
                with nc2:
                    st.link_button("🚀 穿透", row['link'], use_container_width=True)
        else: st.warning("本周暂无深度关联动态。")

    st.divider()
    # 社交情绪模块
    st.subheader(f"🧠 {selected_sector} 社交热度/异动传闻 (7D)")
    sentiment_df = fetch_nova_engine(selected_sector, is_social=True)
    if not sentiment_df.empty:
        scs = st.columns(2)
        for i, (_, row) in enumerate(sentiment_df.iterrows()):
            with scs[i % 2]:
                st.info(f"{row['title']}")
                st.link_button("穿透雪球/股吧", row['link'], use_container_width=True)
    else: st.write("本周板块社交讨论平稳。")

st.divider()

# 2. 全量流（常驻底部）
st.subheader("🔥 实时周内全量探测 (7D)")
main_news = fetch_nova_engine("(并购 OR 重组 OR 借壳 OR 回购 OR 异动)", is_social=False)
if not main_news.empty:
    for _, row in main_news.head(15).iterrows():
        mc1, mc2 = st.columns([5, 1])
        with mc1:
            st.write(f"📌 {row['title']} (_{row['time']}_)")
        with mc2:
            st.link_button("原文", row['link'])

st.markdown("---")
st.caption("Nova 审计脚注：采用 after:7d 穿透深度，关键词已升级为 OR 逻辑矩阵。")
