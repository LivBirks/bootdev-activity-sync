# bootdev-activity-sync

Shows how many commits are owed per day, based on your Boot.dev activity heatmap. Days already synced are recorded in `activity-sync/synced.json`, so running it again never double-counts.

## Usage

Run from the `activity-sync/` folder:

```sh
uv run main.py <username>
uv run main.py <username> --timezone America/New_York
uv run main.py <username> --start-date 2026-10-01
```

| Option | Default | Meaning |
|---|---|---|
| `-t`, `--timezone` | `Europe/London` | Timezone Boot.dev uses to group activity into days. Keep it the same between runs. |
| `-s`, `--start-date` | all history | Only count days on or after this date (`YYYY-MM-DD`). |

## Development

```sh
uv run pytest            # run the tests
uv run ruff format .     # format
uv run ruff check .      # lint
```

## API response

`curl -s 'https://api.boot.dev/v1/users/public/virtualcross04/activity_heatmap?timezone=Europe/London' | jq`

```
{
  "data": {
    "calendar": [
      {
        "date": "2026-08-15T00:00:00Z",
        "count": 24
      },
      {
        "date": "2026-08-16T00:00:00Z",
        "count": 82
      }
    ]
  },
  "status": "success"
}
```
