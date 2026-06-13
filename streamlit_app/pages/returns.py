"""冯芊祎专属辅导面板：退货率诊断 + 预警 + 实操检查表"""

import streamlit as st
import os
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests, urllib3
from datetime import datetime
from collections import defaultdict
urllib3.disable_warnings()

BASE_TOKEN = "Jwu7bRyHvagQ4Hsv8ExcPiOOnnd"

def get_app_creds():
    import os
    try:
        app_id = st.secrets["FEISHU_APP_ID"]
        app_secret = st.secrets["FEISHU_APP_SECRET"]
        return app_id, app_secret
    except:
        return (
            os.environ.get("FEISHU_APP_ID", "cli_a876dccb3d7a101c"),
            os.environ.get("FEISHU_APP_SECRET", "eTURY2xNmRaSBR6nratpsdn86ENxssTA"),
        )

def get_token():
    app_id, app_secret = get_app_creds()
    r = requests.post("https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": app_id, "app_secret": app_secret}, timeout=15, verify=False)
    return r.json()["tenant_access_token"]

def num(v, d=0.0):
    try: return float(v) if v is not None else d
    except: return d

def ts_to_date(ts):
    try: return datetime.fromtimestamp(int(ts)/1000).strftime("%Y-%m-%d")
    except: return str(ts) if ts else ""

@st.cache_data(ttl=1800, show_spinner="📡 加载数据...")
def load_all_data():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"}

    # 蝉管家主播退货率
    return_records = []
    page_token = None
    while True:
        params = {"page_size": 500}
        if page_token: params["page_token"] = page_token
        r = requests.get(
            f"https://open.feishu.cn/open-apis/bitable/v1/apps/{BASE_TOKEN}/tables/tblVwBR0551V40uZ/records",
            params=params, headers=headers, timeout=30, verify=False)
        d = r.json()
        if d.get("code") != 0: break
        return_records.extend(d.get("data", {}).get("items", []))
        if d.get("data", {}).get("has_more"): page_token = d["data"]["page_token"]
        else: break

    # 场次数据
    sessions_records = []
    page_token = None
    while True:
        params = {"page_size": 500}
        if page_token: params["page_token"] = page_token
        r = requests.get(
            f"https://open.feishu.cn/open-apis/bitable/v1/apps/{BASE_TOKEN}/tables/tblHd2VP27BmN0Dt/records",
            params=params, headers=headers, timeout=30, verify=False)
        d = r.json()
        if d.get("code") != 0: break
        sessions_records.extend(d.get("data", {}).get("items", []))
        if d.get("data", {}).get("has_more"): page_token = d["data"]["page_token"]
        else: break

    return return_records, sessions_records

return_records, sessions_records = load_all_data()

# === 解析数据 ===
anchor_returns = defaultdict(lambda: {"sales": 0, "returns": 0, "daily": []})
for rec in return_records:
    f = rec["fields"]
    name = f.get("蝉管家主播名字", "")
    d = ts_to_date(f.get("记录日期"))
    s = num(f.get("蝉管家主播销售额"))
    r = num(f.get("禅管家主播退款金额"))
    anchor_returns[name]["sales"] += s
    anchor_returns[name]["returns"] += r
    anchor_returns[name]["daily"].append({"date": d, "sales": s, "returns": r, "rate": round(r/s*100,1) if s>0 else 0})

# 冯芊祎场次
fqx_sessions = []
for rec in sessions_records:
    f = rec["fields"]
    anc = f.get("主播姓名", [])
    names = []
    if isinstance(anc, list):
        names = [a.get("text","") for a in anc if isinstance(a, dict)]
    if "冯芊祎" not in names: continue
    ts = f.get("记录时间", 0)
    if not isinstance(ts, (int, float)) or ts == 0: continue
    d = datetime.fromtimestamp(ts/1000).strftime("%Y-%m-%d")
    gmv = num(f.get("单小时直播间GMV"))
    gpm = num(f.get("单小时GPM(千次观看成交金额)"))
    uv = num(f.get("UV价值(单人价值)"))
    ret = num(f.get("产品退货率"))
    if gpm > 0:
        fqx_sessions.append({"date": d, "gmv": gmv, "gpm": gpm, "uv": uv, "returnRate": ret})

