# Wrocław Public Transport Route Finder

This project implements a small full‑stack application for exploring Wrocław public transport departures.

## Features

* Backend in **Python + Flask** with **SQLite** database
* REST API:
  * `GET /public_transport/city/{city}/closest_departures`
  * `GET /public_transport/city/{city}/trip/{trip_id}`
* Frontend in plain **HTML/CSS/JavaScript** using **Leaflet** for maps
* Basic **unit tests**:
  * Backend tests using `pytest`
  * Frontend tests using **Jasmine**

## Quick Start

### 1. Create and populate SQLite database

1. Download the official Wrocław GTFS style dataset (zip) from the open data portal.
2. Extract at least these CSV files into `data/raw/` (create the folder if it does not exist):
   * `trips.csv`
   * `stops.csv`
   * `stop_times.csv`
3. From the project root run:

   ```bash
   cd backend
   python ../data/import_gtfs.py
   ```

   This will create `data/gtfs.sqlite` with inferred schema for those three tables.

You can also use the small sample CSVs in `data/sample_*.csv` if you just want to smoke‑test the app.

### 2. Run the backend

From the `backend` folder:

```bash
pip install -r requirements.txt
export FLASK_APP=app.py
export FLASK_ENV=development
# Optionally point to a different DB file:
# export GTFS_DB_PATH=../data/gtfs.sqlite
flask run
```

The API will listen on `http://127.0.0.1:5000`.

### 3. Open the frontend

Simply open `frontend/index.html` in a browser, or serve the `frontend` folder via a simple HTTP server:

```bash
cd frontend
python -m http.server 8000
```

Then go to `http://127.0.0.1:8000` in a browser.

## Backend tests

```bash
cd backend
pip install -r requirements.txt
pytest
```

## Frontend tests

Open `frontend/tests/SpecRunner.html` in your browser. It will load Jasmine from CDN and run the specs defined in `frontend/tests/frontendSpec.js`.

## Notes

* Distance filtering is based on a Haversine formula implementation in Python.
* Direction filtering for `closest_departures` is approximate: a departure is considered "towards" the destination if the next stop of that trip is closer to the destination than the current stop.
* Times in GTFS CSV files (`HH:MM:SS`) are converted to ISO 8601 using the date component from `start_time`.

