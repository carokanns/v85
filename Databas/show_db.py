#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


def format_rows(rows: list[sqlite3.Row]) -> str:
    if not rows:
        return "(inga rader)"

    cols = rows[0].keys()
    widths = {c: len(c) for c in cols}
    for r in rows:
        for c in cols:
            widths[c] = max(widths[c], len(str(r[c] if r[c] is not None else "")))

    sep = " | "
    header = sep.join(c.ljust(widths[c]) for c in cols)
    line = "-+-".join("-" * widths[c] for c in cols)
    body = "\n".join(sep.join(str(r[c] if r[c] is not None else "").ljust(widths[c]) for c in cols) for r in rows)
    return f"{header}\n{line}\n{body}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Visa innehåll i v85 SQLite-databas")
    parser.add_argument("--db", default=str(Path(__file__).resolve().parent / "v85.sqlite"), help="Sökväg till databasfil")
    parser.add_argument("--table", choices=["v85", "v85_history"], default="v85", help="Tabell att visa")
    parser.add_argument("--limit", type=int, default=20, help="Antal rader att visa")
    args = parser.parse_args()

    with sqlite3.connect(args.db) as con:
        con.row_factory = sqlite3.Row
        count = con.execute(f"SELECT COUNT(*) FROM {args.table}").fetchone()[0]
        rows = con.execute(f"SELECT * FROM {args.table} ORDER BY id DESC LIMIT ?", (args.limit,)).fetchall()

    print(f"DB: {args.db}")
    print(f"Tabell: {args.table}")
    print(f"Totalt antal rader: {count}")
    print(format_rows(rows))


if __name__ == "__main__":
    main()
