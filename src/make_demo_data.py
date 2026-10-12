"""FAKE data in the exact CSO MUM01 CSV layout, for testing without internet.

    python run_pipeline.py --demo

Never publish results made from this file: every output is marked DEMO.
"""

import numpy as np
import pandas as pd

from config import RAW_DIR

DEMO_FILE = RAW_DIR.parent / "demo" / "MUM01_DEMO.csv"


def make(seed: int = 3) -> None:
    rng = np.random.default_rng(seed)
    dates = pd.date_range("1998-01-01", "2026-09-01", freq="MS")
    knots = {"1998-01": 7.8, "2001-01": 4.2, "2007-06": 4.6, "2009-06": 12.0, "2012-02": 15.5,
             "2016-01": 8.6, "2019-12": 4.8, "2020-04": 6.5, "2021-06": 6.6, "2022-06": 4.3,
             "2024-06": 4.4, "2026-09": 4.9}
    k = pd.Series(knots)
    k.index = pd.to_datetime(k.index)
    base = k.reindex(k.index.union(dates)).interpolate("time").reindex(dates).to_numpy()
    noise = np.zeros(len(dates))
    for t in range(1, len(dates)):
        noise[t] = 0.8 * noise[t - 1] + rng.normal(0, 0.08)
    total = base + noise

    labour = np.linspace(1750, 2850, len(dates))  # thousands
    groups = {
        ("15 - 24 years", "310"): 2.3, ("25 - 74 years", "4350"): 0.83, ("15 - 74 years", "316"): 1.0,
    }
    sexes = {("Both sexes", "-"): 1.0, ("Male", "1"): 1.07, ("Female", "2"): 0.92}
    rows = []
    for stat_code, stat_label, unit in [("MUM01C01", "Seasonally Adjusted Monthly Unemployment", "Thousand"),
                                        ("MUM01C02", "Seasonally Adjusted Monthly Unemployment Rate", "%")]:
        for d, tot, lf in zip(dates, total, labour):
            for (age, ac), am in groups.items():
                for (sex, sc), sm in sexes.items():
                    rate = max(tot * am * (sm + (0.03 * (tot - 6) if sex == "Male" else -0.02 * (tot - 6)) * 0.1), 1.0)
                    if stat_code == "MUM01C02":
                        val = round(rate, 1)
                    else:
                        # counts built from parts so that they add up, like real data
                        a_share = {"15 - 24 years": [0.15], "25 - 74 years": [0.85],
                                   "15 - 74 years": [0.15, 0.85]}[age]
                        a_mult = {"15 - 24 years": [2.3], "25 - 74 years": [0.83],
                                  "15 - 74 years": [2.3, 0.83]}[age]
                        s_parts = {"Both sexes": [(0.53, 1.07), (0.47, 0.92)], "Male": [(0.53, 1.07)],
                                   "Female": [(0.47, 0.92)]}[sex]
                        val = round(sum(tot * am_ * sm_ / 100 * lf * sh * ss
                                        for sh, am_ in zip(a_share, a_mult) for ss, sm_ in s_parts), 1)
                    rows.append([stat_code, stat_label, d.strftime("%Y%m"), d.strftime("%Y %B"),
                                 ac, age, sc, sex, unit, val])
    df = pd.DataFrame(rows, columns=["STATISTIC", "Statistic Label", "TLIST(M1)", "Month",
                                     "C02076V02508", "Age Group", "C02199V02655", "Sex", "UNIT", "VALUE"])
    DEMO_FILE.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(DEMO_FILE, index=False, quoting=1)
    print(f"Demo file written: {DEMO_FILE}")


if __name__ == "__main__":
    make()
