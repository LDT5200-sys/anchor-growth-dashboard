"""概览页：指标卡片 + 常驻基准 + 新人PK + 能力雷达"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from feishu_client import get_cached_sessions, fmt_date

st.title("🎯 主播成长看板")

all_sessions = get_cached_sessions()
all_anchors = sorted(set(s["anchor"] for s in all_sessions))
default_anchor = "冯芊祎" if "冯芊祎" in all_anchors else (all_anchors[0] if all_anchors else None)

if not default_anchor:
    st.warning("暂无数据")
    st.stop()

selected = st.selectbox("选择主播", all_anchors, index=all_anchors.index(default_anchor))
sessions = [s for s in all_sessions if s["anchor"] == selected]
sessions.sort(key=lambda s: s["date"])

if not sessions:
    st.info(f"「{selected}」暂无场次数据")
    st.stop()

# 指标卡片
total_gmv = sum(s["gmvTotal"] for s in sessions)
avg_gpm = round(sum(s["gpmAvg"] for s in sessions) / len(sessions))
avg_uv = round(sum(s["uvAvg"] for s in sessions) / len(sessions), 2)

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("累计 GMV", f"¥{total_gmv/10000:.1f}万", delta=f"{len(sessions)} 场")
c2.metric("均场 GPM", f"{avg_gpm:,}")
c3.metric("均场 UV", f"{avg_uv}")
c4.metric("均退货率", f"{round(sum(s['returnRate'] for s in sessions)/len(sessions)*100,1)}%")
latest = sessions[-1]
c5.metric("最近 GPM", f"{latest['gpmAvg']:,}", delta=fmt_date(latest['date']))

st.divider()

# 两列
left, right = st.columns([1.2, 1])

with left:
    st.subheader("📅 最近场次详情")
    s = sessions[-1]
    st.markdown(f"""
    **{s['date']}** · {s['shift']}班 · 运营 {s['operator']} · {s['hours']}h
    💰 GMV ¥{s['gmvTotal']:,}　📊 GPM {s['gpmAvg']:,}　👤 UV {s['uvAvg']}
    """)

    recent = sessions[-5:] if len(sessions) >= 5 else sessions
    fig = px.line(x=[fmt_date(r["date"]) for r in recent], y=[r["gpmAvg"] for r in recent],
                  markers=True, title=f"近{len(recent)}场 GPM 趋势")
    fig.update_traces(line=dict(color="#2E7D32", width=3), marker=dict(size=8, color="#2E7D32"))
    fig.update_layout(height=280, margin=dict(l=10, r=10, t=40, b=10),
                      plot_bgcolor="white", paper_bgcolor="white")
    st.plotly_chart(fig, use_container_width=True)

with right:
    SENIOR = ["范晓晶", "邹楠楠", "赵颢棋", "乔莹", "苑含笑", "张新"]
    ROOKIE = ["朱佳琪", "单楚陵", "冯芊祎"]

    anchor_stats = {}
    for s in all_sessions:
        n = s["anchor"]
        if n not in anchor_stats:
            anchor_stats[n] = {"gpm": [], "gmv": [], "uv": [], "count": 0}
        anchor_stats[n]["gpm"].append(s["gpmAvg"])
        anchor_stats[n]["gmv"].append(s["gmvTotal"])
        anchor_stats[n]["uv"].append(s["uvAvg"])
        anchor_stats[n]["count"] += 1

    def build_row(names):
        rows = []
        for n in names:
            if n in anchor_stats:
                d = anchor_stats[n]
                rows.append({
                    "主播": n,
                    "均GPM": round(sum(d["gpm"]) / len(d["gpm"])),
                    "总GMV": f"¥{sum(d['gmv'])/10000:.1f}万",
                    "均UV": round(sum(d["uv"]) / len(d["uv"]), 1),
                    "场次": d["count"],
                })
        return rows

    st.subheader("🏆 常驻主播基准")
    sr = build_row(SENIOR)
    sr.sort(key=lambda x: x["均GPM"], reverse=True)
    st.dataframe(sr, use_container_width=True, hide_index=True,
                 column_config={"均GPM": st.column_config.NumberColumn(format="%d")})

    st.subheader("🔥 新主播 PK")
    rr = build_row(ROOKIE)
    if rr:
        rr.sort(key=lambda x: x["均GPM"], reverse=True)
        st.dataframe(rr, use_container_width=True, hide_index=True,
                     column_config={"均GPM": st.column_config.NumberColumn(format="%d")})
        pk_gpms = []
        for name in ROOKIE:
            if name in anchor_stats:
                for g in anchor_stats[name]["gpm"]:
                    pk_gpms.append({"主播": name, "GPM": g})
        if pk_gpms:
            fig = px.box(pd.DataFrame(pk_gpms), x="主播", y="GPM", color="主播",
                         color_discrete_sequence=["#E53935", "#FB8C00", "#2E7D32"])
            fig.update_traces(hoverinfo="none")  # 隐藏箱线统计标签
            fig.update_layout(height=250, margin=dict(l=10, r=10, t=10, b=10),
                              showlegend=False, plot_bgcolor="white")
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("暂无新主播数据（单楚陵下周入职，暂无数据）")

# 能力雷达
st.divider()
st.subheader("🕸️ 能力雷达")

ability_labels = ["产品知识", "话术框架", "控场节奏", "塑品能力", "逼单转化",
                  "数据感知", "情绪管理", "评论互动", "镜头表现", "学习成长"]

if "ability_history" not in st.session_state:
    st.session_state.ability_history = {}

history = st.session_state.ability_history.get(selected, [])
if history:
    history.sort(key=lambda h: h["date"])
    latest_scores = history[-1]["scores"]
    vals = [latest_scores.get(label, 0) for label in ability_labels]
    fig = go.Figure(go.Scatterpolar(r=vals, theta=ability_labels, fill='toself',
                                    fillcolor='rgba(46,125,50,0.15)',
                                    line=dict(color='#2E7D32', width=2)))
    fig.update_layout(polar=dict(radialaxis=dict(range=[0, 5])), height=320,
                      margin=dict(l=40, r=40, t=20, b=20))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("💡 前往「能力评估」页面对主播进行首次评估")
