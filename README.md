# 主播成长看板 · Anchor Growth Dashboard

## 用途
一对一主播辅导工具，用于新主播冯芊祎的长期化监督、优化、复盘系统性提升。

## 功能
- 📊 **概览**：关键指标卡片 + 最新场次摘要 + 能力雷达图
- 🎯 **能力评估**：10项能力评分 + 历史对比雷达图
- 📈 **业绩趋势**：GMV/GPM/UV/退货率折线图 + 场次对比表
- 📋 **成长计划**：周计划编辑 + 培训资料关联
- 📝 **复盘记录**：每场复盘表单 + 历史复盘列表

## 数据同步

```bash
# 手动同步最新场次数据
python3 sync_feishu.py

# 同步其他主播
python3 sync_feishu.py --anchor 邹楠楠
```

同步脚本从飞书「大方抖音-当日数据表」拉取按小时记录的原始数据，聚合为场次后写入 `data.json`。

## 部署
线上地址：https://ldt5200-sys.github.io/anchor-growth-dashboard/

## 文件结构
```
├── index.html          ← 主页面（含全部 CSS/JS）
├── data.json           ← 数据文件（场次、评估、计划、复盘）
├── sync_feishu.py      ← 飞书数据同步脚本
└── README.md
```
