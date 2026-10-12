"""Release charts. Each title states the finding."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from config import ADULT, ALL_AGES, BOTH, COVID, FIG_DIR, INTERVAL, STAT_RATE, YOUTH  # noqa: E402
from data_loading import series  # noqa: E402
from forecasting import MODEL_NAMES  # noqa: E402

BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK_2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
SHADE = "#efeee9"
BOX = {"facecolor": SURFACE, "edgecolor": "none", "pad": 1.5}

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "axes.edgecolor": GRID,
    "axes.labelcolor": INK_2, "axes.titlecolor": INK, "axes.titlesize": 13,
    "axes.titleweight": "bold", "axes.titlelocation": "left",
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "axes.axisbelow": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "xtick.color": INK_2, "ytick.color": INK_2, "font.size": 10.5,
    "font.family": "DejaVu Sans", "legend.frameon": False,
})


def _save(fig, name):
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    p = FIG_DIR / name
    fig.savefig(p, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return str(p)


def _sub(ax, text):
    ax.text(0, 1.02, text, transform=ax.transAxes, color=INK_2, fontsize=10, va="bottom")


def _covid(ax):
    ax.axvspan(pd.Timestamp(COVID[0]), pd.Timestamp(COVID[1]), color=SHADE, lw=0, zorder=0)


def long_run(df, lr: dict) -> str:
    r = series(df, STAT_RATE, ALL_AGES, BOTH).dropna()
    fig, ax = plt.subplots(figsize=(11, 4.2))
    _covid(ax)
    ax.plot(r.index, r, color=BLUE, lw=1.8)
    pk = r.idxmax()
    ax.annotate(f"Peak {r.max():.1f}% ({pk:%b %Y})", (pk, r.max()), xytext=(8, 6),
                textcoords="offset points", color=INK_2, fontsize=9.5, va="bottom")
    ax.set_ylim(0, r.max() * 1.15)
    ax.plot([r.index[-1]], [r.iloc[-1]], "o", color=BLUE, ms=6)
    ax.annotate(f"{r.iloc[-1]:.1f}%\n{r.index[-1]:%b %Y}", (r.index[-1], r.iloc[-1]), xytext=(-8, 16),
                textcoords="offset points", ha="right", color=INK, fontsize=9.5, fontweight="bold")
    ax.text(pd.Timestamp(COVID[0]), ax.get_ylim()[1] * 0.97, " COVID-19", color=INK_2, fontsize=9, va="top")
    ax.set_ylabel("Unemployment rate (%)")
    ax.set_title(f"Unemployment is {r.iloc[-1]:.1f}%, a fraction of the {r.max():.1f}% peak", pad=26)
    _sub(ax, "Seasonally adjusted monthly unemployment rate, ages 15-74, both sexes")
    return _save(fig, "01_long_run.png")


def youth(df) -> str:
    y = series(df, STAT_RATE, YOUTH, BOTH).dropna()
    a = series(df, STAT_RATE, ADULT, BOTH).dropna()
    fig, ax = plt.subplots(figsize=(11, 4.2))
    _covid(ax)
    ax.plot(y.index, y, color=ORANGE, lw=1.8)
    ax.plot(a.index, a, color=BLUE, lw=1.8)
    for s, lab, c in [(y, "Aged 15-24", ORANGE), (a, "Aged 25-74", BLUE)]:
        ax.text(s.index[-1] + pd.DateOffset(months=3), s.iloc[-1], f"{lab}\n{s.iloc[-1]:.1f}%",
                color=c, fontsize=9.5, va="center", fontweight="bold")
    ax.set_ylabel("Unemployment rate (%)")
    ax.set_ylim(0, None)
    ax.set_xlim(y.index[0], y.index[-1] + pd.DateOffset(months=42))
    ratio = y.iloc[-1] / a.iloc[-1]
    ax.set_title(f"Young people are {ratio:.1f} times as likely to be unemployed", pad=26)
    _sub(ax, "Seasonally adjusted unemployment rate by age group, both sexes")
    return _save(fig, "02_youth.png")


def gender(df) -> str:
    m = series(df, STAT_RATE, ALL_AGES, "Male").dropna()
    f = series(df, STAT_RATE, ALL_AGES, "Female").dropna()
    gap = (m - f).dropna()
    fig, ax = plt.subplots(figsize=(11, 3.8))
    _covid(ax)
    ax.axhline(0, color=INK_2, lw=1)
    ax.fill_between(gap.index, 0, gap, where=gap >= 0, color=BLUE, alpha=0.25, lw=0)
    ax.fill_between(gap.index, 0, gap, where=gap < 0, color=ORANGE, alpha=0.25, lw=0)
    ax.plot(gap.index, gap, color=INK_2, lw=1.2)
    ax.text(gap.index[2], ax.get_ylim()[1] * 0.85, "Men's rate higher", color=BLUE, fontsize=9.5, bbox=BOX)
    if gap.min() < 0:
        ax.text(gap.index[2], ax.get_ylim()[0] * 0.8, "Women's rate higher", color=ORANGE, fontsize=9.5, bbox=BOX)
    ax.set_ylabel("Male minus female rate (pp)")
    widest = gap.idxmax()
    now = gap.iloc[-1]
    now_txt = (f"women's rate is now {abs(now):.1f} pp higher" if now < -0.05 else
               f"men's rate is now {now:.1f} pp higher" if now > 0.05 else "the rates are now equal")
    ax.set_title(f"The gender gap peaked at {gap.max():.1f} pp in {widest:%Y}; {now_txt}", pad=26)
    _sub(ax, "Difference between male and female unemployment rates, ages 15-74, percentage points")
    return _save(fig, "03_gender_gap.png")


def outlook(df, res: dict) -> str:
    r = series(df, STAT_RATE, ALL_AGES, BOTH).dropna()
    hist = r[r.index >= r.index[-1] - pd.DateOffset(months=36)]
    o = res["outlook"]
    fig, ax = plt.subplots(figsize=(11, 4.2))
    xs = [hist.index[-1]] + list(o["month"])
    ax.fill_between(xs, [hist.iloc[-1]] + list(o["lo"]), [hist.iloc[-1]] + list(o["hi"]),
                    color=BLUE, alpha=0.18, lw=0)
    ax.plot(hist.index, hist, color=BLUE, lw=1.8)
    ax.plot(xs, [hist.iloc[-1]] + list(o["forecast"]), color=BLUE, lw=1.8, ls="--")
    last = o.iloc[-1]
    ax.text(last["month"] + pd.DateOffset(days=20), last["forecast"],
            f"{last['month']:%b %Y}\n{last['forecast']:.1f}%\n({last['lo']:.1f}-{last['hi']:.1f}%)",
            color=INK, fontsize=9.5, va="center")
    ax.set_xlim(hist.index[0], o["month"].iloc[-1] + pd.DateOffset(months=4))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.set_ylabel("Unemployment rate (%)")
    ax.set_title(f"Outlook: about {last['forecast']:.1f}% by {last['month']:%B %Y}", pad=26)
    _sub(ax, f"Last 3 years and 3-month forecast; shaded band is the {INTERVAL:.0%} prediction interval")
    return _save(fig, "04_outlook.png")


def accuracy(res: dict) -> str:
    mae = res["mae_test"]
    order = ["naive", "drift", "ar", "damped"]
    fig, ax = plt.subplots(figsize=(10, 4))
    w = 0.2
    colors = {"naive": "#9a9a95", "drift": AQUA, "ar": ORANGE, "damped": BLUE}
    hs = list(mae.columns)
    for j, mname in enumerate(order):
        vals = [mae.loc[mname, h] for h in hs]
        xs = [h + (j - 1.5) * w for h in hs]
        bars = ax.bar(xs, vals, width=w * 0.92, color=colors[mname],
                      label=MODEL_NAMES[mname] + ("  (chosen)" if mname == res["chosen"] else ""))
        if mname == res["chosen"]:
            for b, v in zip(bars, vals):
                ax.text(b.get_x() + b.get_width() / 2, v, f"{v:.2f}", ha="center", va="bottom",
                        fontsize=9, color=INK)
    ax.set_xticks(hs)
    ax.set_xticklabels([f"{h} month{'s' if h > 1 else ''} ahead" for h in hs])
    ax.set_ylabel("Mean absolute error (pp)")
    ax.grid(axis="x", visible=False)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2, fontsize=9)
    ax.set_title("How far off were the forecasts on years the model never saw?", pad=26)
    _sub(ax, f"Average forecast error, test period from {res['test_first']:%B %Y}; lower is better")
    return _save(fig, "05_accuracy.png")
