"""Fetch all RSS/Atom feeds, keep items from the last N hours, write site/feeds.json and site/status.html.

Runs on GitHub Actions (open internet). Claude's daily task then reads
site/feeds.json from GitHub instead of fetching the feeds itself.
"""
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path

import feedparser

ROOT = Path(__file__).resolve().parent.parent
HOURS = int(sys.argv[1]) if len(sys.argv) > 1 else 48
UA = "Mozilla/5.0 (MorningTechBoard RSS fetcher; +https://github.com)"


def entry_time(e):
    for key in ("published_parsed", "updated_parsed"):
        t = e.get(key)
        if t:
            return datetime.fromtimestamp(time.mktime(t), tz=timezone.utc)
    return None  # undated items are dropped


def main():
    feeds = json.loads((ROOT / "scripts" / "feeds.json").read_text())
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=HOURS)
    out = {"generated_utc": now.isoformat(timespec="seconds"), "window_hours": HOURS,
           "status": [], "items": []}

    for cat, sources in feeds.items():
        for src in sources:
            st = {"category": cat, "name": src["name"], "url": src["url"]}
            try:
                d = feedparser.parse(src["url"], agent=UA)
                code = d.get("status")
                st["http"] = code
                if d.bozo and not d.entries:
                    raise RuntimeError(str(d.get("bozo_exception", "parse error"))[:200])
                kept = undated = 0
                for e in d.entries:
                    t = entry_time(e)
                    if t is None:
                        undated += 1
                        continue
                    if t < cutoff:
                        continue
                    kept += 1
                    out["items"].append({
                        "category": cat, "source": src["name"],
                        "title": e.get("title", "").strip(),
                        "url": e.get("link", ""),
                        "published_utc": t.isoformat(timespec="minutes"),
                        "summary": (e.get("summary") or "")[:400],
                    })
                st.update(ok=True, total=len(d.entries), kept=kept, undated=undated)
            except Exception as ex:  # keep going; report per-feed failure
                st.update(ok=False, error=str(ex)[:200])
            out["status"].append(st)

    out["items"].sort(key=lambda i: i["published_utc"], reverse=True)
    site = ROOT / "site"
    site.mkdir(exist_ok=True)
    (site / "feeds.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    (site / "status.html").write_text(render_status(out))
    ok = sum(s["ok"] for s in out["status"])
    print(f"{ok}/{len(out['status'])} feeds OK, {len(out['items'])} items in last {HOURS}h")


def render_status(out):
    rows = "".join(
        f"<tr><td>{escape(s['category'])}</td><td><a href='{escape(s['url'])}'>{escape(s['name'])}</a></td>"
        f"<td class='{'ok' if s['ok'] else 'bad'}'>{'OK' if s['ok'] else 'FAIL'}</td>"
        f"<td>{s.get('http', '')}</td><td>{s.get('total', '')}</td><td>{s.get('kept', '')}</td>"
        f"<td>{s.get('undated', '')}</td><td>{escape(s.get('error', ''))}</td></tr>"
        for s in out["status"])
    items = "".join(
        f"<li><small>{i['published_utc'][:16]} · {escape(i['category'])} · {escape(i['source'])}</small><br>"
        f"<a href='{escape(i['url'])}'>{escape(i['title'])}</a></li>" for i in out["items"])
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>RSS status</title>
<style>body{{font:14px system-ui;max-width:900px;margin:auto;padding:12px}}table{{border-collapse:collapse;width:100%}}
td,th{{border-bottom:1px solid #ddd;padding:4px;text-align:left}}.ok{{color:#0a7d2c;font-weight:600}}.bad{{color:#c0392b;font-weight:600}}
li{{margin:6px 0}}</style></head><body>
<h1>RSS feed status</h1><p>Generated {out['generated_utc']} UTC · window {out['window_hours']}h · <a href="feeds.json">feeds.json</a></p>
<div style="overflow-x:auto"><table><tr><th>Cat</th><th>Feed</th><th>Result</th><th>HTTP</th><th>Total</th><th>Kept</th><th>Undated</th><th>Error</th></tr>{rows}</table></div>
<h2>Items ({len(out['items'])})</h2><ul>{items}</ul></body></html>"""


if __name__ == "__main__":
    main()
