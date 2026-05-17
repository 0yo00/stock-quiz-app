# -*- coding: utf-8 -*-
"""
台股盤中刷題練習（MVP）
=========================
看歷史資料 + Pivot 線，預測後續走勢。

題目格式：
  - 隨機選一檔台股大型股（預設 30 檔熱門）
  - 隨機選近 60 天的某個交易日
  - 揭露 9:00 - 隨機時間（10:00 / 11:00 / 12:00）的 K 線
  - 顯示古典派 Pivot Points 七條線（R3/R2/R1/P/S1/S2/S3）
  - 你猜：當天 13:30 收盤會「漲」還是「跌」相對揭露時間？

啟動方式：
  streamlit run stock_quiz.py
"""
from __future__ import annotations

import json
import random
from datetime import date, datetime, time, timedelta
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import yfinance as yf

# ════════════════════════════════════════════════════════════════════
#  配置
# ════════════════════════════════════════════════════════════════════

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)
SCORES_FILE = DATA_DIR / "scores.json"

# 預設股票池（動態過濾：股價 > 1000 或當日量 < 1 萬張自動排除）
DEFAULT_STOCKS: list[tuple[str, str]] = [
    # ── 半導體製造 / 晶圓代工 ──
    ("2303", "聯電"),     ("2344", "華邦電"),   ("2363", "矽統"),
    ("2329", "華泰"),     ("2408", "南亞科"),   ("3014", "聯陽"),
    ("3105", "穩懋"),     ("3265", "台星科"),   ("5269", "祥碩"),
    ("5347", "世界"),     ("6147", "頎邦"),     ("6531", "愛普"),
    ("6770", "力積電"),   ("8016", "矽創"),     ("8081", "致新"),
    # ── IC 設計 ──
    ("3034", "聯詠"),     ("3035", "智原"),     ("3041", "揚智"),
    ("3094", "聯傑"),     ("4961", "天鈺"),     ("5314", "世紀"),
    ("5471", "松翰"),     ("6189", "豐藝"),     ("6202", "盛群"),
    ("6231", "系微"),     ("6286", "立錡"),     ("6435", "大將"),
    ("6451", "訊芯-KY"), ("6510", "精測"),     ("6533", "晶心科"),
    ("6643", "M31"),      ("8054", "安國"),     ("8083", "瑞穎"),
    ("2436", "偉詮電"),
    # ── 封測 / 探針 / 測試 ──
    ("2441", "超豐"),     ("3266", "昇陽半導體"), ("3402", "漢科"),
    ("3711", "日月光投控"), ("5285", "界霖"),   ("6263", "普萊德"),
    ("6271", "同欣電"),   ("6515", "穎崴"),     ("8131", "福懋科"),
    # ── AI 伺服器 / 代工 / ODM ──
    ("2308", "台達電"),   ("2317", "鴻海"),     ("2353", "宏碁"),
    ("2356", "英業達"),   ("2357", "華碩"),     ("2376", "技嘉"),
    ("2382", "廣達"),     ("3037", "欣興"),     ("3231", "緯創"),
    ("3704", "合勤控"),   ("4938", "和碩"),     ("8210", "勤誠"),
    # ── 散熱 / 機殼 / 風扇 ──
    ("3017", "奇鋐"),     ("3653", "健策"),     ("5371", "中光電"),
    ("5512", "力廣"),     ("6803", "崧城"),     ("8358", "金居"),
    # ── ABF 載板 / PCB / 銅箔基板 ──
    ("1605", "華新"),     ("1815", "富喬"),     ("2316", "楠梓電"),
    ("2368", "金像電"),   ("2371", "大同"),     ("3043", "科風"),
    ("3550", "聯穎"),     ("5469", "瀚宇博"),   ("6213", "聯茂"),
    ("6274", "台燿"),     ("6411", "晶焱"),     ("6679", "鈺太"),
    ("8021", "尖點"),     ("8046", "南電"),
    # ── 記憶體 / 儲存 ──
    ("3530", "晶相光"),   ("4967", "十銓"),     ("8086", "宏捷科"),
    # ── 矽晶圓 / 材料 ──
    ("3258", "環旭電"),   ("4904", "遠傳"),     ("4977", "眾達-KY"),
    ("5483", "中美晶"),   ("6126", "信音"),     ("6552", "易華電"),
    # ── 半導體設備 / 廠務 ──
    ("3163", "波若威"),   ("3437", "榮創"),     ("3563", "牧德"),
    ("6188", "廣明"),     ("6196", "帆宣"),     ("6261", "久元"),
    ("6266", "泰詠"),
    # ── 光通訊 / 高速傳輸 ──
    ("2459", "敦吉"),     ("3450", "聯鈞"),     ("3491", "昇達科"),
    ("4979", "華星光"),   ("6125", "廣運"),     ("8064", "東捷"),
    # ── 連接器 / 電源 / 被動元件 ──
    ("1582", "信錦"),     ("2059", "川湖"),     ("2393", "億光"),
    ("2474", "可成"),     ("3526", "凡甲"),     ("6121", "新普"),
    # ── 機器人 / 自動化 / 工具機 ──
    ("1590", "亞德客-KY"), ("1597", "直得"),   ("2049", "上銀"),
    ("4523", "永彰"),     ("4609", "唐鋒"),
    # ── 車用電子 / 電動車 ──
    ("2207", "和泰車"),   ("2241", "艾姆勒"),   ("3211", "順達"),
    # ── 面板 / 顯示 / 電子紙 ──
    ("2409", "友達"),     ("3481", "群創"),     ("8069", "元太"),
    # ── AI 概念 / 邊緣運算 / 其他高波動 ──
    ("6526", "達發"),     ("6671", "三聯科技"), ("6680", "玖鼎電力"),
]

# 揭露時間選項（盤中時間）
REVEAL_TIMES = [time(10, 0)]

# 分數規則
TRADE_CAPITAL = 1_000_000   # 每題模擬資金（新台幣）

# ════════════════════════════════════════════════════════════════════
#  分數記錄 I/O
# ════════════════════════════════════════════════════════════════════

DEFAULT_SCORES = {
    "total": 0,
    "correct": 0,
    "wrong": 0,
    "total_pnl": 0,     # 累積損益（新台幣，可為負）
    "history": [],      # 最近 50 筆交易記錄
}


