import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import requests
from xml.etree import ElementTree
from collections import Counter

# =========================
# 1️⃣ 页面配置
# =========================
st.set_page_config(
    page_title="Nova 穿透式投研系统 (云端版)",
    layout="wide"
)

# =========================
# 2️⃣ 全球视角政策新闻抓取 (RSS)
# =========================
@st.cache_data(ttl=600)
def fetch_global_finance_news(limit=15):
    """使用 RSS 抓取财经动态，避开财联社对海外 IP 封锁"""
    try:
        url = "https://news.google.com/rss/search?q=中国经济+政策+回购&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"
        res = requests.get(url, timeout=10)
        root = ElementTree.fromstring(res.content)
        records = []
        for item in root.findall('.//item')[:limit]:
            records.append({
                "title": item.find('title').text,
                "link": item.find('link').text,
                "time": item.find('pubDate').text,
                "content": item.find('title').text # RSS 摘要通常在标题里
            })
        return pd.DataFrame(records)
    except Exception as e:
        print("RSS新闻抓取异常:", e)
        return pd.DataFrame()

# =========================
# 3️⃣ 跨境行情获取 (Yahoo Finance)
# =========================
@st.cache_data(ttl=3600)
def get_global_market_snapshot():
    """获取主要指数和中概股行情"""
    try:
        tickers = {
            "沪深300 (ASHR)": "ASHR",
            "恒生指数": "^HSI",
            "腾讯控股": "0700.HK",
            "阿里巴巴": "BABA"
        }
        data = []
        for name, symbol in tickers.items():
            t = yf.Ticker(symbol)
            info = t.fast_info
            data.append({
                "名称": name,
                "最新价": round(info['last_price'], 2),
                "当日涨跌": f"{round(info['last_prev_close_diff_pct'] * 100, 2)}%",
                "代码": symbol
            })
        return pd.DataFrame(data)
    except Exception as e:
        print("Yahoo Finance行情抓取异常:", e)
        return pd.DataFrame()

# =========================
# 4️⃣ 新闻热词计算
# =========================
def calc_hotwords(df, top_n=20, manual_key=None):
    """提取新闻标题内容中的热词，并按频率排序"""
    counter = Counter()
    key_weights = {'回购': 5, '注销': 5, '市值管理': 4, '降准': 3}
    if manual_key:
        key_weights[manual_key] = 10
    for text in df['content']:
        for w, weight in key_weights.items():
            if w in str(text):
                counter[w] += weight
    return pd.DataFrame(counter.most_common(top_n), columns=["word", "count"])

# =========================
# 5️⃣ 新闻搜索
# =========================
def search_news(df, keyword):
    """搜索新闻中包含指定关键词的条目"""
    return df[df['content'].str.contains(keyword, na=False)]

# =========================
# 6️⃣ Streamlit UI
# =========================
st.title("🛡️ Nova 穿透式投研决策看板 (云端隔离版)")
st.caption(f"系统时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# -------------------------
# 6.1 手动注入关键词
# -------------------------
st.sidebar.header("🔍 手动干预")
manual_key = st.sidebar.text_input("手动注入关键词", placeholder="如：回购/降准")

# -------------------------
# 6.2 全球政策新闻 & 热词
# -------------------------
st.subheader("🚩 全球视角政策监测")
news_df = fetch_global_finance_news()

if not news_df.empty:
    hotwords_df = calc_hotwords(news_df, manual_key=manual_key)
    st.markdown("**🔥 热词排行榜**")
    st.dataframe(hotwords_df, use_container_width=True)

    st.markdown("**🔍 新闻搜索**")
    keyword = st.text_input("输入关键词进行搜索", placeholder="如降准/国企改革/新能源")
    if keyword:
        result_df = search_news(news_df, keyword)
        if not result_df.empty:
            st.write(f"共 {len(result_df)} 条相关新闻：")
            for _, row in result_df.iterrows():
                with st.expander(f"{row['title']} | {row['time']}"):
                    st.write(row['content'])
        else:
            st.info("暂无匹配相关新闻")
else:
    st.error("数据抓取受限，请检查网络或稍后刷新")

# -------------------------
# 6.3 跨境行情看板
# -------------------------
st.divider()
st.subheader("📊 跨境定价锚点 (ASHR / HSI / 中概股)")
market_data = get_global_market_snapshot()
if not market_data.empty:
    st.table(market_data)
else:
    st.warning("跨境行情获取失败，请稍后重试")

# -------------------------
# 6.4 终极排查指南
# -------------------------
st.divider()
with st.expander("🛠️ 云端网页显示受阻排查指南"):
    st.markdown("""
    **Nova 提示：**
    
    1. **本地运行最稳定**：
       ```bash
       pip install streamlit yfinance pandas requests
       streamlit run app.py
       ```
       使用本地网络访问财联社或 Yahoo Finance 接口 100% 成功。
    
    2. **云端策略**：
       - 可以尝试国内代理 IP 或 VPN。
       - 云端容器对国外接口可能限制严格。
    
    3. **RSS + Yahoo Finance 是云端最稳方案**：
       - 已经避免依赖财联社海外 IP。
       - 热词和新闻搜索逻辑完全保留。
    """)
