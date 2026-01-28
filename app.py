import streamlit as st
import pandas as pd
import requests
from datetime import datetime
from xml.etree import ElementTree

# -----------------------------
# 1️⃣ 页面配置
# -----------------------------
st.set_page_config(page_title="Nova 2026 深度穿透看板", page_icon="🛡️", layout="wide")
st.title("🛡️ 2026 投行级全量穿透系统")
st.caption(f"系统时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 模式: 7日全网扫描 (高权权重源)")

# -----------------------------
# 2️⃣ 2026 A股核心热词字典 (由 Nova 审计准则定义)
# -----------------------------
SECTOR_CONFIG = {
    "AI算力/先进封装": {
        "keywords": "(玻璃基板 OR HBM4 OR 硅光模块 OR 2.5D封装 OR 算力租赁)", 
        "stocks": ["603501", "688012", "002415"] 
    },
    "人形机器人/智造": {
        "keywords": "(行星丝杠 OR 灵巧手 OR 减速器 OR 触觉传感器 OR 特斯拉机器人)", 
        "stocks": ["603728", "300024", "002031"]
    },
    "商业航天/低空": {
        "keywords": "(eVTOL运营 OR 千帆星座 OR 低空空域 OR 卫星互联网 OR 飞行汽车)", 
        "stocks": ["002085", "600118", "300455"]
    },
    "科创重组/资本运作": {
        "keywords": "(科创板八条 OR 并购重组 OR 借壳 OR 资产注入 OR 举牌 OR 股权激励)", 
        "stocks": ["600104", "000157", "601127"]
    },
    "合成生物/新材料": {
        "keywords": "(合成生物 OR 生物制造 OR PHA OR 基因编辑 OR 固态电池材料)", 
        "stocks": ["688065", "600873", "002493"]
    }
}

# -----------------------------
# 3️⃣ 行情接口：腾讯 Qt 增强型 (2026 稳健版)
# -----------------------------
@st.cache_data(ttl=60)
def get_realtime_stocks(sector_name):
    stock_ids = SECTOR_CONFIG.get(sector_name, {}).get("stocks", ["sh600519"])
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
# 4️⃣ 核心抓取引擎 (锁定7天周期 + 全网高权源)
# -----------------------------
@st.cache_data(ttl=600)
def fetch_news_7d_2026(query=""):
    try:
        # 2026 逻辑：强制穿透主流财经媒体，同时放开 Google 全网索引
        search_query = f"({query}) (site:cls.cn OR site:stcn.com OR site:163.com OR site:qq.com OR site:sina.com.cn OR site:jiemian.com) when:7d"
        url = f"https://news.google.com/rss/search?q={search_query}&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"
        
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        res = requests.get(url, headers=headers, timeout=10)
        root = ElementTree.fromstring(res.content)
        
        records = []
        for item in root.findall('.//item')[:30]: # 增加深度至30条
            full_title = item.find('title').text
            if " - " in full_title:
                title, source = full_title.rsplit(" - ", 1)
            else:
                title, source = full_title, "全网动态"
                
            records.append({
                "来源": source,
                "标题": title,
                "日期": item.find('pubDate').text[5:16],
                "link": item.find('link').text
            })
        return pd.DataFrame(records)
    except:
        return pd.DataFrame()

# =========================
# 5️⃣ Streamlit UI 交互
# =========================

st.sidebar.header("🔍 2026 深度审计控制台")
manual_key = st.sidebar.text_input("注入个股/新热词", placeholder="如：量子通信 / 脑机接口")
probe_trigger = st.sidebar.button("🚀 执行 7D 穿透", use_container_width=True)

if probe_trigger and manual_key:
    st.subheader(f"🛡️ 专项报告：{manual_key} (7日全扫)")
    manual_news = fetch_news_7d_2026(manual_key)
    if not manual_news.empty:
        st.dataframe(manual_news, column_config={"link": st.column_config.LinkColumn("原文")}, use_container_width=True, hide_index=True)
    else:
        st.warning("暂无相关显著波动。")

else:
    st.subheader("🏭 2026 行业周度态势感应")
    selected_sector = st.selectbox("选择审计赛道", list(SECTOR_CONFIG.keys()))
    
    col1, col2 = st.columns([1, 2.5])
    with col1:
        st.write(f"📊 **{selected_sector}** 核心标的：")
        st.table(get_realtime_stocks(selected_sector))
    
    with col2:
        st.write(f"📰 **{selected_sector}** 一周全网穿透：")
        q_words = SECTOR_CONFIG[selected_sector]["keywords"]
        sector_news = fetch_news_7d_2026(q_words)
        
        if not sector_news.empty:
            for _, row in sector_news.iterrows():
                with st.container():
                    c_a, c_b = st.columns([5, 1])
                    c_a.markdown(f"**[{row['来源']}]** {row['标题']}")
                    c_a.caption(f"📅 {row['日期']}")
                    c_b.link_button("阅读", row['link'], use_container_width=True)
                    st.divider()

st.divider()
st.subheader("🔥 2026 并购重组/股权异动池 (全量)")
main_news = fetch_news_7d_2026("并购重组 OR 股权转让 OR 借壳 OR 举牌")
if not main_news.empty:
    st.dataframe(main_news[['日期', '来源', '标题']], use_container_width=True)
