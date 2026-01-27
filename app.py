import streamlit as st
import akshare as ak
import pandas as pd

class NovaAuditEngine:
    @staticmethod
    @st.cache_data(ttl=600)
    def fetch_smart_news():
        try:
            df = ak.stock_telegraph_cls()
            if df.empty: return pd.DataFrame()

            df = df.rename(columns={'标题': 'title', '内容': 'content', '发布时间': 'time'})
            
            # 这里的关键词建议增加“注销”、“限制性股票”等审计敏感词
            key_words = ['增持', '回购', '并购重组', '新质生产力', '低空经济', '红利', '注销']

            def detect_keywords(text):
                found = [w for w in key_words if w in str(text)]
                return ", ".join(found) if found else "常规监测"

            df['signal'] = df['content'].apply(detect_keywords)
            
            # Nova，这里应用了你设计的权重排序逻辑
            df = df[df['signal'] != "常规监测"].copy()
            if not df.empty:
                # 权重计算：关键词越多，权重越高
                df['weight'] = df['signal'].str.count(',') + 1
                df = df.sort_values('weight', ascending=False)
            
            return df
        except Exception:
            return pd.DataFrame()

    @staticmethod
    @st.cache_data(ttl=3600)
    def get_market_data():
        try:
            df = ak.stock_zh_a_spot_em()
            cols = {'代码': 'code', '名称': 'name', '最新价': 'price', 
                    '市盈率-动态': 'pe', '市净率': 'pb', '成交额': 'amount'}
            df = df[list(cols.keys())].rename(columns=cols)
            for col in ['price', 'pe', 'pb', 'amount']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            return df.dropna(subset=['pe', 'pb'])
        except Exception:
            return pd.DataFrame()
