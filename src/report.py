"""One self-contained web page, written like a monthly statistical release."""

from __future__ import annotations

import base64
import html
from pathlib import Path

import pandas as pd

from config import HORIZON, INTERVAL, TABLE, VALIDATION
from forecasting import MODEL_NAMES

AUTHOR = "Mankirat Singh"
LINKS = {"Portfolio": "https://bymankirat.github.io/myportfolio/",
         "GitHub": "https://github.com/bymankirat",
         "LinkedIn": "https://linkedin.com/in/mankirat-singh-694440177"}


def _img(p, alt):
    return f'<img src="data:image/png;base64,{base64.b64encode(Path(p).read_bytes()).decode()}" alt="{html.escape(alt)}">'


def _pp(x, signed=True):
    if x is None or pd.isna(x):
        return "–"
    if signed and abs(x) < 0.05:
        return "0.0"
    return f"{x:+.1f}" if signed else f"{x:.1f}"


def _move(x):
    if x is None or pd.isna(x) or abs(x) < 0.05:
        return "unchanged"
    return f"{'up' if x > 0 else 'down'} {abs(x):.1f} pp"


def _vs_naive(skill: pd.Series) -> str:
    parts = []
    for h, v in skill.items():
        when = f"{h} month{'s' if h > 1 else ''} ahead"
        parts.append(f"{abs(v):.0f}% {'smaller' if v > 0 else 'larger'} {when}" if abs(v) >= 0.5 else f"about the same {when}")
    return ", ".join(parts[:-1]) + " and " + parts[-1] if len(parts) > 1 else parts[0]


