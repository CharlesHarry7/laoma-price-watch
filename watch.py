#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""老马策略表云端盯盘（增强版）
默认模式（盘中，每30分钟）：
  1) 建仓提醒：任何股票触及任意一档建仓价 -> Telegram（每档只提醒一次，涨回3%后再跌破才重新提醒）
  2) 止损提醒：持仓股跌破成本价85% -> 提醒
  3) 异动提醒：持仓股当日涨跌超8% -> 提醒
  4) 大盘警报：纳指当日跌超2% 或 VIX>=30 -> 提醒（每天最多一次）
--digest 模式（每天北京8点）：存储板块日报 + 持仓股未来3天财报提醒
行情来源 Yahoo Finance（约15分钟延迟）。只提醒，不下单。
"""
import json
import os
import sys
import datetime
from zoneinfo import ZoneInfo

import requests
import yfinance as yf

# (代码, 中文名, 板块, [建仓档位从高到低], 标签)
WATCH = [
    ("MSFT", "微软", "科技龙头", [370], "龙头"),
    ("NVDA", "英伟达", "科技龙头", [210, 200], "龙头"),
    ("GOOGL", "谷歌", "科技龙头", [345], "龙头"),
    ("AAPL", "苹果", "科技龙头", [275, 245], "龙头"),
    ("META", "Meta", "科技龙头", [600, 580, 550], "龙头"),
    ("AMZN", "亚马逊", "科技龙头", [235], "龙头"),
    ("TSLA", "特斯拉", "科技龙头", [400, 340], "龙头"),
    ("CRWV", "CoreWeave", "数据中心", [100], "龙头"),
    ("SMCI", "超微电脑", "数据中心", [30], "龙头"),
    ("IREN", "IREN", "数据中心", [55, 50], "普通"),
    ("NBIS", "Nebius", "数据中心", [200, 140], "普通"),
    ("APLD", "Applied Digital", "数据中心", [39, 27], "普通"),
    ("TSM", "台积电", "CPU/半导体", [400, 350], "龙头"),
    ("AVGO", "博通", "CPU/半导体", [400, 350], "龙头"),
    ("AMD", "AMD", "CPU/半导体", [500, 355], "龙头"),
    ("QCOM", "高通", "CPU/半导体", [200, 180], "龙头"),
    ("ARM", "Arm", "CPU/半导体", [300, 230], "龙头"),
    ("INTC", "英特尔", "CPU/半导体", [110, 105, 85], "龙头"),
    ("KLAC", "科磊", "CPU/半导体", [170], "龙头"),
    ("TER", "泰瑞达", "CPU/半导体", [345, 180], "龙头"),
    ("DELL", "戴尔", "CPU/半导体", [330, 250], "龙头"),
    ("ASX", "日月光", "CPU/半导体", [33, 25], "龙头"),
    ("ALAB", "Astera Labs", "CPU/半导体", [320, 250], "普通"),
    ("CBRS", "Cerebras", "CPU/半导体", [170, 160], "普通"),
    ("ON", "安森美", "CPU/半导体", [100, 80], "普通"),
    ("AMKR", "Amkor", "CPU/半导体", [70], "普通"),
    ("FORM", "FormFactor", "CPU/半导体", [130, 110], "普通"),
    ("VSH", "Vishay", "CPU/半导体", [40], "普通"),
    ("TSEM", "Tower半导体", "CPU/半导体", [225, 150], "普通"),
    ("GFS", "格芯", "CPU/半导体", [75, 50], "普通"),
    ("ACMR", "盛美半导体", "CPU/半导体", [70], "普通"),
    ("SMH", "半导体ETF", "CPU/半导体", [490, 440], "ETF"),
    ("RAM", "2倍内存ETF", "CPU/半导体", [18, 15], "ETF"),
    ("MU", "美光", "存储", [850, 650], "龙头"),
    ("SNDK", "闪迪", "存储", [1500, 1300], "龙头"),
    ("STX", "希捷", "存储", [600, 450], "龙头"),
    ("WDC", "西部数据", "存储", [400, 320], "龙头"),
    ("RMBS", "Rambus", "存储", [130, 120, 105], "普通"),
    ("MRAM", "Everspin", "存储", [20, 16], "普通"),
    ("DRAM", "内存ETF", "存储", [55], "ETF"),
    ("KORU", "韩国3倍ETF", "存储", [650], "ETF"),
    ("COHR", "相干", "光模块", [345, 250], "龙头"),
    ("LITE", "Lumentum", "光模块", [800, 600], "龙头"),
    ("FN", "Fabrinet", "光模块", [610, 480], "龙头"),
    ("ANET", "Arista", "光模块", [145, 120], "龙头"),
    ("MRVL", "迈威尔", "光模块", [240, 180], "龙头"),
    ("GLW", "康宁", "光模块", [150, 120], "龙头"),
    ("CIEN", "Ciena", "光模块", [430, 350], "龙头"),
    ("NOK", "诺基亚", "光模块", [13, 8.5], "龙头"),
    ("ERIC", "爱立信", "光模块", [10, 9], "龙头"),
    ("AAOI", "AOI光通信", "光模块", [150, 130], "普通"),
    ("AXTI", "AXT材料", "光模块", [70], "普通"),
    ("CRDO", "Credo", "光模块", [190, 135], "普通"),
    ("EUV", "光刻ETF", "光模块", [27], "ETF"),
    ("FOTO", "光子ETF", "光模块", [20, 18], "ETF"),
    ("RKLB", "火箭实验室", "商业航天", [100, 78, 66], "龙头"),
    ("ASTS", "AST太空移动", "商业航天", [100, 95, 85, 75, 68], "龙头"),
    ("LUNR", "直觉机器", "商业航天", [18], "普通"),
    ("RDW", "Redwire", "商业航天", [12], "普通"),
    ("BKSY", "BlackSky", "商业航天", [25], "普通"),
    ("PL", "行星实验室", "商业航天", [26, 18], "普通"),
    ("DXYZ", "Destiny基金", "商业航天", [45, 29], "普通"),
    ("SIDU", "Sidus太空", "商业航天", [4.5, 4, 3.6], "普通"),
    ("FLY", "萤火虫航天", "商业航天", [38, 33], "普通"),
    ("NASA", "太空ETF", "商业航天", [34, 30], "ETF"),
    ("LMT", "洛克希德马丁", "无人机/国防", [500], "龙头"),
    ("AVAV", "AeroVironment", "无人机/国防", [170], "龙头"),
    ("KRMN", "Karman", "无人机/国防", [47], "普通"),
    ("ONDS", "Ondas", "无人机/国防", [9], "普通"),
    ("PLTR", "Palantir", "AI应用", [135, 125], "龙头"),
    ("ORCL", "甲骨文", "AI应用", [160, 135], "龙头"),
    ("NOW", "ServiceNow", "AI应用", [100, 90], "龙头"),
    ("SNOW", "Snowflake", "AI应用", [145], "龙头"),
    ("PANW", "帕洛阿尔托", "AI应用", [220], "龙头"),
    ("APP", "AppLovin", "AI应用", [480, 390], "龙头"),
    ("HOOD", "Robinhood", "AI应用", [70], "龙头"),
    ("TTWO", "Take-Two", "AI应用", [220, 200], "龙头"),
    ("FIG", "Figma", "AI应用", [18, 16], "普通"),
    ("NTAP", "NetApp", "AI应用", [125], "普通"),
    ("HIMS", "Hims&Hers", "AI应用", [23], "普通"),
    ("FIGR", "Figure", "AI应用", [25], "普通"),
    ("RBLX", "Roblox", "AI应用", [50, 45], "普通"),
    ("SYM", "Symbotic", "AI应用", [40], "普通"),
    ("GEV", "GE Vernova", "能源/核能", [920], "龙头"),
    ("ETN", "伊顿", "能源/核能", [360, 310], "龙头"),
    ("VST", "Vistra", "能源/核能", [145], "龙头"),
    ("VRT", "Vertiv", "能源/核能", [270, 200], "龙头"),
    ("LEU", "Centrus铀浓缩", "能源/核能", [170, 160], "龙头"),
    ("BE", "Bloom能源", "能源/核能", [200], "龙头"),
    ("OKLO", "Oklo", "能源/核能", [50], "普通"),
    ("SMR", "NuScale", "能源/核能", [10], "普通"),
    ("NNE", "纳米核能", "能源/核能", [20], "普通"),
    ("XE", "X-Energy", "能源/核能", [20], "普通"),
    ("AMPX", "Amprius", "能源/核能", [15, 14], "普通"),
    ("WOLF", "Wolfspeed", "能源/核能", [40], "普通"),
    ("PLUG", "Plug Power", "能源/核能", [2.5], "普通"),
    ("FLNC", "Fluence", "能源/核能", [17, 13], "普通"),
    ("LLY", "礼来", "医疗", [860], "龙头"),
    ("NVO", "诺和诺德", "医疗", [42, 40], "龙头"),
    ("ISRG", "直觉外科", "医疗", [400], "龙头"),
    ("VEEV", "Veeva", "医疗", [166], "龙头"),
    ("TEM", "Tempus AI", "医疗", [50], "普通"),
    ("SDGR", "薛定谔", "医疗", [14.5], "普通"),
    ("BMNR", "BitMine", "医疗", [13, 10], "普通"),
    ("RXRX", "Recursion", "医疗", [3.2, 2.8], "普通"),
    ("IBM", "IBM", "量子计算", [235], "龙头"),
    ("IONQ", "IonQ", "量子计算", [60, 40], "龙头"),
    ("QNT", "Quantinuum", "量子计算", [64, 60], "龙头"),
    ("RGTI", "Rigetti", "量子计算", [20], "普通"),
    ("QBTS", "D-Wave", "量子计算", [25, 20], "普通"),
    ("COIN", "Coinbase", "金融/加密", [150], "龙头"),
    ("MSTR", "Strategy", "金融/加密", [100, 70], "龙头"),
    ("CRCL", "Circle", "金融/加密", [80], "龙头"),
    ("SOFI", "SoFi", "金融/加密", [16], "普通"),
    ("MARA", "MARA", "金融/加密", [10], "普通"),
    ("MP", "MP材料", "稀土/资源", [55, 50], "龙头"),
    ("UUUU", "Energy Fuels", "稀土/资源", [15], "龙头"),
    ("USAR", "美国稀土", "稀土/资源", [20, 15], "普通"),
    ("CRML", "关键金属", "稀土/资源", [10], "普通"),
    ("WMT", "沃尔玛", "消费", [100], "龙头"),
    ("ELF", "elf美妆", "消费", [57], "普通"),
    ("MOD", "Modine", "消费", [240, 185], "普通"),
    ("SOXL", "半导体3倍ETF", "ETF参考", [200], "ETF"),
    ("SOXX", "半导体ETF", "ETF参考", [540, 380], "ETF"),
    ("SPMO", "标普动量ETF", "ETF参考", [120, 100], "ETF"),
]

NAME = {w[0]: w[1] for w in WATCH}
STORAGE = ["MU", "SNDK", "STX", "WDC", "RMBS", "MRAM", "DRAM", "KORU"]
# 持仓：代码 -> (股数, 成本价)
HOLDINGS = {
    "AAOI": (3, 134.84),
    "AXTI": (18, 69.18),
    "CRML": (6, 10.06),
    "CRWV": (13, 100.31),
    "MP": (7, 54.09),
    "NVDA": (2, 197.30),
    "OKLO": (2, 51.17),
    "RMBS": (3, 118.31),
    "SMR": (38, 9.86),
}
LEVERAGED = {"KORU": "3倍", "SOXL": "3倍", "RAM": "2倍"}
STOP_LOSS = 0.85      # 成本价的85%（亏15%）触发止损提醒
CRASH = 0.08          # 持仓当日涨跌8%触发异动提醒
STATE_FILE = "state.json"
FOOTER = "到价≠该买，先查一下有没有坏消息再动手。买卖请自己在IBKR操作。（行情来自Yahoo，可能延迟约15分钟）"


def now_et():
    return datetime.datetime.now(ZoneInfo("America/New_York"))


def market_open(t):
    if t.weekday() >= 5:
        return False
    hm = t.hour * 100 + t.minute
    return 925 <= hm <= 1610


def send_telegram(text):
    token = os.environ["TG_TOKEN"]
    chat = os.environ["TG_CHAT"]
    for _ in range(2):
        try:
            r = requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                data={"chat_id": chat, "text": text},
                timeout=20,
            )
            if r.json().get("ok"):
                return True
            print("telegram rejected:", r.text[:300])
        except Exception as e:
            print("telegram error:", e)
    return False


def send_chunked(header, lines, footer=FOOTER):
    ok = True
    msg = header
    for ln in lines:
        if len(msg) + len(ln) + len(footer) + 4 > 3800:
            ok = send_telegram(msg + "\n\n" + footer) and ok
            msg = header + "（续）"
        msg += "\n" + ln
    ok = send_telegram(msg + "\n\n" + footer) and ok
    if not ok:
        raise SystemExit("telegram send failed")


def _grab(df, tickers, out):
    for t in tickers:
        try:
            s = df[t]["Close"].dropna()
            if len(s):
                out[t] = float(s.iloc[-1])
        except Exception:
            pass


def fetch_prices(tickers):
    prices = {}
    try:
        df = yf.download(tickers, period="1d", interval="15m", progress=False,
                         threads=True, group_by="ticker", auto_adjust=False)
        _grab(df, tickers, prices)
    except Exception as e:
        print("download error:", e)
    missing = [t for t in tickers if t not in prices]
    if missing:
        try:
            df = yf.download(missing, period="5d", interval="1d", progress=False,
                             threads=True, group_by="ticker", auto_adjust=False)
            _grab(df, missing, prices)
        except Exception as e:
            print("fallback download error:", e)
    return prices


def fetch_prev_close(tickers):
    """取上一交易日收盘价（若今天的日K已生成则取倒数第二根）"""
    prev = {}
    today = now_et().date()
    try:
        df = yf.download(tickers, period="7d", interval="1d", progress=False,
                         threads=True, group_by="ticker", auto_adjust=False)
        for t in tickers:
            try:
                s = df[t]["Close"].dropna()
                if len(s) >= 2 and s.index[-1].date() >= today:
                    prev[t] = float(s.iloc[-2])
                elif len(s):
                    prev[t] = float(s.iloc[-1])
            except Exception:
                pass
    except Exception as e:
        print("prev close error:", e)
    return prev


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=1, sort_keys=True)


def run_watch():
    t = now_et()
    if not market_open(t):
        print("market closed, skip:", t)
        return
    today = str(t.date())
    tickers = [w[0] for w in WATCH]
    prices = fetch_prices(tickers + ["^IXIC", "^VIX"])
    print(f"got {len(prices)} quotes")
    if len(prices) < len(tickers) * 0.5:
        print("too many missing quotes, skip this round")
        return
    prev = fetch_prev_close(list(HOLDINGS) + ["^IXIC"])
    state = load_state()
    market_lines, stop_lines, crash_lines, entry_lines = [], [], [], []

    # 4) 大盘警报（每天最多一次）
    ixic, ixic_prev, vix = prices.get("^IXIC"), prev.get("^IXIC"), prices.get("^VIX")
    if ixic and ixic_prev and f"MKT:{today}" not in state:
        chg = ixic / ixic_prev - 1
        if chg <= -0.02 or (vix and vix >= 30):
            vix_txt = f"，恐慌指数VIX {vix:.0f}" if vix else ""
            market_lines.append(
                f"🌧 大盘警报：纳指今天{'跌' if chg < 0 else '涨'} {abs(chg) * 100:.1f}%{vix_txt}。"
                f"今天是大盘级波动，个股下跌未必是自身出问题。")
            state[f"MKT:{today}"] = 1

    for tk, name, sector, tiers, tag in WATCH:
        p = prices.get(tk)
        if p is None:
            continue
        # 1) 建仓档位提醒（每档一次）
        broken_new = []
        for tier in tiers:
            key = f"{tk}@{tier}"
            if p <= tier and key not in state:
                broken_new.append(tier)
                state[key] = round(p, 2)
            elif key in state and p > tier * 1.03:
                state.pop(key)
        if broken_new:
            tier_txt = "、".join(str(x) for x in broken_new)
            line = f"【{tag}】{tk} {name}（{sector}）现价 {p:.2f}，触及建仓档位 {tier_txt}"
            if tk in HOLDINGS:
                line += "（你已持有）"
            if tk in LEVERAGED:
                line += f"｜{LEVERAGED[tk]}杠杆产品，波动极大，仓位要小"
            entry_lines.append(line)
        # 2) 止损提醒（持仓，成本价-15%，每次跌破提醒一次）
        if tk in HOLDINGS:
            shares, cost = HOLDINGS[tk]
            sl_key = f"SL:{tk}"
            sl_line_price = cost * STOP_LOSS
            if p <= sl_line_price and sl_key not in state:
                loss = (1 - p / cost) * 100
                stop_lines.append(
                    f"🛑 止损提醒：{tk} {name} 现价 {p:.2f}，比你的成本价 {cost} 低了 {loss:.0f}%，"
                    f"已跌破15%警戒线（持有{shares}股），想好要不要止损")
                state[sl_key] = round(p, 2)
            elif sl_key in state and p > sl_line_price * 1.03:
                state.pop(sl_key)
            # 3) 异动提醒（持仓当日±8%，每天一次）
            pc = prev.get(tk)
            mv_key = f"MV:{tk}:{today}"
            if pc and mv_key not in state:
                chg = p / pc - 1
                if abs(chg) >= CRASH:
                    crash_lines.append(
                        f"⚡ 异动：{tk} {name} 今天{'大跌' if chg < 0 else '大涨'} {abs(chg) * 100:.1f}%"
                        f"（现价 {p:.2f}），多半有新闻，建议查一下原因")
                    state[mv_key] = 1

    save_state(state)
    lines = market_lines + stop_lines + crash_lines + entry_lines
    if lines:
        header = f"🔔 提醒（美东 {t:%m-%d %H:%M}）"
        send_chunked(header, lines)
        print(f"sent {len(lines)} lines")
    else:
        print("no new alerts")


def upcoming_earnings():
    """持仓股未来3天内的财报日（每个日期只提醒一次）"""
    lines = []
    state = load_state()
    today = now_et().date()
    for tk in HOLDINGS:
        try:
            cal = yf.Ticker(tk).calendar or {}
            dates = cal.get("Earnings Date") or []
            for d in dates:
                if hasattr(d, "date"):
                    d = d.date()
                if today <= d <= today + datetime.timedelta(days=3):
                    key = f"ER:{tk}:{d}"
                    if key not in state:
                        lines.append(f"📅 财报提醒：{tk} {NAME.get(tk, tk)} 将于 {d:%m-%d} 发布财报，"
                                     f"财报夜波动可能很大")
                        state[key] = 1
                    break
        except Exception as e:
            print("earnings error", tk, e)
    save_state(state)
    return lines


def run_digest():
    bj = datetime.datetime.now(ZoneInfo("Asia/Shanghai"))
    et = now_et()
    prices = fetch_prices(STORAGE)
    hit, near, far = [], [], []
    for tk in STORAGE:
        tiers = next(w[3] for w in WATCH if w[0] == tk)
        top = max(tiers)
        tier_str = "/".join(str(x) for x in tiers)
        p = prices.get(tk)
        if p is None:
            far.append(f"{tk} 无行情")
            continue
        if p <= top:
            hit.append(f"✅ {tk} {NAME[tk]}：现价 {p:.2f}，已到建仓区（档位 {tier_str}）")
        elif p <= top * 1.05:
            near.append(f"⚠️ {tk} {NAME[tk]}：现价 {p:.2f}，距建仓价 {top} 差 {(p / top - 1) * 100:.1f}%")
        else:
            far.append(f"{tk} 差{(p / top - 1) * 100:.0f}%")
    header = f"📊 存储股日报 {bj:%m-%d}"
    if et.weekday() >= 5:
        header += "（周末休市，为上个交易日收盘价）"
    lines = hit + near
    if not lines:
        lines = ["今天都没到价"]
    if far:
        lines.append("未到：" + "、".join(far))
    if any(" KORU " in l for l in hit):
        lines.append("KORU 是3倍杠杆产品，波动极大，仓位要小。")
    lines += upcoming_earnings()
    send_chunked(header, lines)
    print("digest sent")


if __name__ == "__main__":
    if "--digest" in sys.argv:
        run_digest()
    else:
        run_watch()
