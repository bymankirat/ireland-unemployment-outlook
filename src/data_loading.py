"""Download and tidy CSO table MUM01."""

from __future__ import annotations

import urllib.request
from pathlib import Path

import pandas as pd

from config import API_URL, RAW_FILE, STAT_COUNT, STAT_RATE, TABLE


def download(force: bool = False) -> Path:
    """Fetch MUM01 as CSV from the CSO's open data API (PxStat)."""
    if RAW_FILE.exists() and not force:
        return RAW_FILE
    RAW_FILE.parent.mkdir(parents=True, exist_ok=True)
    url = API_URL.format(table=TABLE)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=90) as r:
            data = r.read()
    except Exception:  # noqa: BLE001  (e.g. missing SSL certificates in some Python installs)
        import subprocess
        data = subprocess.run(["curl", "-sSL", "--max-time", "120", url],
                              capture_output=True, check=True).stdout
    if b"STATISTIC" not in data[:500]:
        raise ValueError("The CSO API returned something unexpected (no STATISTIC header).")
    RAW_FILE.write_bytes(data)
    return RAW_FILE


def load(path: Path | None = None) -> pd.DataFrame:
    """Tidy long table: date, statistic, age, sex, value."""
    path = Path(path) if path else RAW_FILE
    raw = pd.read_csv(path, dtype=str, encoding="utf-8-sig")
    raw.columns = [c.strip().strip('"') for c in raw.columns]

    month_col = next(c for c in raw.columns if c.upper().startswith("TLIST"))
    out = pd.DataFrame({
        "date": pd.to_datetime(raw[month_col].str.strip(), format="%Y%m", errors="coerce"),
        "statistic": raw["Statistic Label"].str.strip(),
        "age": raw["Age Group"].str.strip(),
        "sex": raw["Sex"].str.strip(),
        "value": pd.to_numeric(raw["VALUE"].str.strip(), errors="coerce"),
    }).dropna(subset=["date"])

    missing = {STAT_COUNT, STAT_RATE} - set(out["statistic"].unique())
    if missing:
        raise ValueError(f"MUM01 file is missing statistics: {missing}")
    return out.sort_values("date").reset_index(drop=True)


def series(df: pd.DataFrame, statistic: str, age: str, sex: str) -> pd.Series:
    s = df[(df["statistic"] == statistic) & (df["age"] == age) & (df["sex"] == sex)]
    s = s.set_index("date")["value"].sort_index()
    s.index.freq = None
    return s.asfreq("MS")
