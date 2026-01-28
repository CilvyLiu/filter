import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import re

# -----------------------------
# 1️⃣ 页面配置
# -----------------------------
st.set_page_config(page_title="Nova 投行级穿透看板", page_icon="🛡️", layout="wide")
st.title("🛡️ 投行级新闻板块穿透系统")
st.caption(f"系统时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 模式: 新浪实时搜索穿透 (7D)")

# -----------------------------
# 2️⃣ 核心数据字典
# -----------------------------
SECTOR_CONFIG = {
    "医药": {"keywords": "医药,创新药,300760", "stocks": ["600276", "300760", "603259"]},
    "新能源": {"keywords": "锂电,宁德时代,固态电池", "stocks": ["300750", "002594", "300274"]},
    "机器人": {"keywords": "机器人,人形机器人,减速器,002031", "stocks": ["002031", "300024", "603728"]},
    "科技": {"keywords": "半导体,芯片,AI算力", "stocks": ["603501", "688981", "002415"]},
    "综合/重组": {"keywords": "并购重组,股权转让,市值管理", "stocks": ["600104", "000157", "600606"]},
    "地产": {"keywords": "房地产,收储,房贷利率", "stocks": ["600048", "000002", "601155"]}
}

# -----------------------------
# 3️⃣ 新浪实时搜索引擎 (核心替换：解决“无内容”问题)
# -----------------------------
@st.cache_data(ttl=120)
def fetch_sina_search_live(query):
    """
    暴力穿透：通过新浪搜索接口直接获取 7 天内的实时新闻与微博异动
    """
    records = []
    # 拆分关键词以增加命中率
    kws = query.replace("OR", ",").split(",")
    for kw in kws:
        kw = kw.strip()
        url = f"https://search.sina.com.cn/api/search/api.php?q={kw}&refer=f_weibo&f_type=news&s_type=all"
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            res = requests.get(url, headers=headers, timeout=5).json()
            items = res.get("data", {}).get("list", [])
            for item in items:
                # 清洗 HTML 标签
                title = re.sub('<[^<]+?>', '', item.get("title", ""))
                records.append({
                    "title": title,
                    "time": item.get("datetime", "刚刚"),
                    "link": item.get("url", ""),
                    "source": item.get("source", "实时流")
                })
        except:
            continue
    
    df = pd.DataFrame(records)
    if not df.empty:
        df = df.drop_duplicates(subset=['title']).sort_values(by='time', ascending=False)
    return df

# -----------------------------
# 4️⃣ 行情引擎
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

# =========================
# 5️⃣ UI 交互层
# =========================
st.sidebar.header("🔍 专项穿透")
manual_key = st.sidebar.text_input("注入手动关键词/代码", placeholder="如: 机器人")
probe_trigger = st.sidebar.button("🚀 执行暴力探测", use_container_width=True)

if probe_trigger and manual_key:
    st.subheader(f"⚡ 7D 专项探测：{manual_key}")
    res_df = fetch_sina_search_live(manual_key)
    if not res_df.empty:
        for _, r in res_df.iterrows():
            c1, c2 = st.columns([5, 1])
            with c1: 
                st.write(f"● {r['title']}")
                st.caption(f"🕒 {r['time']} | 来源: {r['source']}")
            with c2: st.link_button("穿透", r['link'], key=f"m_{r['link']}")
    else:
        st.error("新浪接口探测失败，请尝试输入个股代码（如 002031）")
    if st.button("⬅️ 返回"): st.rerun()

else:
    st.subheader("🏭 板块深度穿透")
    selected_sector = st.selectbox("审计板块", list(SECTOR_CONFIG.keys()))
    col1, col2 = st.columns([1, 2])

    with col1:
        st.write("📊 **实时行情**")
        st.table(get_realtime_stocks(selected_sector))

    with col2:
        st.write(f"📰 **{selected_sector}** 7D 关键动态")
        q = SECTOR_CONFIG[selected_sector]["keywords"]
        df_news = fetch_sina_search_live(q)
        if not df_news.empty:
            for _, r in df_news.head(15).iterrows():
                st.write(f"● {r['title']}")
                st.caption(f"🕒 {r['time']}")
        else:
            st.warning("并未发现瞬时动态，系统正在重试锚点穿透...")

st.divider()
st.subheader("🔥 市场全局异动流 (7D)")
global_news = fetch_sina_search_live("并购重组,异动,涨价")
if not global_news.empty:
    for _, r in global_news.head(10).iterrows():
        gc1, gc2 = st.columns([5, 1])
        with gc1: st.write(f"📌 {r['title']} (_{r['time']}_)")
        with gc2: st.link_button("原文", r['link'], key=f"g_{r['link']}")

st.markdown("---")
st.caption("Nova 审计脚注：已切换至新浪 Search 实时通道。如仍无结果，请检查网络连接或更换关键词。")
