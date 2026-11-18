# Morning Tech Board — RSS fetcher

GitHub Actions fetches the RSS/Atom feeds in `scripts/feeds.json` every day at 06:15 Asia/Bangkok,
keeps items from the last 48 hours (undated items are dropped), and writes:

- `site/feeds.json` — items + per-feed status, read by the Claude daily summary task
- `site/status.html` — human-readable check of which feeds work (published to GitHub Pages)

Run manually: Actions → "Fetch RSS feeds" → Run workflow. Locally: `pip install feedparser && python scripts/fetch_feeds.py 48`.

To add or remove a source, edit `scripts/feeds.json`.
