# Capital Bikeshare summer 2026 initial inspection

Downloaded October 27, 2026 from https://capitalbikeshare.com/system-data and its linked public archive. Original ZIP files are preserved in data/raw. Source URLs, file sizes, SHA-256 hashes, and download timestamps are in data/source_manifest.json.

## Results

| Month | Trips | Missing start station IDs | Missing end station IDs | Duplicate ride ID excess rows |
|---|---:|---:|---:|---:|
| June 2026 | 655,744 | 94,394 (14.39%) | 99,597 (15.19%) | 0 |
| July 2026 | 653,671 | 94,235 (14.42%) | 98,978 (15.14%) | 0 |
| August 2026 | 646,082 | 87,607 (13.56%) | 91,949 (14.23%) | 0 |

Total: **1,955,497 trip records**. All three files have the same 13 columns in the same order. No records have been changed or removed.

## Important findings

- No missing ride IDs, duplicate ride IDs within or across months, exact duplicate rows, unparseable timestamps, or trips ending before they started were found.
- Missing station IDs affect roughly 14% of departure endpoints and 15% of arrival endpoints. Do not assume these are lost bikes. A valid endpoint may still support one side of the flow analysis. Report missing endpoint coverage alongside station rankings.
- Five station IDs have multiple names. Review reports/station_id_name_inventory.csv before selecting display labels. IDs are preserved as text; labels have not been merged.
- Files appear grouped by trip end month: all observed end dates fall within the named month, while 117 June-file trips, 69 July-file trips, and 163 August-file trips started in the preceding month. This is an observed pattern, not a confirmed publisher guarantee.
- For a strict June 1 through August 31 event window, filter departures by started_at and arrivals by ended_at independently. Exclude May departures without discarding their June arrivals. Inspect September for trips departing in August and ending in September before claiming complete August departure coverage. September has not been downloaded.
- There are 49,592 trips shorter than 60 seconds and 1,329 longer than 24 hours. Flag these for review rather than automatically deleting them. The system-data webpage describes filtering short trips, but the downloaded files contain them.
- Start coordinates are complete. There are 1,296 records missing at least one end coordinate. No nonblank coordinate failed numeric or global latitude/longitude bounds checks. This does not establish geographic plausibility or accurate station locations.
- Timestamps were parsed as supplied, without timezone conversion. Confirm the publisher's timezone convention before interpreting hourly profiles.

## Calendar

June has 22 weekdays and 8 weekend days; July has 23 and 8; August has 21 and 10. Across summer there are 66 weekdays and 26 weekend days. Average over all eligible calendar days, including zero-trip days; station openings and closures need separate consideration.

reports/study_calendar.csv flags June 19, July 3 (observed Independence Day), and July 4. Holidays retain their calendar weekday/weekend category for a separate sensitivity comparison. Federal holiday source: https://www.archives.gov/news/federal-holidays

## Reproduce the inspection

Install Python and pandas. The inspection was run with pandas 3.0.1. Run these from this project folder:

```text
pip install -r requirements.txt
python src/download_data.py
python src/inspect_data.py
```

The downloader retrieves missing archives. The inspection reads ZIPs directly without extraction and regenerates the reports. Allow several minutes and enough memory for one monthly file. The notebook in notebooks offers a walkthrough; Jupyter is optional and can be installed separately with pip install jupyterlab.

Blank means empty or whitespace-only. Duplicate excess rows means repeated nonblank ride IDs beyond the first. Exact duplicates compare all original fields. Missing percentages use the corresponding monthly file's entire row count. Coordinates are checked against latitude [-90,90] and longitude [-180,180]. Sample trips are the first 10 records per file, not a representative sample.

## Team handoff

Brett: agree on missing endpoint handling and review the five station-name conflicts. Devang: address the monthly boundary and use calendar denominators before computing hourly flow. Camden: use schemas.json and sample_trips.csv to plan charts.

No final cleaning rules, station rankings, or combined analysis dataset have been produced. No remote repository has been created. The included .gitignore excludes raw ZIP archives from a future shared repository.
