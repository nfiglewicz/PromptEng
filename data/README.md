# Data folder

* `raw/` – place the original `trips.csv`, `stops.csv`, and `stop_times.csv` from the Wrocław public transport open data zip here.
* `import_gtfs.py` – script that infers schema from CSVs and creates `gtfs.sqlite`.
* `sample_*.csv` – tiny sample files for local smoke tests (not real data).
* `gtfs.sqlite` – generated SQLite database (not tracked in source control).