def load_scores() -> dict:
    if not SCORES_FILE.exists():
        return dict(DEFAULT_SCORES)
    try:
        data = json.loads(SCORES_FILE.read_text(encoding="utf-8"))
        # 補齊缺欄
        for k, v in DEFAULT_SCORES.items():
            data.setdefault(k, v)
        return data
    except Exception:
        return dict(DEFAULT_SCORES)


def save_scores(data: dict) -> None:
    SCORES_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ════════════════════════════════════════════════════════════════════
#  Pivot Points（古典派）— 用前一交易日 H/L/C 算當日 Pivot
# ════════════════════════════════════════════════════════════════════

def compute_pivot(prev_high: float, prev_low: float, prev_close: float) -> dict:
    H, L, C = prev_high, prev_low, prev_close
    P  = (H + L + C) / 3
    return {
        "R3": round(H + 2 * (P - L), 2),
        "R2": round(P + (H - L), 2),
        "R1": round(2 * P - L, 2),
        "P":  round(P, 2),
        "S1": round(2 * P - H, 2),
        "S2": round(P - (H - L), 2),
        "S3": round(L - 2 * (H - P), 2),
    }


# ════════════════════════════════════════════════════════════════════
#  題目生成（隨機抽：股票 + 日期 + 揭露時間）
# ════════════════════════════════════════════════════════════════════

@st.cache_data(show_spinner=False, ttl=3600)
def fetch_intraday_5m(symbol: str) -> pd.DataFrame:
    """抓近 60 天 5 分 K（cached 1 小時）"""
    df = yf.download(symbol, period="60d", interval="5m",
                     progress=False, auto_adjust=False)
    if df.empty:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    # 轉成台北時區
    if df.index.tz is not None:
        df = df.tz_convert("Asia/Taipei").tz_localize(None)
    return df


@st.cache_data(show_spinner=False, ttl=3600)
def fetch_daily(symbol: str) -> pd.DataFrame:
    """抓近 3 個月日 K（cached 1 小時）"""
    df = yf.download(symbol, period="3mo", interval="1d",
                     progress=False, auto_adjust=False)
    if df.empty:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df


def generate_question(stocks: list, max_attempts: int = 80) -> dict | None:
    """
    隨機產生一道題。失敗會重試（最多 max_attempts 次）。
    回傳 None 表示沒抽到（資料源異常或多次失敗）。
    """
    for attempt in range(max_attempts):
        code, name = random.choice(stocks)
        symbol = f"{code}.TW"

        # 抓 5m 與日 K（cached）
        try:
            df_5m = fetch_intraday_5m(symbol)
            df_daily = fetch_daily(symbol)
        except Exception:
            continue

        if df_5m.empty or df_daily.empty:
            # 試上櫃
            symbol = f"{code}.TWO"
            try:
                df_5m = fetch_intraday_5m(symbol)
                df_daily = fetch_daily(symbol)
            except Exception:
                continue
            if df_5m.empty or df_daily.empty:
                continue

        # 排除股價 > 1000（一張超過 10 萬，不適合刷題練習）
        try:
            close_vals = df_daily["Close"].dropna()
            if not close_vals.empty and float(close_vals.iloc[-1]) > 1000:
                continue
        except Exception:
            pass

        # 5m 資料中所有有資料的交易日
        unique_dates = sorted(set(df_5m.index.date))
        if len(unique_dates) < 3:
            continue
        # 排除最近 1 天（避免抽到今天還在開盤中）
        candidate_dates = unique_dates[:-1]
        target_date = random.choice(candidate_dates)

        # 該日 K 線
        df_day = df_5m[df_5m.index.date == target_date].copy()
        # 篩出 9:00-13:30 之間
        df_day = df_day[(df_day.index.time >= time(9, 0)) &
                        (df_day.index.time <= time(13, 30))]
        if len(df_day) < 30:  # 至少要 30 根 5m
            continue
        if df_day["Close"].isna().sum() > len(df_day) * 0.2:  # Close 缺值 > 20% 跳過
            continue

        # 找前一個交易日（從日 K）
        prev_days = df_daily[df_daily.index.date < target_date]
        if prev_days.empty:
            continue
        prev_day = prev_days.iloc[-1]
        try:
            pH = float(prev_day["High"])
            pL = float(prev_day["Low"])
            pC = float(prev_day["Close"])
            pV = float(prev_day["Volume"])
        except Exception:
            continue
        if pH <= 0 or pL <= 0 or pC <= 0:
            continue

        pivot = compute_pivot(pH, pL, pC)

        # ── 5 日 / 20 日均價（用前 N 個交易日的「日 K 收盤」平均）─
        # 不含當日，純粹是過去的平均，當作「歷史參考價位」
        df_daily_before = df_daily[df_daily.index.date < target_date]
        try:
            ma5_daily  = round(float(df_daily_before["Close"].tail(5).mean()),  2) \
                         if len(df_daily_before) >= 5  else None
            ma20_daily = round(float(df_daily_before["Close"].tail(20).mean()), 2) \
                         if len(df_daily_before) >= 20 else None
        except Exception:
            ma5_daily = ma20_daily = None

        # 隨機揭露時間
        reveal_t = random.choice(REVEAL_TIMES)
        # 找揭露時間的索引
        idx_reveal = None
        for i, ts in enumerate(df_day.index):
            if ts.time() >= reveal_t:
                idx_reveal = i
                break
        if idx_reveal is None or idx_reveal < 6 or idx_reveal >= len(df_day) - 5:
            continue

        reveal_price = float(df_day["Close"].iloc[idx_reveal - 1])  # 揭露時間前一根的收盤
        close_price  = float(df_day["Close"].iloc[-1])               # 13:30 收盤

        # 判定用價格：12:00 附近的收盤（避免尾盤當沖回補雜訊）
        idx_judgment = None
        for i, ts in enumerate(df_day.index):
            if ts.time() >= time(12, 30):
                idx_judgment = i
                break
        if idx_judgment is None:
            idx_judgment = len(df_day) - 1
        judgment_price = float(df_day["Close"].iloc[idx_judgment])
        judgment_time  = df_day.index[idx_judgment].time()

        # ── 過濾條件 1：日內振幅太小（整天平盤死水）──────────────
        day_high  = float(df_day["High"].max())
        day_low   = float(df_day["Low"].min())
        day_range_pct = (day_high - day_low) / pC * 100 if pC > 0 else 0
        if day_range_pct < 3.0:        # 日內振幅 < 3% → 太平，過濾
            continue

        # ── 過濾條件 2：揭露後到收盤的振幅太小（揭露後死水）──────
        df_after_reveal = df_day.iloc[idx_reveal:]
        if not df_after_reveal.empty:
            after_high = float(df_after_reveal["High"].max())
            after_low  = float(df_after_reveal["Low"].min())
            after_range_pct = (after_high - after_low) / reveal_price * 100 if reveal_price > 0 else 0
            if after_range_pct < 1.5:  # 揭露後振幅 < 1.5% → 沒戲，過濾
                continue

        # ── 過濾條件 3：總成交金額（過濾低量股票）─────────────
        try:
            total_turnover = float((df_day["Close"] * df_day["Volume"]).sum())
            if total_turnover < 1e8:    # 當日總成交金額 < 1 億，過濾
                continue
        except Exception:
            continue

        # ── 過濾條件 4：總成交張數（過濾冷門/低流動性日）───────
        try:
            total_volume_lots = float(df_day["Volume"].sum()) / 1000  # 股 → 張
            if total_volume_lots < 10000:  # 當日成交 < 1 萬張，過濾
                continue
        except Exception:
            continue

        # 正確答案（以 12:30 判定，排除尾盤當沖雜訊）
        chg = judgment_price - reveal_price
        if abs(chg) / reveal_price < 0.005:   # 揭露到 12:30 變動 < 0.5%（平盤過濾）
            continue
        answer = "up" if chg > 0 else "down"

        # ── 台股漲跌停（±10%）+ 平盤價 ────────────────────────────
        limit_up   = round(pC * 1.10, 2)
        limit_down = round(pC * 0.90, 2)
        par_price  = round(pC, 2)
        # 揭露至當下的當日高低
        df_disclosed = df_day.iloc[:idx_reveal]
        try:
            today_high_so_far = round(float(df_disclosed["High"].max()), 2)
            today_low_so_far  = round(float(df_disclosed["Low"].min()), 2)
            open_price        = round(float(df_disclosed["Open"].iloc[0]), 2)
        except Exception:
            today_high_so_far = today_low_so_far = open_price = 0.0
        chg_vs_par = (reveal_price - par_price) / par_price * 100 if par_price > 0 else 0

        return {
            "code": code, "name": name, "symbol": symbol,
            "target_date": target_date,
            "prev_high": pH, "prev_low": pL, "prev_close": pC,
            "pivot": pivot,
            "df_day": df_day,
            "reveal_time": reveal_t,
            "reveal_idx": idx_reveal,
            "reveal_price":    round(reveal_price, 2),
            "close_price":     round(close_price, 2),
            "judgment_price":  round(judgment_price, 2),
            "judgment_time":   judgment_time,
            "change_pct":      round(chg / reveal_price * 100, 2),
            "answer":          answer,
            # ── 新增欄位（看盤軟體常見資訊）──
            "limit_up":         limit_up,
            "limit_down":       limit_down,
            "par_price":        par_price,
            "open_price":       open_price,
            "today_high":       today_high_so_far,
            "today_low":        today_low_so_far,
            "chg_vs_par":       round(chg_vs_par, 2),
            "chg_vs_par_abs":   round(reveal_price - par_price, 2),
            "ma5_daily":        ma5_daily,
            "ma20_daily":       ma20_daily,
            "prev_volume":      pV,
        }
    return None


