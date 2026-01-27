import streamlit as st
import requests
import pandas as pd
from collections import Counter
from datetime import datetime

# --- 1. 页面配置 ---
st.set_page_config(page_title="2026政策热词 + 板块实时分析", layout="wide")

# =========================
# 1️⃣ 数据抓取逻辑 (保持高效请求)
# =========================
@st.cache_data(ttl=300)
def fetch_cls_news(limit=50):
    try:
        url = "https://www.cls.cn/nodeapi/telegraphs"
        # 增加伪装头防止云端阻断
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10).json()
        items = res.get("data", {}).get("roll_data", []) # 注意财联社字段结构
        if not items: items = res.get("data", [])
        
        records = []
        for item in items[:limit]:
            records.append({
                "title": item.get("title", ""),
                "content": item.get("content", ""),
                "time": datetime.fromtimestamp(item.get("ctime", 0))
            })
        return pd.DataFrame(records)
    except Exception as e:
        return pd.DataFrame()

@st.cache_data(ttl=1800)
def fetch_eastmoney_boards():
    try:
        url = ("https://push2.eastmoney.com/api/qt/clist/get?"
               "pn=1&pz=200&po=1&np=1&fltt=2&invt=2&fid=f3&fs=m:90+t:2+f:!50&fields=f12,f14,f3,f6")
        res = requests.get(url, timeout=10).json()
        data = res.get("data", {}).get("diff", [])
        if not data: return pd.DataFrame()
        df = pd.DataFrame(data).rename(columns={"f12": "code", "f14": "name", "f3": "change_pct", "f6": "amount"})
        return df
    except:
        return pd.DataFrame()

# =========================
# 2️⃣ 逻辑改写：合并关键词侦测
# =========================
def analyze_with_custom_keywords(news_df, manual_keyword):
    # 第一：预设专家级热词
    expert_keywords = {
        '回购注销': 5, '市值管理': 4, '新质生产力': 3, 
        '特别国债': 5, '并购重组': 4, '低空经济': 3
    }
    
    # 第二：合并手动输入关键词 (赋予最高权重)
    if manual_keyword:
        expert_keywords[manual_keyword] = 10 # 手动输入设为最高优先级
    
    def detect(text):
        content = str(text)
        found = [w for w in expert_keywords.keys() if w in content]
        score = sum([expert_keywords[w] for w in found])
        return score, ", ".join(found)

    if not news_df.empty:
        res = news_df['content'].apply(detect)
        news_df['weight'] = [x[0] for x in res]
        news_df['signals'] = [x[1] for x in res]
        return news_df[news_df['weight'] > 0].sort_values('weight', ascending=False)
    return news_df

# =========================
# 3️⃣ UI 渲染层
# =========================
st.title("📊 2026政策热词 & 板块穿透系统")

# 侧边栏：交互输入
st.sidebar.header("🔍 手动干预逻辑")
manual_key = st.sidebar.text_input("手动注入关键词 (实时合并搜索)", placeholder="如：固态电池")

# 获取数据
news_df = fetch_cls_news()
boards_df = fetch_eastmoney_boards()

# 第一部分：热词融合与搜索
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("🚩 政策权重看板 (自动热词 + 手动注入)")
    processed_news = analyze_with_custom_keywords(news_df.copy(), manual_key)
    
    if not processed_news.empty:
        for _, row in processed_news.head(10).iterrows():
            # 突出显示手动搜索到的词
            is_manual = manual_key and manual_key in row['signals']
            box_type = st.error if is_manual else st.info
            box_type(f"**【权重: {row['weight']} | 信号: {row['signals']}】** {row['time']}\n\n{row['content']}")
    else:
        st.info("当前暂无匹配的高权重信号。")

with col2:
    st.subheader("🏭 行业板块活跃度")
    if not boards_df.empty:
        # 按照成交额排序，撇掉无流动性的板块
        top_boards = boards_df.sort_values('amount', ascending=False).head(15)
        st.dataframe(top_boards[['name', 'change_pct']], hide_index=True)
    else:
        st.warning("板块数据获取受阻。")

# 第二部分：多源热词云提取
st.divider()
st.subheader("🔗 多源词频透视 (财联社 + 板块名)")
if not news_df.empty:
    all_text = " ".join(news_df['content'].astype(str)) + " ".join(boards_df['name'].astype(str))
    # 简单的词频过滤逻辑
    stop_words = ['关于', '进行', '已经', '目前', '通过', '发布']
    words = [w for w in all_text.replace('\n','').split() if len(w) > 1 and w not in stop_words]
    hot_counts = Counter(words).most_common(20)
    
    # 转换成 DataFrame 展示
    hot_df = pd.DataFrame(hot_counts, columns=['热词', '频率'])
    st.bar_chart(hot_df.set_index('热词'))

st.markdown("""
<div style='text-align:center; color:gray; font-size:0.8em;'>
系统逻辑：[手动关键词优先级10] + [专家关键词优先级3-5] -> 权重加权排序<br>
Nova，当前模式已撇掉表面溢价，直击政策核心。
</div>
""", unsafe_allow_html=True)
