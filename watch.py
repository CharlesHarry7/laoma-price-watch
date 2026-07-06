#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""老马策略表云端盯盘
- 默认模式：美股开盘时段运行，任何股票跌破最低建仓价 -> 发 Telegram（去重，涨回3%后再跌破才重新提醒）
- --digest 模式：发存储板块日报
行情来源 Yahoo Finance（可能延迟约15分钟）。只提醒，不下单。
"""
import json
import os
import sys
import datetime
from zoneinfo import ZoneInfo

import requests
import yfinance as yf

# (代码, 中文名, 板块, 最低建仓价, 标签)
WATCH = [
    ("MSFT", "微软", "科技龙头", 370, "龙头"),
    ("NVDA", "英伟达", "科技龙头", 200, "龙头"),
    ("GOOGL", "谷歌", "科技龙头", 345, "龙头"),
    ("AAPL", "苹果", "科技龙头", 245, "龙头"),
    ("META", "Meta", "科技龙头", 550, "龙头"),
    ("AMZN", "亚马逊", "科技龙头", 235, "龙头"),
    ("TSLA", "特斯拉", "科技龙头", 340, "龙头"),
    ("CRWV", "CoreWeave", "数据中心", 100, "龙头"),
    ("SMCI", "超微电脑", "数据中心", 30, "龙头"),
    ("IREN", "IREN", "数据中心", 50, "普通"),
    ("NBIS", "Nebius", "数据中心", 140, "普通"),
    ("APLD", "Applied Digital", "数据中心", 27, "普通"),
    ("TSM", "台积电", "CPU/半导体", 350, "龙头"),
    ("AVGO", "博通", "CPU/半导体", 350, "龙头"),
    ("AMD", "AMD", "CPU/半导体", 355, "龙头"),
    ("QCOM", "高通", "CPU/半导体", 180, "龙头"),
    ("ARM", "Arm", "CPU/半导体", 230, "龙头"),
    ("INTC", "英特尔", "CPU/半导体", 85, "龙头"),
    ("KLAC", "科磊", "CPU/半导体", 170, "龙头"),
    ("TER", "泰瑞达", "CPU/半导体", 180, "龙头"),
    ("DELL", "戴尔", "CPU/半导体", 250, "龙头"),
    ("ASX", "日月光", "CPU/半导体", 25, "龙头"),
    ("ALAB", "Astera Labs", "CPU/半导体", 250, "普通"),
    ("CBRS", "Cerebras", "CPU/半导体", 160, "普通"),
    ("ON", "安森美", "CPU/半导体", 80, "普通"),
    ("AMKR", "Amkor", "CPU/半导体", 70, "普通"),
    ("FORM", "FormFactor", "CPU/半导体", 110, "普通"),
    ("VSH", "Vishay", "CPU/半导体", 40, "普通"),
    ("TSEM", "Tower半导体", "CPU/半导体", 150, "普通"),
    ("GFS", "格芯", "CPU/半导体", 50, "普通"),
    ("ACMR", "盛美半导体", "CPU/半导体", 70, "普通"),
    ("SMH", "半导体ETF", "CPU/半导体", 440, "ETF"),
    ("RAM", "2倍内存ETF", "CPU/半导体", 15, "ETF"),
    ("MU", "美光", "存储", 650, "龙头"),
    ("SNDK", "闪迪", "存储", 1300, "龙头"),
    ("STX", "希捷", "存储", 450, "龙头"),
    ("WDC", "西部数据", "存储", 320, "龙头"),
    ("RMBS", "Rambus", "存储", 105, "普通"),
    ("MRAM", "Everspin", "存储", 16, "普通"),
    ("DRAM", "内存ETF", "存储", 55, "ETF"),
    ("KORU", "韩国3倍ETF", "存储", 650, "ETF"),
    ("COHR", "相干", "光模块", 250, "龙头"),
    ("LITE", "Lumentum", "光模块", 600, "龙头"),
    ("FN", "Fabrinet", "光模块", 480, "龙头"),
    ("ANET", "Arista", "光模块", 120, "龙头"),
    ("MRVL", "迈威尔", "光模块", 180, "龙头"),
    ("GLW", "康宁", "光模块", 120, "龙头"),
    ("CIEN", "Ciena", "光模块", 350, "龙头"),
    ("NOK", "诺基亚", "光模块", 8.5, "龙头"),
    ("ERIC", "爱立信", "光模块", 9, "龙头"),
    ("AAOI", "AOI光通信", "光模块", 130, "普通"),
    ("AXTI", "AXT材料", "光模块", 70, "普通"),
    ("CRDO", "Credo", "光模块", 135, "普通"),
    ("EUV", "光刻ETF", "光模块", 27, "ETF"),
    ("FOTO", "光子ETF", "光模块", 18, "ETF"),
    ("RKLB", "火箭实验室", "商业航天", 66, "龙头"),
    ("ASTS", "AST太空移动", "商业航天", 68, "龙头"),
    ("LUNR", "直觉机器", "商业航天", 18, "普通"),
    ("RDW", "Redwire", "商业航天", 12, "普通"),
    ("BKSY", "BlackSky", "商业航天", 25, "普通"),
    ("PL", "行星实验室", "商业航天", 18, "普通"),
    ("DXYZ", "Destiny基金", "商业航天", 29, "普通"),
    ("SIDU", "Sidus太空", "商业航天", 3.6, "普通"),
    ("FLY", "萤火虫航天", "商业航天", 33, "普通"),
    ("NASA", "太空ETF", "商业航天", 30, "ETF"),
    ("LMT", "洛克希德马丁", "无人机/国防", 500, "龙头"),
    ("AVAV", "AeroVironment", "无人机/国防", 170, "龙头"),
    ("KRMN", "Karman", "无人机/国防", 47, "普通"),
    ("ONDS", "Ondas", "无人机/国防", 9, "普通"),
    ("PLTR", "Palantir", "AI应用", 125, "龙头"),
    ("ORCL", "甲骨文", "AI应用", 135, "龙头"),
    ("NOW", "ServiceNow", "AI应用", 90, "龙头"),
    ("SNOW", "Snowflake", "AI应用", 145, "龙头"),
    ("PANW", "帕洛阿尔托", "AI应用", 220, "龙头"),
    ("APP", "AppLovin", "AI应用", 390, "龙头"),
    ("HOOD", "Robinhood", "AI应用", 70, "龙头"),
    ("TTWO", "Take-Two", "AI应用", 200, "龙头"),
    ("FIG", "Figma", "AI应用", 16, "普通"),
    ("NTAP", "NetApp", "AI应用", 125, "普通"),
    ("HIMS", "Hims&Hers", "AI应用", 23, "普通"),
    ("FIGR", "Figure", "AI应用", 25, "普通"),
    ("RBLX", "Roblox", "AI应用", 45, "普通"),
    ("SYM", "Symbotic", "AI应用", 40, "普通"),
    ("GEV", "GE Vernova", "能源/核能", 920, "龙头"),
    ("ETN", "伊顿", "能源/核能", 310, "龙头"),
    ("VST", "Vistra", "能源/核能", 145, "龙头"),
    ("VRT", "Vertiv", "能源/核能", 200, "龙头"),
    ("LEU", "Centrus铀浓缩", "能源/核能", 160, "龙头"),
    ("BE", "Bloom能源", "能源/核能", 200, "龙头"),
    ("OKLO", "Oklo", "能源/核能", 50, "普通"),
    ("SMR", "NuScale", "能源/核能", 10, "普通"),
    ("NNE", "纳米核能", "能源/核能", 20, "普通"),
    ("XE", "X-Energy", "能源/核能", 20, "普通"),
    ("AMPX", "Amprius", "能源/核能", 14, "普通"),
    ("WOLF", "Wolfspeed", "能源/核能", 40, "普通"),
    ("PLUG", "Plug Power", "能源/核能", 2.5, "普通"),
    ("FLNC", "Fluence", "能源/核能", 13, "普通"),
    ("LLY", "礼来", "医疗", 860, "龙头"),
    ("NVO", "诺和诺德", "医疗", 40, "龙头"),
    ("ISRG", "直觉外科", "医疗", 400, "龙头"),
    ("VEEV", "Veeva", "医疗", 166, "龙头"),
    ("TEM", "Tempus AI", "医疗", 50, "普通"),
    ("SDGR", "薛定谔", "医疗", 14.5, "普通"),
    ("BMNR", "BitMine", "医疗", 10, "普通"),
    ("RXRX", "Recursion", "医疗", 2.8, "普通"),
    ("IBM", "IBM", "量子计算", 235, "龙头"),
    ("IONQ", "IonQ", "量子计算", 40, "龙头"),
    ("QNT", "Quantinuum", "量子计算", 60, "龙头"),
    ("RGTI", "Rigetti", "量子计算", 20, "普通"),
    ("QBTS", "D-Wave", "量子计算", 20, "普通"),
    ("COIN", "Coinbase", "金融/加密", 150, "龙头"),
    ("MSTR", "Strategy", "金融/加密", 70, "龙头"),
    ("CRCL", "Circle", "金融/加密", 80, "龙头"),
    ("SOFI", "SoFi", "金融/加密", 16, "普通"),
    ("MARA", "MARA", "金融/加密", 10, "普通"),
    ("MP", "MP材料", "稀土/资源", 50, "龙头"),
    ("UUUU", "Energy Fuels", "稀土/资源", 15, "龙头"),
    ("USAR", "美国稀土", "稀土/资源", 15, "普通"),
    ("CRML", "关键金属", "稀土/资源", 10, "普通"),
    ("WMT", "沃尔玛", "消费", 100, "龙头"),
    ("ELF", "elf美妆", "消费", 57, "普通"),
    ("MOD", "Modine", "消费", 185, "普通"),
    ("SOXL", "半导体3倍ETF", "ETF参考", 200, "ETF"),
    ("SOXX", "半导体ETF", "ETF参考", 380, "ETF"),
    ("SPMO", "标普动量ETF", "ETF参考", 100, "ETF"),
]

# 存储板块完整建仓档位（日报用）
STORAGE_TIERS = {
    "MU": [850, 650],
    "SNDK": [1500, 1300],
    "STX": [600, 450],
    "WDC": [400, 320],
    "RMBS": [130, 120, 105],
    "MRAM": [20, 16],
    "DRAM": [55],
    "KORU": [650],
}
HELD = {"AAOI", "AXTI", "CRML", "CRWV", "MP", "NVDA", "OKLO", "RMBS", "SMR"}
LEVERAGED = {"KORU": "3倍", "SOXL": "3倍", "RAM": "2倍"}
STATE_FILE = "state.json"
FOOTER = "到价≠该买，先查一下有没有坏消息再动手。买入请自己在IBKR操作。（行情来自Yahoo，可能延迟约15分钟）"


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
        except Exception as e:
            print("telegram error:", e)
    return False


def send_chunked(header, lines, footer):
    msg = header
    for ln in lines:
        if len(msg) + len(ln) + len(footer) + 4 > 3800:
            send_telegram(msg + "\n\n" + footer)
            msg = header + "（续）"
        msg += "\n" + ln
    send_telegram(msg + "\n\n" + footer)


def fetch_prices(tickers):
    prices = {}

    def grab(df, ts):
        for t in ts:
            try:
                s = df[t]["Close"].dropna()
                if len(s):
                    prices[t] = float(s.iloc[-1])
            except Exception:
                pass

    try:
        df = yf.download(tickers, period="1d", interval="15m", progress=False,
                         threads=True, group_by="ticker", auto_adjust=False)
        grab(df, tickers)
    except Exception as e:
        print("download error:", e)
    missing = [t for t in tickers if t not in prices]
    if missing:
        try:
            df = yf.download(missing, period="5d", interval="1d", progress=False,
                             threads=True, group_by="ticker", auto_adjust=False)
            grab(df, missing)
        except Exception as e:
            print("fallback download error:", e)
    return prices


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
    prices = fetch_prices([w[0] for w in WATCH])
    print(f"got {len(prices)}/{len(WATCH)} prices")
    if len(prices) < len(WATCH) * 0.5:
        print("too many missing quotes, skip this round")
        return
    state = load_state()
    alerts = []
    for tk, name, sector, entry, tag in WATCH:
        p = prices.get(tk)
        if p is None:
            continue
        if p <= entry and tk not in state:
            state[tk] = round(p, 2)
            line = f"【{tag}】{tk} {name}（{sector}）现价 {p:.2f}，跌破最低建仓价 {entry}"
            if tk in HELD:
                line += "（你已持有）"
            if tk in LEVERAGED:
                line += f"｜注意：{LEVERAGED[tk]}杠杆产品，波动极大，仓位要小"
            alerts.append(line)
        elif tk in state and p > entry * 1.03:
            state.pop(tk)
            print(f"{tk} recovered above {entry}*1.03, reset")
    save_state(state)
    if alerts:
        header = f"🔔 到价提醒（美东 {t:%m-%d %H:%M}）"
        send_chunked(header, alerts, FOOTER)
        print(f"sent {len(alerts)} alerts")
    else:
        print("no new alerts")


def run_digest():
    bj = datetime.datetime.now(ZoneInfo("Asia/Shanghai"))
    et = now_et()
    tickers = list(STORAGE_TIERS)
    prices = fetch_prices(tickers)
    hit, near, far = [], [], []
    for tk in tickers:
        tiers = STORAGE_TIERS[tk]
        top = max(tiers)
        tier_str = "/".join(str(x) for x in tiers)
        p = prices.get(tk)
        if p is None:
            far.append(f"{tk} 无行情")
            continue
        name = next((w[1] for w in WATCH if w[0] == tk), tk)
        if p <= top:
            hit.append(f"✅ {tk} {name}：现价 {p:.2f}，已到建仓区（档位 {tier_str}）")
        elif p <= top * 1.05:
            near.append(f"⚠️ {tk} {name}：现价 {p:.2f}，距建仓价 {top} 差 {(p / top - 1) * 100:.1f}%")
        else:
            far.append(f"{tk} 差{(p / top - 1) * 100:.0f}%")
    header = f"📊 存储股日报 {bj:%m-%d}"
    if et.weekday() >= 5:
        header += "（周末休市，为上个交易日收盘价）"
    lines = hit + near
    if not lines:
        lines = ["今天都没到价"]
    lines.append("未到：" + "、".join(far) if far else "")
    if "KORU" in [l.split()[1] for l in hit if len(l.split()) > 1]:
        lines.append("KORU 是3倍杠杆产品，波动极大，仓位要小。")
    send_chunked(header, [l for l in lines if l], FOOTER)
    print("digest sent")


if __name__ == "__main__":
    if "--digest" in sys.argv:
        run_digest()
    else:
        run_watch()