# ════════════════════════════════════════════════════════════════════
#  K 線圖繪製
# ════════════════════════════════════════════════════════════════════

def build_chart(q: dict, revealed: bool = False) -> go.Figure:
    """
    繪製專業看盤介面：
      Row 1 主圖：價格折線 + VWAP + 漲跌停/平盤/Pivot 七條/現價色塊
      Row 2 量副圖：紅綠分色成交量條（紅=收高於開、綠=收低於開）
      Row 3 估算盤差：累積買賣壓力差（用「收盤位置 × 成交量」估算）
    """
    df_full   = q["df_day"]
    reveal_idx = q["reveal_idx"]
    # 揭曉前只露揭露時間前的資料；揭曉後全部露出
    df_calc = df_full if revealed else df_full.iloc[:reveal_idx]

    limit_up   = q["limit_up"]
    limit_down = q["limit_down"]
    par_price  = q["par_price"]

    # ── 建立 3 列子圖（主圖佔比加大，視覺更舒服）─────────────
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.035,
        row_heights=[0.66, 0.14, 0.20],
        subplot_titles=(
            None,
            "<span style='color:#94a3b8;font-size:11px'>成交量（紅=收高於開／綠=收低於開）</span>",
            "<span style='color:#94a3b8;font-size:11px'>估算累積買賣壓力 [盤差近似值]</span>",
        ),
    )

    # ═══════════════════════════════════════════════════
    # Row 1：主圖（價格折線 + VWAP）
    # ═══════════════════════════════════════════════════
    if revealed:
        df_before = df_full.iloc[:reveal_idx].dropna(subset=["Close"])
        df_after  = df_full.iloc[reveal_idx - 1:].dropna(subset=["Close"])
        after_color = "#22c55e" if q["answer"] == "up" else "#ef4444"

        fig.add_trace(go.Scatter(
            x=df_before.index, y=df_before["Close"],
            mode="lines",
            line=dict(color="#60a5fa", width=2.5),
            hovertemplate="%{x|%H:%M}<br>價 %{y:.2f}<extra></extra>",
            showlegend=False,
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=df_after.index, y=df_after["Close"],
            mode="lines",
            line=dict(color=after_color, width=2.5),
            hovertemplate="%{x|%H:%M}<br>價 %{y:.2f}<extra></extra>",
            showlegend=False,
        ), row=1, col=1)
    else:
        df_show = df_full.iloc[:reveal_idx].dropna(subset=["Close"])
        fig.add_trace(go.Scatter(
            x=df_show.index, y=df_show["Close"],
            mode="lines",
            line=dict(color="#60a5fa", width=2.5),
            hovertemplate="%{x|%H:%M}<br>價 %{y:.2f}<extra></extra>",
            showlegend=False,
        ), row=1, col=1)

    # 揭露點圓圈
    last_show_idx = reveal_idx - 1
    last_ts    = df_full.index[last_show_idx]
    last_price = float(df_full["Close"].iloc[last_show_idx])
    fig.add_trace(go.Scatter(
        x=[last_ts], y=[last_price],
        mode="markers",
        marker=dict(color="#fbbf24", size=11, line=dict(color="#fff", width=2)),
        hovertemplate="揭露點<br>%{x|%H:%M}<br>%{y:.2f}<extra></extra>",
        showlegend=False,
    ), row=1, col=1)

    # ── VWAP（量價加權平均，看「大戶公允價」）──
    try:
        typ = (df_calc["High"] + df_calc["Low"] + df_calc["Close"]) / 3
        vwap = (typ * df_calc["Volume"]).cumsum() / df_calc["Volume"].cumsum()
        fig.add_trace(go.Scatter(
            x=vwap.index, y=vwap,
            mode="lines",
            line=dict(color="#a855f7", width=1.5, dash="dot"),
            hovertemplate="VWAP %{y:.2f}<extra></extra>",
            name="VWAP", showlegend=False,
        ), row=1, col=1)
    except Exception:
        pass

    # ── 共用：圖表左右兩端 x 座標（給所有水平線用）──
    x_left  = df_full.index[0]
    x_right = df_full.index[-1]

    # ── 5 日 / 20 日均價（橫向虛線，跟 Pivot 同風格）──
    # 5日均價 = 過去 5 個交易日的「日 K 收盤」平均；當作中期參考價位
    ma5_d  = q.get("ma5_daily")
    ma20_d = q.get("ma20_daily")
    if ma5_d:
        fig.add_shape(type="line", row=1, col=1,
                      x0=x_left, x1=x_right, y0=ma5_d, y1=ma5_d,
                      line=dict(color="#06b6d4", width=1.4, dash="dash"))
        fig.add_annotation(x=x_right, y=ma5_d,
                           text=f"5日均 {ma5_d:.2f}",
                           showarrow=False, xanchor="left",
                           font=dict(size=10, color="#06b6d4"),
                           bgcolor="rgba(15,23,42,0.65)", borderpad=2,
                           xref="x", yref="y")
    if ma20_d:
        fig.add_shape(type="line", row=1, col=1,
                      x0=x_left, x1=x_right, y0=ma20_d, y1=ma20_d,
                      line=dict(color="#d946ef", width=1.4, dash="dash"))
        fig.add_annotation(x=x_right, y=ma20_d,
                           text=f"20日均 {ma20_d:.2f}",
                           showarrow=False, xanchor="left",
                           font=dict(size=10, color="#d946ef"),
                           bgcolor="rgba(15,23,42,0.65)", borderpad=2,
                           xref="x", yref="y")

    # ── Pivot 七條（細虛線，右側標籤）──
    for lbl, val, color in [
        ("R3", q["pivot"]["R3"], "#dc2626"),
        ("R2", q["pivot"]["R2"], "#ef4444"),
        ("R1", q["pivot"]["R1"], "#f87171"),
        ("P",  q["pivot"]["P"],  "#fbbf24"),
        ("S1", q["pivot"]["S1"], "#86efac"),
        ("S2", q["pivot"]["S2"], "#4ade80"),
        ("S3", q["pivot"]["S3"], "#22c55e"),
    ]:
        fig.add_shape(type="line", row=1, col=1,
                      x0=x_left, x1=x_right, y0=val, y1=val,
                      line=dict(color=color, width=1.0, dash="dash"))
        fig.add_annotation(x=x_right, y=val, text=f"{lbl} {val:.2f}",
                           showarrow=False, xanchor="left",
                           font=dict(size=10, color=color),
                           bgcolor="rgba(15,23,42,0.6)", borderpad=2,
                           xref="x", yref="y")

    # ── 漲停 / 平盤 / 跌停 粗實線 ──
    fig.add_shape(type="line", row=1, col=1,
                  x0=x_left, x1=x_right, y0=limit_up, y1=limit_up,
                  line=dict(color="#ef4444", width=2.5))
    fig.add_shape(type="line", row=1, col=1,
                  x0=x_left, x1=x_right, y0=par_price, y1=par_price,
                  line=dict(color="#f59e0b", width=1.8))
    fig.add_shape(type="line", row=1, col=1,
                  x0=x_left, x1=x_right, y0=limit_down, y1=limit_down,
                  line=dict(color="#22c55e", width=2.5))

    # ── 左側色塊標籤（漲停/平盤/跌停/現價）──
    fig.add_annotation(xref="paper", yref="y", x=0, y=limit_up,
                       text=f"<b>漲停 {limit_up:.2f}</b>", showarrow=False,
                       xanchor="right", font=dict(size=10, color="#fff"),
                       bgcolor="#dc2626", bordercolor="#fca5a5",
                       borderwidth=1, borderpad=2, xshift=-2)
    fig.add_annotation(xref="paper", yref="y", x=0, y=par_price,
                       text=f"<b>平盤 {par_price:.2f}</b>", showarrow=False,
                       xanchor="right", font=dict(size=10, color="#0b1220"),
                       bgcolor="#fbbf24", bordercolor="#fde047",
                       borderwidth=1, borderpad=2, xshift=-2)
    fig.add_annotation(xref="paper", yref="y", x=0, y=limit_down,
                       text=f"<b>跌停 {limit_down:.2f}</b>", showarrow=False,
                       xanchor="right", font=dict(size=10, color="#fff"),
                       bgcolor="#16a34a", bordercolor="#86efac",
                       borderwidth=1, borderpad=2, xshift=-2)

    reveal_price = q["reveal_price"]
    _chg_par = q.get("chg_vs_par", 0)
    _r_color = "#22c55e" if reveal_price > par_price else (
        "#ef4444" if reveal_price < par_price else "#94a3b8")
    fig.add_annotation(xref="paper", yref="y", x=0, y=reveal_price,
                       text=f"<b>現價 {reveal_price:.2f}<br>{_chg_par:+.2f}%</b>",
                       showarrow=False, xanchor="right",
                       font=dict(size=10, color="#fff"),
                       bgcolor=_r_color, bordercolor="#fff",
                       borderwidth=1, borderpad=2, xshift=-2)

    # ── 揭露垂直線（揭曉後）──
    if revealed and reveal_idx < len(df_full):
        reveal_ts = df_full.index[reveal_idx]
        fig.add_shape(type="line", row=1, col=1,
                      x0=reveal_ts, x1=reveal_ts,
                      y0=limit_down, y1=limit_up,
                      line=dict(color="#fbbf24", width=2, dash="dot"))

    # ═══════════════════════════════════════════════════
    # Row 2：成交量副圖（紅綠分色）
    # ═══════════════════════════════════════════════════
    try:
        vol_lots = df_calc["Volume"] / 1000     # 轉為「張」
        vol_colors = ["#ef4444" if c >= o else "#22c55e"
                      for c, o in zip(df_calc["Close"], df_calc["Open"])]
        fig.add_trace(go.Bar(
            x=df_calc.index, y=vol_lots,
            marker=dict(color=vol_colors),
            hovertemplate="%{x|%H:%M}<br>量 %{y:.0f} 張<extra></extra>",
            showlegend=False,
        ), row=2, col=1)
    except Exception:
        pass

    # ═══════════════════════════════════════════════════
    # Row 3：估算累積買賣壓力（盤差近似）
    # 公式：每根 K 的「收盤位置」(0~1) → 對應 sign (-1~+1) → × 量
    #       累積後得到 cumulative signed volume，類似三竹「盤差」
    # ═══════════════════════════════════════════════════
    try:
        rng = (df_calc["High"] - df_calc["Low"]).replace(0, 1)
        position = (df_calc["Close"] - df_calc["Low"]) / rng       # 0~1
        signed = (2 * position - 1) * (df_calc["Volume"] / 1000)    # ±張
        cumulative = signed.cumsum()
        press_colors = ["#ef4444" if v >= 0 else "#22c55e" for v in cumulative]
        fig.add_trace(go.Bar(
            x=df_calc.index, y=cumulative,
            marker=dict(color=press_colors),
            hovertemplate="%{x|%H:%M}<br>盤差 %{y:+.0f} 張<extra></extra>",
            showlegend=False,
        ), row=3, col=1)
        # 0 線
        fig.add_shape(type="line", row=3, col=1,
                      x0=x_left, x1=x_right, y0=0, y1=0,
                      line=dict(color="rgba(255,255,255,0.35)", width=1))
        # 顯示最後一筆盤差（右側標籤）
        final_press = float(cumulative.iloc[-1])
        final_color = "#ef4444" if final_press >= 0 else "#22c55e"
        fig.add_annotation(
            x=x_right, y=final_press,
            text=f"<b>{final_press:+.0f}</b>", showarrow=False, xanchor="left",
            font=dict(size=12, color="#fff"),
            bgcolor=final_color, borderwidth=1, borderpad=3,
            xref="x3", yref="y3",
        )
    except Exception:
        pass

    # ═══════════════════════════════════════════════════
    # Layout
    # ═══════════════════════════════════════════════════
    _y_pad = (limit_up - limit_down) * 0.02
    fig.update_layout(
        template="plotly_dark",
        height=1100,
        showlegend=False,
        margin=dict(l=70, r=70, t=40, b=10),
        paper_bgcolor="#0b1220",
        plot_bgcolor="#0b1220",
        title=dict(
            text=f"{q['name']}（{q['code']}）｜{q['target_date']}",
            font=dict(size=16, color="#d8ecff"), x=0,
        ),
        hovermode="x unified",
        bargap=0.1,
    )
    fig.update_xaxes(gridcolor="rgba(100,140,220,0.10)", showspikes=False, fixedrange=True)
    fig.update_yaxes(gridcolor="rgba(100,140,220,0.10)", showspikes=False, fixedrange=True)
    fig.update_yaxes(range=[limit_down - _y_pad, limit_up + _y_pad], row=1, col=1)
    fig.update_xaxes(rangeslider_visible=False)
    return fig


