#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import re
import sqlite3
from pathlib import Path

CURRENT_RE = re.compile(r"^v85_(\d{8})_([1-8])\.csv$")
HISTORY_RE = re.compile(r"^v85_history_(\d{8})_([1-8])\.csv$")


def yyyymmdd_to_iso(d: str) -> str:
    return f"{d[0:4]}-{d[4:6]}-{d[6:8]}"


def load_current(con: sqlite3.Connection, csv_dir: Path) -> tuple[int, int]:
    files = sorted(p for p in csv_dir.iterdir() if p.is_file() and CURRENT_RE.match(p.name))
    imported_rows = 0

    for p in files:
        m = CURRENT_RE.match(p.name)
        assert m
        game_date = yyyymmdd_to_iso(m.group(1))
        avd = m.group(2)
        legacy_name = p.name.replace("v85_", "v86_", 1)

        with p.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        con.execute("DELETE FROM v85 WHERE source_file IN (?, ?)", (p.name, legacy_name))

        for r in rows:
            con.execute(
                """
                INSERT INTO v85 (
                  datum, avd, startnummer, hastnamn, kusk, tranare,
                  v85_procent, v_odds, vagn, source_file
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(datum, avd, hastnamn) DO UPDATE SET
                  startnummer=excluded.startnummer,
                  kusk=excluded.kusk,
                  tranare=excluded.tranare,
                  v85_procent=excluded.v85_procent,
                  v_odds=excluded.v_odds,
                  vagn=excluded.vagn,
                  source_file=excluded.source_file
                """,
                (
                    game_date,
                    avd,
                    (r.get("startnummer") or "").strip(),
                    (r.get("hästnamn") or "").strip(),
                    (r.get("kusk") or "").strip(),
                    (r.get("tränare") or "").strip(),
                    (r.get("v85%") or "").strip(),
                    (r.get("v-odds") or "").strip(),
                    (r.get("vagn") or "").strip(),
                    p.name,
                ),
            )
            imported_rows += 1

    return len(files), imported_rows


def load_history(con: sqlite3.Connection, csv_dir: Path) -> tuple[int, int]:
    files = sorted(p for p in csv_dir.iterdir() if p.is_file() and HISTORY_RE.match(p.name))
    imported_rows = 0

    for p in files:
        m = HISTORY_RE.match(p.name)
        assert m
        avd = m.group(2)
        legacy_name = p.name.replace("v85_history_", "v86_history_", 1)

        with p.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        con.execute("DELETE FROM v85_history WHERE source_file IN (?, ?)", (p.name, legacy_name))

        for r in rows:
            con.execute(
                """
                INSERT INTO v85_history (
                  datum, avd, hastnamn, bana, kusk, placering,
                  distans_spor, km_tid, skor, odds, pris, vagn, source_file
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    (r.get("datum") or "").strip(),
                    avd,
                    (r.get("hästnamn") or "").strip(),
                    (r.get("bana") or "").strip(),
                    (r.get("kusk") or "").strip(),
                    str(r.get("placering") or "").strip(),
                    (r.get("distans:spår") or "").strip(),
                    (r.get("KM-tid") or "").strip(),
                    (r.get("skor") or "").strip(),
                    str(r.get("odds") or "").strip(),
                    str(r.get("pris") or "").strip(),
                    (r.get("vagn") or "").strip(),
                    p.name,
                ),
            )
            imported_rows += 1

    return len(files), imported_rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Importera v85 CSV-filer till SQLite")
    parser.add_argument("--db", default=str(Path(__file__).resolve().parent / "v85.sqlite"), help="Sökväg till SQLite")
    parser.add_argument("--csv-dir", default=str(Path(__file__).resolve().parent.parent / "csv"), help="Mapp med CSV-filer")
    parser.add_argument("-s", "--skip-history", action="store_true", dest="skip_history", help="Hoppa över import av historikfiler")
    args = parser.parse_args()

    db_path = Path(args.db).expanduser().resolve()
    csv_dir = Path(args.csv_dir).expanduser().resolve()

    with sqlite3.connect(db_path) as con:
        cur_files, cur_rows = load_current(con, csv_dir)
        hist_files = hist_rows = 0
        if not args.skip_history:
            hist_files, hist_rows = load_history(con, csv_dir)
        con.commit()

    print(f"DB: {db_path}")
    print(f"CSV-katalog: {csv_dir}")
    print(f"Importerade current-filer: {cur_files}, rader: {cur_rows}")
    print(f"Importerade history-filer: {hist_files}, rader: {hist_rows}")


if __name__ == "__main__":
    main()
