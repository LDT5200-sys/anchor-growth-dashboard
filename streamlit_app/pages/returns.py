"""冯芊祎专属辅导面板：退货率诊断 + 预警 + 实操检查表"""

import streamlit as st
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
avg_rate = sum(all_rates)/len(all_rates) if all_rates else 0

# ============================================
st.title("🎯 冯芊祎 · 专属辅导面板")

c1, c2, c3, c4 = st.columns(4)
c1.metric("累计销售额", f"¥{r_data['sales']/10000:.1f}万")
c2.metric("累计退货额", f"¥{r_data['returns']/10000:.1f}万")
c3.metric("退货率", f"{r_rate}%")
delta = round(r_rate - avg_rate, 1)
c4.metric("vs 大盘均值", f"{'🔴' if delta>3 else '🟡' if delta>0 else '🟢'} {delta:+.1f}%", delta=f"大盘 {avg_rate}%")

st.divider()

tab1, tab2, tab3 = st.tabs(["📈 退货率 × GPM", "⚠️ 异常预警", "✅ 辅导检查清单"])

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
        "产品知识": ["主推品卖点能脱稿讲", "能回答尺码/面料常见问题", "了解竞品区别"],
        "开场承接": ["前5分钟破冰完成", "福袋/互动话术到位", "讲品框架没散"],
        "控场节奏": ["高低流速切换自如", "没被公屏带偏", "语速适中没起飞"],
        "逼单转化": ["每轮讲完都逼单了", "制造了紧迫感但不假", "售后保障话术到位"],
        "塑品能力": ["痛点场景化到位", "连带推荐自然", "画面展示清晰"],
        "复盘动作": ["看了录屏回放", "找到1个改进点", "练了下场话术"],
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
