"""Short-term forecasts of the unemployment rate, tested honestly.

Four simple, transparent models are compared with a rolling-origin backtest:
each month, every model is fitted only on the data available at that time and
asked to forecast the next 1-3 months. The model is chosen on 2012-2019 and
then judged once on 2022 onwards, which it never saw while being chosen.
Prediction intervals come from the model's own past errors (empirical intervals),
and we check whether they really contain the outcome as often as claimed.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from config import COVID, HORIZON, INTERVAL, MIN_TRAIN_MONTHS, TEST_START, VALIDATION

MODEL_NAMES = {
    "naive": "No change (naive)",
    "drift": "Recent trend (12-month drift)",
    "ar": "Autoregressive on changes, AR(2)",
    "damped": "Damped-trend exponential smoothing",
}

# Damped Holt parameter grid, evaluated in one vectorised pass
_A, _B, _P = np.meshgrid(np.arange(0.2, 1.01, 0.1), [0.02, 0.05, 0.1, 0.2, 0.3],
                         [0.8, 0.9, 0.95, 0.98], indexing="ij")
ALPHA, BETA, PHI = _A.ravel(), _B.ravel(), _P.ravel()


def _naive(y, H):
    return np.repeat(y[-1], H)


def _drift(y, H):
    slope = (y[-1] - y[-13]) / 12 if len(y) > 12 else 0.0
    return y[-1] + slope * np.arange(1, H + 1)


def _ar(y, H, window=120):
    d = np.diff(y[-(window + 1):])
    if len(d) < 10:
        return _naive(y, H)
    X = np.column_stack([np.ones(len(d) - 2), d[1:-1], d[:-2]])
    coef, *_ = np.linalg.lstsq(X, d[2:], rcond=None)
    hist, level, out = list(d[-2:]), y[-1], []
    for _ in range(H):
        nxt = coef[0] + coef[1] * hist[-1] + coef[2] * hist[-2]
        hist.append(nxt)
        level = level + nxt
        out.append(level)
    return np.array(out)


def _damped(y, H, window=120):
    z = y[-window:]
    lev = np.full(ALPHA.shape, z[0], dtype=float)
    tr = np.full(ALPHA.shape, z[1] - z[0], dtype=float)
    sse = np.zeros(ALPHA.shape)
    for t in range(1, len(z)):
        fc = lev + PHI * tr
        sse += (z[t] - fc) ** 2
        new_lev = ALPHA * z[t] + (1 - ALPHA) * fc
        tr = BETA * (new_lev - lev) + (1 - BETA) * PHI * tr
        lev = new_lev
    k = int(np.argmin(sse))
    phi_pows = np.cumsum(PHI[k] ** np.arange(1, H + 1))
    return lev[k] + phi_pows * tr[k]


MODELS = {"naive": _naive, "drift": _drift, "ar": _ar, "damped": _damped}


def backtest(rate: pd.Series) -> pd.DataFrame:
    """Every origin, every model, horizons 1..H: forecast, actual and error."""
    y = rate.dropna()
    vals, dates = y.to_numpy(float), y.index
    rows = []
    for i in range(MIN_TRAIN_MONTHS, len(y) - 1):
        hist = vals[: i + 1]
        for name, fn in MODELS.items():
            fc = fn(hist, HORIZON)
            for h in range(1, HORIZON + 1):
                if i + h >= len(y):
                    break
                rows.append({
                    "origin": dates[i], "target": dates[i + h], "h": h, "model": name,
                    "forecast": fc[h - 1], "actual": vals[i + h],
                    "error": vals[i + h] - fc[h - 1],
                })
    return pd.DataFrame(rows)


def _period(bt: pd.DataFrame, which: str) -> pd.DataFrame:
    if which == "validation":
        m = (bt["origin"] >= VALIDATION[0]) & (bt["origin"] <= VALIDATION[1]) & (bt["target"] < COVID[0])
    else:
        m = bt["origin"] >= TEST_START
    return bt[m]


def evaluate(rate: pd.Series) -> dict:
    bt = backtest(rate)
    val, test = _period(bt, "validation"), _period(bt, "test")

    mae = lambda d: d.groupby(["model", "h"])["error"].apply(lambda e: e.abs().mean()).unstack("h")  # noqa: E731
    mae_val, mae_test = mae(val), mae(test)
    chosen = mae_val.mean(axis=1).idxmin()

    lo_q, hi_q = (1 - INTERVAL) / 2, 1 - (1 - INTERVAL) / 2
    errs = val[val["model"] == chosen].groupby("h")["error"]
    bands = {h: (float(e.quantile(lo_q)), float(e.quantile(hi_q))) for h, e in errs}

    t = test[test["model"] == chosen].copy()
    t["lo"] = t["forecast"] + t["h"].map(lambda h: bands[h][0])
    t["hi"] = t["forecast"] + t["h"].map(lambda h: bands[h][1])
    t["inside"] = (t["actual"] >= t["lo"]) & (t["actual"] <= t["hi"])
    coverage = t.groupby("h")["inside"].mean()

    skill = 100 * (1 - mae_test.loc[chosen] / mae_test.loc["naive"])

    # Forecast the next HORIZON months from all data
    y = rate.dropna()
    fc = MODELS[chosen](y.to_numpy(float), HORIZON)
    future = pd.date_range(y.index[-1] + pd.DateOffset(months=1), periods=HORIZON, freq="MS")
    outlook = pd.DataFrame({
        "month": future, "forecast": fc,
        "lo": [fc[h - 1] + bands[h][0] for h in range(1, HORIZON + 1)],
        "hi": [fc[h - 1] + bands[h][1] for h in range(1, HORIZON + 1)],
    })

    return {
        "chosen": chosen,
        "chosen_name": MODEL_NAMES[chosen],
        "mae_validation": mae_val,
        "mae_test": mae_test,
        "skill_vs_naive_pct": skill,
        "coverage": coverage,
        "bands": bands,
        "outlook": outlook,
        "test_rows": t,
        "n_val_origins": int(val["origin"].nunique()),
        "n_test_origins": int(test["origin"].nunique()),
        "test_first": test["origin"].min(),
        "test_last_target": test["target"].max(),
    }
