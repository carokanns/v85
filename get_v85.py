#!/usr/bin/env python3
"""
Hämta V85-startlista från ATG och skriv vald avdelning (1-8) till CSV.

Regel för datum: välj den V85-omgång som kommer först från och med dagens datum.

Exempel:
  python3 get_v85_csv.py --avd 1
  python3 get_v85_csv.py --avd 3 --out ./csv/v86_20260226_3.csv
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import date, datetime
from pathlib import Path
from urllib.request import Request, urlopen

PRODUCT_URL = "https://www.atg.se/services/racinginfo/v1/api/products/V85"
GAME_URL_TEMPLATE = "https://www.atg.se/services/racinginfo/v1/api/games/{game_id}"


def fetch_json(url: str) -> dict:
    req = Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    with urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def parse_iso_dt(s: str) -> datetime:
    # API ger normalt "2026-02-21T16:10:00"
    return datetime.fromisoformat(s)


def game_date_str(game: dict, race: dict) -> str:
    # Använd i första hand vald avdelnings starttid för filnamn.
    race_start = race.get("startTime")
    if race_start:
        return parse_iso_dt(race_start).strftime("%Y%m%d")

    game_start = game.get("startTime")
    if game_start:
        return parse_iso_dt(game_start).strftime("%Y%m%d")

    return date.today().strftime("%Y%m%d")


def choose_game_from_today(upcoming: list[dict]) -> dict:
    today = date.today()
    candidates: list[tuple[datetime, dict]] = []

    for g in upcoming:
        start = g.get("startTime")
        if not start:
            continue
        dt = parse_iso_dt(start)
        if dt.date() >= today:
            candidates.append((dt, g))

    if not candidates:
        raise RuntimeError("Hittade ingen V85-omgång från och med idag.")

    candidates.sort(key=lambda x: x[0])
    return candidates[0][1]


def fmt_percent(v: int | None) -> str:
    if v is None:
        return ""
    return f"{v / 100:.2f}"


def fmt_odds(v: int | None) -> str:
    if v is None:
        return ""
    return f"{v / 100:.2f}"


def extract_rows(race: dict) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for s in race.get("starts", []):
        horse = s.get("horse", {})
        driver = s.get("driver", {})
        trainer = horse.get("trainer", {})
        pools = s.get("pools", {})

        rows.append(
            {
                "startnummer": str(s.get("number", "")),
                "hästnamn": horse.get("name", ""),
                "kusk": f"{driver.get('firstName', '')} {driver.get('lastName', '')}".strip(),
                "tränare": f"{trainer.get('firstName', '')} {trainer.get('lastName', '')}".strip(),
                "v85%": fmt_percent(pools.get("V85", {}).get("betDistribution")),
                "v-odds": fmt_odds(pools.get("vinnare", {}).get("odds")),
                "vagn": horse.get("sulky", {}).get("type", {}).get("text", ""),
            }
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Hämta V85 avdelning till CSV")
    parser.add_argument("--avd", type=int, required=True, help="Avdelning 1-8")
    parser.add_argument(
        "--out",
        type=str,
        default=None,
        help="Sökväg till CSV (default: ./csv/v86_<YYYYMMDD>_<avd>.csv)",
    )
    args = parser.parse_args()

    if not (1 <= args.avd <= 8):
        raise SystemExit("--avd måste vara mellan 1 och 8")

    products = fetch_json(PRODUCT_URL)
    upcoming = products.get("upcoming", [])
    if not upcoming:
        raise SystemExit("Inga kommande V85 hittades i API-svaret.")

    game = choose_game_from_today(upcoming)
    game_id = game["id"]
    game_data = fetch_json(GAME_URL_TEMPLATE.format(game_id=game_id))

    races = game_data.get("races", [])
    if len(races) < args.avd:
        raise SystemExit(f"Omgången har bara {len(races)} avdelningar i svaret.")

    race = races[args.avd - 1]
    rows = extract_rows(race)

    if args.out:
        out_path = Path(args.out).expanduser()
    else:
        game_date = game_date_str(game, race)
        out_path = Path(__file__).resolve().parent / "csv" / f"v86_{game_date}_{args.avd}.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = ["startnummer", "hästnamn", "kusk", "tränare", "v85%", "v-odds", "vagn"]
    with out_path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    print(f"Skrev {len(rows)} rader till: {out_path}")
    print(f"Omgång: {game_id}")
    print(f"Starttid (vald avdelning): {race.get('startTime')}")
    print(f"Bana/loppnummer: {race.get('track', {}).get('name', '')} / lopp {race.get('number')}")


if __name__ == "__main__":
    main()
