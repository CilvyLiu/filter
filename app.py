import streamlit as st
import pandas as pd
import requests
from collections import Counter
from datetime import datetime
import re

# -----------------------------
# 1️⃣ 页面配置
# -----------------------------
st.set_page_config(
    page_title="投行级早盘新闻板块穿透 (2026版)",
    page_icon="🛡️",
    layout="wide"
)
st.title("🛡️ 投行级早盘新闻板块穿透系统")
st.caption(f"系统时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# -----------------------------
# 2️⃣ 新闻抓取 (财联社 / 21财经 / 证券时报)
# 这里用示例接口，实际可替换为官方 JSON 接口
# -----------------------------
@st.cache_data(ttl=300)
def fetch_news():
    # 这里使用示例 RSS / JSON
    try:
        url = "https://www.cls.cn/nodeapi/telegraphs"  # 财联社接口示例
        res = requests.get(url, timeout=10).json()
        items = res.get("data", [])[:50]  # 最新50条
        records = []
        for item in items:
            records.append({
                "title": item.get("title"),
                "content": item.get("content"),
                "time": datetime.fromtimestamp(item.get("ctime", datetime.now().timestamp()))
            })
        return pd.DataFrame(records)
    except:
        return pd.DataFrame()

# -----------------------------
# 3️⃣ 热词排行榜
# -----------------------------
def extract_hotwords(df, top_n=20):
    counter = Counter()
    for text in df['content']:
        # 简单中文分词
        words = re.findall(r'[\u4e00-\u9fff]{2,5}', str(text))
        counter.update(words)
    hotwords = counter.most_common(top_n)
    return pd.DataFrame(hotwords, columns=["word", "count"])

# -----------------------------
# 4️⃣ 板块成分股抓取 (东方财富免费接口)
# -----------------------------
@st.cache_data(ttl=3600)
def get_sector_stocks():
    sector_codes = {
        "新能源": "BK0998",
        "化工": "BK0436",
        "原材料": "BK0486",
        "医药": "BK0506",
        "综合/重组": "BK0110",
        "光伏": "BK0933",
        "AI": "BK1096",
        "元宇宙": "BK1009",
        "低空经济": "BK1158",
        "科技": "BK0707",
        "地产": "BK0451"
    }
    sector_data = {}
    for name, code in sector_codes.items():
        try:
            url = f"http://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=5000&po=1&np=1&fltt=2&invt=2&fs=b:{code}&fields=f12,f14"
            res = requests.get(url, timeout=10).json()
            stocks = []
            for item in res.get('data', {}).get('diff', []):
                stocks.append(f"{item['f14']}({item['f12']})")
            sector_data[name] = stocks
        except:
            sector_data[name] = []
    return sector_data

# -----------------------------
# 5️⃣ 新闻 → 板块映射
# -----------------------------
def map_news_to_sector(news_df, sector_map):
    news_df['板块'] = ""
    news_df['相关股票'] = ""
    for idx, row in news_df.iterrows():
        sectors_hit = []
        stocks_hit = []
        for sector, tickers in sector_map.items():
            for keyword in [sector, "并购", "回购", "IPO", "增持"]:
                if keyword in str(row['content']):
                    sectors_hit.append(sector)
                    stocks_hit.extend(tickers)
                    break
        news_df.at[idx, '板块'] = ", ".join(list(set(sectors_hit)))
        news_df.at[idx, '相关股票'] = ", ".join(list(set(stocks_hit)))
    return news_df

# -----------------------------
# 6️⃣ 股票最新价格 (新浪财经)
# -----------------------------
@st.cache_data(ttl=300)
def get_stock_prices(stock_list):
    data = []
    batch = [",".join(["sh"+s[1:-1] if s[1]=="6" else "sz"+s[1:-1] for s in stock_list[i:i+50]]) 
             for i in range(0, len(stock_list), 50)]
    for codes in batch:
        try:
            url = f"http://hq.sinajs.cn/list={codes}"
            res = requests.get(url, timeout=10).text.splitlines()
            for line, s in zip(res, stock_list):
                match = re.findall(r'"(.*?)"', line)
                if match:
                    fields = match[0].split(",")
                    if len(fields)>3:
                        price = float(fields[3])
                        data.append({"股票": s, "最新价": price})
                    else:
                        data.append({"股票": s, "最新价": None})
                else:
                    data.append({"股票": s, "最新价": None})
        except:
            data.append({"股票": s, "最新价": None})
    return pd.DataFrame(data)

# =========================
# Streamlit UI
# =========================
news_df = fetch_news()
sector_map = get_sector_stocks()
news_df = map_news_to_sector(news_df, sector_map)

# -------------------------
# 热词排行榜
# -------------------------
st.subheader("🔥 热词排行榜")
if not news_df.empty:
    hotwords_df = extract_hotwords(news_df)
    st.dataframe(hotwords_df, use_container_width=True)
else:
    st.warning("暂无新闻可提取热词")

# -------------------------
# 板块新闻穿透
# -------------------------
st.subheader("🏭 板块新闻穿透")
sector_list = list(sector_map.keys())
selected_sector = st.selectbox("选择板块查看新闻", sector_list)
sector_news = news_df[news_df['板块'].str.contains(selected_sector)]
if not sector_news.empty:
    for _, row in sector_news.iterrows():
        with st.expander(f"{row['title']} | {row['time']}"):
            st.write(row['content'])
            st.write(f"📌 相关股票: {row['相关股票']}")
else:
    st.info(f"{selected_sector}板块暂无新闻")

# -------------------------
# 手动关键词搜索
# -------------------------
st.subheader("🔍 手动关键词搜索")
manual_key = st.text_input("输入关键词搜索新闻")
if manual_key:
    manual_news = news_df[news_df['content'].str.contains(manual_key, na=False)]
    if not manual_news.empty:
        for _, row in manual_news.iterrows():
            with st.expander(f"{row['title']} | {row['time']}"):
                st.write(row['content'])
                st.write(f"📌 相关股票: {row['相关股票']}")
    else:
        st.info("暂无匹配新闻")

# -------------------------
# 板块相关股票最新价格
# -------------------------
st.subheader("📊 板块相关股票最新价格")
all_stocks = list({s for s_list in news_df['相关股票'] for s in s_list.split(',') if s})
if all_stocks:
    prices_df = get_stock_prices(all_stocks)
    st.table(prices_df)
else:
    st.info("暂无新闻涉及的股票")
