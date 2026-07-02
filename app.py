from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st


APP_NAME = "蚂蚁经营助手"
BASE_DIR = Path(__file__).resolve().parent
HERO_IMAGES = [
    BASE_DIR / "assets" / "hero-business-data-clean.png",
    BASE_DIR / "assets" / "hero-business-data.png",
    BASE_DIR / "assets" / "图片1.png",
]

st.set_page_config(
    page_title=APP_NAME,
    page_icon="AI",
    layout="centered",
    initial_sidebar_state="collapsed",
)


REQUIRED_COLUMNS = [
    "date",
    "period",
    "orders",
    "revenue",
    "new_customers",
    "coupon_claims",
    "rating_reply_delay",
    "delivery_delay",
    "weather_heat",
    "competitor_index",
]

PERIOD_TIME = {
    "早餐": "07:00-10:00",
    "午市": "11:00-14:00",
    "晚市": "17:00-20:00",
    "夜宵": "20:00-23:00",
}

SCENARIOS = {
    "午市新客下滑": {
        "target_period": "午市",
        "shock": "new_customer_drop",
        "title": "午市新客下滑",
        "hint": "适合演示拉新券方案",
    },
    "晚市履约延迟": {
        "target_period": "晚市",
        "shock": "delivery_delay",
        "title": "晚市履约延迟",
        "hint": "适合演示履约补救方案",
    },
    "早餐券领取下降": {
        "target_period": "早餐",
        "shock": "coupon_drop",
        "title": "早餐券领取下降",
        "hint": "适合演示触达优化方案",
    },
}

AI_PROVIDERS = [
    "本地智能模拟",
    "蚂蚁百灵/通义千问 API",
    "Ollama 本地大模型",
    "OpenAI-compatible API",
]


@dataclass
class Diagnosis:
    period: str
    current_days: int
    baseline_days: int
    orders_now: int
    orders_base: int
    revenue_now: float
    revenue_base: float
    new_now: int
    new_base: int
    coupon_now: int
    coupon_base: int
    order_delta: float
    revenue_delta: float
    new_delta: float
    coupon_delta: float
    confidence: int
    reasons: list[dict]
    scenario_name: str


