"""飞书多维表客户端：实时读写主播数据和成长管理数据。"""
import time, json, os
import requests
import streamlit as st
import urllib3
urllib3.disable_warnings()

BASE_URL = "https://open.feishu.cn/open-apis"
BASE_TOKEN = "Jwu7bRyHvagQ4Hsv8ExcPiOOnnd"
TABLE_SESSIONS = "tblHd2VP27BmN0Dt"  # 大方抖音-当日数据表

# 成长管理表（app 自动创建）
TABLE_ABILITIES = "tblVwBR0551V40uZ"  # 复用大方主播退货率表暂存，后续建独立表


class FeishuClient:
    """飞书 API 客户端，支持读/写多维表"""

    def __init__(self):
        self._token = None
        self._expires = 0

    def _get_token(self):
        if self._token and time.time() < self._expires - 60:
            return self._token
        app_id = st.secrets.get("FEISHU_APP_ID", os.environ.get("FEISHU_APP_ID", "cli_a876dccb3d7a101c"))
        app_secret = st.secrets.get("FEISHU_APP_SECRET", os.environ.get("FEISHU_APP_SECRET", "eTURY2xNmRaSBR6nratpsdn86ENxssTA"))
        try:
            r = requests.post(verify=False, f"{BASE_URL}/auth/v3/tenant_access_token/internal",
                              json={"app_id": app_id, "app_secret": app_secret}, verify=False, timeout=15)
            data = r.json()
            if data.get("code") != 0:
                raise RuntimeError(f"飞书 Token 失败: {data}")
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"网络错误（连不上飞书API）: {e}")
        self._token = data["tenant_access_token"]
        self._expires = time.time() + data.get("expire", 7200)
        return self._token

    def _headers(self):
        return {"Authorization": f"Bearer {self._get_token()}",
                "Content-Type": "application/json; charset=utf-8"}

    # ========== 读取 ==========
    def fetch_all_records(self, table_id, page_size=500):
        """读取一张表的全部记录"""
        items = []
        page_token = None
        while True:
            params = {"page_size": page_size}
            if page_token:
                params["page_token"] = page_token
            r = requests.get(verify=False, 
                f"{BASE_URL}/bitable/v1/apps/{BASE_TOKEN}/tables/{table_id}/records",
                params=params, headers=self._headers(), timeout=60)
            data = r.json()
            if data.get("code") != 0:
                st.error(f"API 错误: {data.get('msg')}")
                break
            d = data.get("data", {})
            items.extend(d.get("items", []))
            if d.get("has_more") and d.get("page_token"):
                page_token = d["page_token"]
            else:
                break
        return items

    def get_sessions(self, anchor_names=None):
        """读取场次数据，聚合为 session 列表"""
        from datetime import datetime
        from collections import defaultdict

        records = self.fetch_all_records(TABLE_SESSIONS)

        # 筛选主播
        filtered = []
        for rec in records:
            fds = rec.get("fields", {})
            anchor = self._text_list(fds.get("主播姓名", []))
            if anchor_names and not any(n in anchor for n in anchor_names):
                continue
            if not anchor:
                continue
            clean = {}
            for k, v in fds.items():
                clean[k] = self._value(v)
            clean["_主播"] = anchor[0] if anchor else "?"
            filtered.append(clean)

        # 按 主播+日期 分组
        groups = defaultdict(list)
        for rec in filtered:
            ts = rec.get("记录时间", 0)
            if isinstance(ts, (int, float)) and ts > 0:
                date = datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d")
            else:
                continue
            key = (rec.get("_主播", "?"), date)
            groups[key].append(rec)

        sessions = []
        for (name, date), recs in groups.items():
            shifts = set()
            ops = set()
            hours_l, gpm_l, uv_l, gmv_l = [], [], [], []
            for r in recs:
                s = self._text_list(r.get("班次", []))
                if s: shifts.update(s)
                op = r.get("跟播运营姓名", "")
                if isinstance(op, str) and op: ops.add(op)
                for f, lst in [("主播直播时长", hours_l), ("单小时GPM(千次观看成交金额)", gpm_l),
                               ("UV价值(单人价值)", uv_l), ("单小时直播间GMV", gmv_l)]:
                    v = r.get(f, 0)
                    if isinstance(v, (int, float)) and v > 0:
                        lst.append(v)

            sessions.append({
                "anchor": name, "date": date,
                "shift": sorted(shifts)[0] if shifts else "?",
                "operator": sorted(ops)[0] if ops else "?",
                "hours": round(sum(hours_l), 1),
                "gmvTotal": round(sum(gmv_l)),
                "gpmAvg": round(sum(gpm_l) / len(gpm_l)) if gpm_l else 0,
                "uvAvg": round(sum(uv_l) / len(uv_l), 2) if uv_l else 0,
                "returnRate": round(self._num(recs[0].get("产品退货率", 0.3)), 3),
            })
        sessions.sort(key=lambda s: (s["anchor"], s["date"]))
        return sessions

    def get_all_anchors(self):
        """获取所有主播列表"""
        sessions = self.get_sessions()
        seen = set()
        for s in sessions:
            seen.add(s["anchor"])
        return sorted(seen)

    def get_anchor_sessions(self, anchor_name):
        """获取指定主播的场次"""
        return [s for s in self.get_sessions([anchor_name]) if s["anchor"] == anchor_name]

    # ========== 成长管理表 ==========
    def _ensure_growth_table(self):
        """确保成长管理表存在，不存在则创建"""
        # 先检查是否已存在
        r = requests.get(verify=False, f"{BASE_URL}/bitable/v1/apps/{BASE_TOKEN}/tables",
                         headers=self._headers(), timeout=15)
        tables = r.json().get("data", {}).get("items", [])
        for t in tables:
            if t.get("name") == "主播成长管理":
                return t["table_id"]

        # 创建新表
        r = requests.post(verify=False, 
            f"{BASE_URL}/bitable/v1/apps/{BASE_TOKEN}/tables",
            headers=self._headers(),
            json={"table": {"name": "主播成长管理"}}, timeout=15)
        data = r.json()
        if data.get("code") != 0:
            st.warning(f"创建成长管理表失败: {data.get('msg')}")
            return None
        table_id = data["data"]["table_id"]

        # 创建字段
        fields = [
            {"field_name": "记录类型", "type": 1},   # 文本: ability/plan/review
            {"field_name": "主播姓名", "type": 1},
            {"field_name": "日期", "type": 1},
            {"field_name": "数据JSON", "type": 1},   # 存整个 JSON
        ]
        for f in fields:
            requests.post(verify=False, 
                f"{BASE_URL}/bitable/v1/apps/{BASE_TOKEN}/tables/{table_id}/fields",
                headers=self._headers(), json={"field_name": f["field_name"], "type": f["type"]}, timeout=15)
        return table_id

    def save_growth_data(self, data_type, anchor, date_str, json_data):
        """保存成长数据（能力评估/计划/复盘）到飞书"""
        # 暂时用 st.session_state 存储，后续可接入飞书表
        pass

    # ========== 工具 ==========
    @staticmethod
    def _text_list(v):
        if isinstance(v, list):
            return [x.get("text", str(x)) if isinstance(x, dict) else str(x) for x in v]
        return [str(v)] if v else []

    @staticmethod
    def _value(v):
        if isinstance(v, list) and v and isinstance(v[0], dict):
            return [x.get("text", x) for x in v]
        return v

    @staticmethod
    def _num(v):
        if isinstance(v, (int, float)):
            return float(v)
        return 0.0


def fmt_date(date_str):
    """2026-05-25 → 5/25"""
    parts = date_str.split("-")
    return f"{int(parts[1])}/{int(parts[2])}"

@st.cache_data(ttl=1800, show_spinner="📡 正在同步飞书数据...")
def get_cached_sessions():
    """30分钟缓存的场次数据"""
    client = FeishuClient()
    return client.get_sessions()


@st.cache_data(ttl=600)
def get_cached_anchors():
    """10分钟缓存的主播列表"""
    client = FeishuClient()
    return client.get_all_anchors()
