"""退货率分析页：蝉管家主播维度退货率数据"""

import streamlit as st
import plotly.graph_objects as go
import requests
from datetime import datetime
from collections import defaultdict

BASE_URL = "https://open.feishu.cn/open-apis"
BASE_TOKEN = "Jwu7bRyHvagQ4Hsv8ExcPiOOnnd"
TABLE_ID = "tblVwBR0551V40uZ"  # 大方主播退货率
APP_ID = "cli_a876dccb3d7a101c"
APP_SECRET = "eTURY2xNmRaSBR6nratpsdn86ENxssTA"

def num(v, default=0.0):
    """安全转换为数字"""
    try:
        return float(v) if v is not None else default
    except (ValueError, TypeError):
        return default

def ts_to_date(ts):
    """毫秒时间戳 → 日期字符串 2026-05-25"""
    try:
        return datetime.fromtimestamp(int(ts) / 1000).strftime('%Y-%m-%d')
    except:
        return str(ts) if ts else ""

def get_date(r):
    """从记录中获取日期字符串（兼容时间戳和字符串）"""
    d = r.get("记录日期")
    if d is None:
        return r.get("蝉管家统计日期", "")
    if isinstance(d, (int, float)) and d > 10000000:
        return ts_to_date(d)
    return str(d) if d else ""

def get_token():
    r = requests.post(f"{BASE_URL}/auth/v3/tenant_access_token/internal",
        json={"app_id": APP_ID, "app_secret": APP_SECRET}, timeout=15, verify=False)
    return r.json()["tenant_access_token"]

@st.cache_data(ttl=1800, show_spinner="📡 加载蝉管家退货率数据...")
def load_anchor_returns():
    """读取飞书「大方主播退货率」表"""
    token = get_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"}

    items = []
    page_token = None
    while True:
        params = {"page_size": 500}
        if page_token:
            params["page_token"] = page_token
        r = requests.get(f"{BASE_URL}/bitable/v1/apps/{BASE_TOKEN}/tables/{TABLE_ID}/records",
            params=params, headers=headers, timeout=60, verify=False)
        data = r.json()
        if data.get("code") != 0:
            return [], f"API错误: {data.get('msg')}"
        d = data.get("data", {})
        items.extend(d.get("items", []))
        if d.get("has_more") and d.get("page_token"):
            page_token = d["page_token"]
        else:
            break

    return [r["fields"] for r in items], None


st.title("📉 主播退货率分析")

records, error = load_anchor_returns()

if error:
    st.error(error)
    st.stop()

if not records:
    st.info("💡 「大方主播退货率」表中暂无数据，请先运行缓存脚本")
    st.stop()

# 提取主播列表
anchors = sorted(set(r.get("蝉管家主播名字", "") for r in records if r.get("蝉管家主播名字")))
st.caption(f"数据来源：蝉管家 · {len(records):,} 条记录 · {len(anchors)} 位主播")

# === 筛选器 ===
col1, col2 = st.columns(2)
with col1:
    sel_anchor = st.selectbox("选择主播", ["全部"] + anchors)
with col2:
    dates = sorted(set(get_date(r) for r in records if r.get("记录日期")))
    sel_date = st.selectbox("日期", ["全部"] + dates[-15:])

# 筛选
filtered = records
if sel_anchor != "全部":
    filtered = [r for r in filtered if r.get("蝉管家主播名字") == sel_anchor]
if sel_date != "全部":
    filtered = [r for r in filtered if get_date(r) == sel_date]

# === 汇总指标 ===
total_sales = sum(num(r.get("蝉管家主播销售额")) for r in filtered)
total_returns = sum(num(r.get("禅管家主播退款金额")) for r in filtered)
overall_rate = round(total_returns / total_sales * 100, 1) if total_sales > 0 else 0

c1, c2, c3 = st.columns(3)
c1.metric("销售额", f"¥{total_sales/10000:.1f}万")
c2.metric("退款额", f"¥{total_returns/10000:.1f}万")
c3.metric("退货率", f"{overall_rate}%")

st.divider()

# === 主播退货率排名 ===
st.subheader("🏆 主播退货率排名")

anchor_totals = defaultdict(lambda: {"sales": 0, "returns": 0})
for r in records:
    a = r.get("蝉管家主播名字", "")
    anchor_totals[a]["sales"] += num(r.get("蝉管家主播销售额"))
    anchor_totals[a]["returns"] += num(r.get("禅管家主播退款金额"))

ranking = []
for a, v in anchor_totals.items():
    rate = round(v["returns"] / v["sales"] * 100, 1) if v["sales"] > 0 else 0
    # 只显示有显著数据的
    if v["sales"] > 10000:
        ranking.append({"主播": a, "退货率%": rate, "销售额(万)": round(v["sales"]/10000, 1), "退款额(万)": round(v["returns"]/10000, 1)})
ranking.sort(key=lambda x: x["退货率%"], reverse=True)

col_a, col_b = st.columns([1, 1.5])
with col_a:
    st.dataframe(ranking, use_container_width=True, hide_index=True,
                 column_config={"退货率%": f"{v}%"})
with col_b:
    # 柱状图
    top15 = ranking[:15]
    fig = go.Figure(go.Bar(
        x=[r["退货率%"] for r in top15],
        y=[r["主播"] for r in top15],
        orientation='h',
        marker_color=['#E53935' if r["退货率%"] > 30 else '#FB8C00' if r["退货率%"] > 20 else '#43A047' for r in top15],
        text=[f"{r['退货率%']}%" for r in top15],
        textposition='outside',
    ))
    fig.update_layout(height=400, margin=dict(l=10, r=40, t=10, b=10),
                      xaxis=dict(title="退货率 %"))
    st.plotly_chart(fig, use_container_width=True)

# === 冯芊祎专属 ===
st.divider()
st.subheader("🎯 冯芊祎 退货率趋势")

fqx_data = [r for r in records if "冯芊祎" in r.get("蝉管家主播名字", "")]
if fqx_data:
    fqx_data.sort(key=lambda r: get_date(r))
    dates = [get_date(r)[5:] for r in fqx_data]
    rates = []
    for r in fqx_data:
        s = num(r.get("蝉管家主播销售额"))
        ret = num(r.get("禅管家主播退款金额"))
        rates.append(round(ret / s * 100, 1) if s > 0 else 0)

    fig = go.Figure()
    fig.add_trace(go.Bar(x=dates, y=[num(r.get("蝉管家主播销售额"))/10000 for r in fqx_data], name="销售额(万)", marker_color="#90CAF9", yaxis="y2", hovertemplate="销售额: ¥%{y:.1f}万<extra></extra>"))
    fig.add_trace(go.Scatter(x=dates, y=rates, name="退货率", mode="lines+markers+text", line=dict(color="#E53935", width=2.5), marker=dict(size=8), text=[f"{v}%" for v in rates], textposition="top center", textfont=dict(color="#E53935", size=11), hovertemplate="退货率: %{y}%<extra></extra>"))
    fig.update_layout(height=380, yaxis=dict(title="退货率 %"), yaxis2=dict(title="销售额(万)", overlaying="y", side="right", showgrid=False),
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0), margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("冯芊祎暂无蝉管家退货率数据")
