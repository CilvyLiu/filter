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
st.set_page_config(page_title="Nova 投行级新闻看板 (穿透版)", page_icon="🛡️", layout="wide")
st.title("🛡️ 投行级新闻板块穿透系统")
st.caption(f"系统时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 数据流状态: 穿透隔离模式")

# -----------------------------
# 2️⃣ 核心数据抓取 (RSS 镜像流)
# -----------------------------
@st.cache_data(ttl=600)
def fetch_news_stable():
    try:
        # 使用 Google News 聚合，确保 2026 年云端部署不被财联社 WAF 封锁
        url = "https://news.google.com/rss/search?q=财联社+并购+回购+IPO+板块+异动&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        root = ElementTree.fromstring(res.content)
        records = []
        for item in root.findall('.//item')[:50]:
            records.append({
                "title": item.find('title').text,
                "time": item.find('pubDate').text,
                "link": item.find('link').text
            })
        return pd.DataFrame(records)
    except:
        return pd.DataFrame()

# -----------------------------
# 3️⃣ 板块代码库与关联词簇 (核心扩充)
# -----------------------------
SECTOR_CONFIG = {
    "新能源": {"code": "BK0998", "keywords": ["锂电", "电池", "宁德", "储能", "电网", "光伏"]},
    "化工": {"code": "BK0436", "keywords": ["涨价", "材料", "磷", "氟", "产能", "炼化"]},
    "原材料": {"code": "BK0486", "keywords": ["水泥", "建材", "钢铁", "矿产", "金属"]},
    "医药": {"code": "BK0506", "keywords": ["生物", "创新药", "集采", "临床", "疫苗"]},
    "综合/重组": {"code": "BK0110", "keywords": ["并购", "重组", "股权", "壳资源", "资产"]},
    "光伏": {"code": "BK0933", "keywords": ["组件", "硅片", "隆基", "逆变器", "多晶硅"]},
    "AI": {"code": "BK1096", "keywords": ["大模型", "算力", "芯片", "英伟达", "智算"]},
    "元宇宙": {"code": "BK1009", "keywords": ["虚拟现实", "VR", "AR", "数字人", "沉浸"]},
    "低空经济": {"code": "BK1158", "keywords": ["无人机", "飞行汽车", "eVTOL", "空管"]},
    "科技": {"code": "BK0707", "keywords": ["半导体", "集成电路", "封测", "光刻机"]},
    "地产": {"code": "BK0451", "keywords": ["存量房", "房贷", "土拍", "收储", "保障房"]}
}

@st.cache_data(ttl=3600)
def get_sector_stocks():
    sector_data = {}
    for name, config in SECTOR_CONFIG.items():
        try:
            url = f"http://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=15&po=1&np=1&fltt=2&invt=2&fs=b:{config['code']}&fields=f12,f14"
            res = requests.get(url, timeout=5).json()
            stocks = [f"{item['f14']}({item['f12']})" for item in res.get('data', {}).get('diff', [])]
            sector_data[name] = stocks
        except:
            sector_data[name] = []
    return sector_data

# -----------------------------
# 4️⃣ 穿透映射逻辑
# -----------------------------
def filter_news_by_sector(news_df, sector_name):
    if news_df.empty: return news_df
    
    # 获取该板块的关联特征词
    config = SECTOR_CONFIG.get(sector_name, {})
    keywords = [sector_name] + config.get("keywords", [])
    
    # 投行通用高权词
    keywords += ["回购", "增持", "并购", "异动"]
    
    # 构建正则匹配模式
    pattern = "|".join(keywords)
    return news_df[news_df['title'].str.contains(pattern, case=False, na=False)]

# =========================
# 5️⃣ Streamlit UI
# =========================
st.sidebar.header("🔍 审计干预")
manual_key = st.sidebar.text_input("手动关键词搜索", placeholder="如：市值管理")

news_df = fetch_news_stable()
sector_map = get_sector_stocks()

if not news_df.empty:
    # --- 第一部分：板块深度穿透 ---
    st.subheader("🏭 板块深度穿透")
    selected_sector = st.selectbox("选择审计板块", list(SECTOR_CONFIG.keys()))
    
    c1, c2 = st.columns([1, 2])
    with c1:
        st.write(f"📌 **{selected_sector}** 核心成分股：")
        stocks = sector_map.get(selected_sector, [])
        if stocks:
            st.code("\n".join(stocks), language="text")
        else:
            st.warning("行情接口限流中")

    with c2:
        # 核心改进：根据选中的板块，自动穿透相关新闻
        st.write(f"📰 **{selected_sector}** 板块关联新闻：")
        sector_related_news = filter_news_by_sector(news_df, selected_sector)
        
        if not sector_related_news.empty:
            for _, row in sector_related_news.head(8).iterrows():
                with st.expander(f"{row['title']}"):
                    st.caption(f"发布时间: {row['time']}")
                    st.markdown(f"[原文链接]({row['link']})")
        else:
            st.info(f"当前流中暂无与 {selected_sector} 强相关的线索")

    st.divider()

    # --- 第二部分：全量审计流 ---
    st.subheader("🔍 全量新闻审计流")
    search_term = manual_key if manual_key else ""
    display_news = news_df[news_df['title'].str.contains(search_term)] if search_term else news_df
    
    for _, row in display_news.head(15).iterrows():
        with st.expander(f"{row['title']}"):
            st.write(f"发布时间: {row['time']}")
            st.markdown(f"[跳转原文]({row['link']})")
            # 标记该新闻命中了哪些板块
            hits = [name for name, cfg in SECTOR_CONFIG.items() if any(k in row['title'] for k in [name]+cfg['keywords'])]
            if hits:
                st.info(f"审计标记 - 关联板块: {', '.join(hits)}")

else:
    st.error("无法建立安全连接。Nova，请检查本地代理或云端防火墙设置。")

st.markdown("---")
st.caption("Nova 审计逻辑：第一通过词簇模糊映射，次之下钻成分股，终于全球 RSS 隔离抓取。")