def init_state() -> None:
    defaults = {
        "step": "home",
        "df": None,
        "diagnosis": None,
        "scenario": None,
        "role": "商家主账号",
        "confirmed": False,
        "executed": False,
        "chat": [],
        "ai_provider": AI_PROVIDERS[0],
        "plan": {
            "goal": "拉新",
            "threshold": 35,
            "discount": 6,
            "budget": 1000,
            "audience": "近 30 天浏览未下单新客",
            "copy": "午市来小满餐饮，满 35 元减 6 元。今日 11:00-14:00 可用。",
        },
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def go(step: str) -> None:
    st.session_state.step = step
    st.rerun()


def css() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;600;700;800&display=swap');

        html, body, [class*="css"] {
          font-family: "PingFang SC", "Noto Sans SC", "Microsoft YaHei", sans-serif;
        }
        .stApp {
          background: linear-gradient(180deg, #eef6ff 0%, #f7fbff 44%, #ffffff 100%);
          color: #111827;
        }
        [data-testid="stHeader"], [data-testid="stToolbar"], #MainMenu, footer,
        [data-testid="collapsedControl"] {
          display: none;
        }
        .block-container {
          max-width: 430px;
          padding: 12px 14px 42px;
        }
        div[data-testid="stVerticalBlock"] { gap: .55rem; }
        .app-shell {
          width: min(100%, 390px);
          margin: 0 auto;
        }
        .topbar {
          display: flex;
          align-items: center;
          justify-content: center;
          height: 38px;
          color: #111827;
          font-weight: 800;
          font-size: 17px;
          letter-spacing: 0;
        }
        .hero-card {
          background: linear-gradient(180deg, #ffffff 0%, #fbfdff 100%);
          border: 1px solid #dbe6f3;
          border-radius: 12px;
          padding: 16px 18px 14px;
          margin: 8px 0 12px;
          box-shadow: 0 8px 20px rgba(22, 119, 255, .045);
          position: relative;
          overflow: hidden;
        }
        .hero-image-card {
          background: #fff;
          border: 1px solid #dbe6f3;
          border-radius: 12px;
          overflow: hidden;
          margin: 8px 0 10px;
          box-shadow: 0 8px 20px rgba(22, 119, 255, .045);
        }
        .hero-image-wrap img {
          display: block;
          width: 100%;
          height: auto;
        }
        .hero-image-footer {
          background: #f4f9ff;
          border-top: 1px solid #dbeaff;
          padding: 10px 14px 12px;
        }
        .hero-image-footer .hero-mini {
          margin-top: 0;
        }
        .hero-status {
          border: 1px solid #dbe6f3;
          background: rgba(255, 255, 255, .88);
          border-radius: 12px;
          padding: 12px 14px;
          margin: 0 0 10px;
          box-shadow: 0 6px 16px rgba(16, 24, 40, .026);
        }
        .hero-status-title {
          color: #111827;
          font-size: 16px;
          line-height: 1.35;
          font-weight: 800;
        }
        .hero-status-note {
          margin-top: 4px;
          color: #667085;
          font-size: 12px;
          line-height: 1.45;
        }
        .hero-card::before {
          content: "";
          position: absolute;
          left: 0;
          top: 16px;
          width: 4px;
          height: calc(100% - 32px);
          border-radius: 999px;
          background: #1677ff;
        }
        .hero-card h1 {
          margin: 7px 0 0;
          font-size: 21px;
          line-height: 1.32;
          letter-spacing: 0;
          color: #111827;
          font-weight: 800;
        }
        .hero-card .hero-note {
          margin-top: 7px;
          color: #667085;
          font-size: 13px;
          line-height: 1.45;
        }
        .eyebrow {
          color: #1677ff;
          font-size: 12px;
          line-height: 1.2;
          font-weight: 800;
        }
        .hero-mini {
          display: flex;
          gap: 8px;
          margin-top: 12px;
          flex-wrap: wrap;
        }
        .mini-pill {
          display: inline-flex;
          align-items: center;
          min-height: 24px;
          border-radius: 999px;
          padding: 0 12px;
          color: #1d6fe8;
          background: #e9f3ff;
          font-size: 12px;
          line-height: 1;
          font-weight: 650;
        }
        .step-row {
          display: flex;
          align-items: center;
          gap: 5px;
          margin: 2px 0 10px;
          padding: 6px 8px;
          border-radius: 999px;
          background: rgba(255, 255, 255, .72);
          border: 1px solid #edf3fa;
          overflow-x: auto;
          scrollbar-width: none;
        }
        .step-row::-webkit-scrollbar { display: none; }
        .step-dot {
          flex: 0 0 auto;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          height: 24px;
          min-width: 24px;
          border-radius: 999px;
          padding: 0 8px;
          background: #fff;
          border: 1px solid #dbe6f3;
          color: #667085;
          font-size: 12px;
          line-height: 1;
          font-weight: 800;
          white-space: nowrap;
        }
        .step-dot.active {
          background: #1677ff;
          border-color: #1677ff;
          color: #fff;
        }
        .section-title {
          margin: 4px 0 10px;
          font-size: 15px;
          line-height: 1.35;
          font-weight: 800;
          color: #111827;
        }
        .home-grid {
          display: grid;
          gap: 12px;
        }
        .card {
          background: #fff;
          border: 1px solid #dbe6f3;
          border-radius: 12px;
          padding: 16px;
          margin: 0 0 12px;
          box-shadow: 0 6px 16px rgba(16, 24, 40, .028);
        }
        .card-title {
          margin: 0 0 10px;
          font-size: 16px;
          line-height: 1.35;
          font-weight: 800;
          color: #111827;
        }
        .big-title {
          margin: 6px 0 12px;
          font-size: 22px;
          line-height: 1.28;
          font-weight: 800;
          color: #111827;
        }
        .subtle {
          color: #667085;
          font-size: 13px;
          line-height: 1.6;
        }
        .body {
          color: #111827;
          font-size: 14px;
          line-height: 1.56;
        }
        .tag {
          display: inline-flex;
          align-items: center;
          height: 28px;
          border-radius: 999px;
          padding: 0 10px;
          margin: 0 6px 6px 0;
          font-size: 12px;
          font-weight: 800;
          background: #ffe9ed;
          color: #ef3340;
        }
        .tag.green {
          background: #e9fbf1;
          color: #00875a;
        }
        .tag.blue {
          background: #e9f2ff;
          color: #1677ff;
        }
        .metric-grid {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 8px;
          margin: 10px 0 18px;
        }
        .metric {
          min-height: 94px;
          border: 1px solid #dbe6f3;
          background: #f8fbff;
          border-radius: 10px;
          padding: 10px 8px;
          overflow: hidden;
        }
        .metric.order { background: #fff8f9; border-color: #ffd9de; }
        .metric.revenue { background: #f5f9ff; border-color: #d9e8ff; }
        .metric.customer { background: #f4fbf7; border-color: #cfefd9; }
        .metric .label {
          color: #667085;
          font-size: 12px;
          white-space: nowrap;
        }
        .metric .value {
          margin-top: 6px;
          color: #111827;
          font-size: 17px;
          line-height: 1.2;
          font-weight: 800;
        }
        .metric .delta {
          margin-top: 6px;
          color: #ef3340;
          font-size: 12px;
          font-weight: 700;
          line-height: 1.2;
        }
        .reason-card {
          margin-top: 4px;
        }
        .reason-card .card-title {
          margin-bottom: 14px;
        }
        .reason {
          margin: 0 0 18px;
        }
        .reason:last-child { margin-bottom: 0; }
        .reason-top {
          display: flex;
          justify-content: space-between;
          gap: 12px;
          margin-bottom: 8px;
          color: #111827;
          font-size: 13px;
          font-weight: 800;
        }
        .bar-bg {
          height: 6px;
          border-radius: 999px;
          background: #e7eef7;
          overflow: hidden;
        }
        .bar {
          height: 6px;
          border-radius: 999px;
        }
        .notice {
          border: 1px solid #ffe3b8;
          background: #fffaf0;
          color: #7a4a05;
          border-radius: 10px;
          padding: 10px 12px;
          font-size: 12px;
          line-height: 1.45;
          margin: 10px 0;
        }
        .softbox {
          border: 1px solid #d9e8ff;
          background: #f5f9ff;
          border-radius: 10px;
          padding: 12px 12px 12px 14px;
          color: #344054;
          font-size: 13px;
          line-height: 1.55;
          margin: 10px 0;
          border-left: 4px solid #1677ff;
        }
        .softbox b {
          color: #111827;
          font-size: 15px;
        }
        .okbox {
          border: 1px solid #b7ebc6;
          background: #effaf3;
          color: #027a48;
          border-radius: 10px;
          padding: 12px 14px;
          font-size: 13px;
          line-height: 1.55;
          margin: 10px 0;
        }
        .kv {
          display: grid;
          grid-template-columns: 76px 1fr;
          gap: 12px;
          padding: 9px 0;
          border-bottom: 1px dashed #e4ebf3;
          font-size: 13px;
        }
        .kv:last-child { border-bottom: none; }
        .kv .k { color: #667085; }
        .kv .v { color: #111827; font-weight: 800; }
        .chat-user, .chat-ai {
          border-radius: 10px;
          padding: 10px 12px;
          margin: 8px 0;
          font-size: 13px;
          line-height: 1.5;
        }
        .chat-user {
          background: #e9f2ff;
          color: #155eef;
        }
        .chat-ai {
          background: #f6f8fb;
          color: #111827;
          border: 1px solid #e4ebf3;
        }
        .stButton > button {
          min-height: 44px;
          border-radius: 10px;
          border: none;
          background: #1677ff;
          color: #fff;
          font-weight: 800;
          font-size: 14px;
        }
        .stButton > button:hover {
          background: #155eef;
          border: none;
          color: #fff;
        }
        .stButton > button[kind="secondary"] {
          background: #fff;
          color: #111827;
          border: 1px solid #d0d5dd;
        }
        .stButton > button:disabled {
          background: #d0d5dd;
          color: #fff;
        }
        .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"], .stNumberInput input {
          border-radius: 10px !important;
          border-color: #dbe6f3 !important;
          background: #fff !important;
          font-size: 14px !important;
        }
        .stTabs [data-baseweb="tab-list"] {
          gap: 8px;
          background: #eef6ff;
          padding: 4px;
          border-radius: 999px;
        }
        .stTabs [data-baseweb="tab"] {
          flex: 1;
          justify-content: center;
          min-height: 36px;
          border-radius: 999px;
          color: #667085;
          font-weight: 800;
          font-size: 13px;
        }
        .stTabs [aria-selected="true"] {
          background: #fff;
          color: #1677ff;
          box-shadow: 0 4px 12px rgba(16, 24, 40, .06);
        }
        div[data-testid="stExpander"] {
          border: 1px solid #dbe6f3;
          border-radius: 10px;
          background: #fff;
        }
        @media (max-width: 420px) {
          .block-container { padding-left: 10px; padding-right: 10px; }
          .hero-card h1 { font-size: 23px; }
          .big-title { font-size: 24px; }
          .metric-grid { gap: 8px; }
          .metric .value { font-size: 16px; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def scenario_data(scenario_name: str) -> pd.DataFrame:
    spec = SCENARIOS[scenario_name]
    today = date.today()
    rows = []
    periods = [
        ("早餐", 118, 2860, 22, 38),
        ("午市", 168, 4890, 34, 55),
        ("晚市", 156, 5220, 28, 44),
    ]
    day_count = 10 if spec["shock"] == "low_confidence" else 18
    for offset in range(day_count - 1, -1, -1):
        day = today - timedelta(days=offset)
        for period, base_orders, base_revenue, base_new, base_coupon in periods:
            weekend = 1.06 if day.weekday() >= 5 else 1.0
            drift = 1 + ((offset % 5) - 2) * 0.012
            factor = weekend * drift
            new_factor = factor
            coupon_factor = factor
            reply_delay = 18 + (offset % 4) * 4
            delivery_delay = 8 + (offset % 5)
            heat = 64 + (offset % 5) * 3
            competitor = 52 + (offset % 6) * 2

            if period == spec["target_period"] and offset <= 3:
                if spec["shock"] == "new_customer_drop":
                    factor *= 0.74
                    new_factor = 0.66
                    coupon_factor = 0.72
                    heat = 87
                    competitor = 79
                    reply_delay = 43
                elif spec["shock"] == "delivery_delay":
                    factor *= 0.79
                    new_factor = 0.84
                    coupon_factor = 0.96
                    delivery_delay = 29
                    reply_delay = 36
                    competitor = 70
                elif spec["shock"] == "coupon_drop":
                    factor *= 0.82
                    new_factor = 0.88
                    coupon_factor = 0.48
                    competitor = 65
                elif spec["shock"] == "rating_delay":
                    factor *= 0.81
                    new_factor = 0.83
                    coupon_factor = 0.92
                    reply_delay = 58
                    delivery_delay = 18
                elif spec["shock"] == "low_confidence":
                    factor *= 0.94
                    new_factor = 0.92
                    coupon_factor = 0.96
                    heat = 69
                    competitor = 58

            rows.append(
                {
                    "date": day.isoformat(),
                    "period": period,
                    "orders": round(base_orders * factor),
                    "revenue": round(base_revenue * factor, 2),
                    "new_customers": round(base_new * new_factor),
                    "coupon_claims": round(base_coupon * coupon_factor),
                    "rating_reply_delay": reply_delay,
                    "delivery_delay": delivery_delay,
                    "weather_heat": heat,
                    "competitor_index": competitor,
                }
            )
    return pd.DataFrame(rows)


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8-sig")


def validate_data(df: pd.DataFrame) -> tuple[bool, str]:
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        return False, "缺少字段：" + "、".join(missing)
    try:
        pd.to_datetime(df["date"])
    except Exception:
        return False, "日期字段无法识别"
    for col in REQUIRED_COLUMNS[2:]:
        if pd.to_numeric(df[col], errors="coerce").isna().any():
            return False, f"{col} 需要全部为数字"
    if pd.to_datetime(df["date"]).nunique() < 10:
        return False, "建议至少提供 10 天数据"
    return True, "ok"


def prepare_data(df: pd.DataFrame) -> pd.DataFrame:
    data = df.copy()
    data["date"] = pd.to_datetime(data["date"])
    data["period"] = data["period"].astype(str)
    for col in REQUIRED_COLUMNS[2:]:
        data[col] = pd.to_numeric(data[col], errors="coerce").fillna(0)
    return data.sort_values(["date", "period"])


def pct(now: float, base: float) -> float:
    if base == 0:
        return 0.0
    return (now - base) / base


def fmt_pct(value: float) -> str:
    return f"{value * 100:+.1f}%"


def fmt_money(value: float) -> str:
    return f"¥{value:,.0f}"


def analyze(df: pd.DataFrame, scenario_name: str = "自定义数据") -> Diagnosis:
    data = prepare_data(df)
    last_day = data["date"].max()
    current_start = last_day - pd.Timedelta(days=2)
    base_start = current_start - pd.Timedelta(days=7)
    base_end = current_start - pd.Timedelta(days=1)
    current = data[data["date"] >= current_start]
    baseline = data[(data["date"] >= base_start) & (data["date"] <= base_end)]

    candidates = []
    for period in sorted(data["period"].unique()):
        c = current[current["period"] == period]
        b = baseline[baseline["period"] == period]
        if c.empty or b.empty:
            continue
        c_days = max(c["date"].nunique(), 1)
        b_days = max(b["date"].nunique(), 1)
        orders_now = c["orders"].sum() / c_days
        orders_base = b["orders"].sum() / b_days
        candidates.append((pct(orders_now, orders_base), period, c, b))
    if not candidates:
        raise ValueError("数据不足，无法形成同经营时段对比。")

    _, period, c, b = min(candidates, key=lambda item: item[0])
    current_days = max(c["date"].nunique(), 1)
    baseline_days = max(b["date"].nunique(), 1)

    def avg_sum(col: str, frame: pd.DataFrame, days: int) -> float:
        return float(frame[col].sum() / days)

    orders_now = avg_sum("orders", c, current_days)
    orders_base = avg_sum("orders", b, baseline_days)
    revenue_now = avg_sum("revenue", c, current_days)
    revenue_base = avg_sum("revenue", b, baseline_days)
    new_now = avg_sum("new_customers", c, current_days)
    new_base = avg_sum("new_customers", b, baseline_days)
    coupon_now = avg_sum("coupon_claims", c, current_days)
    coupon_base = avg_sum("coupon_claims", b, baseline_days)

    order_delta = pct(orders_now, orders_base)
    revenue_delta = pct(revenue_now, revenue_base)
    new_delta = pct(new_now, new_base)
    coupon_delta = pct(coupon_now, coupon_base)
    heat_gap = max(0.0, float(c["weather_heat"].mean() - b["weather_heat"].mean()))
    competitor_gap = max(0.0, float(c["competitor_index"].mean() - b["competitor_index"].mean()))
    reply_gap = max(0.0, float(c["rating_reply_delay"].mean() - b["rating_reply_delay"].mean()))
    delivery_gap = max(0.0, float(c["delivery_delay"].mean() - b["delivery_delay"].mean()))

    external_score = heat_gap * 0.55 + competitor_gap * 0.75
    new_score = abs(min(new_delta, 0)) * 105
    coupon_score = abs(min(coupon_delta, 0)) * 100
    service_score = reply_gap * 0.9 + delivery_gap * 1.65
    if delivery_gap > 10 or reply_gap > 24:
        service_score *= 1.35
    if coupon_delta < -0.25:
        coupon_score *= 1.25
    raw_reasons = [
        ("天气与周边竞争变化", external_score),
        ("新客兴趣与进店转化下降", new_score),
        ("优惠领取与触达不足", coupon_score),
        ("评价回复与履约延迟", service_score),
    ]
    total = sum(max(score, 0) for _, score in raw_reasons) or 1
    colors = ["#EF3340", "#1677ff", "#FA8C16", "#722ed1"]
    reasons = [
        {
            "name": name,
            "weight": max(8, round(max(score, 0) / total * 100)),
            "color": colors[index],
        }
        for index, (name, score) in enumerate(raw_reasons)
    ]
    overflow = sum(reason["weight"] for reason in reasons) - 100
    if overflow > 0:
        reasons[0]["weight"] = max(8, reasons[0]["weight"] - overflow)

    confidence = 58 + min(28, int(abs(order_delta) * 90)) + (8 if len(data) >= 30 else 0)
    if abs(order_delta) < 0.1 or scenario_name == "低置信度数据不足":
        confidence -= 25
    confidence = max(42, min(confidence, 92))

    return Diagnosis(
        period=period,
        current_days=current_days,
        baseline_days=baseline_days,
        orders_now=round(orders_now),
        orders_base=round(orders_base),
        revenue_now=revenue_now,
        revenue_base=revenue_base,
        new_now=round(new_now),
        new_base=round(new_base),
        coupon_now=round(coupon_now),
        coupon_base=round(coupon_base),
        order_delta=order_delta,
        revenue_delta=revenue_delta,
        new_delta=new_delta,
        coupon_delta=coupon_delta,
        confidence=confidence,
        reasons=reasons,
        scenario_name=scenario_name,
    )


def seed_plan(d: Diagnosis) -> dict:
    period_time = PERIOD_TIME.get(d.period, "11:00-14:00")
    top_reason = max(d.reasons, key=lambda item: item["weight"])["name"]
    if "新客" in top_reason:
        plan = {
            "goal": "拉新",
            "threshold": 35,
            "discount": 6,
            "budget": 1000,
            "audience": "近 30 天浏览未下单新客",
            "copy": f"{d.period}来小满餐饮，满 35 元减 6 元。今日 {period_time} 可用。",
        }
    elif "履约" in top_reason or "评价" in top_reason:
        plan = {
            "goal": "修复体验",
            "threshold": 45,
            "discount": 8,
            "budget": 900,
            "audience": "近 30 天下单但未复购顾客",
            "copy": f"{d.period}服务体验补偿券，满 45 元减 8 元，今日 {period_time} 可用。",
        }
    elif d.coupon_delta < -0.2:
        plan = {
            "goal": "提升触达",
            "threshold": 30,
            "discount": 5,
            "budget": 800,
            "audience": "近 7 天领券未核销用户",
            "copy": f"{d.period}限时提醒：满 30 元减 5 元，今天 {period_time} 可用。",
        }
    elif d.new_delta < -0.15:
        plan = {
            "goal": "拉新",
            "threshold": 35,
            "discount": 6,
            "budget": 1000,
            "audience": "近 30 天浏览未下单新客",
            "copy": f"{d.period}来小满餐饮，满 35 元减 6 元。今日 {period_time} 可用。",
        }
    else:
        plan = {
            "goal": "复购",
            "threshold": 45,
            "discount": 8,
            "budget": 900,
            "audience": "近 60 天未复购老客",
            "copy": f"{d.period}专属回访券，满 45 元减 8 元，限今天 {period_time} 使用。",
        }
    st.session_state.plan = plan
    return plan


def flow() -> None:
    labels = [
        ("home", "选择"),
        ("report", "日报"),
        ("diagnosis", "诊断"),
        ("confirm", "确认"),
        ("review", "复盘"),
    ]
    html = "<div class='step-row'>"
    for key, label in labels:
        cls = "step-dot active" if st.session_state.step == key else "step-dot"
        html += f"<div class='{cls}'>{label}</div>"
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def image_data_uri(path_value: str, modified: float) -> str | None:
    path = Path(path_value)
    if not path.exists():
        return None
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def app_header() -> None:
    d = st.session_state.get("diagnosis")
    if d is None:
        hero_title = "午市新客有波动"
        hero_note = "先用样例看一遍，也可以接入自己的经营数据。"
    else:
        hero_title = f"{d.period}订单需要关注"
        hero_note = f"订单较基线 {fmt_pct(d.order_delta)}，建议先看诊断再决定动作。"
    hero_image = next((path for path in HERO_IMAGES if path.exists()), None)
    hero_modified = hero_image.stat().st_mtime if hero_image else 0.0
    hero_src = image_data_uri(str(hero_image), hero_modified) if hero_image else None
    if hero_src:
        hero_visual = f"""
          <div class="hero-image-card">
            <div class="hero-image-wrap">
              <img src="{hero_src}" alt="经营数据，一目了然" />
            </div>
            <div class="hero-image-footer">
              <div class="hero-mini">
              <span class="mini-pill">接入经营数据</span>
              <span class="mini-pill">确认后执行</span>
              </div>
            </div>
          </div>
        """
    else:
        hero_visual = f"""
          <div class="hero-card">
            <div class="eyebrow">早上好，小满餐饮</div>
            <h1>{hero_title}</h1>
            <div class="hero-note">{hero_note}</div>
            <div class="hero-mini">
              <span class="mini-pill">接入经营数据</span>
              <span class="mini-pill">确认后执行</span>
            </div>
          </div>
        """
    st.markdown(
        f"""
        <div class="app-shell">
          <div class="topbar">{APP_NAME}</div>
          {hero_visual}
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric_grid(d: Diagnosis) -> None:
    cards = [
        ("订单变化", fmt_pct(d.order_delta), f"{d.orders_now} / {d.orders_base}", "order"),
        ("实收变化", fmt_pct(d.revenue_delta), fmt_money(d.revenue_now), "revenue"),
        ("新客变化", fmt_pct(d.new_delta), f"{d.new_now} / {d.new_base}", "customer"),
    ]
    html = "<div class='metric-grid'>"
    for label, value, detail, kind in cards:
        html += (
            f"<div class='metric {kind}'>"
            f"<div class='label'>{label}</div>"
            f"<div class='value'>{value}</div>"
            f"<div class='delta'>{detail}</div>"
            "</div>"
        )
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def load_scenario(name: str) -> None:
    df = scenario_data(name)
    st.session_state.df = df
    st.session_state.scenario = name
    st.session_state.diagnosis = analyze(df, name)
    st.session_state.confirmed = False
    st.session_state.executed = False
    st.session_state.chat = []
    st.session_state.step = "report"


def load_custom_data(raw: pd.DataFrame, source_name: str) -> None:
    st.session_state.df = prepare_data(raw)
    st.session_state.scenario = source_name
    st.session_state.diagnosis = analyze(st.session_state.df, source_name)
    st.session_state.confirmed = False
    st.session_state.executed = False
    st.session_state.chat = []
    st.session_state.step = "report"


def home_page() -> None:
    st.markdown("<div class='app-shell'>", unsafe_allow_html=True)
    sample_tab, data_tab = st.tabs(["样例体验", "接入数据"])

    with sample_tab:
        st.markdown("<div class='section-title'>选择一个经营场景</div>", unsafe_allow_html=True)
        selected = st.selectbox(
            "体验场景",
            list(SCENARIOS.keys()),
            format_func=lambda name: SCENARIOS[name]["title"],
            label_visibility="collapsed",
        )
        spec = SCENARIOS[selected]
        st.markdown(
            f"""
            <div class="softbox">
              <b>{spec['title']}</b><br/>
              <span>{spec['hint']}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("查看经营日报", use_container_width=True):
            load_scenario(selected)
            st.rerun()

    with data_tab:
        st.markdown("<div class='section-title'>接入经营数据</div>", unsafe_allow_html=True)
        uploaded = st.file_uploader("上传 CSV", type=["csv"], label_visibility="collapsed")
        data_url = st.text_input(
            "公开 CSV 链接",
            placeholder="粘贴公开 CSV 链接",
            label_visibility="collapsed",
        )
        if uploaded is not None and st.button("读取上传数据", use_container_width=True):
            try:
                raw = pd.read_csv(uploaded)
                ok, message = validate_data(raw)
                if not ok:
                    st.error(message)
                else:
                    load_custom_data(raw, "上传数据")
                    st.rerun()
            except Exception:
                st.error("CSV 无法读取，请检查文件格式。")
        if data_url and st.button("读取链接数据", use_container_width=True):
            try:
                raw = pd.read_csv(data_url)
                ok, message = validate_data(raw)
                if not ok:
                    st.error(message)
                else:
                    load_custom_data(raw, "链接数据")
                    st.rerun()
            except Exception:
                st.error("链接数据无法读取，请确认是可公开访问的 CSV。")
        with st.expander("数据格式帮助"):
            st.caption("字段：" + "、".join(REQUIRED_COLUMNS))
            demo = scenario_data("午市新客下滑")
            st.download_button(
                "下载样例 CSV",
                data=to_csv_bytes(demo),
                file_name="ant_business_sample.csv",
                mime="text/csv",
                use_container_width=True,
            )
    st.markdown("</div>", unsafe_allow_html=True)


def require_data() -> bool:
    if st.session_state.df is None or st.session_state.diagnosis is None:
        st.info("请先选择一个体验场景，或接入经营数据。")
        if st.button("返回选择场景"):
            go("home")
        return False
    return True


def report_page() -> None:
    if not require_data():
        return
    d = st.session_state.diagnosis
    st.markdown("<div class='app-shell'>", unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="card">
          <div class="card-title">今日最建议处理</div>
          <span class="tag">收入下滑</span>
          <span class="tag green">置信度 {d.confidence}%</span>
          <div class="big-title">近 3 天{d.period}订单下滑明显</div>
          <div class="body">{d.period}订单较基线 {fmt_pct(d.order_delta)}，建议先查看诊断。</div>
        """,
        unsafe_allow_html=True,
    )
    metric_grid(d)
    st.markdown("</div>", unsafe_allow_html=True)

    evidence_tags = "".join(f"<span class='tag'>{r['name']}</span>" for r in d.reasons)
    st.markdown(
        f"""
        <div class="card">
          <div class="card-title">关键证据</div>
          {evidence_tags}
          <div class="notice">确认前不会执行。</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("查看异常诊断", use_container_width=True):
        go("diagnosis")
    st.markdown("</div>", unsafe_allow_html=True)


def local_ai_answer(question: str, d: Diagnosis) -> str:
    top = max(d.reasons, key=lambda item: item["weight"])
    return f"已记录追问。当前为本地演示模式，可先参考最高权重原因：{top['name']}（{top['weight']}%）。接入 AI 密钥后可生成完整回答。"


def call_openai_compatible(question: str, d: Diagnosis) -> str | None:
    base_url = os.getenv("AI_API_BASE_URL")
    api_key = os.getenv("AI_API_KEY")
    model = os.getenv("AI_MODEL", "qwen-plus")
    if not base_url or not api_key:
        return None
    url = base_url.rstrip("/") + "/chat/completions"
    prompt = (
        f"你是蚂蚁经营助手。当前诊断：时段={d.period}，订单变化={fmt_pct(d.order_delta)}，"
        f"实收变化={fmt_pct(d.revenue_delta)}，新客变化={fmt_pct(d.new_delta)}，"
        f"原因={d.reasons}。请用简短、可信、可执行的中文回答商家问题：{question}"
    )
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "你只做经营辅助，不承诺收益，不越过商家确认边界。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
    }
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]
    except (urllib.error.URLError, KeyError, TimeoutError, json.JSONDecodeError):
        return None


def call_ollama(question: str, d: Diagnosis) -> str | None:
    base_url = os.getenv("OLLAMA_BASE_URL")
    if not base_url:
        return None
    model = os.getenv("OLLAMA_MODEL", "qwen2.5")
    url = base_url.rstrip("/") + "/api/generate"
    prompt = (
        f"你是蚂蚁经营助手。当前{d.period}订单变化{fmt_pct(d.order_delta)}，"
        f"原因权重{d.reasons}。请回答：{question}"
    )
    payload = {"model": model, "prompt": prompt, "stream": False}
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=18) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data.get("response")
    except (urllib.error.URLError, KeyError, TimeoutError, json.JSONDecodeError):
        return None


def ai_answer(question: str, d: Diagnosis) -> str:
    provider = st.session_state.ai_provider
    if provider in {"OpenAI-compatible API", "蚂蚁百灵/通义千问 API"}:
        return call_openai_compatible(question, d) or "已选择外部 API。当前未检测到可用密钥或接口，部署时配置环境变量后即可生成回答。"
    if provider == "Ollama 本地大模型":
        return call_ollama(question, d) or "已选择 Ollama。本机未检测到可用服务时，会保留追问但不生成长回答。"
    return local_ai_answer(question, d)


def diagnosis_page() -> None:
    if not require_data():
        return
    d = st.session_state.diagnosis
    st.markdown("<div class='app-shell'>", unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="card">
          <div class="card-title">{d.period}订单下滑诊断</div>
          <div class="body">对比近 3 天与前 7 天同经营时段，订单 {fmt_pct(d.order_delta)}，实收 {fmt_pct(d.revenue_delta)}，新客 {fmt_pct(d.new_delta)}。</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    metric_grid(d)

    reasons_html = "<div class='card reason-card'><div class='card-title'>可能原因</div>"
    for reason in d.reasons:
        reasons_html += (
            f"<div class='reason'>"
            f"<div class='reason-top'><span>{reason['name']}</span>"
            f"<span style='color:{reason['color']}'>{reason['weight']}%</span></div>"
            f"<div class='bar-bg'><div class='bar' style='width:{reason['weight']}%; background:{reason['color']};'></div></div>"
            f"</div>"
        )
    reasons_html += "</div>"
    st.markdown(reasons_html, unsafe_allow_html=True)

    st.markdown("<div class='card'><div class='card-title'>继续追问</div>", unsafe_allow_html=True)
    if st.session_state.ai_provider not in AI_PROVIDERS:
        st.session_state.ai_provider = AI_PROVIDERS[0]
    st.session_state.ai_provider = st.selectbox(
        "选择工具",
        AI_PROVIDERS,
        index=AI_PROVIDERS.index(st.session_state.ai_provider),
    )
    st.markdown("<div class='subtle'>当前保留工具选择入口；接入密钥后可生成完整回答。</div>", unsafe_allow_html=True)
    for item in st.session_state.chat[-4:]:
        st.markdown(f"<div class='chat-user'>{item['q']}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='chat-ai'>{item['a']}</div>", unsafe_allow_html=True)
    question = st.text_input("继续追问", placeholder=f"例如：为什么{d.period}新客下降更明显？")
    if st.button("发送追问", use_container_width=True):
        answer = ai_answer(question, d)
        st.session_state.chat.append({"q": question or f"为什么{d.period}下滑？", "a": answer})
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    if d.confidence < 60:
        st.markdown("<div class='notice'>当前置信度偏低，建议补充更多经营数据后再执行。</div>", unsafe_allow_html=True)
    else:
        if st.button("生成经营方案", use_container_width=True):
            seed_plan(d)
            go("confirm")
    st.markdown("</div>", unsafe_allow_html=True)


def confirm_page() -> None:
    if not require_data():
        return
    d = st.session_state.diagnosis
    plan = st.session_state.plan
    st.markdown("<div class='app-shell'>", unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="card">
          <div class="card-title">{d.period}{plan['goal']}方案</div>
          <div class="body">确认前可调整券门槛、人群、预算和触达文案。</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    plan["threshold"] = st.number_input("券门槛", 20, 200, int(plan["threshold"]), 5)
    plan["discount"] = st.number_input("优惠金额", 1, 50, int(plan["discount"]), 1)
    plan["budget"] = st.number_input("预算上限", 100, 5000, int(plan["budget"]), 100)
    audiences = ["近 30 天浏览未下单新客", "近 60 天未复购老客", "午市高意向附近用户", "近 7 天领券未核销用户", "近 30 天下单但未复购顾客"]
    plan["audience"] = st.selectbox(
        "触达人群",
        audiences,
        index=audiences.index(plan["audience"]) if plan["audience"] in audiences else 0,
    )
    plan["copy"] = st.text_area("触达文案", value=plan["copy"], height=96)

    projected_cost = min(plan["budget"], max(120, round(plan["discount"] * max(d.new_base - d.new_now, 24) * 1.8)))
    over_budget = plan["budget"] > 1500
    readonly = st.session_state.role == "只读子账号"
    st.markdown(
        f"""
        <div class="card">
          <div class="card-title">预览确认</div>
          <div class="kv"><div class="k">券配置</div><div class="v">满 {plan['threshold']} 元减 {plan['discount']} 元</div></div>
          <div class="kv"><div class="k">触达人群</div><div class="v">{plan['audience']}</div></div>
          <div class="kv"><div class="k">预计成本</div><div class="v">{fmt_money(projected_cost)}</div></div>
          <div class="kv"><div class="k">复盘指标</div><div class="v">券核销、新增顾客、成本、7 日复购</div></div>
        </div>
        <div class="notice">确认前不会执行。</div>
        """,
        unsafe_allow_html=True,
    )
    if over_budget:
        st.error("预算超过安全上限，请调低预算或缩小人群。")
    if readonly:
        st.error("当前账号无权确认执行，请切换具备经营权限的账号。")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("返回诊断", use_container_width=True):
            go("diagnosis")
    with c2:
        if st.button("确认执行", disabled=over_budget or readonly, use_container_width=True):
            with st.spinner("正在创建任务..."):
                time.sleep(0.6)
            st.session_state.confirmed = True
            st.session_state.executed = True
            go("review")
    st.markdown("</div>", unsafe_allow_html=True)


def review_page() -> None:
    if not require_data():
        return
    d = st.session_state.diagnosis
    plan = st.session_state.plan
    st.markdown("<div class='app-shell'>", unsafe_allow_html=True)
    if not st.session_state.executed:
        st.markdown(
            "<div class='card'><div class='card-title'>暂无复盘</div><div class='body'>请先确认执行方案。</div></div>",
            unsafe_allow_html=True,
        )
        if st.button("去确认方案", use_container_width=True):
            go("confirm")
        st.markdown("</div>", unsafe_allow_html=True)
        return
    redeemed = max(38, round((d.new_base - d.new_now) * 3 + plan["discount"] * 9))
    new_gain = max(16, round(redeemed * 0.38))
    cost = min(plan["budget"], redeemed * plan["discount"])
    st.markdown(
        f"""
        <div class="card">
          <div class="card-title">执行复盘</div>
          <div class="okbox">{d.period}{plan['goal']}方案已完成执行，复盘数据已回流。</div>
        </div>
        <div class="metric-grid">
          <div class="metric"><div class="label">券核销</div><div class="value">{redeemed}</div><div class="delta">已完成</div></div>
          <div class="metric"><div class="label">新增顾客</div><div class="value">{new_gain}</div><div class="delta">可验证</div></div>
          <div class="metric"><div class="label">成本</div><div class="value">{fmt_money(cost)}</div><div class="delta">预算内</div></div>
        </div>
        <div class="card">
          <div class="card-title">复盘摘要</div>
          <div class="body"><b>事实数据：</b>{d.period}券核销 {redeemed} 张，新增顾客 {new_gain} 人，成本 {fmt_money(cost)}。</div>
          <div class="body" style="margin-top:10px;"><b>可能判断：</b>目标时段响应较集中，说明小范围触达有效，但不等同于长期因果结论。</div>
          <div class="body" style="margin-top:10px;"><b>下一步建议：</b>保持预算上限，补充评价回复任务，再观察 7 日复购。</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("生成下一轮待办", use_container_width=True):
        st.toast("已生成：评价回复与复购提醒待办")
    st.markdown("</div>", unsafe_allow_html=True)


def controls() -> None:
    with st.expander("设置", expanded=False):
        st.session_state.role = st.selectbox(
            "当前账号",
            ["商家主账号", "具备经营权限的子账号", "只读子账号"],
            index=["商家主账号", "具备经营权限的子账号", "只读子账号"].index(st.session_state.role),
        )
        if st.button("重置体验"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            init_state()
            st.rerun()


def main() -> None:
    init_state()
    css()
    st.markdown("<div class='app-shell'>", unsafe_allow_html=True)
    app_header()
    flow()
    st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.step == "home":
        home_page()
    elif st.session_state.step == "report":
        report_page()
    elif st.session_state.step == "diagnosis":
        diagnosis_page()
    elif st.session_state.step == "confirm":
        confirm_page()
    elif st.session_state.step == "review":
        review_page()
    else:
        go("home")
    controls()


if __name__ == "__main__":
    main()
