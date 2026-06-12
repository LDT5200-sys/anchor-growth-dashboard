"""概览页：指标卡片 + 能力雷达 + 最近场次"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from feishu_client import get_cached_sessions

st.markdown('<div class="main-header">🎯 主播成长看板</div>', unsafe_allow_html=True)

# 主播选择
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

# 计算指标
total_gmv = sum(s["gmvTotal"] for s in sessions)
avg_gpm = round(sum(s["gpmAvg"] for s in sessions) / len(sessions))
avg_uv = round(sum(s["uvAvg"] for s in sessions) / len(sessions), 2)
avg_ret = round(sum(s["returnRate"] for s in sessions) / len(sessions) * 100, 1)

# 指标卡片
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("累计 GMV", f"¥{total_gmv/10000:.1f}万", delta=f"{len(sessions)} 场")
c2.metric("均场 GPM", f"{avg_gpm:,}")
c3.metric("均场 UV", f"{avg_uv}")
c4.metric("均退货率", f"{avg_ret}%")
latest = sessions[-1]
c5.metric("最近 GPM", f"{latest['gpmAvg']:,}", delta=f"{latest['date'][5:]}")

st.markdown("---")

# 两列布局
left, right = st.columns([1.2, 1])

with left:
    st.subheader("📅 最近一场摘要")
    s = sessions[-1]
    st.markdown(f"""
    **{s['date']}** · {s['shift']}班 · 运营{s['operator']} · {s['hours']}h
    GMV ¥{s['gmvTotal']:,} · GPM {s['gpmAvg']:,} · UV {s['uvAvg']}
    """)

    # 最近5场趋势
    recent = sessions[-5:] if len(sessions) >= 5 else sessions
    fig = px.line(x=[r["date"][5:] for r in recent], y=[r["gpmAvg"] for r in recent],
                  markers=True, title=f"近{len(recent)}场 GPM 趋势")
    fig.update_layout(height=220, margin=dict(l=10, r=10, t=30, b=10),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font_color="#9298AA")
    fig.update_traces(line=dict(color="#46CC8D", width=2.5))
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("🎯 场次对比（全体主播）")
    # 所有主播最近场均GPM对比
    anchor_gpm = {}
    for s in all_sessions:
        if s["anchor"] not in anchor_gpm:
            anchor_gpm[s["anchor"]] = []
        anchor_gpm[s["anchor"]].append(s["gpmAvg"])

    compare_data = []
    for name, gpms in sorted(anchor_gpm.items()):
        compare_data.append({
            "主播": name,
            "均GPM": round(sum(gpms) / len(gpms)),
            "最高GPM": max(gpms),
            "场次": len(gpms),
            "标记": "⭐ 当前" if name == selected else ""
        })

    # 按均GPM排序
    compare_data.sort(key=lambda x: x["均GPM"], reverse=True)

    # 高亮当前主播
    st.dataframe(
        compare_data,
        use_container_width=True,
        column_config={
            "主播": st.column_config.TextColumn(width="small"),
            "均GPM": st.column_config.NumberColumn(format="%d"),
            "最高GPM": st.column_config.NumberColumn(format="%d"),
            "场次": st.column_config.NumberColumn(width="small"),
            "标记": st.column_config.TextColumn(width="small"),
        },
        hide_index=True,
    )

# 底部：能力雷达图（如果有评估数据）
st.markdown("---")
st.subheader("🕸️ 能力雷达")

# 用样本数据展示雷达图结构（能力评估数据待确认后替换）
ability_labels = ["产品知识", "话术框架", "控场节奏", "塑品能力", "逼单转化",
                  "数据感知", "情绪管理", "评论互动", "镜头表现", "学习成长"]

# 如果 session_state 中有评估数据就用，否则显示占位
if "ability_scores" not in st.session_state:
    st.session_state.ability_scores = {}

scores = st.session_state.ability_scores.get(selected, {})

if scores:
    vals = [scores.get(label, 0) for label in ability_labels]
    fig = go.Figure(go.Scatterpolar(r=vals, theta=ability_labels, fill='toself',
                                     fillcolor='rgba(70,204,141,0.2)',
                                     line=dict(color='#46CC8D', width=2)))
    fig.update_layout(polar=dict(radialaxis=dict(range=[0, 5], tickfont=dict(color="#5C6377"),
                                                  gridcolor="#2B3242"),
                                  angularaxis=dict(tickfont=dict(color="#9298AA"), gridcolor="#2B3242")),
                      height=320, margin=dict(l=40, r=40, t=20, b=20),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("💡 前往「能力评估」页面对主播进行首次评估，即可看到能力雷达图")
