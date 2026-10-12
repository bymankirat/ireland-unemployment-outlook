# Finish this project in 30 minutes

This one downloads its own data, so there are no manual downloads.

## 1. Run it (5 min)

Unzip the folder (double-click the zip). Then in Terminal:

```
cd ~/MSc_Thesis/THESIS_PAPER_DATA_PDF/03_Gut_Microbiota_Dysbiosis/ireland-unemployment-outlook
python run_pipeline.py
```

(If you unzipped it somewhere else, use `cd ` and drag the folder into Terminal.)

It prints the results and creates `docs/index.html`. Open it with:

```
open docs/index.html
```

Check: **no orange DEMO banner**, and the latest month is recent (e.g. September 2026).

If the download fails: go to data.cso.ie, search **MUM01**, download it as **CSV**, save it as
`data/raw/MUM01.csv`, and run `python run_pipeline.py` again.

## 2. Put it on GitHub (15 min)

1. On github.com: **+ → New repository**, name it exactly `ireland-unemployment-outlook`, **Public**, no README.
2. Click **uploading an existing file**. In **Chrome**, drag in the folders `docs`, `reports`, `src`
   (one at a time is fine) and the files `README.md`, `requirements.txt`, `run_pipeline.py`,
   `RUN_IN_30_MIN.md`. You don't need to upload `data`.
3. **Commit changes**.
4. **Settings → Pages → Deploy from a branch → main → /docs → Save**. Wait 3 minutes.
5. Your report is live at `https://bymankirat.github.io/ireland-unemployment-outlook/`.

## 3. CV and website (10 min)

- Your CV line is in `reports/summary.md` (`cat reports/summary.md`). Send it to Claude to add to your CV.
- Each month after the CSO publishes new figures, run `python run_pipeline.py --refresh` and upload
  the new `docs/index.html` to keep the report current. That is a great interview talking point.

## Interview talking points (CSO)

- **Why a no-change benchmark?** Seasonally adjusted rates move slowly; any model has to beat "no change" to be useful.
- **How did you avoid fooling yourself?** Rolling-origin backtest, model chosen on 2012-2019, judged once on 2022+.
- **Are your intervals honest?** I checked their coverage on the test years, not just their width.
- **How do you know the data is right?** Ten automatic quality checks run before any analysis and stop the run on a failure. One example: men plus women don't add exactly to the total, because the CSO seasonally adjusts each series separately, so that check warns instead of failing.
- **Limitations?** Revisions (I used revised data, not real-time vintages), COVID-19 period, one series only.
- **Next steps:** real-time vintages, adding claimant counts or job vacancy data as leading indicators.
