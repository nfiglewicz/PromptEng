import csv
import os
import sqlite3
from pathlib import Path
from typing import Dict, List

DATA_DIR = Path(__file__).resolve().parent
RAW_DIR = DATA_DIR / "raw"
DB_PATH = DATA_DIR / "gtfs.sqlite"


def detect_type(value: str) -> str:
    value = value.strip()
    if value == "":
        return "TEXT"
    try:
        int(value)
        return "INTEGER"
    except ValueError:
        pass
    try:
        float(value)
        return "REAL"
    except ValueError:
        pass
    return "TEXT"


def merge_types(type1: str, type2: str) -> str:
    # TEXT dominates, then REAL, then INTEGER
    order = ["INTEGER", "REAL", "TEXT"]
    return order[max(order.index(type1), order.index(type2))]


def infer_schema(csv_path: Path) -> Dict[str, str]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        header = [h.strip().strip("\ufeff") for h in header]

        # Initialize as TEXT by default
        types = {name: "TEXT" for name in header}

        for row in reader:
            if not row:
                continue
            for name, value in zip(header, row):
                t = detect_type(value)
                types[name] = merge_types(types[name], t)
    return types


def import_csv_to_table(conn: sqlite3.Connection, table_name: str, csv_path: Path):
    print(f"Importing {csv_path.name} into table {table_name}")
    schema = infer_schema(csv_path)
    cols_def = ", ".join(f'"{col}" {ctype}' for col, ctype in schema.items())

    cur = conn.cursor()
    cur.execute(f'DROP TABLE IF EXISTS "{table_name}"')
    cur.execute(f'CREATE TABLE "{table_name}" ({cols_def})')

    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    col_names = list(schema.keys())
    placeholders = ", ".join(["?"] * len(col_names))
    insert_sql = f'INSERT INTO "{table_name}" ({", ".join(col_names)}) VALUES ({placeholders})'

    for row in rows:
        values = [row.get(col, "").strip() for col in col_names]
        cur.execute(insert_sql, values)

    conn.commit()


def main():
    if not RAW_DIR.exists():
        raise SystemExit(f"Expected raw CSVs in {RAW_DIR}, but the folder does not exist.")

    conn = sqlite3.connect(DB_PATH.as_posix())

    mapping = {
        "trips.txt": "trips",
        "stops.txt": "stops",
        "stop_times.txt": "stop_times",
    }

    for csv_name, table_name in mapping.items():
        csv_path = RAW_DIR / csv_name
        if not csv_path.exists():
            print(f"WARNING: {csv_path} does not exist, skipping.")
            continue
        import_csv_to_table(conn, table_name, csv_path)

    conn.close()
    print(f"Database created at {DB_PATH}")


if __name__ == "__main__":
    main()
