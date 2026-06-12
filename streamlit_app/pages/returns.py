"""退货率分析页：基于飞书缓存的 BI 数据"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import requests
import time
from collections import defaultdict
from feishu_client import fmt_date

BASE_URL = "https://open.feishu.cn/open-apis"
BASE_TOKEN = "Jwu7bRyHvagQ4Hsv8ExcPiOOnnd"
TABLE_RETURNS = None  # 动态查找

APP_ID = "cli_a876dccb3d7a101c"
APP_SECRET = "eTURY2xNmRaSBR6nratpsdn86ENxssTA"

@st.cache_data(ttl=1800, show_spinner="📡 加载退货率数据...")
def load_return_data():
    """从飞书 BI退货率数据缓存 表读取聚合数据"""
    # 获取 token
    r = requests.post(f"{BASE_URL}/auth/v3/tenant_access_token/internal",
        json={"app_id": APP_ID, "app_secret": APP_SECRET}, timeout=15)
    token = r.json()["tenant_access_token"]
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"}

    # 找到退货率表
    r = requests.get(f"{BASE_URL}/bitable/v1/apps/{BASE_TOKEN}/tables", headers=headers, timeout=15)
    tables = r.json().get("data", {}).get("items", [])
    table_id = None
    for t in tables:
        if "退货率" in t.get("name", ""):
            table_id = t["table_id"]
            break

    if not table_id:
        return [], "未找到 BI退货率数据缓存 表，请先运行缓存脚本"

    # 读取全部记录
    items = []
    page_token = None
    while True:
        params = {"page_size": 500}
        if page_token:
            params["page_token"] = page_token
        r = requests.get(
            f"{BASE_URL}/bitable/v1/apps/{BASE_TOKEN}/tables/{table_id}/records",
            params=params, headers=headers, timeout=60)
        data = r.json()
        if data.get("code") != 0:
            return [], f"API错误: {data.get('msg')}"
        d = data.get("data", {})
        items.extend(d.get("items", []))
        if d.get("has_more") and d.get("page_token"):
            page_token = d["page_token"]
        else:
            break

    records = [r["fields"] for r in items]
    return records, None


st.title("📉 退货率分析")

records, error = load_return_data()

if error:
    st.info(f"💡 {error}")
    st.stop()

if not records:
    st.warning("暂无退货率数据")
    st.stop()

st.caption(f"数据来源：BI退货率数据缓存 · 共 {len(records):,} 条聚合记录")

# === 筛选器 ===
col1, col2, col3 = st.columns(3)

# 商品列表
products = sorted(set(r.get("商品名称", "") for r in records if r.get("商品名称")))
with col1:
    sel_product = st.selectbox("商品", ["全部"] + products)

# 日期范围
dates = sorted(set(r.get("订单日期", "") for r in records if r.get("订单日期")))
with col2:
    date_range = st.selectbox("时间", ["全部"] + dates[-10:] if len(dates) > 10 else ["全部"] + dates)

# 渠道
channels = sorted(set(r.get("销售渠道", "") for r in records if r.get("销售渠道")))
with col3:
    sel_channel = st.selectbox("渠道", ["全部"] + channels)

# 筛选
filtered = records
if sel_product != "全部":
    filtered = [r for r in filtered if r.get("商品名称") == sel_product]
if date_range != "全部":
    filtered = [r for r in filtered if r.get("订单日期") == date_range]
if sel_channel != "全部":
    filtered = [r for r in filtered if r.get("销售渠道") == sel_channel]

# === 汇总指标 ===
total_sales = sum(r.get("销售额", 0) or 0 for r in filtered)
total_returns = sum(r.get("退货额", 0) or 0 for r in filtered)
overall_rate = round(total_returns / total_sales * 100, 1) if total_sales > 0 else 0

c1, c2, c3 = st.columns(3)
c1.metric("总销售额", f"¥{total_sales/10000:.1f}万")
c2.metric("总退货额", f"¥{total_returns/10000:.1f}万")
c3.metric("整体退货率", f"{overall_rate}%")

st.divider()

# === 按日期退货率趋势 ===
tab1, tab2, tab3 = st.tabs(["📈 日期趋势", "🏷️ 商品对比", "👤 达人对比"])

with tab1:
    st.subheader("每日退货率趋势")
    by_date = defaultdict(lambda: {"sales": 0, "returns": 0})
    for r in filtered:
        d = r.get("订单日期", "")
        by_date[d]["sales"] += r.get("销售额", 0) or 0
        by_date[d]["returns"] += r.get("退货额", 0) or 0

    sorted_dates = sorted(by_date.keys())
    rates = [
        round(by_date[d]["returns"] / by_date[d]["sales"] * 100, 1)
        if by_date[d]["sales"] > 0 else 0
        for d in sorted_dates
    ]
    sales_vals = [by_date[d]["sales"] for d in sorted_dates]

    fig = go.Figure()
    fig.add_trace(go.Bar(x=[fmt_date(d) for d in sorted_dates], y=sales_vals,
                          name="销售额", marker_color="#E8E8E8", yaxis="y2"))
    fig.add_trace(go.Scatter(x=[fmt_date(d) for d in sorted_dates], y=rates,
                              name="退货率%", mode="lines+markers",
                              line=dict(color="#E53935", width=2.5), marker=dict(size=6)))
    fig.update_layout(height=380, yaxis=dict(title="退货率 %", side="left", range=[0, max(rates)*1.3 if rates else 10]),
                      yaxis2=dict(title="销售额", overlaying="y", side="right", showgrid=False),
                      legend=dict(orientation="h"), margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("商品退货率排名")
    by_prod = defaultdict(lambda: {"sales": 0, "returns": 0})
    for r in filtered:
        p = r.get("商品名称", "")
        by_prod[p]["sales"] += r.get("销售额", 0) or 0
        by_prod[p]["returns"] += r.get("退货额", 0) or 0

    prod_data = []
    for p, v in by_prod.items():
        rate = round(v["returns"] / v["sales"] * 100, 1) if v["sales"] > 0 else 0
        prod_data.append({"商品": p, "退货率%": rate, "销售额": v["sales"], "退货额": v["returns"]})
    prod_data.sort(key=lambda x: x["退货率%"], reverse=True)

    st.dataframe(prod_data, use_container_width=True, hide_index=True,
                 column_config={"退货率%": st.column_config.NumberColumn(format="%.1f%%"),
                               "销售额": st.column_config.NumberColumn(format="¥%.0f")})

    # 图表
    fig = px.bar(prod_data[:15], x="商品", y="退货率%", color="退货率%",
                 color_continuous_scale="Reds")
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.subheader("达人退货率排名")
    by_anchor = defaultdict(lambda: {"sales": 0, "returns": 0})
    for r in filtered:
        a = r.get("达人名称", "") or "未知"
        by_anchor[a]["sales"] += r.get("销售额", 0) or 0
        by_anchor[a]["returns"] += r.get("退货额", 0) or 0

    anchor_data = []
    for a, v in by_anchor.items():
        rate = round(v["returns"] / v["sales"] * 100, 1) if v["sales"] > 0 else 0
        anchor_data.append({"达人": a, "退货率%": rate, "销售额": v["sales"]})
    anchor_data.sort(key=lambda x: x["退货率%"], reverse=True)

    st.dataframe(anchor_data, use_container_width=True, hide_index=True)

    fig = px.bar(anchor_data[:15], x="达人", y="退货率%", color="退货率%",
                 color_continuous_scale="Reds")
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)