# 冯芊祎每日聚合
fqx_daily = defaultdict(lambda: {"gmv": 0, "gpm": [], "uv": []})
for s in fqx_sessions:
    fqx_daily[s["date"]]["gmv"] += s["gmv"]
    fqx_daily[s["date"]]["gpm"].append(s["gpm"])
    fqx_daily[s["date"]]["uv"].append(s["uv"])

r_data = anchor_returns.get("冯芊祎", {"sales": 0, "returns": 0, "daily": []})
r_rate = round(r_data["returns"]/r_data["sales"]*100, 1) if r_data["sales"] > 0 else 0

# 大盘对比
all_rates = []
for name, d in anchor_returns.items():
    if name != "冯芊祎" and d["sales"] > 50000:
        rate = round(d["returns"]/d["sales"]*100, 1) if d["sales"] > 0 else 0
        all_rates.append(rate)
avg_rate = round(sum(all_rates)/len(all_rates), 1) if all_rates else 0

# ============================================
st.title("🎯 冯芊祎 · 专属辅导面板")
if st.button("🔄 刷新数据", type="secondary"):
    st.cache_data.clear()
    st.rerun()

c1, c2, c3, c4 = st.columns(4)
c1.metric("累计销售额", f"¥{r_data['sales']/10000:.1f}万")
c2.metric("累计退货额", f"¥{r_data['returns']/10000:.1f}万")
c3.metric("退货率", f"{r_rate}%")
delta = round(r_rate - avg_rate, 1)
c4.metric("vs 大盘均值", f"{'🔴' if delta>3 else '🟡' if delta>0 else '🟢'} {delta:+.1f}%", delta=f"大盘 {avg_rate}%")

st.divider()

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 退货率 × GPM", "⚠️ 异常预警", "✅ 综合检查清单",
    "🎙️ 秘纤话术覆盖", "🆚 话术对比"
])

with tab1:
    st.subheader("退货率 vs GPM 关联")

    fqx_dates = sorted(fqx_daily.keys())
    points = []
    for d in fqx_dates:
        gpm_avg = sum(fqx_daily[d]["gpm"]) / len(fqx_daily[d]["gpm"]) if fqx_daily[d]["gpm"] else 0
        matching = [x for x in r_data["daily"] if x["date"] == d]
        ret_rate = matching[0]["rate"] if matching else None
        if ret_rate is not None:
            points.append({"date": d, "gpm": gpm_avg, "rate": ret_rate})

    if points:
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Scatter(
            x=[p["date"][5:] for p in points], y=[p["rate"] for p in points],
            name="退货率%", mode="lines+markers",
            line=dict(color="#E53935", width=2.5), marker=dict(size=10)),
            secondary_y=False)
        fig.add_trace(go.Bar(
            x=[p["date"][5:] for p in points], y=[p["gpm"] for p in points],
            name="GPM", marker_color="#90CAF9"),
            secondary_y=True)
        fig.update_layout(height=380, hovermode="x unified",
            legend=dict(orientation="h", y=1.1), margin=dict(l=10,r=10,t=10,b=10))
        fig.update_yaxes(title_text="退货率 %", secondary_y=False, range=[0, max(p["rate"] for p in points)*1.5])
        fig.update_yaxes(title_text="GPM", secondary_y=True, showgrid=False)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("**📊 解读**")
        if points[-1]["rate"] < points[0]["rate"]:
            st.success(f"退货率 {points[0]['date']} {points[0]['rate']}% → {points[-1]['date']} {points[-1]['rate']}%，趋势向好 📉")
        else:
            st.warning(f"退货率 {points[0]['date']} {points[0]['rate']}% → {points[-1]['date']} {points[-1]['rate']}%，需关注 📈")
        if points[-1]["gpm"] > points[0]["gpm"]:
            st.success(f"GPM {points[0]['gpm']} → {points[-1]['gpm']}，上升中 💰")
    else:
        st.info("暂无足够数据点（需同时有场次和蝉管家数据覆盖同一日期）")

