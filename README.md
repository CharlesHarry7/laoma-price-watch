# Laoma Price Watch｜美股价格监控与 Telegram 提醒

基于 Python 和 GitHub Actions 的云端盯盘工具。按自定义价格档位检查美股行情，将到价、持仓异动、大盘警报和存储板块日报发送到 Telegram。

## 功能

| 功能 | 当前实现 |
| --- | --- |
| 多档到价提醒 | 读取 `WATCH` 的价格档位；每档去重，价格回到该档位上方 3% 后重置 |
| 持仓提醒 | 按 `HOLDINGS_JSON` 检查成本价警戒线和单日涨跌幅 |
| 大盘警报 | 检查纳指与 VIX 的配置阈值，每天去重 |
| 存储板块日报 | 汇总存储股与配置档位的距离，并附持仓未来三天财报提醒 |
| 手动快照 | `--snapshot` 汇总当前到价股票 |
| 状态持久化 | `state.json` 保存提醒状态，Actions 自动提交更新 |

行情由 Yahoo Finance / `yfinance` 提供，可能延迟。工具只发送提醒，不执行交易；档位和阈值是用户配置。

## 配置

在 **Settings → Secrets and variables → Actions** 中配置：

| Secret | 是否必需 | 用途 |
| --- | --- | --- |
| `TG_TOKEN` | 必需 | Telegram 机器人令牌 |
| `TG_CHAT` | 必需 | 接收提醒的聊天 ID |
| `HOLDINGS_JSON` | 可选 | 持仓 JSON，格式为 `{"股票代码": [股数, 成本价]}`；默认空对象 |

## 运行方式

Actions 页面可以手动运行 `intraday-watch` 或 `daily-storage-digest`。本地使用 Python 3.12，并先配置上述环境变量：

```bash
python3 -m pip install yfinance requests
python3 watch.py
python3 watch.py --digest
python3 watch.py --snapshot
```

这些命令会按对应模式向配置的 Telegram 聊天发送提醒。

## 调度与状态

- 盘中任务：工作日 UTC 13:07–21:37，每小时第 7、37 分触发；脚本再按纽约时间 09:25–16:10 检查运行窗口。
- 日报任务：UTC 00:11、01:11、02:11、03:11，即北京时间／台北时间 08:11–11:11；按当天状态去重。
- Actions 调度可能延迟。当前交易时段过滤基于星期和时钟，不是完整交易所节假日日历。

## 仓库导航

| 文件 | 用途 |
| --- | --- |
| [watch.py](watch.py) | 行情读取、价格档位、提醒规则和命令入口 |
| [state.json](state.json) | 提醒去重状态 |
| [.github/workflows/watch.yml](.github/workflows/watch.yml) | 盘中监控调度 |
| [.github/workflows/digest.yml](.github/workflows/digest.yml) | 日报调度 |

修改监控标的和档位时编辑 `watch.py` 的 `WATCH`；修改持仓时更新 `HOLDINGS_JSON` Secret。个人持仓和机器人令牌应保存在 Secrets 中。
