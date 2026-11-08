import argparse
import datetime as dt
import json
from pathlib import Path

import requests

START_DATE = None
STATE_PATH = Path(__file__).parent / "synced.json"


class HeatmapError(Exception):
    pass


def fetch_heatmap(username: str, timezone: str) -> dict:
    response = requests.get(
        f"https://api.boot.dev/v1/users/public/{username}/activity_heatmap?timezone={timezone}",
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def parse_heatmap(raw: dict):
    if "data" not in raw or "calendar" not in raw["data"]:
        raise HeatmapError("data shape not valid")
    if not raw["data"]["calendar"]:
        raise HeatmapError("No calendar data")
    if not all(
        "date" in entry and "count" in entry and type(entry["count"]) == int
        for entry in raw["data"]["calendar"]
    ):
        raise HeatmapError("invalid data")
    new_dict = {
        dt.datetime.fromisoformat(item["date"]).date(): item["count"]
        for item in raw["data"]["calendar"]
    }
    return new_dict


def load_state(path=STATE_PATH):
    try:
        with open(path) as json_data:
            raw = json.load(json_data)
            return {dt.date.fromisoformat(date): count for date, count in raw.items()}
    except FileNotFoundError:
        return {}


def save_state(state, path=STATE_PATH):
    formatted = {dt.date.isoformat(date): count for date, count in state.items()}
    with open(path, mode="w") as json_data:
        json.dump(formatted, json_data, sort_keys=True, indent=4)


def compute_todo(activity, state, start_date=None):
    result = {}
    for date, count in activity.items():
        if start_date is not None and date < start_date:
            continue
        owed = count - state.get(date, 0)
        if owed > 0:
            result[date] = owed
    return result


def main():
    parser = argparse.ArgumentParser(
        prog="BootdevActivitySync",
        description="Syncs activity from Boot.dev to GitHub",
        epilog="See README.md for more info.",
    )
    parser.add_argument("username")
    parser.add_argument(
        "-t",
        "--timezone",
        default="Europe/London",
        help="timezone Boot.dev groups days by (default: %(default)s)",
    )
    args = parser.parse_args()
    # fetch
    raw_json = fetch_heatmap(args.username, args.timezone)
    # parse
    heatmap = parse_heatmap(raw_json)
    # compare with what's already synced
    state = load_state(STATE_PATH)
    result = compute_todo(heatmap, state, START_DATE)
    if not result:
        print("Nothing to sync")
        return
    for date, owed in sorted(result.items()):
        print(f"{date}: {owed}")
    print(f"Total: {sum(result.values())} commits owed across {len(result)} days")


if __name__ == "__main__":
    main()