with tab2:
    st.subheader("⚠️ 退货率异常检测")

    if r_data["daily"]:
        daily_rates = [x["rate"] for x in r_data["daily"] if x["rate"] > 0]
        if len(daily_rates) >= 2:
            mean_rate = sum(daily_rates)/len(daily_rates)
            std_rate = (sum((r-mean_rate)**2 for r in daily_rates)/len(daily_rates))**0.5
            threshold = mean_rate + 1.5*std_rate

            st.markdown(f"个人基线: **{mean_rate:.1f}%** ± 1.5σ = 预警线 **{threshold:.1f}%**")

            alerts = [x for x in r_data["daily"] if x["rate"] > threshold]
            if alerts:
                for a in alerts:
                    st.error(f"🚨 {a['date']}: 退货率 {a['rate']}%（超预警线 +{round(a['rate']-mean_rate,1)}%）")
            else:
                st.success("✅ 暂无异动")
        else:
            st.info("数据点不足")

    st.divider()
    st.markdown("**vs 大盘**")
    if all_rates:
        all_rates.sort()
        p75 = all_rates[int(len(all_rates)*0.75)] if len(all_rates)>3 else max(all_rates)
        st.markdown(f"大盘 P75: **{p75}%**")
        if r_rate > p75:
            st.error(f"冯芊祎 {r_rate}% > P75 {p75}%，高风险区间")
        else:
            st.success(f"冯芊祎 {r_rate}% ≤ P75 {p75}%，正常范围")

with tab3:
    st.subheader("✅ 直播辅导检查清单")

    if "coaching_checklist" not in st.session_state:
        st.session_state.coaching_checklist = {}

    today = datetime.now()
    sel_date = st.date_input("检查日期", value=today)
    sd = str(sel_date)

    checklist = {
        "逼单转化（决定GPM上限）": [
            "每次讲完卖点都逼单了",
            "逼单有明确的时间/库存紧迫感",
            "不靠降价硬逼，靠价值塑造逼",
        ],
        "塑品能力（降低退货率）": [
            "痛点场景化让用户代入",
            "没夸大卖点导致收货落差",
            "连带推荐自然不突兀",
        ],
        "控场节奏（稳定产出）": [
            "流量高时节奏能加快逼单",
            "流量低时能点对点互动暖场",
            "没被公屏带偏，始终掌控讲品主线",
        ],
        "个人风格（拉开差距）": [
            "有自己的表达风格不是模仿",
            "直播间有活人感不机械",
            "跟粉丝有粘性互动不是单向输出",
        ],
        "复盘习惯": ["每场后看了录屏回放", "能找到1个具体改进点", "下一场确实改了"],
    }

    for cat, items in checklist.items():
        with st.expander(f"📋 {cat}", expanded=cat=="产品知识"):
            for item in items:
                key = f"{sd}_{cat}_{item}"
                checked = st.checkbox(item, value=st.session_state.coaching_checklist.get(key, False), key=key)
                st.session_state.coaching_checklist[key] = checked

    total = sum(len(v) for v in checklist.values())
    done = sum(1 for k, v in st.session_state.coaching_checklist.items() if sd in k and v)
    st.progress(done/total if total>0 else 0)
    st.caption(f"今日完成: {done}/{total} ({round(done/total*100) if total>0 else 0}%)")

    st.divider()
    st.subheader("📝 辅导笔记")
    note_key = f"coaching_note_{sd}"
    note = st.text_area("今日观察和行动项", value=st.session_state.get(note_key, ""), height=100,
                        placeholder="例如：秘纤卖点已经能脱稿了，但逼单太硬需要练...")
    if st.button("💾 保存笔记"):
        st.session_state[note_key] = note
        st.toast("已保存 ✅")

