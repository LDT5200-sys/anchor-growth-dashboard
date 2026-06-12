#!/usr/bin/env python3
"""
飞书数据同步脚本 —— 拉取指定主播的场次数据，生成 data.json

用法：
  python3 sync_feishu.py                          # 更新冯芊祎
  python3 sync_feishu.py --anchor 邹楠楠            # 更新其他主播
"""
import sys, json, os, time
from datetime import datetime
from collections import defaultdict
import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(SCRIPT_DIR, "data.json")

# ====== 凭据加载 ======
def _load_env():
    env_file = os.path.join(SCRIPT_DIR, ".env")
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    if k.strip() not in os.environ:
                        os.environ[k.strip()] = v.strip()

_load_env()

APP_ID = os.environ.get("FEISHU_APP_ID", "")
APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "")
if not APP_ID or not APP_SECRET:
    print("❌ 请设置 FEISHU_APP_ID 和 FEISHU_APP_SECRET 环境变量，或在 .env 文件中配置")
    sys.exit(1)

BASE_TOKEN = "Jwu7bRyHvagQ4Hsv8ExcPiOOnnd"
TABLE_ID = "tblHd2VP27BmN0Dt"  # 大方抖音-当日数据表

# ====== Token 缓存 ======
_token_cache = {"token": None, "expires_at": 0}

def get_token():
    if _token_cache["token"] and time.time() < _token_cache["expires_at"] - 60:
        return _token_cache["token"]
    r = requests.post(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": APP_ID, "app_secret": APP_SECRET}, timeout=15
    )
    data = r.json()
    if data.get("code") != 0:
        raise RuntimeError(f"获取 token 失败: {data}")
    _token_cache["token"] = data["tenant_access_token"]
    _token_cache["expires_at"] = time.time() + data.get("expire", 7200)
    return _token_cache["token"]

# ====== 工具函数 ======
def ts_to_date(ms):
    return datetime.fromtimestamp(ms / 1000).strftime('%Y-%m-%d')

def get_field_value(fields_dict, key, default=None):
    v = fields_dict.get(key, default)
    if isinstance(v, list) and v and isinstance(v[0], dict):
        return [x.get('text', x) for x in v]
    return v

# ====== 核心逻辑 ======
def fetch_records(anchor_name):
    """拉取指定主播的全部原始记录"""
    headers = {
        "Authorization": f"Bearer {get_token()}",
        "Content-Type": "application/json; charset=utf-8",
    }

    records = []
    page_token = None

    while True:
        params = {"page_size": 500}
        if page_token:
            params["page_token"] = page_token

        r = requests.get(
            f"https://open.feishu.cn/open-apis/bitable/v1/apps/{BASE_TOKEN}/tables/{TABLE_ID}/records",
            params=params, headers=headers, timeout=60
        )
        data = r.json()
        if data.get("code") != 0:
            print(f"  ❌ API 错误: {data.get('msg', data)}")
            break

        d = data.get("data", {})
        for rec in d.get("items", []):
            fds = rec.get("fields", {})
            anchor_field = fds.get("主播姓名", [])
            names = []
            if isinstance(anchor_field, list):
                names = [a.get('text', '') for a in anchor_field if isinstance(a, dict)]
            elif isinstance(anchor_field, str):
                names = [anchor_field]

            if any(anchor_name in n for n in names):
                clean = {k: get_field_value(fds, k) for k in fds}
                records.append(clean)

        print(f"  已扫描 {len(records)} 条...", end='\r')

        if d.get("has_more") and d.get("page_token"):
            page_token = d["page_token"]
        else:
            break

    return records

def aggregate_sessions(records):
    """将按小时的原始记录聚合为场次"""
    by_date = defaultdict(list)
    for rec in records:
        ts = rec.get('记录时间', 0)
        date = ts_to_date(ts)
        by_date[date].append(rec)

    sessions = []
    for date, recs in sorted(by_date.items()):
        shifts = set()
        ops = set()
        hours_list, gpm_list, uv_list, gmv_list = [], [], [], []

        for r in recs:
            shift = r.get('班次', ['?'])
            if isinstance(shift, list):
                shifts.update(shift)
            else:
                shifts.add(str(shift))

            op = r.get('跟播运营姓名', '?')
            if isinstance(op, str):
                ops.add(op)

            for field, lst in [('主播直播时长', hours_list),
                               ('单小时GPM(千次观看成交金额)', gpm_list),
                               ('UV价值(单人价值)', uv_list),
                               ('单小时直播间GMV', gmv_list)]:
                v = r.get(field, 0)
                if isinstance(v, (int, float)) and v > 0:
                    lst.append(v)

        sessions.append({
            "date": date,
            "shift": sorted(shifts)[0] if shifts else '?',
            "operator": sorted(ops)[0] if ops else '?',
            "hours": round(sum(hours_list), 1),
            "gmvTotal": round(sum(gmv_list)),
            "gpmAvg": round(sum(gpm_list) / len(gpm_list)) if gpm_list else 0,
            "uvAvg": round(sum(uv_list) / len(uv_list), 2) if uv_list else 0,
            "returnRate": round(recs[0].get('产品退货率', 0.3), 3) if recs else 0.3,
        })

    return sessions

def main():
    anchor_name = "冯芊祎"
    for arg in sys.argv[1:]:
        if arg.startswith("--anchor="):
            anchor_name = arg.split("=", 1)[1]
        elif arg == "--anchor":
            idx = sys.argv.index("--anchor") + 1
            if idx < len(sys.argv):
                anchor_name = sys.argv[idx]

    print(f"🔄 同步「{anchor_name}」数据...")

    records = fetch_records(anchor_name)
    print(f"\n📊 找到 {len(records)} 条原始记录")

    if not records:
        print(f"⚠️ 未找到「{anchor_name}」的数据，请检查姓名是否正确")
        return

    sessions = aggregate_sessions(records)
    print(f"📅 聚合为 {len(sessions)} 场：")
    for s in sessions:
        print(f"  {s['date']} | {s['shift']}班 | {s['operator']} | "
              f"{s['hours']}h | GMV ¥{s['gmvTotal']:,} | "
              f"GPM {s['gpmAvg']:,} | UV {s['uvAvg']}")

    # 加载现有 data.json（保留人工数据：评估/计划/复盘）
    existing = {}
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                existing = json.load(f)
        except:
            pass

    output = {
        "anchor": {
            "name": anchor_name,
            "startDate": sessions[0]['date'] if sessions else existing.get('anchor', {}).get('startDate', ''),
            "level": existing.get('anchor', {}).get('level', '新人期'),
            "mainProduct": existing.get('anchor', {}).get('mainProduct', '秘纤'),
        },
        "abilityLabels": existing.get("abilityLabels", [
            "产品知识", "话术框架", "控场节奏", "塑品能力", "逼单转化",
            "数据感知", "情绪管理", "评论互动", "镜头表现", "学习成长"
        ]),
        "sessions": sessions,
        "abilities": existing.get("abilities", []),
        "weeklyPlans": existing.get("weeklyPlans", []),
        "reviews": existing.get("reviews", []),
        "materials": existing.get("materials", []),
    }

    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 已写入 {DATA_FILE}")

if __name__ == "__main__":
    main()
