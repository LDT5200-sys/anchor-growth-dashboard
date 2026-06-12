"""复盘记录页：每场下播后的亮点/待改进/行动项"""

import streamlit as st
from datetime import date
from feishu_client import get_cached_sessions

if "reviews" not in st.session_state:
    st.session_state.reviews = {}  # {anchor: [{date, sessionDate, highlight, toImprove, action, score}, ...]}

st.markdown('<div class="main-header">📝 复盘记录</div>', unsafe_allow_html=True)

anchor = st.text_input("主播姓名", value="冯芊祎", key="review_anchor")

# 获取该主播的场次列表用于关联
sessions = get_cached_sessions()
anchor_sessions = sorted(
    [s for s in sessions if s["anchor"] == anchor],
    key=lambda s: s["date"], reverse=True
)

col1, col2 = st.columns([1, 1.2])

with col1:
    st.subheader("✍️ 新建复盘")

    # 场次关联
    session_options = [f"{s['date']} · {s['shift']}班 · GPM {s['gpmAvg']}" for s in anchor_sessions]
    session_dates = [s["date"] for s in anchor_sessions]
    if session_options:
        sel_idx = st.selectbox("关联场次", range(len(session_options)),
                               format_func=lambda i: session_options[i])
        sel_date = session_dates[sel_idx]
    else:
        sel_date = st.text_input("场次日期", value=str(date.today()))
        st.info("💡 尚无场次数据，手动输入日期")

    score = st.slider("综合评分", 1, 10, 6)
    highlight = st.text_area("🌟 亮点", placeholder="这场做得好的地方...")
    to_improve = st.text_area("⚠️ 待改进", placeholder="哪里掉链子、什么原因...")
    action = st.text_area("🎯 下一步行动", placeholder="下场/下周要练什么...")

    if st.button("💾 保存复盘", use_container_width=True):
        if not highlight and not to_improve:
            st.warning("至少填写一项内容")
        else:
            if anchor not in st.session_state.reviews:
                st.session_state.reviews[anchor] = []
            st.session_state.reviews[anchor].append({
                "date": str(date.today()),
                "sessionDate": sel_date,
                "highlight": highlight,
                "toImprove": to_improve,
                "action": action,
                "score": score,
            })
            st.success("✅ 复盘已保存")
            st.rerun()

with col2:
    st.subheader("📋 历史复盘")

    reviews = st.session_state.reviews.get(anchor, [])
    if reviews:
        reviews.sort(key=lambda r: r["sessionDate"], reverse=True)
        for i, r in enumerate(reviews):
            dots = "●" * r["score"] + "○" * (10 - r["score"])
            with st.expander(f"{r['sessionDate']} · {dots} · {r['score']}/10"):
                st.markdown(f"**🌟 亮点**: {r.get('highlight','')}")
                st.markdown(f"**⚠️ 待改进**: {r.get('toImprove','')}")
                st.markdown(f"**🎯 下一步**: {r.get('action','')}")
                if st.button(f"🗑️ 删除", key=f"del_rv_{i}"):
                    st.session_state.reviews[anchor].pop(i)
                    st.rerun()
    else:
        st.info("💡 尚无复盘记录")

# 复盘统计
reviews = st.session_state.reviews.get(anchor, [])
if reviews:
    st.markdown("---")
    st.subheader("📊 复盘统计")

    scores = [r["score"] for r in reviews]
    avg_score = sum(scores) / len(scores)
    c1, c2 = st.columns(2)
    c1.metric("累计复盘", f"{len(reviews)} 次")
    c2.metric("均分", f"{avg_score:.1f}/10", delta=f"最高 {max(scores)}" if scores else None)
