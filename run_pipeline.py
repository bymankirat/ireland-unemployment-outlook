"""Run everything: download CSO data -> analysis -> forecasts -> charts -> web report.

    python run_pipeline.py          # downloads the latest CSO data automatically
    python run_pipeline.py --demo   # simulated data for testing (outputs marked DEMO)
    python run_pipeline.py --refresh  # re-download even if a copy exists
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "src"))

import analysis  # noqa: E402
import charts  # noqa: E402
import forecasting  # noqa: E402
import quality  # noqa: E402
import report  # noqa: E402
from config import ALL_AGES, BOTH, DOCS_DIR, INTERVAL, REPORTS_DIR, STAT_RATE, TABLE  # noqa: E402
from data_loading import download, load, series  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--refresh", action="store_true")
    args = ap.parse_args()

    print("1/5  Getting the data ...")
    if args.demo:
        from make_demo_data import DEMO_FILE, make
        make()
        path = DEMO_FILE
    else:
        try:
            path = download(force=args.refresh)
        except Exception as e:  # noqa: BLE001
            sys.exit(f"\n[!] Could not download CSO table {TABLE}: {e}\n"
                     f"    Download it by hand: data.cso.ie, search {TABLE}, download CSV,\n"
                     f"    and save it as data/raw/{TABLE}.csv. Then run this again.")
    df = load(path)
    print(f"     {df['date'].min():%b %Y} to {df['date'].max():%b %Y}, {len(df):,} rows")
    qc = quality.run_checks(df)
    print(f"     {qc['summary']}  (details: reports/qc_log.txt)")
    for status, check, detail in qc["results"]:
        if status != "PASS":
            print(f"       [{status}] {check}: {detail}")
    if not qc["passed"]:
        sys.exit("\n[!] Quality checks failed, so no report was produced. See reports/qc_log.txt.")

    print("2/5  Analysing ...")
    table, latest = analysis.headline_table(df)
    lr, yv, gg = analysis.long_run(df), analysis.youth_vs_adult(df), analysis.gender_gap(df)

    print("3/5  Forecasting and backtesting ...")
    res = forecasting.evaluate(series(df, STAT_RATE, ALL_AGES, BOTH))

    print("4/5  Drawing charts ...")
    figs = {
        "long": charts.long_run(df, lr), "youth": charts.youth(df), "gender": charts.gender(df),
        "outlook": charts.outlook(df, res), "accuracy": charts.accuracy(res),
    }

    print("5/5  Writing the report ...")
    DOCS_DIR.mkdir(exist_ok=True)
    (DOCS_DIR / "index.html").write_text(report.build(table, lr, yv, gg, res, figs, args.demo, qc), encoding="utf-8")
    REPORTS_DIR.mkdir(exist_ok=True)
    table.to_csv(REPORTS_DIR / "headline_table.csv", index=False, float_format="%.2f")
    res["outlook"].to_csv(REPORTS_DIR / "outlook.csv", index=False, float_format="%.3f")
    res["test_rows"].to_csv(REPORTS_DIR / "backtest_test_period.csv", index=False, float_format="%.3f")
    summary = {
        "demo": args.demo, "latest": lr, "youth": yv, "gender": gg,
        "chosen_model": res["chosen_name"],
        "mae_test": res["mae_test"].round(3).to_dict(),
        "skill_vs_naive_pct": res["skill_vs_naive_pct"].round(1).to_dict(),
        "interval_coverage": res["coverage"].round(3).to_dict(),
    }
    (REPORTS_DIR / "results.json").write_text(json.dumps(summary, indent=2, default=str))

    o, sk = res["outlook"], res["skill_vs_naive_pct"]
    if (sk > 0).all():
        test_part = (f"in a rolling-origin backtest over {res['n_test_origins']} unseen months it cut forecast errors "
                     f"by {sk.min():.0f}-{sk.max():.0f}% versus a no-change benchmark")
    else:
        test_part = (f"benchmarked four models in a rolling-origin backtest over {res['n_test_origins']} unseen months "
                     f"and reported honestly where none beat a no-change forecast")
    cv = (f"**Irish Unemployment Outlook (Python, pandas, NumPy):** built an automated pipeline on CSO open data "
          f"(table {TABLE}, {lr['first_month']} to {lr['latest_month']}) that produces a statistical-release-style "
          f"report and a 3-month unemployment forecast; {test_part}, with empirical "
          f"{INTERVAL:.0%} prediction intervals checked for coverage.")
    (REPORTS_DIR / "summary.md").write_text(("> DEMO DATA - do not publish.\n\n" if args.demo else "") + cv + "\n")

    print("\n================ RESULTS ================" + ("  (DEMO DATA - NOT REAL)" if args.demo else ""))
    print(f"Latest rate ({lr['latest_month']}): {lr['latest_rate']:.1f}%   youth: {yv['youth_latest']:.1f}%")
    print(f"Chosen model: {res['chosen_name']}")
    print("Test error vs no-change (negative = worse):", ", ".join(f"{h}m {v:+.0f}%" for h, v in sk.items()))
    print("80% interval coverage on test:", ", ".join(f"{h}m {v:.0%}" for h, v in res["coverage"].items()))
    for _, r in o.iterrows():
        print(f"Forecast {r['month']:%b %Y}: {r['forecast']:.1f}%  ({r['lo']:.1f}-{r['hi']:.1f}%)")
    print(f"\nReport: {DOCS_DIR / 'index.html'}\nCV line: {REPORTS_DIR / 'summary.md'}")


if __name__ == "__main__":
    main()
