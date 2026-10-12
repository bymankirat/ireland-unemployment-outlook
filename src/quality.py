"""Quality control: automatic checks on the downloaded data before any analysis.

Every check writes a PASS / WARN / FAIL line to reports/qc_log.txt. A FAIL stops
the pipeline, so a broken download can never produce a published report.
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from config import ADULT, ALL_AGES, BOTH, REPORTS_DIR, STAT_COUNT, STAT_RATE, YOUTH

AGES = [ALL_AGES, YOUTH, ADULT]
SEXES = [BOTH, "Male", "Female"]


def run_checks(df: pd.DataFrame) -> dict:
    results: list[tuple[str, str, str]] = []

    def add(status, check, detail):
        results.append((status, check, detail))

    # 1. Structure: every statistic x age x sex combination is present
    missing = [(s, a, x) for s in (STAT_RATE, STAT_COUNT) for a in AGES for x in SEXES
               if df[(df.statistic == s) & (df.age == a) & (df.sex == x)].empty]
    add("FAIL" if missing else "PASS", "All 18 series present",
        f"missing: {missing}" if missing else "2 statistics x 3 age groups x 3 sexes")

    # 2. Time coverage: monthly, no gaps, no duplicates
    months = pd.DatetimeIndex(sorted(df["date"].unique()))
    full = pd.date_range(months.min(), months.max(), freq="MS")
    gaps = full.difference(months)
    dups = df.duplicated(["date", "statistic", "age", "sex"]).sum()
    add("FAIL" if len(gaps) else "PASS", "No missing months",
        f"{len(gaps)} gaps, e.g. {list(gaps[:3].strftime('%b %Y'))}" if len(gaps)
        else f"{len(full)} consecutive months, {months.min():%b %Y} to {months.max():%b %Y}")
    add("FAIL" if dups else "PASS", "No duplicate rows", f"{dups} duplicates")

    # 3. Missing values
    n_na = int(df["value"].isna().sum())
    pct = 100 * n_na / len(df)
    add("FAIL" if pct > 5 else "WARN" if n_na else "PASS", "Missing values",
        f"{n_na} of {len(df):,} values missing ({pct:.2f}%)")

    # 4. Plausible ranges
    rates = df[df.statistic == STAT_RATE]["value"].dropna()
    counts = df[df.statistic == STAT_COUNT]["value"].dropna()
    bad_r = int(((rates < 0) | (rates > 60)).sum())
    bad_c = int((counts < 0).sum())
    add("FAIL" if bad_r else "PASS", "Rates between 0% and 60%", f"{bad_r} out of range")
    add("FAIL" if bad_c else "PASS", "Counts not negative", f"{bad_c} negative")

    # 5. Internal consistency: parts add up to totals (allowing for CSO rounding)
    def cnt(a, x):
        return df[(df.statistic == STAT_COUNT) & (df.age == a) & (df.sex == x)].set_index("date")["value"]

    sex_diff = (cnt(ALL_AGES, "Male") + cnt(ALL_AGES, "Female") - cnt(ALL_AGES, BOTH)).abs().dropna()
    age_diff = (cnt(YOUTH, BOTH) + cnt(ADULT, BOTH) - cnt(ALL_AGES, BOTH)).abs().dropna()
    # Seasonally adjusted series are adjusted separately, so parts need not add exactly to the
    # total. Small gaps are expected; large ones are flagged for a person to look at, never fatal.
    total = cnt(ALL_AGES, BOTH)
    for name, d in [("Male + female close to both sexes (counts)", sex_diff),
                    ("15-24 + 25-74 close to 15-74 (counts)", age_diff)]:
        rel = (100 * d / total.reindex(d.index)).dropna()
        worst = float(rel.max()) if len(rel) else 0.0
        status = "PASS" if worst <= 3 else "WARN"
        add(status, name, f"largest gap {worst:.1f}% of the total "
                          f"(small gaps are normal: each series is seasonally adjusted separately)")

    # 6. Month-to-month jumps (flag, don't fail: real shocks such as COVID-19 happen)
    r = df[(df.statistic == STAT_RATE) & (df.age == ALL_AGES) & (df.sex == BOTH)].set_index("date")["value"]
    jumps = r.diff().abs()
    big = jumps[jumps > 1.0]
    add("WARN" if len(big) else "PASS", "No monthly jump above 1 pp (15-74 rate)",
        f"{len(big)} large jumps: {', '.join(f'{d:%b %Y}' for d in big.index[:5])}" if len(big) else "none")

    # 7. Freshness
    age_days = (pd.Timestamp(datetime.now().date()) - months.max()).days
    add("WARN" if age_days > 120 else "PASS", "Data is recent",
        f"latest month {months.max():%B %Y} ({age_days} days ago)")

    n_fail = sum(s == "FAIL" for s, *_ in results)
    n_warn = sum(s == "WARN" for s, *_ in results)
    summary = (f"QC {'FAILED' if n_fail else 'PASSED'}: {len(results) - n_fail - n_warn} passed, "
               f"{n_warn} warnings, {n_fail} failures")

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    lines = [f"Quality control log - {datetime.now():%Y-%m-%d %H:%M}", summary, ""]
    lines += [f"[{s}] {c}: {d}" for s, c, d in results]
    (REPORTS_DIR / "qc_log.txt").write_text("\n".join(lines) + "\n")
    return {"passed": n_fail == 0, "summary": summary, "results": results}
