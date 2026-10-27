"""First look at the Capital Bikeshare data: timezone check + missing-station chart.

Run from the project folder (the one containing data/raw):
    python quick_look.py
Needs: pandas, matplotlib.  Writes PNGs and CSVs into ./figures
"""
import glob, os, re, zipfile
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Find data/raw whether run from the project root or from a subfolder like viz/
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = next((d for d in (os.getcwd(), HERE, os.path.dirname(HERE))
             if os.path.isdir(os.path.join(d, "data", "raw"))), None)
if ROOT is None:
    raise SystemExit("Can't find data/raw. cd to the project folder (the one containing data\\raw) and rerun.")
RAW = os.path.join(ROOT, "data", "raw")
OUT = os.path.join(ROOT, "figures")
os.makedirs(OUT, exist_ok=True)
COLS = ["started_at", "start_station_id", "end_station_id", "rideable_type"]

def blank_to_nan(s):
    s = s.astype("string").str.strip()
    return s.mask(s == "")

hour_rows, miss_rows = [], []
for path in sorted(glob.glob(os.path.join(RAW, "*.zip"))):
    month = re.search(r"(\d{6})", os.path.basename(path)).group(1)
    print("reading", path)
    with zipfile.ZipFile(path) as z:                         # skip macOS junk (__MACOSX/._*.csv)
        names = [n for n in z.namelist()
                 if n.lower().endswith(".csv") and "__MACOSX" not in n and not os.path.basename(n).startswith("._")]
        with z.open(names[0]) as f:
            df = pd.read_csv(f, usecols=COLS, dtype=str)
    for c in COLS:
        df[c] = blank_to_nan(df[c])
    ts = pd.to_datetime(df["started_at"], errors="coerce")   # parsed as supplied, no timezone change
    df["hour"] = ts.dt.hour
    df["date"] = ts.dt.date
    df["daytype"] = ts.dt.dayofweek.map(lambda d: "weekend" if d >= 5 else "weekday")

    # 1) trips per hour, averaged per calendar day, weekday vs weekend
    days = df.dropna(subset=["hour"]).groupby("daytype")["date"].nunique()
    h = df.dropna(subset=["hour"]).groupby(["daytype", "hour"]).size().rename("trips").reset_index()
    h["trips_per_day"] = h.apply(lambda r: r["trips"] / days[r["daytype"]], axis=1)
    h["month"] = month
    hour_rows.append(h)

    # 2) missing station IDs by bike type
    g = df.groupby(df["rideable_type"].fillna("unknown"))
    m = pd.DataFrame({"trips": g.size(),
                      "missing_start_pct": g["start_station_id"].apply(lambda s: 100 * s.isna().mean()),
                      "missing_end_pct": g["end_station_id"].apply(lambda s: 100 * s.isna().mean())}).reset_index()
    m["month"] = month
    miss_rows.append(m)

if not hour_rows:
    raise SystemExit(f"No .zip files found in {RAW}")
hours = pd.concat(hour_rows)
miss = pd.concat(miss_rows)
hours.to_csv(os.path.join(OUT, "trips_by_hour.csv"), index=False)
miss.to_csv(os.path.join(OUT, "missing_by_biketype.csv"), index=False)

# ---- timezone check: print and plot
fig, axes = plt.subplots(1, 2, figsize=(12, 4), sharey=False)
for ax, dt in zip(axes, ["weekday", "weekend"]):
    for month, g in hours[hours.daytype == dt].groupby("month"):
        ax.plot(g["hour"], g["trips_per_day"], marker="o", label=month)
    ax.set_title(f"Trips per {dt} day, by hour of started_at")
    ax.set_xlabel("Hour (as supplied in file)"); ax.set_ylabel("Trips per day")
    ax.set_xticks(range(0, 24, 2)); ax.grid(True); ax.legend()
plt.tight_layout(); plt.savefig(os.path.join(OUT, "trips_by_hour.png"), dpi=200); plt.close()

wk = hours[hours.daytype == "weekday"].groupby("hour")["trips_per_day"].sum()
print("\nTop 3 weekday hours (as supplied):", list(wk.sort_values(ascending=False).head(3).index))
print("Local time would peak around 8 and 17-18. A peak ~4-5 hours earlier/later than that suggests UTC.")

# ---- missing-station chart
agg = miss.groupby("rideable_type").apply(
    lambda g: pd.Series({"missing_start_pct": (g.missing_start_pct * g.trips).sum() / g.trips.sum(),
                         "missing_end_pct": (g.missing_end_pct * g.trips).sum() / g.trips.sum(),
                         "trips": g.trips.sum()}), include_groups=False).reset_index()
print("\n", agg.to_string(index=False))
ax = agg.set_index("rideable_type")[["missing_start_pct", "missing_end_pct"]].plot.bar(figsize=(8, 4))
ax.set_ylabel("% of trips with no station ID"); ax.set_xlabel("Bike type"); ax.grid(True, axis="y")
ax.set_title("Missing station IDs by bike type (all months)")
plt.xticks(rotation=0); plt.tight_layout(); plt.savefig(os.path.join(OUT, "missing_by_biketype.png"), dpi=200)
print(f"\nWrote {OUT} with trips_by_hour.png, missing_by_biketype.png and two CSVs")