def build(table: pd.DataFrame, lr: dict, yv: dict, gg: dict, res: dict, figs: dict, demo: bool, qc: dict) -> str:
    head = table[(table["Age group"] == "15 - 74 years") & (table["Sex"] == "Both sexes")].iloc[0]
    o = res["outlook"]
    skill = res["skill_vs_naive_pct"]
    cov = res["coverage"]
    beat_all = bool((skill > 0).all())

    if beat_all:
        skill_text = (f"On {res['n_test_origins']} monthly forecasts made from {res['test_first']:%B %Y} onwards, "
                      f"the chosen model's errors were {skill.min():.0f}-{skill.max():.0f}% smaller than "
                      f"simply assuming no change.")
    else:
        skill_text = (f"On {res['n_test_origins']} monthly forecasts made from {res['test_first']:%B %Y} onwards, "
                      f"the chosen model did <b>not</b> consistently beat simply assuming no change: its average "
                      f"error was {_vs_naive(skill)}. "
                      f"That is a real finding: month to month, the seasonally adjusted rate moves very little, "
                      f"so \"no change\" is a hard benchmark to beat.")

    findings = [
        f"The seasonally adjusted unemployment rate was <b>{lr['latest_rate']:.1f}%</b> in {lr['latest_month']}, "
        f"{_move(head['Change on month (pp)'])} on the month and {_move(head['Change on year (pp)'])} on the year, "
        f"with about <b>{lr['latest_count']:.0f},000</b> people unemployed.",
        f"This compares with a peak of {lr['peak_rate']:.1f}% in {lr['peak_month']} "
        f"and a low of {lr['low_rate_since_2015']:.1f}% in {lr['low_month_since_2015']}.",
        f"Young people (15-24) had a rate of {yv['youth_latest']:.1f}%, "
        f"<b>{yv['ratio_latest']:.1f} times</b> the rate for those aged 25-74 ({yv['adult_latest']:.1f}%).",
        f"The rate for men ({gg['male_latest']:.1f}%) was {abs(gg['gap_latest']):.1f} pp "
        f"{'above' if gg['gap_latest'] >= 0 else 'below'} the rate for women ({gg['female_latest']:.1f}%).",
        f"<b>Outlook:</b> the unemployment rate is forecast at {o['forecast'].iloc[-1]:.1f}% in "
        f"{o['month'].iloc[-1]:%B %Y} ({INTERVAL:.0%} interval {o['lo'].iloc[-1]:.1f}-{o['hi'].iloc[-1]:.1f}%).",
    ]

    t_rows = "".join(
        f"<tr><td>{r['Age group']}</td><td>{r['Sex']}</td><td class='num'>{r['Rate (%)']:.1f}</td>"
        f"<td class='num'>{_pp(r['Unemployed (thousands)'], signed=False)}</td>"
        f"<td class='num'>{_pp(r['Change on month (pp)'])}</td><td class='num'>{_pp(r['Change on year (pp)'])}</td></tr>"
        for _, r in table.iterrows()
    )
    o_rows = "".join(
        f"<tr><td>{m:%B %Y}</td><td class='num'>{f:.1f}</td><td class='num'>{lo:.1f} – {hi:.1f}</td></tr>"
        for m, f, lo, hi in zip(o["month"], o["forecast"], o["lo"], o["hi"])
    )
    mt, mv = res["mae_test"], res["mae_validation"]
    hs = list(mt.columns)
    acc_head = "".join(f"<th class='num'>{h} month{'s' if h > 1 else ''}</th>" for h in hs)
    acc_rows = "".join(
        f"<tr{' class=chosen' if k == res['chosen'] else ''}><td>{MODEL_NAMES[k]}"
        f"{' <b>(chosen)</b>' if k == res['chosen'] else ''}</td>"
        + "".join(f"<td class='num'>{mt.loc[k, h]:.2f}</td>" for h in hs) + "</tr>"
        for k in ["naive", "drift", "ar", "damped"]
    )
    cov_text = ", ".join(f"{cov[h]:.0%} at {h} month{'s' if h > 1 else ''}" for h in hs)

    qc_rows = "".join(f"<tr><td class='qc-{st.lower()}'>{st}</td><td>{html.escape(c)}</td><td>{html.escape(d)}</td></tr>"
                      for st, c, d in qc["results"])

    avg5 = gg["gap_avg_last_5y"]
    if abs(avg5) < 0.15:
        recent = "men's and women's rates have been almost the same, on average, over the last five years"
    elif avg5 > 0:
        recent = f"men's rate has averaged {avg5:.1f} pp above women's over the last five years"
    else:
        recent = f"women's rate has averaged {abs(avg5):.1f} pp above men's over the last five years"
    now = (f"Today women's rate is {abs(gg['gap_latest']):.1f} pp higher." if gg["gap_latest"] < -0.05 else
           f"Today men's rate is {gg['gap_latest']:.1f} pp higher." if gg["gap_latest"] > 0.05 else
           "Today the two rates are equal.")
    gender_text = (f"The gap between men and women was widest in {gg['gap_widest_month']} ({gg['gap_widest']:.1f} pp higher "
                   f"for men), during the downturn that hit male-dominated sectors such as construction hardest. It has "
                   f"since closed: {recent}. {now}")

    banner = ('<div class="banner">DEMO DATA: simulated numbers for testing. '
              "Run without --demo to download the real CSO data before publishing.</div>") if demo else ""
    links = " · ".join(f'<a href="{u}">{k}</a>' for k, u in LINKS.items())

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Irish Unemployment Outlook</title>
<style>
:root{{--bg:#fcfcfb;--card:#fff;--ink:#0b0b0b;--ink-2:#52514e;--line:#e4e3df;--accent:#2a78d6;--hl:#eef4fc;--warn-bg:#fff4e5;--warn-ink:#7a3d00}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--bg:#1a1a19;--card:#232322;--ink:#f0efec;--ink-2:#c3c2b7;--line:#3a3a38;--accent:#3987e5;--hl:#1f2a3a;--warn-bg:#3a2a12;--warn-ink:#ffd08a}}:root:not([data-theme="light"]) img{{background:#fcfcfb}}}}
:root[data-theme="dark"]{{--bg:#1a1a19;--card:#232322;--ink:#f0efec;--ink-2:#c3c2b7;--line:#3a3a38;--accent:#3987e5;--hl:#1f2a3a;--warn-bg:#3a2a12;--warn-ink:#ffd08a}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}}
main{{max-width:900px;margin:0 auto;padding:40px 16px 64px}}
.kicker{{color:var(--accent);font-weight:700;letter-spacing:.04em;text-transform:uppercase;font-size:.82rem}}
h1{{font-size:clamp(1.6rem,4vw,2.3rem);line-height:1.2;margin:6px 0 8px}}h2{{font-size:1.3rem;margin:44px 0 8px}}
.byline,.muted{{color:var(--ink-2)}}a{{color:var(--accent)}}
.banner{{background:var(--warn-bg);color:var(--warn-ink);padding:12px 16px;border-radius:8px;font-weight:600;margin:16px 0}}
.note{{border-left:3px solid var(--accent);padding:6px 12px;color:var(--ink-2);font-size:.92rem;margin:14px 0}}
.findings{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px 20px 16px 36px;margin:20px 0}}
.findings li{{margin:6px 0}}
img{{width:100%;height:auto;border:1px solid var(--line);border-radius:8px;margin:12px 0}}
.table-wrap{{overflow-x:auto}}table{{border-collapse:collapse;width:100%;margin:12px 0;font-size:.94rem}}
th,td{{text-align:left;padding:7px 10px;border-bottom:1px solid var(--line)}}th{{color:var(--ink-2);font-weight:600}}
.num{{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}}tr.chosen{{background:var(--hl)}}
td.qc-pass{{color:#008300;font-weight:700}}td.qc-warn{{color:#b06f00;font-weight:700}}td.qc-fail{{color:#e34948;font-weight:700}}
footer{{margin-top:52px;padding-top:16px;border-top:1px solid var(--line);color:var(--ink-2);font-size:.9rem}}
</style></head><body><main>
{banner}
<div class="kicker">Independent analysis of CSO data</div>
<h1>Irish Unemployment, {lr['latest_month']}: Trends and a {HORIZON}-Month Outlook</h1>
<p class="byline">{AUTHOR} · {links}</p>
<p class="note">This is an independent analysis using open data from the Central Statistics Office (table {TABLE}).
It is not an official CSO publication.</p>

<h2>Key findings</h2>
<ul class="findings">{''.join(f'<li>{f}</li>' for f in findings)}</ul>

<h2>1. The latest picture</h2>
<div class="table-wrap"><table>
<thead><tr><th>Age group</th><th>Sex</th><th class="num">Rate (%)</th><th class="num">Unemployed (000s)</th>
<th class="num">Change on month (pp)</th><th class="num">Change on year (pp)</th></tr></thead>
<tbody>{t_rows}</tbody></table></div>
<p class="muted">Seasonally adjusted, {lr['latest_month']}. pp = percentage points.</p>

<h2>2. The long view</h2>
<p>Since {lr['first_month']} the rate has ranged from {lr['low_rate_all']:.1f}% ({lr['low_month_all']}) to {lr['peak_rate']:.1f}% ({lr['peak_month']}).
The average over the last 12 months was {lr['avg_last_12m']:.1f}%, against {lr['avg_prev_12m']:.1f}% in the 12 months before.</p>
{_img(figs['long'], 'Unemployment rate since 1998')}

<h2>3. Young people</h2>
<p>Youth unemployment is consistently higher. Today's ratio of {yv['ratio_latest']:.1f} compares with an average of
{yv['ratio_avg']:.1f} since 1998.</p>
{_img(figs['youth'], 'Unemployment rate by age group')}

<h2>4. Men and women</h2>
<p>{gender_text}</p>
{_img(figs['gender'], 'Gender gap in unemployment rates')}

<h2>5. Outlook for the next {HORIZON} months</h2>
<div class="table-wrap"><table><thead><tr><th>Month</th><th class="num">Forecast rate (%)</th>
<th class="num">{INTERVAL:.0%} interval (%)</th></tr></thead><tbody>{o_rows}</tbody></table></div>
{_img(figs['outlook'], 'Three-month forecast')}
<p class="muted">Model: {res['chosen_name']}. These months have not been published yet, so the forecast can be checked
against the CSO's releases as they come out.</p>

<h2>6. How good are these forecasts?</h2>
<p>Four simple, transparent models were compared. Every month from {VALIDATION[0][:4]}, each model was fitted only on the data
available at that time and asked to forecast the next {HORIZON} months. The model was chosen on {VALIDATION[0][:4]}-{VALIDATION[1][:4]}
({res['n_val_origins']} forecast dates, excluding the COVID-19 period) and then judged once on later years it never saw.</p>
<p>{skill_text}</p>
{_img(figs['accuracy'], 'Forecast accuracy by model')}
<div class="table-wrap"><table><thead><tr><th>Mean absolute error, test period (pp)</th>{acc_head}</tr></thead>
<tbody>{acc_rows}</tbody></table></div>
<p>The {INTERVAL:.0%} intervals were built from the model's own past errors. On the test period they contained the outcome
{cov_text}, against the {INTERVAL:.0%} claimed{'; they are slightly too narrow, so treat them as a minimum range' if (cov < INTERVAL - 0.05).any() else ''}.</p>

<h2>7. Quality checks</h2>
<p>Before any analysis, the pipeline runs automatic checks on the downloaded data and stops if any check fails.
Result: <b>{qc['summary']}</b>.</p>
<div class="table-wrap"><table><thead><tr><th>Status</th><th>Check</th><th>Detail</th></tr></thead>
<tbody>{qc_rows}</tbody></table></div>

<h2>Background notes</h2>
<ul>
<li><b>Source:</b> CSO table {TABLE}, Seasonally Adjusted Monthly Unemployment, downloaded through the CSO's open data API (PxStat).
Rates are for ages 15-74 unless stated.</li>
<li><b>Seasonal adjustment</b> is carried out by the CSO; no further adjustment was applied.</li>
<li><b>Revisions:</b> the CSO revises recent months as new Labour Force Survey results arrive. The backtest uses today's
revised figures, not the figures available at the time, so real-time accuracy would be somewhat lower.</li>
<li><b>COVID-19:</b> from March 2020 the CSO also published COVID-adjusted measures. This analysis uses the standard series
and excludes the pandemic months from model selection.</li>
<li><b>Methods:</b> Python (pandas, NumPy), matplotlib. Models: no-change, 12-month drift, AR(2) on monthly changes,
and damped-trend exponential smoothing with parameters chosen by least squares. Code:
<a href="https://github.com/bymankirat/ireland-unemployment-outlook">GitHub</a>.</li>
</ul>
<footer>Contains CSO data, licensed under CC BY 4.0. Analysis and any errors are the author's own.</footer>
</main></body></html>
"""
