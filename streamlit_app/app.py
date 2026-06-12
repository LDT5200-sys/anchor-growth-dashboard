"""主播成长看板 · Streamlit 版 — 飞书实时数据 + 多主播对比"""

import streamlit as st

st.set_page_config(
    page_title="主播成长看板",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 页面
overview = st.Page("pages/overview.py", title="概览", icon="📊")
ability = st.Page("pages/ability.py", title="能力评估", icon="🎯")
trend = st.Page("pages/trend.py", title="业绩对比", icon="📈")
returns = st.Page("pages/returns.py", title="退货率分析", icon="📉")
plan = st.Page("pages/plan.py", title="成长计划", icon="📋")
review = st.Page("pages/review.py", title="复盘记录", icon="📝")

pg = st.navigation({
    "看板": [overview, trend, returns],
    "管理": [ability, plan, review],
})
pg.run()