with tab4:
    st.subheader("🎙️ 秘纤卖点覆盖检查")

    st.caption("跟播时逐一核对，确保核心卖点一个不漏")

    # 秘纤话术卖点清单
    mxf_checklist = {
        "🎬 开篇引入": [
            "龙牙自主研发速干科技面料",
            "高端T颜值 + 睡衣T亲肤透气 + 功能T吸湿速干",
        ],
        "💧 轻爽科技": [
            "柔软轻盈透气，上身舒服",
            "不易缩水、不易变形、机洗好打理",
            "耐脏好洗、不易发黄、久洗如新",
            "风车型截面纱线 → 快速导汗不粘身",
            "透气测试对比（与普通T恤）",
            "腋下矩阵式透气网孔",
        ],
        "💎 提升价值感": [
            "夏季单穿 + 春秋内搭",
            "展示做工走线细节",
            "六边形战士总结：亲肤/吸湿/速干/不变形/不黄变/久洗如新",
            "和大几百T恤对比不逊色",
        ],
        "🔧 补充卖点": [
            "领口罗纹设计，穿脱不变形",
            "腋下立体剪裁，活动更灵活",
            "四面弹力，胖哥哥也能穿",
            "三代侧摆口袋（放物品方便）",
        ],
        "📏 尺码互动": [
            "13个尺码体系，高矮胖瘦全覆盖",
            "引导用户报身高体重",
            "颜色推荐（显年轻）",
        ],
        "🎁 活动话术": [
            "讲清楚当前活动机制（618/满减/券）",
            "品牌+平台双重补贴/折上折",
            "合并付款更划算（不要单件买）",
            "活动限时/倒计时制造紧迫感",
        ],
        "🛡️ 售后逼单": [
            "一年质保 + 顺丰包邮 + 7天无理由 + 退货运费险",
            "价值感逼单（买的是品质/帅气/省心）",
        ],
        "⚠️ 口径红线": [
            "不讲「排汗」→ 讲吸湿、速干、导汗",
            "不承诺不易勾丝/起球（被动回复口径）",
            "不主动宣传针织品一年质保",
        ],
    }

    if "mxf_coverage" not in st.session_state:
        st.session_state.mxf_coverage = {}

    total_mxf = sum(len(v) for v in mxf_checklist.values())

    for cat, items in mxf_checklist.items():
        cat_done = sum(1 for item in items if st.session_state.mxf_coverage.get(f"{sd}_{cat}_{item}", False))
        with st.expander(f"{cat} ({cat_done}/{len(items)})", expanded="⚠️" in cat):
            for item in items:
                key = f"{sd}_{cat}_{item}"
                checked = st.checkbox(item, value=st.session_state.mxf_coverage.get(key, False), key=f"mxf_{key}")
                st.session_state.mxf_coverage[key] = checked

    done_mxf = sum(1 for k, v in st.session_state.mxf_coverage.items() if sd in k and v)
    percent = round(done_mxf/total_mxf*100) if total_mxf > 0 else 0

    color = "red" if percent < 50 else ("orange" if percent < 80 else "green")
    st.markdown(f"### 话术覆盖率：<span style='color:{color}'>{percent}%</span>（{done_mxf}/{total_mxf}）", unsafe_allow_html=True)
    st.progress(done_mxf/total_mxf if total_mxf > 0 else 0)

    if percent >= 90:
        st.success("🎉 卖点覆盖优秀，话术基本功扎实")
    elif percent >= 70:
        st.warning("⚠️ 还有提升空间，重点补漏标黄模块")
    else:
        st.error("🔴 核心卖点遗漏较多，建议回看录播定位问题")