# ════════════════════════════════════════════════════════════════════
#  Streamlit 介面
# ════════════════════════════════════════════════════════════════════

st.set_page_config(page_title="台股刷題練習", page_icon="🎯", layout="wide")

# ── 自訂 CSS：壓低 padding、metric 卡片美化、按鈕放大 ──
st.markdown("""
<style>
/* 縮小頁面外圍 padding，讓圖表盡量寬 */
.block-container { padding-top: 1.2rem; padding-bottom: 2rem;
                   padding-left: 2rem !important; padding-right: 2rem !important; }
/* metric 卡片 */
div[data-testid="stMetric"] {
    background: #0f1729; padding: 10px 14px;
    border-radius: 10px; border: 1px solid #1e293b;
    min-height: 92px;
}
div[data-testid="stMetric"] label {
    color: #94a3b8 !important; font-size: 0.78rem !important;
    white-space: nowrap !important;
}
/* metric 數值不要被截斷 */
div[data-testid="stMetricValue"] {
    font-size: 1.45rem !important; font-weight: 700 !important;
    overflow: visible !important; white-space: nowrap !important;
}
div[data-testid="stMetricDelta"] {
    font-size: 0.72rem !important; white-space: nowrap !important;
}
/* 答題按鈕放大 */
.stButton > button { font-size: 1.2rem !important; padding: 0.8rem !important; }
.big-btn-up    > button { background: #16a34a !important; color: white !important; border: none !important; }
.big-btn-down  > button { background: #dc2626 !important; color: white !important; border: none !important; }
.big-btn-wait  > button { background: #f59e0b !important; color: #1a1a1a !important; border: none !important; font-weight: 700 !important; }
.big-btn-next  > button { background: #3b82f6 !important; color: white !important; border: none !important; }
</style>
""", unsafe_allow_html=True)

