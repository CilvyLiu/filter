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
st.caption(f"系统时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 模式: 腾讯行情+财联社语义穿透")

# -----------------------------
# 2️⃣ 2026 核心数据字典 (热词逻辑增强)
# -----------------------------
SECTOR_CONFIG = {
    "机器人/智造": {"keywords": "(机器人 OR 行星丝杠 OR 灵巧手 OR 减速器 OR 具身智能)", "stocks": ["603728", "300024", "002031"]},
    "AI算力/封装": {"keywords": "(玻璃基板 OR HBM4 OR 算力租赁 OR 硅光模块 OR CPO)", "stocks": ["603501", "688012", "002415"]},
    "商业航天/低空": {"keywords": "(eVTOL OR 千帆星座 OR 低空空域 OR 卫星互联网)", "stocks": ["002085", "600118", "300455"]},
    "医药/生物": {"keywords": "(GLP-1 OR ADC药物 OR 出海授权 OR 合成生物)", "stocks": ["600276", "300760", "603259"]},
    "新能源/储能": {"keywords": "(全固态电池 OR 钠电池 OR 构网型储能 OR 钙钛矿)", "stocks": ["300750", "002594", "300274"]},
    "重组/科创": {"keywords": "(并购重组 OR 科创板八条 OR 资产注入 OR 举牌 OR 借壳)", "stocks": ["600104", "000157", "600606"]},
    "地产/宏观": {"keywords": "(收储 OR 存量房贷 OR 房地联动 OR 专项债)", "stocks": ["600048", "000002", "601155"]}
}

# -----------------------------
# 3️⃣ 稳定行情接口：腾讯 Qt
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
                if len(p) > 32:
                    data.append({
                        "名称": p[1], 
                        "最新价": f"{float(p[3]):.2f}", 
                        "涨跌幅": f"{float(p[32]):+.2f}%"
                    })
        return pd.DataFrame(data)
    except:
        return pd.DataFrame()

# -----------------------------
# 4️⃣ 核心抓取引擎：Google RSS (7D)
# -----------------------------
@st.cache_data(ttl=600)
def fetch_news_via_google(query=""):
    try:
        search_query = f"({query}) (site:cls.cn OR site:jiemian.com OR site:stcn.com OR site:163.com OR site:qq.com OR site:sina.com.cn)"
        url = f"https://news.google.com/rss/search?q={search_query}+when:7d&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"
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
# 5️⃣ 热词分析 (财联社风格+A股深度扩展)
# -----------------------------
def analyze_hot_keywords(df):
    if df.empty: return []
    # 扩展：过滤非实质性词，保留 A 股核心题材词
    stop_words = [
        "财经", "新闻", "发布", "公司", "中国", "市场", "披露", "进行", "分析", "关注", 
        "研报", "证券", "表示", "机构", "持续", "核心", "板块", "业务", "正式", "亿元"
    ]
    # 强制关注词（提高权重）
    focus_words = [
        "量产", "破产", "借壳", "重组", "获批", "暴涨", "首发", "订单", "问询", "涨停"
    ]
    
    text = " ".join(df['title'].tolist())
    # 匹配中文词
    words = re.findall(r'[\u4e00-\u9fa5]{2,}', text) 
    
    filtered_words = []
    for w in words:
        if w not in stop_words:
            # 如果是重点词，增加出现权重
            if w in focus_words:
                filtered_words.extend([w] * 2)
            else:
                filtered_words.append(w)
                
    return Counter(filtered_words).most_common(10)

# =========================
# 6️⃣ UI 交互
# =========================

st.sidebar.header("🔍 审计搜索控制台")
manual_key = st.sidebar.text_input("注入手动关键词", placeholder="如：人形机器人 / 资产注入")
probe_trigger = st.sidebar.button("🚀 执行穿透探测", use_container_width=True)
st.sidebar.divider()

if probe_trigger and manual_key:
    st.subheader(f"🚀 专项探测：{manual_key} (7D)")
    news = fetch_news_via_google(manual_key)
    if not news.empty:
        hot_tags = analyze_hot_keywords(news)
        st.write("🏷️ **动态热词统计：** " + " ".join([f"`{w[0]}({w[1]})`" for w in hot_tags]))
        st.dataframe(news, use_container_width=True, hide_index=True)
    else:
        st.warning("未能穿透相关线索。")
else:
    # 默认看板
    st.subheader("🏭 行业深度穿透看板")
    selected_sector = st.selectbox("审计板块切换", list(SECTOR_CONFIG.keys()))
    col1, col2 = st.columns([1, 2.5])

    with col1:
        st.write(f"📊 **{selected_sector}** 实时行情：")
        stock_df = get_realtime_stocks(selected_sector)
        if not stock_df.empty:
            st.table(stock_df)
            
        st.divider()
        st.write("📈 **舆情热点词云 (财联社风控)**")
        q_words = SECTOR_CONFIG[selected_sector]["keywords"]
        sector_news = fetch_news_via_google(q_words)
        hot_tags = analyze_hot_keywords(sector_news)
        if hot_tags:
            for tag, count in hot_tags:
                st.write(f"· {tag}")
                st.progress(min(count * 10, 100))
        else:
            st.caption("暂未提取到足够频次的关键词。")

    with col2:
        st.write(f"📰 **{selected_sector}** 7D 关键动态穿透：")
        if not sector_news.empty:
            for _, row in sector_news.iterrows():
                with st.container():
                    c_a, c_b = st.columns([5, 1])
                    c_a.markdown(f"**[{row['source']}]** {row['title']}")
                    c_a.caption(f"⏳ {row['time']}")
                    c_b.link_button("穿透", row['link'], use_container_width=True)
                    st.divider()
        else:
            st.warning("⚠️ 探测受阻。")

st.divider()
st.subheader("🔥 市场全局异动流 (7D回溯)")
main_news = fetch_news_via_google("并购重组 OR 股权转让 OR 异动 OR 举牌 OR 可转债")
if not main_news.empty:
    st.dataframe(main_news[['time', 'source', 'title']], use_container_width=True, hide_index=True)

st.caption("Nova 审计脚注：采用腾讯 Qt + Google 7D 镜像穿透。热词统计已整合 A 股题材深度模型。")
