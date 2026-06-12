"""业绩对比页：多主播GMV/GPM/UV趋势对比"""

import streamlit as st
import plotly.graph_objects as go
from feishu_client import get_cached_sessions, fmt_date

st.title("📈 业绩趋势对比")

sessions = get_cached_sessions()
all_anchors = sorted(set(s["anchor"] for s in sessions))

if not all_anchors:
    st.warning("暂无数据")
    st.stop()

# 多主播选择
default_anchors = ["冯芊祎"] if "冯芊祎" in all_anchors else all_anchors[:3]
selected = st.multiselect("选择对比主播", all_anchors, default=default_anchors)

if not selected:
    st.info("请至少选择一个主播")
    st.stop()

# 指标选择
metric = st.radio("对比指标", ["GPM", "GMV", "UV价值", "退货率"], horizontal=True)
metric_key = {"GPM": "gpmAvg", "GMV": "gmvTotal", "UV价值": "uvAvg", "退货率": "returnRate"}[metric]
colors = ["#2E7D32", "#1565C0", "#E65100", "#6A1B9A", "#C62828", "#00838F", "#4E342E"]

# 趋势图
fig = go.Figure()
for i, name in enumerate(selected):
    data = [s for s in sessions if s["anchor"] == name]
    data.sort(key=lambda s: s["date"])
    if not data:
        continue
    dates = [fmt_date(s["date"]) for s in data]
    vals = [s[metric_key] for s in data]
    if metric == "退货率":
        vals = [v * 100 for v in vals]

    fig.add_trace(go.Scatter(x=dates, y=vals, mode='lines+markers', name=name,
                             line=dict(color=colors[i % len(colors)], width=2.5),
                             marker=dict(size=8)))

fig.update_layout(height=420, margin=dict(l=10, r=10, t=10, b=10),
                  plot_bgcolor="white", paper_bgcolor="white",
                  legend=dict(orientation="h", yanchor="top", y=-0.2, x=0),
                  yaxis=dict(title=metric, gridcolor="#E0E0E0"),
                  xaxis=dict(gridcolor="#E0E0E0"))
st.plotly_chart(fig, use_container_width=True)

# 汇总对比表
st.divider()
st.subheader("📊 汇总对比")

rows = []
for name in selected:
    data = [s for s in sessions if s["anchor"] == name]
    if not data:
        continue
    rows.append({
        "主播": name,
        "场次": len(data),
        "均GPM": round(sum(s["gpmAvg"] for s in data) / len(data)),
        "最高GPM": max(s["gpmAvg"] for s in data),
        "最低GPM": min(s["gpmAvg"] for s in data),
        "总GMV": f"¥{sum(s['gmvTotal'] for s in data)/10000:.1f}万",
        "均UV": round(sum(s["uvAvg"] for s in data) / len(data), 2),
        "均退货率": f"{sum(s['returnRate'] for s in data)/len(data)*100:.1f}%",
    })

if rows:
    st.dataframe(rows, use_container_width=True, hide_index=True)

# 逐场明细
st.divider()
st.subheader("📋 逐场明细")

all_data = []
for name in selected:
    for s in sessions:
        if s["anchor"] == name:
            all_data.append(s)
all_data.sort(key=lambda s: (s["anchor"], s["date"]))

if all_data:
    detail_rows = [{
        "主播": s["anchor"], "日期": s["date"], "班次": s["shift"],
        "时长(h)": s["hours"], "GMV": f"¥{s['gmvTotal']:,}",
        "GPM": f"{s['gpmAvg']:,}", "UV": s["uvAvg"],
        "退货率": f"{s['returnRate']*100:.1f}%", "运营": s["operator"],
    } for s in all_data]
    st.dataframe(detail_rows, use_container_width=True, hide_index=True)