st.markdown("## 🎯 台股盤中刷題練習")
st.caption("看歷史 K 線 + Pivot 七條線，預測收盤走勢。每題隨機抽：股票（30 檔大型股）／日期（近 60 天）／揭露時間（10:00、11:00、12:00）。")

# ── 載入分數 ──
if "scores" not in st.session_state:
    st.session_state.scores = load_scores()
scores = st.session_state.scores

# ── 載入題目（初次進入或點下一題時生成）──
if "current_q" not in st.session_state:
    st.session_state.current_q = None
if "answered" not in st.session_state:
    st.session_state.answered = False
if "last_result" not in st.session_state:
    st.session_state.last_result = None
if "quiz_mode" not in st.session_state:
    st.session_state.quiz_mode = "normal"   # "normal" | "pick"
if "picked_stock" not in st.session_state:
    st.session_state.picked_stock = DEFAULT_STOCKS[0]


def new_question():
    if st.session_state.quiz_mode == "pick":
        stock_list = [st.session_state.picked_stock]
    else:
        stock_list = DEFAULT_STOCKS
    with st.spinner("正在抽題..."):
        q = generate_question(stock_list)
    st.session_state.current_q = q
    st.session_state.answered = False
    st.session_state.last_result = None
    st.session_state.extra_minutes = 0


