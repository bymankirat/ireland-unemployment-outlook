"""Headline figures and trends, in the style of a monthly statistical release."""

from __future__ import annotations

import pandas as pd

from config import ADULT, ALL_AGES, BOTH, STAT_COUNT, STAT_RATE, YOUTH
from data_loading import series


def _fmt_month(d: pd.Timestamp) -> str:
    return d.strftime("%B %Y")


def headline_table(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Timestamp]:
    """Latest rate and count for each age group and sex, with monthly and annual change."""
    rows = []
    latest = None
    for age in [ALL_AGES, YOUTH, ADULT]:
        for sex in [BOTH, "Male", "Female"]:
            rate = series(df, STAT_RATE, age, sex).dropna()
            count = series(df, STAT_COUNT, age, sex).dropna()
            if rate.empty:
                continue
            t = rate.index[-1]
            latest = t if latest is None else max(latest, t)
            prev_m = rate.get(t - pd.DateOffset(months=1))
            prev_y = rate.get(t - pd.DateOffset(years=1))
            rows.append({
                "Age group": age, "Sex": sex,
                "Rate (%)": rate.iloc[-1],
                "Unemployed (thousands)": count.get(t),
                "Change on month (pp)": None if prev_m is None else rate.iloc[-1] - prev_m,
                "Change on year (pp)": None if prev_y is None else rate.iloc[-1] - prev_y,
            })
    return pd.DataFrame(rows), latest


def long_run(df: pd.DataFrame) -> dict:
    r = series(df, STAT_RATE, ALL_AGES, BOTH).dropna()
    c = series(df, STAT_COUNT, ALL_AGES, BOTH).dropna()
    peak, low = r.idxmax(), r[r.index >= "2005-01-01"].idxmin()
    recent_low = r[r.index >= "2015-01-01"].idxmin()
    all_low = r.idxmin()
    return {
        "first_month": _fmt_month(r.index[0]),
        "latest_month": _fmt_month(r.index[-1]),
        "latest_rate": float(r.iloc[-1]),
        "latest_count": float(c.iloc[-1]),
        "peak_rate": float(r.max()), "peak_month": _fmt_month(peak),
        "low_rate_since_2005": float(r.loc[low]), "low_month_since_2005": _fmt_month(low),
        "low_rate_since_2015": float(r.loc[recent_low]), "low_month_since_2015": _fmt_month(recent_low),
        "low_rate_all": float(r.loc[all_low]), "low_month_all": _fmt_month(all_low),
        "avg_last_12m": float(r.iloc[-12:].mean()),
        "avg_prev_12m": float(r.iloc[-24:-12].mean()),
    }


def youth_vs_adult(df: pd.DataFrame) -> dict:
    y = series(df, STAT_RATE, YOUTH, BOTH).dropna()
    a = series(df, STAT_RATE, ADULT, BOTH).dropna()
    ratio = (y / a).dropna()
    return {
        "youth_latest": float(y.iloc[-1]), "adult_latest": float(a.iloc[-1]),
        "ratio_latest": float(ratio.iloc[-1]),
        "ratio_avg": float(ratio.mean()),
        "ratio_avg_2015_2019": float(ratio["2015":"2019"].mean()) if len(ratio["2015":"2019"]) else None,
    }


def gender_gap(df: pd.DataFrame) -> dict:
    m = series(df, STAT_RATE, ALL_AGES, "Male").dropna()
    f = series(df, STAT_RATE, ALL_AGES, "Female").dropna()
    gap = (m - f).dropna()
    widest = gap.idxmax()
    return {
        "male_latest": float(m.iloc[-1]), "female_latest": float(f.iloc[-1]),
        "gap_latest": float(gap.iloc[-1]),
        "gap_widest": float(gap.max()), "gap_widest_month": _fmt_month(widest),
        "gap_avg_last_5y": float(gap.iloc[-60:].mean()),
    }
