"""Project settings."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
REPORTS_DIR = ROOT / "reports"
FIG_DIR = REPORTS_DIR / "figures"
DOCS_DIR = ROOT / "docs"

# CSO table MUM01: Seasonally Adjusted Monthly Unemployment (from January 1998)
TABLE = "MUM01"
API_URL = ("https://ws.cso.ie/public/api.restful/"
           "PxStat.Data.Cube_API.ReadDataset/{table}/CSV/1.0/en")
RAW_FILE = RAW_DIR / f"{TABLE}.csv"

STAT_COUNT = "Seasonally Adjusted Monthly Unemployment"        # thousands
STAT_RATE = "Seasonally Adjusted Monthly Unemployment Rate"    # %

ALL_AGES = "15 - 74 years"
YOUTH = "15 - 24 years"
ADULT = "25 - 74 years"
BOTH = "Both sexes"

# Forecasting
HORIZON = 3                                  # months ahead
VALIDATION = ("2012-01-01", "2019-12-01")    # forecast origins used to choose the model
TEST_START = "2022-01-01"                    # forecast origins from here are the honest test
COVID = ("2020-03-01", "2021-12-01")         # shown on charts; excluded from model choice
MIN_TRAIN_MONTHS = 60                        # need 5 years of history before forecasting
INTERVAL = 0.80                              # prediction interval coverage
