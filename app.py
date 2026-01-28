import streamlit as st
import pandas as pd
import requests
from datetime import datetime
from collections import Counter

# -----------------------------
# 1️⃣ 页面配置
# -----------------------------
st.set_page_config(page_title="Nova 投行级穿透看板", page_icon="🛡️", layout="wide")
st.title("🛡️ 投行级新闻板块穿透系统")
st.caption(f"系统时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 模式: 东财 API 实时穿透")

# -----------------------------
# 2️⃣ 核心数据字典
# -----------------------------
SECTOR_CONFIG = {
    "医药": {"keywords": "医药, 创新药, 300760, 600276", "stocks": ["600276", "300760", "603259"]},
    "新能源": {"keywords": "锂电, 宁德时代, 储能, 300750", "stocks": ["300750", "002594", "300274"]},
    "科技": {"keywords": "芯片, 半导体, 华为, AI, 688981", "stocks": ["603501", "688981", "002415"]},
    "低空经济": {"keywords": "无人机, 飞行汽车, eVTOL, 002085", "stocks": ["002085", "000099", "600677"]},
    "化工": {"keywords": "化工涨价, 磷化工, 600309", "stocks": ["600309", "002493", "600096"]},
    "综合/重组": {"keywords": "并购重组, 股权转让, 市值管理", "stocks": ["600104", "000157", "600606"]},
    "地产": {"keywords": "房地产, 房贷利率, 万科, 000002", "stocks": ["600048", "000002", "601155"]}
}

# -----------------------------
# 3️⃣ 行情引擎
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
# 4️⃣ 核心探测引擎 (API 拆解增强版)
# -----------------------------
@st.cache_data(ttl=120)
def fetch_nova_engine(query="", is_social=False):
    records = []
    try:
        # 将 "A OR B" 或 "A,B" 统一拆分为列表
        keywords = [k.strip() for k in query.replace("OR", ",").split(",") if k.strip()]
        
        for kw in keywords:
            if is_social:
                # 社交接口
                url = f"http://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=8&po=1&np=1&ut=7eea3edcaed734bea9cbfc24409ed989&fid=f3&fs=b:MK0001&fields=f12,f14,f2,f13&q={kw}"
            else:
                # 新闻接口
                url = f"http://push2.eastmoney.com/api/qt/kcstock/get?pn=1&pz=8&po=1&np=1&ut=7eea3edcaed734bea9cbfc24409ed989&fid=f12&fields=f12,f14,f2,f13&q={kw}"
            
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url, headers=headers, timeout=5).json()
            items = response.get("data", {}).get("diff", [])

            for item in items:
                title = item.get("f14", item.get("f12", "无标题"))
                # 链接清洗：东财 API 有时返回纯 ID，需拼接
                raw_link = item.get("f13", "")
                link = raw_link if "http" in raw_link else f"https://finance.eastmoney.com/a/{raw_link}.html"
                
                records.append({
                    "title": title,
                    "time": datetime.fromtimestamp(item.get("f2", 0)).strftime('%m-%d %H:%M') if item.get("f2") else "刚刚",
                    "link": link,
                    "source": "🔥 社交/异动" if is_social else "📰 官方信源"
                })
        
        df = pd.DataFrame(records)
        if not df.empty:
            return df.drop_duplicates(subset=['title']) # 去除不同关键词命中的重复新闻
        return df
    except Exception as e:
        return pd.DataFrame(records)

# =========================
# 5️⃣ Streamlit UI 交互
# =========================

st.sidebar.header("🔍 审计控制台")
manual_key = st.sidebar.text_input("手动穿透 (代码/热词)", placeholder="如: 300760")
probe_trigger = st.sidebar.button("🚀 执行深度探测", use_container_width=True)

if probe_trigger and manual_key:
    st.subheader(f"⚡ 专项探测：{manual_key}")
    c1, c2 = st.columns(2)
    with c1:
        st.write("📖 **官方信源**")
        res_n = fetch_nova_engine(manual_key, is_social=False)
        if not res_n.empty:
            for _, r in res_n.iterrows():
                st.write(f"● {r['title']}")
                st.link_button("穿透原文", r['link'], key=f"n_{r['link']}")
        else: st.info("无相关动态")
    with c2:
        st.write("🧠 **社区情绪**")
        res_s = fetch_nova_engine(manual_key, is_social=True)
        if not res_s.empty:
            for _, r in res_s.iterrows():
                st.write(f"● {r['title']}")
                st.link_button("进入现场", r['link'], key=f"s_{r['link']}")
        else: st.info("讨论平稳")
    if st.button("⬅️ 重置"): st.rerun()

else:
    st.subheader("🏭 板块深度穿透")
    selected_sector = st.selectbox("审计板块", list(SECTOR_CONFIG.keys()))
    col1, col2 = st.columns([1, 2])

    with col1:
        st.write("📊 **实时行情**")
        st.table(get_realtime_stocks(selected_sector))

    with col2:
        st.write(f"📰 **{selected_sector}** 核心动态")
        q = SECTOR_CONFIG[selected_sector]["keywords"]
        df_sector = fetch_nova_engine(q, is_social=False)
        if not df_sector.empty:
            for _, row in df_sector.iterrows():
                st.write(f"● {row['title']} (_{row['time']}_)")
                st.link_button("阅读原文", row['link'], key=f"sec_{row['link']}")
        else:
            st.warning("💡 API 暂未匹配。请尝试在侧边栏手动输入个股代码穿透。")

st.markdown("---")
st.caption("Nova 审计脚注：采用 API 关键词 token 化技术，已自动清洗链接。")