def apply_extra_minutes(q: dict, extra_minutes: int) -> dict:
    """
    根據「再看 N 分鐘」延長後重新計算揭露點各欄位。
    - 揭露 idx 往後推 extra_minutes / 5 根
    - 重算 reveal_price、reveal_time、當日高低、答案、漲跌幅
    - 不可越過 13:00（至少留 30 分鐘給答案）
    回傳：新的 q dict（不修改原物件）
    """
    if extra_minutes <= 0:
        return q
    df = q["df_day"]
    extra_bars = extra_minutes // 5
    original_idx = q.get("_original_reveal_idx", q["reveal_idx"])
    max_idx = len(df) - 6                    # 留 30 分鐘給結算
    new_idx = min(original_idx + extra_bars, max_idx)

    if new_idx == original_idx:
        return q

    # 重算
    new_reveal_price = float(df["Close"].iloc[new_idx - 1])
    new_reveal_time  = df.index[new_idx].time() if new_idx < len(df) else df.index[-1].time()
    df_disclosed = df.iloc[:new_idx]
    new_today_high = float(df_disclosed["High"].max())
    new_today_low  = float(df_disclosed["Low"].min())
    judgment_price = q["judgment_price"]
    chg = judgment_price - new_reveal_price
    new_answer = "up" if chg > 0 else ("down" if chg < 0 else "up")
    new_chg_vs_par = ((new_reveal_price - q["par_price"]) / q["par_price"] * 100) if q["par_price"] else 0

    q2 = dict(q)
    q2["_original_reveal_idx"] = original_idx
    q2["reveal_idx"]   = new_idx
    q2["reveal_price"] = round(new_reveal_price, 2)
    q2["reveal_time"]  = new_reveal_time
    q2["today_high"]   = round(new_today_high, 2)
    q2["today_low"]    = round(new_today_low, 2)
    q2["answer"]       = new_answer
    q2["change_pct"]   = round(chg / new_reveal_price * 100, 2) if new_reveal_price > 0 else 0
    q2["chg_vs_par"]   = round(new_chg_vs_par, 2)
    q2["chg_vs_par_abs"] = round(new_reveal_price - q["par_price"], 2)
    return q2


if st.session_state.current_q is None:
    new_question()
if "extra_minutes" not in st.session_state:
    st.session_state.extra_minutes = 0

# 把「目前是否延長過」套用到題目（不會修改原 q）
q = apply_extra_minutes(st.session_state.current_q, st.session_state.extra_minutes)

# ── 上方：損益面板 ──
total = scores["total"]
win_rate = (scores["correct"] / total * 100) if total > 0 else 0.0
total_pnl = scores.get("total_pnl", 0)
pnl_color = "normal" if total_pnl == 0 else ("inverse" if total_pnl < 0 else "normal")
m1, m2, m3 = st.columns(3)
pnl_str = f"+NT${total_pnl:,.0f}" if total_pnl >= 0 else f"-NT${abs(total_pnl):,.0f}"
m1.metric("累積損益", pnl_str)
m2.metric("勝率", f"{win_rate:.1f}%", f"{scores['correct']}勝 {scores['wrong']}負")
m3.metric("已交易次數", total)

st.markdown("---")

# ── 中間：題目區 ──
if q is None:
    st.error("抽題失敗，可能是 yfinance 暫時無法連線。請按下方「重新抽題」。")
    if st.button("🔄 重新抽題"):
        new_question()
        st.rerun()
