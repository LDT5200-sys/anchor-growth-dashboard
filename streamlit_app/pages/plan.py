"""成长计划页：周计划管理 + 培训资料关联"""

import streamlit as st
from datetime import date, timedelta

ABILITY_LABELS = ["产品知识", "话术框架", "控场节奏", "塑品能力", "逼单转化",
                  "数据感知", "情绪管理", "评论互动", "镜头表现", "学习成长"]

MATERIALS = [
    {"name": "三代秘纤速干圆领短袖T恤话术", "category": "产品知识"},
    {"name": "话术逻辑万能公式", "category": "话术框架"},
    {"name": "如何精准逼单，话术不单一", "category": "逼单转化"},
    {"name": "如何把握直播节奏", "category": "控场节奏"},
    {"name": "主播如何调整心态", "category": "情绪管理"},
    {"name": "痛点场景化", "category": "塑品能力"},
    {"name": "评论区尺码多怎么办", "category": "评论互动"},
    {"name": "评论区遇到差评恶评怎么办", "category": "评论互动"},
    {"name": "问的人多但是不下单怎么办", "category": "逼单转化"},
    {"name": "主播经验手册-早A承接篇", "category": "话术框架"},
    {"name": "主播经验手册-控场篇", "category": "控场节奏"},
    {"name": "主播经验手册-情绪管理篇", "category": "情绪管理"},
    {"name": "主播经验手册-塑品篇", "category": "塑品能力"},
    {"name": "主播经验手册-逼单篇", "category": "逼单转化"},
    {"name": "主播经验手册-数据篇", "category": "数据感知"},
    {"name": "主播经验手册-避坑篇", "category": "学习成长"},
    {"name": "主播经验手册-外部学习篇", "category": "学习成长"},
]

if "plans" not in st.session_state:
    st.session_state.plans = {}  # {anchor: {week: {focus, materials, target, status}}}

st.markdown('<div class="main-header">📋 成长计划</div>', unsafe_allow_html=True)

anchor = st.text_input("主播姓名", value="冯芊祎", key="plan_anchor")

# 当前周
today = date.today()
iso = today.isocalendar()
current_week = f"{iso[0]}-W{iso[1]:02d}"

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📝 新增 / 编辑周计划")

    week = st.text_input("周次", value=current_week, help="格式：2026-W24")
    target = st.text_area("本周目标", placeholder="例如：GPM 稳定在 5000+，话术结构完整不散架")
    status = st.selectbox("状态", ["未开始", "进行中", "已完成"])

    st.markdown("**🎯 重点能力项**")
    focus = st.multiselect("选择能力项", ABILITY_LABELS)

    st.markdown("**📚 关联培训资料**")
    mat_options = [m["name"] for m in MATERIALS]
    selected_mats = st.multiselect("选择培训资料", mat_options)

    if st.button("💾 保存计划", use_container_width=True):
        if anchor not in st.session_state.plans:
            st.session_state.plans[anchor] = {}
        st.session_state.plans[anchor][week] = {
            "focus": focus, "materials": selected_mats,
            "target": target, "status": status
        }
        st.success(f"✅ {week} 计划已保存")
        st.rerun()

with col2:
    st.subheader("📅 已有计划")

    plans = st.session_state.plans.get(anchor, {})
    if plans:
        for wk in sorted(plans.keys(), reverse=True):
            p = plans[wk]
            status_icon = {"已完成": "✅", "进行中": "🔄", "未开始": "⚪"}.get(p["status"], "⚪")
            with st.expander(f"{status_icon} {wk} · {p.get('status','')} · 重点: {', '.join(p.get('focus',[]))}"):
                st.markdown(f"**目标**: {p.get('target','')}")
                st.markdown(f"**能力项**: {', '.join(p.get('focus',[]))}")
                st.markdown(f"**培训资料**: {', '.join(p.get('materials',[]))}")
                if st.button(f"🗑️ 删除 {wk}", key=f"del_{wk}"):
                    del st.session_state.plans[anchor][wk]
                    st.rerun()
    else:
        st.info("💡 尚无成长计划")

# 培训资料速查
st.markdown("---")
st.subheader("📚 培训资料库")

cat = st.selectbox("按类别筛选", ["全部"] + sorted(set(m["category"] for m in MATERIALS)))
filtered = MATERIALS if cat == "全部" else [m for m in MATERIALS if m["category"] == cat]
for m in filtered:
    st.markdown(f"- **{m['name']}** `{m['category']}`")
