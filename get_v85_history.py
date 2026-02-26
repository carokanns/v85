#!/usr/bin/env python3
"""
Hämtar historik för alla hästar i valfri V85-avdelning (1-8)
och sparar till CSV.

Väljer automatiskt den V85-omgång som kommer först från och med dagens datum.

Exempel:
  python3 get_v85_history_csv.py --avd 1
  python3 get_v85_history_csv.py --avd 3 --out ./csv/v86_history_20260226_143000.csv
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import date, datetime
from pathlib import Path
from urllib.request import Request, urlopen

PRODUCT_URL = "https://www.atg.se/services/racinginfo/v1/api/products/V85"
GAME_URL = "https://www.atg.se/services/racinginfo/v1/api/games/{game_id}"
HORSE_RESULTS_URL = "https://www.atg.se/services/racinginfo/v1/api/horses/{horse_id}/results"
DEFAULT_MAX_HISTORY_PER_HORSE = 5


def fetch_json(url: str) -> dict:
    req = Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    with urlopen(req, timeout=25) as resp:
        return json.loads(resp.read().decode("utf-8"))


def choose_game_from_today(upcoming: list[dict]) -> dict:
    today = date.today()
    candidates: list[tuple[datetime, dict]] = []

    for item in upcoming:
        start = item.get("startTime")
        if not start:
            continue
        dt = datetime.fromisoformat(start)
        if dt.date() >= today:
            candidates.append((dt, item))

    if not candidates:
        if not upcoming:
            raise RuntimeError("Ingen V85-omgång hittades i API-svaret.")
        return upcoming[0]

    candidates.sort(key=lambda x: x[0])
    return candidates[0][1]


def fmt_km_time(km: dict | None) -> str:
    if not km:
        return ""
    m = km.get("minutes", 0)
    s = km.get("seconds", 0)
    t = km.get("tenths", 0)
    return f"{m}:{s:02d},{t}"


def fmt_dist_spor(start: dict | None) -> str:
    if not start:
        return ""
    dist = start.get("distance")
    pos = start.get("postPosition")
    if dist is None and pos is None:
        return ""
    if dist is None:
        return str(pos)
    if pos is None:
        return str(dist)
    return f"{dist}:{pos}"


def fmt_driver(start: dict | None) -> str:
    d = (start or {}).get("driver") or {}
    return f"{d.get('firstName', '')} {d.get('lastName', '')}".strip()


def fmt_shoes(start: dict | None) -> str:
    shoes = (((start or {}).get("horse") or {}).get("shoes")) or {}
    front = shoes.get("front")
    back = shoes.get("back")

    if front is None or back is None:
        return ""
    if front and back:
        return "Skor runt om"
    if (not front) and (not back):
        return "Barfota runt om"
    if (not front) and back:
        return "Barfota fram"
    if front and (not back):
        return "Barfota bak"
    return ""


def fmt_vagn(start: dict | None) -> str:
    return ((((start or {}).get("horse") or {}).get("sulky") or {}).get("type") or {}).get("text", "")


def fmt_odds(odds: int | None) -> str:
    if odds is None:
        return ""
    return f"{odds / 100:.2f}"


def fmt_pris(first_prize: int | None) -> str:
    if first_prize is None:
        return ""
    # ATG API brukar ge ören
    return str(int(round(first_prize / 100)))


def collect_history_rows(race: dict, max_history_per_horse: int = DEFAULT_MAX_HISTORY_PER_HORSE) -> list[dict[str, str]]:
    by_horse: dict[str, list[dict[str, str]]] = {}

    for start in race.get("starts", []):
        horse = start.get("horse") or {}
        horse_name = (horse.get("name") or "").strip()
        horse_id = horse.get("id")
        if not horse_id:
            continue
        if not horse_name:
            # Fallback så kolumnen aldrig blir tom
            horse_name = f"horse_{horse_id}"

        results = fetch_json(HORSE_RESULTS_URL.format(horse_id=horse_id))
        horse_rows: list[dict[str, str]] = []

        for rec in results.get("records", []):
            rec_start = rec.get("start") or {}
            rec_race = rec.get("race") or {}
            rec_track = rec.get("track") or {}

            horse_rows.append(
                {
                    "hästnamn": horse_name,
                    "datum": rec.get("date", ""),
                    "bana": rec_track.get("name", ""),
                    "kusk": fmt_driver(rec_start),
                    "placering": rec.get("place", ""),
                    "distans:spår": fmt_dist_spor(rec_start),
                    "KM-tid": fmt_km_time(rec.get("kmTime")),
                    "skor": fmt_shoes(rec_start),
                    "odds": fmt_odds(rec.get("odds")),
                    "pris": fmt_pris(rec_race.get("firstPrize")),
                    "vagn": fmt_vagn(rec_start),
                }
            )

        # Nyast först per häst, behåll max N
        horse_rows.sort(key=lambda r: r["datum"], reverse=True)
        by_horse[horse_name] = horse_rows[:max_history_per_horse]

    rows: list[dict[str, str]] = []
    for horse_name in sorted(by_horse.keys()):
        rows.extend(by_horse[horse_name])

    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Hämta V85-historik till CSV")
    parser.add_argument("--avd", type=int, required=True, help="Avdelning 1-8")
    parser.add_argument(
        "--out",
        type=str,
        default=None,
        help="Outputfil (default: ./csv/v86_history_<YYYYMMDD_HHMMSS>.csv)",
    )
    parser.add_argument(
        "--max-history",
        type=int,
        default=DEFAULT_MAX_HISTORY_PER_HORSE,
        help=f"Max antal historikrader per häst (default: {DEFAULT_MAX_HISTORY_PER_HORSE})",
    )
    args = parser.parse_args()

    if not (1 <= args.avd <= 8):
        raise SystemExit("--avd måste vara mellan 1 och 8")
    if args.max_history < 1:
        raise SystemExit("--max-history måste vara minst 1")

    products = fetch_json(PRODUCT_URL)
    upcoming = products.get("upcoming", [])
    game = choose_game_from_today(upcoming)
    game_id = game["id"]

    game_data = fetch_json(GAME_URL.format(game_id=game_id))
    races = game_data.get("races", [])

    if len(races) < args.avd:
        raise SystemExit(f"Hittade bara {len(races)} avdelningar i omgången.")

    race = races[args.avd - 1]
    rows = collect_history_rows(race, max_history_per_horse=args.max_history)

    if args.out:
        out_path = Path(args.out).expanduser()
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = Path(__file__).resolve().parent / "csv" / f"v86_history_{timestamp}.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "hästnamn",
        "datum",
        "bana",
        "kusk",
        "placering",
        "distans:spår",
        "KM-tid",
        "skor",
        "odds",
        "pris",
        "vagn",
    ]

    with out_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Skrev {len(rows)} rader till: {out_path}")
    print(f"Omgång: {game_id}")
    print(f"Avdelning: {args.avd} (lopnr {race.get('number')})")
    print(f"Max historik per häst: {args.max_history}")


if __name__ == "__main__":
    main()