else:
    # 題目資訊：股名 + 日期 + 揭露時間
    st.markdown(f"### {q['name']}（{q['code']}）")
    st.caption(
        f"📅 日期：**{q['target_date']}**　｜　"
        f"⏰ 揭露至：**{q['reveal_time'].strftime('%H:%M')}**　｜　"
        f"共顯示 {q['reveal_idx']} 根 5 分 K"
    )

    # ── 看盤資訊列 ──────────────────────────────────────────────────

    def _vol_status(df_day, reveal_idx, reveal_t, prev_volume):
        """計算量增/量縮：把揭露前累積量換算成全日基準比較。"""
        try:
            vol_so_far = float(df_day.iloc[:reveal_idx]["Volume"].sum())
            elapsed_min = (reveal_t.hour - 9) * 60 + reveal_t.minute
            if elapsed_min <= 0 or prev_volume <= 0:
                return None, None
            expected = prev_volume * (elapsed_min / 270)
            ratio = vol_so_far / expected
            pct = (ratio - 1) * 100
            pct = max(min(pct, 999), -99)
            label = f"量增 +{pct:.0f}%" if pct >= 0 else f"量縮 {pct:.0f}%"
            color = "normal" if pct >= 0 else "inverse"
            return label, color
        except Exception:
            return None, None

    _info_color = ("normal" if q["chg_vs_par"] > 0 else
                   "inverse" if q["chg_vs_par"] < 0 else "off")
    _reveal_label = f"💰 {q['reveal_time'].strftime('%H:%M')} 價"

    # 關鍵價位列：10:00 價 / 開盤 / Pivot P
    mc1, mc2, mc3 = st.columns(3)
    mc1.metric(_reveal_label, f"{q['reveal_price']:.2f}",
               delta=f"{q['chg_vs_par']:+.2f}% vs 平盤",
               delta_color=_info_color)
    mc2.metric("⏰ 開盤", f"{q['open_price']:.2f}")
    mc3.metric("📐 Pivot P", f"{q['pivot']['P']:.2f}",
               delta="多空分水嶺", delta_color="off")

    # 第 3 列：量增/量縮 ＋ 延長價格 ＋（答題後）判定價/收盤
    _vol_lbl, _vol_color = _vol_status(
        q["df_day"], q["reveal_idx"], q["reveal_time"], q.get("prev_volume", 0)
    )
    _extra = st.session_state.extra_minutes
    _answered = st.session_state.answered

    if _answered:
        # 揭曉後：量增縮 | 12:00 判定價 | 13:30 收盤
        _cols = st.columns(3)
        if _vol_lbl:
            _cols[0].metric("📊 成交量", _vol_lbl, delta_color=_vol_color)
        _cols[1].metric("🎯 12:30 判定價", f"{q['judgment_price']:.2f}",
                        delta=f"{q['change_pct']:+.2f}%",
                        delta_color="normal" if q["change_pct"] >= 0 else "inverse")
        _cols[2].metric("🔔 13:30 收盤", f"{q['close_price']:.2f}",
                        delta="僅參考", delta_color="off")
    elif _extra > 0:
        # 已延長：量增縮 | 10:30 價格
        _cols = st.columns(2)
        if _vol_lbl:
            _cols[0].metric("📊 成交量", _vol_lbl, delta_color=_vol_color)
        _ext_color = ("normal" if q["chg_vs_par"] >= 0 else "inverse")
        _cols[1].metric(f"💰 {q['reveal_time'].strftime('%H:%M')} 價（延長）",
                        f"{q['reveal_price']:.2f}",
                        delta=f"{q['chg_vs_par']:+.2f}% vs 平盤",
                        delta_color=_ext_color)
    else:
        # 尚未延長：只顯示量增縮
        if _vol_lbl:
            _c1, _c2, _c3 = st.columns(3)
            _c1.metric("📊 成交量", _vol_lbl, delta_color=_vol_color)

    # K 線圖
    fig = build_chart(q, revealed=st.session_state.answered)
    st.plotly_chart(fig, use_container_width=True, config={
        "displayModeBar": False,
        "scrollZoom": False,
        "doubleClick": False,
    })

    # 線條顏色說明
    st.caption(
        "**🎨 線條說明**　"
        "<span style='color:#60a5fa'>▬ 價格</span>　"
        "<span style='color:#a855f7'>┄ VWAP（量加權均價・大戶公允價）</span>　"
        "<span style='color:#06b6d4'>┄ 5日均（5 個交易日收盤平均）</span>　"
        "<span style='color:#d946ef'>┄ 20日均（20 個交易日收盤平均）</span>　"
        "<span style='color:#fbbf24'>┄ Pivot 七條</span>　"
        "<span style='color:#ef4444'>▬ 漲停</span>　"
        "<span style='color:#22c55e'>▬ 跌停</span>",
        unsafe_allow_html=True,
    )

    if not st.session_state.answered:
        # ── 作答按鈕 + 延長揭露時間 ──
        st.markdown(
            f"#### ❓ 從 **{q['reveal_time'].strftime('%H:%M')}**"
            f"（價位 **{q['reveal_price']:.2f}**）到 **12:30**，會「漲」還是「跌」？"
        )

        # 計算是否還能再延長（限制：揭露時間不超過 10:30，只能延長一次）
        _df_q = q["df_day"]
        _current_extra = st.session_state.extra_minutes
        _can_extend = _current_extra < 30

        ans_l, ans_m, ans_r = st.columns([1, 1.3, 1])
        with ans_l:
            st.markdown('<div class="big-btn-up">', unsafe_allow_html=True)
            up_clicked = st.button("📈 看漲（收盤 > 揭露價）",
                                   use_container_width=True, key="ans_up")
            st.markdown('</div>', unsafe_allow_html=True)
        with ans_m:
            # 中間按鈕：看不清楚時可延長揭露時間
            if _can_extend:
                # 預覽延長後是什麼時間
                _next_idx = min(
                    q["reveal_idx"] + 6,
                    len(_df_q) - 6,
                )
                _next_time = (_df_q.index[_next_idx].time()
                              if _next_idx < len(_df_q) else _df_q.index[-1].time())
                st.markdown('<div class="big-btn-wait">', unsafe_allow_html=True)
                wait_clicked = st.button(
                    f"⏭️ 再看 30 分（→ {_next_time.strftime('%H:%M')}）",
                    use_container_width=True, key="ans_wait",
                    help="看不清楚可以多等 30 分鐘，最多看到 10:30。",
                )
                st.markdown('</div>', unsafe_allow_html=True)
                if wait_clicked:
                    st.session_state.extra_minutes = _current_extra + 30
                    st.rerun()
            else:
                st.button("⏰ 已達 10:30 上限，請作答",
                          use_container_width=True, disabled=True, key="ans_wait_disabled")
        with ans_r:
            st.markdown('<div class="big-btn-down">', unsafe_allow_html=True)
            down_clicked = st.button("📉 看跌（收盤 < 揭露價）",
                                     use_container_width=True, key="ans_down")
            st.markdown('</div>', unsafe_allow_html=True)

        # 提示已延長多少
        if _current_extra > 0:
            _orig_time = REVEAL_TIMES[0]  # 不重要，下面用原始 idx 換算
            _orig_idx = q.get("_original_reveal_idx", q["reveal_idx"])
            _orig_t = _df_q.index[_orig_idx].time() if _orig_idx < len(_df_q) else _df_q.index[-1].time()
            st.caption(
                f"⏳ 本題已延長 **{_current_extra} 分鐘**："
                f"原揭露 {_orig_t.strftime('%H:%M')} → 現揭露 **{q['reveal_time'].strftime('%H:%M')}**"
                f"（答案依新揭露點重新計算）"
            )

        user_answer = None
        if up_clicked:
            user_answer = "up"
        elif down_clicked:
            user_answer = "down"

        if user_answer:
            correct = (user_answer == q["answer"])

            # ── 模擬損益計算 ──────────────────────────────────────
            reveal_p   = q["reveal_price"]
            judgment_p = q["judgment_price"]
            lots = int(TRADE_CAPITAL // (reveal_p * 1000))   # 100萬能買幾張
            price_diff = judgment_p - reveal_p               # 漲為正、跌為負
            if user_answer == "up":
                trade_pnl = round(lots * 1000 * price_diff)
            else:  # down（放空）
                trade_pnl = round(lots * 1000 * (-price_diff))

            # 更新統計
            scores["total"] += 1
            scores["total_pnl"] = scores.get("total_pnl", 0) + trade_pnl
            if correct:
                scores["correct"] += 1
            else:
                scores["wrong"] += 1

            # 寫入歷史
            scores["history"].insert(0, {
                "at": datetime.now().isoformat(timespec="seconds"),
                "code": q["code"], "name": q["name"],
                "date": str(q["target_date"]),
                "user_answer": user_answer,
                "correct_answer": q["answer"],
                "correct": correct,
                "reveal_price": reveal_p,
                "judgment_price": judgment_p,
                "close_price": q["close_price"],
                "change_pct": q["change_pct"],
                "lots": lots,
                "trade_pnl": trade_pnl,
            })
            scores["history"] = scores["history"][:50]
            save_scores(scores)

            st.session_state.answered = True
            st.session_state.last_result = {
                "correct": correct,
                "user_answer": user_answer,
                "lots": lots,
                "trade_pnl": trade_pnl,
                "reveal_price": reveal_p,
                "judgment_price": judgment_p,
            }
            st.rerun()

    else:
        # ── 揭曉答案 ──
        result = st.session_state.last_result
        pnl = result["trade_pnl"]
        lots = result["lots"]
        pnl_sign = "+" if pnl >= 0 else ""
        if result["correct"]:
            st.success(f"✅ 方向正確！　本題損益：**{pnl_sign}NT${pnl:,}**　（{lots} 張）")
        else:
            correct_text = "看漲" if q["answer"] == "up" else "看跌"
            st.error(f"❌ 方向錯誤！　本題損益：**{pnl_sign}NT${pnl:,}**　（正確：**{correct_text}**）")

        # 結果明細
        st.markdown(f"""
        - **進場（{q['reveal_time'].strftime('%H:%M')}）**：{result['reveal_price']:.2f}　→　**出場（12:30）**：{result['judgment_price']:.2f}　|　**價差**：**{q['change_pct']:+.2f}%**
        - **模擬口數**：{lots} 張（100萬 ÷ {result['reveal_price']:.2f} × 1000）
        - **13:30 收盤**：{q['close_price']:.2f}　（僅參考）
        """)

        st.markdown("---")
        st.markdown('<div class="big-btn-next">', unsafe_allow_html=True)
        if st.button("➡️ 下一題", use_container_width=True, key="next_q"):
            new_question()
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# ── 側邊欄：模式選擇 + 歷史 + 設定 ──
with st.sidebar:
    st.markdown("### 🎮 出題模式")
    _mode = st.radio(
        "模式",
        options=["normal", "pick"],
        format_func=lambda x: "🎲 正常模式（隨機選股）" if x == "normal" else "🎯 挑選模式（指定股票）",
        index=0 if st.session_state.quiz_mode == "normal" else 1,
        label_visibility="collapsed",
    )
    if _mode != st.session_state.quiz_mode:
        st.session_state.quiz_mode = _mode
        st.session_state.current_q = None  # 切換模式重新抽題
        st.rerun()

    if st.session_state.quiz_mode == "pick":
        # ── 方式一：直接輸入代碼 ──
        _code_input = st.text_input(
            "輸入股票代碼",
            placeholder="例如：2382，按 Enter 確認",
            key="code_search",
        )
        if _code_input:
            _code_input = _code_input.strip()
            # 先從池子找
            _match = next(((c, n) for c, n in DEFAULT_STOCKS if c == _code_input), None)
            if _match:
                if _match != st.session_state.picked_stock:
                    st.session_state.picked_stock = _match
                    st.session_state.current_q = None
                    st.rerun()
                st.success(f"✅ {_match[0]} {_match[1]}")
            else:
                # 池子外的代碼，直接試
                _custom = (_code_input, _code_input)
                if _custom != st.session_state.picked_stock:
                    st.session_state.picked_stock = _custom
                    st.session_state.current_q = None
                    st.rerun()
                st.warning(f"⚠️ {_code_input} 不在預設池，直接嘗試抓取")

        # ── 方式二：下拉選單 ──
        _stock_labels = [f"{code} {name}" for code, name in DEFAULT_STOCKS]
        _cur_code = st.session_state.picked_stock[0]
        _cur_idx = next(
            (i for i, (c, _) in enumerate(DEFAULT_STOCKS) if c == _cur_code), 0
        )
        _selected_label = st.selectbox(
            "或從清單選擇",
            options=_stock_labels,
            index=_cur_idx,
        )
        _sel_idx = _stock_labels.index(_selected_label)
        _new_pick = DEFAULT_STOCKS[_sel_idx]
        if _new_pick != st.session_state.picked_stock:
            st.session_state.picked_stock = _new_pick
            st.session_state.current_q = None
            st.rerun()

        st.caption(f"目前鎖定：**{st.session_state.picked_stock[0]} {st.session_state.picked_stock[1]}**")

    st.markdown("---")
    st.markdown("### 📊 統計")
    _pnl = scores.get("total_pnl", 0)
    _pnl_sign = "+" if _pnl >= 0 else ""
    st.caption(f"累積損益：**{_pnl_sign}NT${_pnl:,}**")
    st.caption(f"勝率：**{win_rate:.1f}%**（{scores['correct']}勝 {scores['wrong']}負）")

    st.markdown("---")
    st.markdown("### 📋 最近 10 題")
    history = scores.get("history", [])[:10]
    if not history:
        st.caption("尚無紀錄")
    else:
        for h in history:
            mark = "✅" if h["correct"] else "❌"
            user_a = "📈" if h["user_answer"] == "up" else "📉"
            pnl_h = h.get("trade_pnl", 0)
            pnl_s = f"+{pnl_h:,}" if pnl_h >= 0 else f"{pnl_h:,}"
            st.caption(f"{mark} {h['code']} {h['name']}・{h['date']}　{user_a}　NT${pnl_s}")

    st.markdown("---")
    if st.button("🗑 清空所有紀錄", use_container_width=True):
        save_scores(dict(DEFAULT_SCORES))
        st.session_state.scores = load_scores()
        st.success("已清空，重新整理頁面")
        st.rerun()

    st.markdown("---")
    st.caption("資料來源：Yahoo Finance（近 60 天 5 分 K）")
    st.caption("Pivot 公式：古典派（用前日 H/L/C 計算）")
