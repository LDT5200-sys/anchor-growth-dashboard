"""能力评估页：10项能力评分 + 雷达图历史对比"""

import streamlit as st
import plotly.graph_objects as go
from datetime import date

ABILITY_LABELS = ["产品知识", "话术框架", "控场节奏", "塑品能力", "逼单转化",
                  "数据感知", "情绪管理", "评论互动", "镜头表现", "学习成长"]

if "ability_history" not in st.session_state:
    st.session_state.ability_history = {}  # {主播名: [{date, scores, comment}, ...]}

st.markdown('<div class="main-header">🎯 能力评估</div>', unsafe_allow_html=True)

# 主播输入
anchor = st.text_input("主播姓名", value="冯芊祎")

col1, col2 = st.columns([1, 1.3])

with col1:
    st.subheader("📝 新增 / 更新评估")

    eval_date = st.date_input("评估日期", value=date.today())
    comment = st.text_area("整体评语", placeholder="例如：话术框架进步明显，数据感知开始建立...")

    st.markdown("**10项能力评分 (1-5)**")
    scores = {}
    cols = st.columns(2)
    for i, label in enumerate(ABILITY_LABELS):
        with cols[i % 2]:
            scores[label] = st.slider(label, 1, 5, 3, 1)

    if st.button("💾 保存评估", use_container_width=True):
        history = st.session_state.ability_history.get(anchor, [])
        record = {"date": str(eval_date), "scores": scores, "comment": comment}
        # 同一天覆盖
        existing = [h for h in history if h["date"] == str(eval_date)]
        if existing:
            history[history.index(existing[0])] = record
        else:
            history.append(record)
        st.session_state.ability_history[anchor] = history
        st.success(f"✅ {anchor} 评估已保存")
        st.rerun()

with col2:
    st.subheader("🕸️ 能力雷达")

    history = st.session_state.ability_history.get(anchor, [])
    if history:
        history.sort(key=lambda h: h["date"])
        latest = history[-1]

        # 雷达图
        vals = [latest["scores"].get(label, 0) for label in ABILITY_LABELS]
        fig = go.Figure()

        # 如果有历史，叠加上次评估
        if len(history) >= 2:
            prev = history[-2]
            prev_vals = [prev["scores"].get(label, 0) for label in ABILITY_LABELS]
            fig.add_trace(go.Scatterpolar(r=prev_vals, theta=ABILITY_LABELS, name=f"上次 ({prev['date']})",
                                          fill='toself', fillcolor='rgba(146,152,170,0.1)',
                                          line=dict(color='#5C6377', width=2, dash='dot')))

        fig.add_trace(go.Scatterpolar(r=vals, theta=ABILITY_LABELS, name=f"本次 ({latest['date']})",
                                      fill='toself', fillcolor='rgba(70,204,141,0.2)',
                                      line=dict(color='#46CC8D', width=2.5)))

        fig.update_layout(polar=dict(radialaxis=dict(range=[0, 5], tickfont=dict(color="#5C6377"),
                                                      gridcolor="#2B3242"),
                                     angularaxis=dict(tickfont=dict(color="#9298AA"), gridcolor="#2B3242")),
                          height=350, margin=dict(l=40, r=40, t=20, b=20),
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                          font_color="#9298AA")
        st.plotly_chart(fig, use_container_width=True)

        # 评语
        if latest.get("comment"):
            st.info(f"💬 {latest['comment']}")

        # 能力变化表
        if len(history) >= 2:
            st.markdown("**📊 能力变化**")
            prev = history[-2]
            delta_data = []
            for label in ABILITY_LABELS:
                cur = latest["scores"].get(label, 0)
                prv = prev["scores"].get(label, 0)
                d = cur - prv
                icon = "🟢" if d > 0 else ("🔴" if d < 0 else "⚪")
                delta_data.append({"能力项": label, "上次": prv, "本次": cur, "变化": f"{icon} {d:+d}"})
            import pandas as pd
            st.dataframe(pd.DataFrame(delta_data), use_container_width=True, hide_index=True)
    else:
        st.info("💡 尚无评估数据，在左侧进行首次评估")

# 历史评估列表
history = st.session_state.ability_history.get(anchor, [])
if history:
    st.markdown("---")
    st.subheader("📋 评估历史")
    history.sort(key=lambda h: h["date"], reverse=True)
    for h in history:
        total = sum(h["scores"].values())
        with st.expander(f"{h['date']}  ·  总分 {total}/50  ·  {h.get('comment', '')[:40]}..."):
            cols = st.columns(5)
            for i, (k, v) in enumerate(h["scores"].items()):
                with cols[i % 5]:
                    level = "🟢" if v >= 4 else ("🟡" if v == 3 else "🔴")
                    st.metric(k, f"{level} {v}/5")
