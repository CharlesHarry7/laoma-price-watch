# 老马策略表云端盯盘

跑在 GitHub Actions 上的自动盯盘，电脑关机也能工作。

- **盘中盯价**（watch.yml）：美股交易时段每 30 分钟查一遍表上约 120 只股票，谁跌破最低建仓价就发 Telegram 提醒，标注【龙头】/【普通】/【ETF】。同一只股票提醒一次后，涨回 3% 以上再跌破才会重新提醒（记录在 state.json）。
- **存储日报**（digest.yml）：每天北京时间早上 8 点，把存储板块 8 只股票和建仓价的对比发到 Telegram。

行情来源 Yahoo Finance（免费，约 15 分钟延迟）。**只提醒，不下单。**

## 配置

仓库 Settings → Secrets and variables → Actions 里需要两个密钥：

- `TG_TOKEN`：Telegram 机器人令牌
- `TG_CHAT`：Telegram 聊天号

## 修改建仓价

改 `watch.py` 里的 `WATCH` 列表（最低建仓价）和 `STORAGE_TIERS`（存储板块完整档位）即可。
