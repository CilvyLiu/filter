import streamlit as st
import pandas as pd
import requests
from collections import Counter
from datetime import datetime
from xml.etree import ElementTree
import re

# -----------------------------
# 1️⃣ 页面配置
# -----------------------------
st.set_page_config(page_title="Nova 2026 穿透看板", page_icon="🛡️", layout="wide")
st.title("🛡️ 投行级 7D 全网穿透系统")
st.caption(f"系统时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 模式: 谷歌全网探测 + 2026热词库")

# -----------------------------
# 2️⃣ 2026 核心数据字典 (热词板块增加)
# -----------------------------
SECTOR_CONFIG = {
    "医药/生物": {"keywords": "(GLP-1 OR ADC药物 OR 创新药问询 OR 出海授权 OR 医疗合规)", "stocks": ["600276", "300760", "603259"]},
    "AI算力/封装": {"keywords": "(玻璃基板 OR HBM4 OR 算力租赁 OR 硅光模块 OR 先进封装)", "stocks": ["603501", "688012", "002415"]},
    "人形机器人": {"keywords": "(行星丝杠 OR 灵巧手 OR 减速器 OR 触觉传感器 OR 特斯拉机器人)", "stocks": ["603728", "300024", "002031"]},
    "商业航天/低空": {"keywords": "(eVTOL OR 千帆星座 OR 低空空域 OR 卫星互联网 OR 飞行汽车)", "stocks": ["002085", "600118", "300455"]},
    "新能源/储能": {"keywords": "(全固态电池 OR 钠离子电池 OR 构网型储能 OR 钙钛矿)", "stocks": ["300750", "002594", "300274"]},
    "科创重组/资本": {"keywords": "(科创板八条 OR 并购重组 OR 借壳 OR 资产注入 OR 举牌)", "stocks": ["600104", "000157", "600606"]},
    "地产/宏观": {"keywords": "(房地产收储 OR 存量房贷 OR 房地联动 OR 降息)", "stocks": ["600048", "000002", "601155"]}
}

# -----------------------------
# 3️⃣ 不限流个股行情 (腾讯源更稳)
# -----------------------------
@st.cache_data(ttl=60)
def get_realtime_stocks(sector_name):
    stock_ids = SECTOR_CONFIG.get(sector_name, {}).get("stocks", ["600519"])
    formatted_ids = ",".join([f"sh{s}" if s.startswith('6') else f"sz{s}" for s in stock_ids])
    url = f"http://qt.gtimg.cn/q={formatted_ids}"
    try:
        res = requests.get(url, timeout=5).text
        data = []
        for line in res.splitlines():
            if '~' in line:
                p = line.split('~')
                data.append({"名称": p[1], "最新价": p[3], "涨跌幅": f"{p[32]}%"})
        return pd.DataFrame(data)
    except:
        return pd.DataFrame()

# -----------------------------
# 4️⃣ 核心抓取引擎 (谷歌 7D 功能保留)
# -----------------------------
@st.cache_data(ttl=600)
def fetch_news_via_google(query=""):
    try:
        # 宽口径搜索：锁定 7 天内，包含主流财经源
        search_query = f"({query}) (site:cls.cn OR site:qq.com OR site:163.com OR site:sina.com.cn OR site:jiemian.com) when:7d"
        url = f"https://news.google.com/rss/search?q={search_query}&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"
        
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        root = ElementTree.fromstring(res.content)
        
        records = []
        for item in root.findall('.//item')[:25]:
            full_title = item.find('title').text
            title = full_title.rsplit(' - ', 1)[0] if ' - ' in full_title else full_title
            source = full_title.rsplit(' - ', 1)[1] if ' - ' in full_title else "全网"
            
            records.append({
                "source": source,
                "title": title,
                "time": item.find('pubDate').text[5:16],
                "link": item.find('link').text
            })
        return pd.DataFrame(records)
    except:
        return pd.DataFrame()

# -----------------------------
# 5️⃣ 热词统计函数
# -----------------------------
def analyze_hot_keywords(df):
    if df.empty: return []
    # 简单的分词清洗逻辑（去除无意义词）
    stop_words = ["财经", "新闻", "发布", "公司", "进行", "分析", "关注", "进行", "中国"]
    text = " ".join(df['title'].tolist())
    words = re.findall(r'\w{2,}', text) # 提取2字以上词
    filtered_words = [w for w in words if w not in stop_words and not w.isdigit()]
    return Counter(filtered_words).most_common(8)

# =========================
# 6️⃣ Streamlit UI 交互
# =========================

st.sidebar.header("🔍 审计搜索控制台")
manual_key = st.sidebar.text_input("注入手动关键词", placeholder="如：市值管理 / 固态电池")
probe_trigger = st.sidebar.button("🚀 执行穿透探测", use_container_width=True)
st.sidebar.divider()

if probe_trigger and manual_key:
    st.subheader(f"🚀 专项探测：{manual_key}")
    news = fetch_news_google(manual_key)
    if not news.empty:
        # 热词分析
        hot_tags = analyze_hot_keywords(news)
        st.write("🏷️ **动态热词统计：** " + " ".join([f"`{w[0]}({w[1]})`" for w in hot_tags]))
        st.dataframe(news, use_container_width=True, hide_index=True)
    else:
        st.warning("未能发现相关情报。")

else:
    # 1. 板块看板模式
    st.subheader("🏭 行业深度穿透")
    selected_sector = st.selectbox("选择审计板块", list(SECTOR_CONFIG.keys()))

    col1, col2 = st.columns([1, 2.5])

    with col1:
        st.write(f"📊 **{selected_sector}** 实时标的：")
        stock_df = get_realtime_stocks(selected_sector)
        if not stock_df.empty:
            st.table(stock_df)
            
        # 统计分析展示在行情下方
        st.divider()
        st.write("📈 **本周舆情热点分布**")
        q_words = SECTOR_CONFIG[selected_sector]["keywords"]
        sector_news = fetch_news_via_google(q_words)
        hot_tags = analyze_hot_keywords(sector_news)
        for tag, count in hot_tags:
            st.write(f"· {tag}")
            st.progress(min(count * 10, 100))

    with col2:
        st.write(f"📰 **{selected_sector}** 7D 关键动态：")
        if not sector_news.empty:
            for _, row in sector_news.iterrows():
                with st.container():
                    c_a, c_b = st.columns([5, 1])
                    c_a.markdown(f"**[{row['source']}]** {row['title']}")
                    c_a.caption(f"⏳ {row['time']}")
                    c_b.link_button("穿透", row['link'], use_container_width=True)
                    st.divider()
        else:
            st.info("并未发现瞬时动态，系统正在重试锚点穿透...")

st.divider()
# 2. 全量流
st.subheader("🔥 市场全局异动流 (7D回溯)")
main_news = fetch_news_via_google("并购重组 OR 股权转让 OR 异动 OR 举牌")
if not main_news.empty:
    st.dataframe(main_news[['time', 'source', 'title']], use_container_width=True, hide_index=True)

st.markdown("---")
st.caption("Nova 审计脚注：采用 7D 全网镜像联动逻辑。热词统计通过实时 NLP 语义提取生成。")