with tab5:
    st.subheader("🆚 话术覆盖对比")

    mode = st.radio("对比模式", ["🔥 新人PK", "🏆 新人 vs 头部", "📈 自己历史对比"], horizontal=True)

    if mode == "🔥 新人PK":
        st.caption("上传冯芊祎、朱佳琪等人的话术文件 → 看谁覆盖更全")
    elif mode == "🏆 新人 vs 头部":
        st.caption("上传冯芊祎 + 一位常驻主播（如范晓晶）的话术 → 找差距")
    else:
        st.caption("上传冯芊祎不同日期的话术文件 → 看进步还是退步（先旧后新）")

    # 上传区域
    uploaded_files = st.file_uploader(
        "上传蝉管家话术文件（可多选）",
        type=["xlsx"],
        accept_multiple_files=True,
        help="蝉管家 → 下载视频话术 → 选择 Excel 格式",
        key="speech_upload"
    )

    if uploaded_files:
        import zipfile, xml.etree.ElementTree as ET, re

        # 话术分析函数
        def analyze_speech(file_bytes, anchor_label):
            try:
                z = zipfile.ZipFile(file_bytes)
                sheet = z.read('xl/worksheets/sheet1.xml').decode('utf-8')
                tree = ET.fromstring(sheet)
                ns = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'

                rows = []
                for row in tree.findall(f'{{{ns}}}sheetData/{{{ns}}}row'):
                    cells = {}
                    for c in row.findall(f'{{{ns}}}c'):
                        ref = c.get('r')
                        v = c.find(f'{{{ns}}}v')
                        if v is not None and v.text:
                            cells[ref[0]] = v.text.replace('&#xA;', '\n')
                    if cells:
                        rows.append(cells)

                # 提取主播话术
                anchor_text = ""
                for row_data in rows[1:]:
                    content = row_data.get('B', '')
                    for line in content.split('\n'):
                        line = line.strip()
                        if line.startswith('主播:'):
                            anchor_text += line[3:].strip() + ' '

                # 检测覆盖（简化版）
                checks = [
                    ("自主研发/速干科技", ["自主研发", "速干科技"]),
                    ("高端+亲肤+速干定位", ["高端", "亲肤", "速干"]),
                    ("柔软轻盈透气", ["柔软", "轻盈", "透气"]),
                    ("不变形/不缩水", ["不变形", "不缩水", "好打理"]),
                    ("不发黄/久洗如新", ["不发黄", "久洗如新"]),
                    ("导汗/风车型", ["导汗", "风车"]),
                    ("腋下透气网孔", ["腋下", "网孔"]),
                    ("日常通勤场景", ["日常", "通勤", "上班", "商务", "周末"]),
                    ("做工走线细节", ["做工", "走线"]),
                    ("大几百对比", ["大几百", "几百"]),
                    ("领口罗纹", ["领口"]),
                    ("腋下立体剪裁", ["立体"]),
                    ("四面弹力", ["弹力"]),
                    ("侧摆口袋", ["口袋"]),
                    ("尺码+身高体重", ["身高", "体重"]),
                    ("质保/顺丰/无理由", ["质保", "顺丰", "无理由"]),
                    ("活动机制讲清楚（618/满减/券）", ["618", "满减", "券", "活动"]),
                    ("品牌+平台双重补贴/折上折", ["补贴", "折上折", "双重"]),
                    ("合并付款更划算", ["合并", "不要单件"]),
                    ("价值逼单", ["便宜", "划算", "质保", "顺丰"]),
                    ("禁讲排汗", []),  # 反向
                ]

                covered = 0
                details = []
                for label, keywords in checks:
                    if label == "禁讲排汗":
                        if "排汗" not in anchor_text:
                            details.append(("✅", label))
                            covered += 1
                        else:
                            details.append(("❌", label))
                    elif keywords:
                        hit = any(kw in anchor_text for kw in keywords)
                        details.append(("✅" if hit else "❌", label))
                        if hit:
                            covered += 1

                z.close()
                return {
                    "anchor": anchor_label,
                    "total": len(checks),
                    "covered": covered,
                    "pct": round(covered / len(checks) * 100),
                    "details": details,
                    "sentences": len([l for l in anchor_text.split('。') if l.strip()]),
                }
            except Exception as e:
                return {"anchor": anchor_label, "error": str(e)}

        # 处理上传文件
        results = []
        for uf in uploaded_files:
            # 从文件名推测主播名
            fname = uf.name
            anchor_name = "未知"
            for name in ["冯芊祎", "朱佳琪", "单楚陵"]:
                if name in fname:
                    anchor_name = name
                    break
            if anchor_name == "未知":
                anchor_name = fname[:20]

            with st.spinner(f"分析 {anchor_name} 的话术..."):
                result = analyze_speech(uf, anchor_name)
                results.append(result)

        # 显示对比
        if results:
            st.divider()

            if mode == "🔥 新人PK":
                st.subheader("🔥 新主播 PK")
            elif mode == "🏆 新人 vs 头部":
                st.subheader("🏆 新人 vs 头部主播")
            else:
                st.subheader("📈 自己历史对比")

            # 柱状图
            valid = [r for r in results if "error" not in r]
            if valid:
                import plotly.express as px
                import pandas as pd
                df = pd.DataFrame([{"主播": r["anchor"], "覆盖率%": r["pct"], "命中": r["covered"], "总项": r["total"]} for r in valid])
                fig = px.bar(df, x="主播", y="覆盖率%", color="主播", text="覆盖率%",
                             color_discrete_sequence=["#E53935", "#FB8C00", "#2E7D32"])
                fig.update_traces(texttemplate='%{text}%', textposition='outside')
                fig.update_layout(height=300, showlegend=False, yaxis_range=[0, 110])
                st.plotly_chart(fig, use_container_width=True)

            # 逐项对比表
            st.subheader("📋 逐项对比")
            if len(valid) >= 2:
                import pandas as pd
                labels = [d[1] for d in valid[0]["details"]]
                rows = []
                for i, label in enumerate(labels):
                    row_data = {"卖点": label}
                    for r in valid:
                        icon, _ = r["details"][i]
                        row_data[r["anchor"]] = icon
                    rows.append(row_data)
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

            # 各主播详情
            for i, r in enumerate(results):
                if "error" in r:
                    st.error(f"❌ {r['anchor']}: {r['error']}")
                else:
                    if mode == "📈 自己历史对比":
                        # 历史对比：第一份是旧的，最后一份是新的
                        if i == 0:
                            delta = 0
                            icon = "📌 上次"
                        else:
                            prev_pct = results[i-1]["pct"]
                            delta = r["pct"] - prev_pct
                            icon = f"{'📈' if delta>0 else '📉' if delta<0 else '➡️'} {'+' if delta>0 else ''}{delta}%"
                        label = f"{icon} {r['anchor']}: {r['pct']}%"
                    else:
                        label = f"{'🥇' if r['pct']>=80 else '🥈' if r['pct']>=60 else '🥉'} {r['anchor']}: {r['pct']}%（{r['covered']}/{r['total']}）"

                    with st.expander(label):
                        missed = [d[1] for d in r["details"] if d[0] == "❌"]
                        if missed:
                            st.markdown("**❌ 遗漏项：**")
                            for m in missed:
                                st.markdown(f"- {m}")
                        else:
                            st.success("全部覆盖 ✅")

            # === AI 总结分析 ===
            st.divider()
            st.subheader("🤖 AI 总结分析")

            if st.button("🔍 AI 分析话术", type="primary", use_container_width=True):
                with st.spinner("AI 分析中..."):
                    valid_results = [r for r in results if "error" not in r]
                    context = f"""你是直播带货话术教练。请分析以下新主播的秘纤产品话术覆盖情况，给出具体评价。

## 秘纤核心卖点清单（共24项）
🎬开篇：龙牙自主研发速干面料、高端+亲肤+速干三合一
💧轻爽科技：柔软透气、不变形不缩水、不发黄久洗如新、风车型导汗、透气对比、腋下网孔
💎价值感：日常通勤场景、做工走线细节、六边形总结、大几百对比
🔧补充：领口罗纹、腋下立体、四面弹力、侧摆口袋
📏尺码：13尺码体系、引导身高体重
🎁活动：618机制讲清、平台品牌双重补贴、合并付款更划算、限时紧迫感
🛡️售后：质保顺丰无理由运费险、价值逼单
⚠️红线：禁讲排汗

## 各主播话术覆盖情况
"""
                    for r in valid_results:
                        context += f"\n### {r['anchor']}：覆盖率 {r['pct']}%（{r['covered']}/{r['total']}）\n"
                        missed = [d[1] for d in r["details"] if d[0] == "❌"]
                        if missed:
                            context += f"遗漏：{'、'.join(missed)}\n"

                    context += f"\n对比模式：{mode}\n请输出：1.各主播优缺点 2.谁表现更好及原因 3.各自最需要提升的3个点 4.具体练习建议。用中文回答，简洁直接。"

                    try:
                        import requests as req, time
                        key = st.secrets.get("SILICONFLOW_KEY", os.environ.get("SILICONFLOW_KEY", ""))
                        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
                        # 依次尝试不同模型（DeepSeek-V3 高峰期容易503）
                        models = ["Pro/zai-org/GLM-4.7"]
                        ai_text = None
                        for model in models:
                            resp = req.post(
                                "https://api.siliconflow.cn/v1/chat/completions",
                                headers=headers,
                                json={"model": model, "max_tokens": 600,
                                      "messages": [{"role": "user", "content": context}]},
                                timeout=60)
                            if resp.status_code == 200:
                                ai_text = resp.json()["choices"][0]["message"]["content"]
                                break
                            elif resp.status_code == 503:
                                time.sleep(1)  # 模型忙，换个试试
                                continue
                            else:
                                st.error(f"API 错误 ({resp.status_code}): {resp.text[:300]}")
                                break
                        if ai_text:
                            st.markdown("### 🤖 AI 分析")
                            st.markdown(ai_text)
                        elif not st.session_state.get("_ai_error_shown"):
                            st.error("所有模型均繁忙，请稍后重试")
                    except Exception as e:
                        st.error(f"AI 调用失败：{e}")
    else:
        st.info("💡 从蝉管家导出「视频话术」xlsx 文件，拖入上方即可自动分析。支持多个文件同时上传对比。")
