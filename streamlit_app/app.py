"""主播成长看板 · Streamlit 版 — 飞书实时数据 + 多主播对比"""

import streamlit as st

st.set_page_config(
    page_title="主播成长看板",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 深色主题 CSS
st.markdown("""
<style>
    /* 全局深色主题 */
    .stApp { background: #0F1116; }
    .stMarkdown, .stText, p, span, div { color: #EAECF3; }
    .stMetric { background: #1B1F2A; border: 1px solid #232938; border-radius: 10px; padding: 14px 18px; }
    .stMetric label { color: #9298AA !important; font-size: 12px; }
    .stMetric [data-testid="stMetricValue"] { color: #EAECF3 !important; font-size: 28px; font-weight: 600; }
    .stMetric [data-testid="stMetricDelta"] { font-size: 13px; }

    /* 卡片容器 */
    .card { background: #1B1F2A; border: 1px solid #232938; border-radius: 12px; padding: 20px; margin-bottom: 14px; }

    /* Sidebar */
    [data-testid="stSidebar"] { background: #14171F; border-right: 1px solid #2B3242; }
    [data-testid="stSidebar"] * { color: #EAECF3 !important; }
    [data-testid="stSidebar"] select, [data-testid="stSidebar"] input { background: #0F1116; border: 1px solid #2B3242; color: #EAECF3; }

    /* 按钮 */
    .stButton > button { background: #1B1F2A; border: 1px solid #2B3242; color: #9298AA; border-radius: 9px; }
    .stButton > button:hover { border-color: #3a4356; color: #EAECF3; }

    /* 表格 */
    [data-testid="stTable"] { background: transparent; }
    [data-testid="stTable"] th { color: #5C6377 !important; font-size: 11px; text-transform: uppercase; letter-spacing: .06em; }
    [data-testid="stTable"] td { color: #EAECF3 !important; }

    /* 标签 */
    .stTabs [data-baseweb="tab-list"] { background: #14171F; border: 1px solid #232938; border-radius: 12px; padding: 5px; gap: 4px; }
    .stTabs [data-baseweb="tab"] { color: #9298AA; border-radius: 8px; }
    .stTabs [aria-selected="true"] { background: #222736 !important; color: #EAECF3 !important; }

    /* Header */
    .main-header { font-size: 24px; font-weight: 700; margin-bottom: 4px; }
    .sub-header { color: #9298AA; font-size: 13px; margin-bottom: 20px; }
</style>
""", unsafe_allow_html=True)

# 页面
overview = st.Page("pages/overview.py", title="概览", icon="📊")
ability = st.Page("pages/ability.py", title="能力评估", icon="🎯")
trend = st.Page("pages/trend.py", title="业绩对比", icon="📈")
plan = st.Page("pages/plan.py", title="成长计划", icon="📋")
review = st.Page("pages/review.py", title="复盘记录", icon="📝")

pg = st.navigation({
    "看板": [overview, trend, ability],
    "管理": [plan, review],
})
pg.run()
