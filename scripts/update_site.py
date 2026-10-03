#!/usr/bin/env python3
"""Maintain stories.json and feed.xml for Kseniia's Good News.

Standard library only. Run from the repository root.

  python3 scripts/update_site.py list
      Print the id and url of every stored story (one per line), so a run
      can skip stories it already has.

  python3 scripts/update_site.py add new_stories.json [--sources "A,B"] [--failed "C"]
      Merge new stories (a JSON list of story objects), drop duplicates,
      prune stories older than KEEP_DAYS, then rewrite stories.json and
      feed.xml. An empty list is fine: it just refreshes the timestamp.
"""
import argparse, json, re, sys
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
STORIES = ROOT / "stories.json"
FEED = ROOT / "feed.xml"
SITE = ROOT / "site.json"
KEEP_DAYS = 10
FEED_MIN_SCORE = 6
CATEGORIES = {"Animals", "Environment", "Energy", "Health", "Science", "Society", "Culture"}
REQUIRED = ["id", "title", "summary", "why", "source", "url", "score", "category", "region", "published"]
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,79}$")


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_dt(s):
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def load_db():
    if STORIES.exists():
        return json.loads(STORIES.read_text(encoding="utf-8"))
    return {"updated": None, "sources": [], "stories": []}


def check(story):
    """Return a cleaned story, or raise ValueError explaining what is wrong."""
    missing = [k for k in REQUIRED if story.get(k) in (None, "")]
    if missing:
        raise ValueError("missing " + ", ".join(missing))
    s = {k: story[k] for k in REQUIRED}
    s["id"] = str(s["id"]).strip().lower()
    if not ID_RE.match(s["id"]):
        raise ValueError(f"bad id {s['id']!r} (lowercase letters, digits, hyphens)")
    try:
        s["score"] = int(round(float(s["score"])))
    except Exception:
        raise ValueError("score is not a number")
    if not 0 <= s["score"] <= 10:
        raise ValueError("score outside 0-10")
    if s["category"] not in CATEGORIES:
        raise ValueError(f"category {s['category']!r} not in {sorted(CATEGORIES)}")
    if not str(s["url"]).startswith(("https://", "http://")):
        raise ValueError("url must start with http(s)://")
    if parse_dt(s["published"]) is None:
        raise ValueError("published is not an ISO date")
    if len(str(s["summary"]).split()) > 45:
        raise ValueError("summary longer than 45 words")
    s["added"] = story.get("added") or now_iso()
    return s


def write_feed(stories, updated):
    site = json.loads(SITE.read_text(encoding="utf-8")) if SITE.exists() else {}
    title = site.get("title", "Kseniia's Good News")
    link = site.get("url", "")
    desc = site.get("description", "Positive news, scored 0-10 for goodness.")
    items = []
    for s in [x for x in stories if x["score"] >= FEED_MIN_SCORE][:60]:
        pub = parse_dt(s["published"])
        body = f"{s['summary']} (Goodness {s['score']}/10: {s['why']})"
        items.append(
            "    <item>\n"
            f"      <title>{escape(s['title'])} [{s['score']}/10]</title>\n"
            f"      <link>{escape(s['url'])}</link>\n"
            f"      <guid isPermaLink=\"false\">{escape(s['id'])}</guid>\n"
            f"      <pubDate>{format_datetime(pub)}</pubDate>\n"
            f"      <category>{escape(s['category'])}</category>\n"
            f"      <source url=\"{escape(link + 'feed.xml')}\">{escape(s['source'])}</source>\n"
            f"      <description>{escape(body)}</description>\n"
            "    </item>"
        )
    upd = parse_dt(updated) or datetime.now(timezone.utc)
    FEED.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0">\n  <channel>\n'
        f"    <title>{escape(title)}</title>\n    <link>{escape(link)}</link>\n"
        f"    <description>{escape(desc)}</description>\n    <language>en</language>\n"
        f"    <lastBuildDate>{format_datetime(upd)}</lastBuildDate>\n"
        + "\n".join(items) + "\n  </channel>\n</rss>\n",
        encoding="utf-8",
    )


def cmd_list(_):
    for s in load_db()["stories"]:
        print(s["id"], s["url"])


def cmd_add(args):
    db = load_db()
    incoming = json.loads(Path(args.file).read_text(encoding="utf-8"))
    if isinstance(incoming, dict):
        incoming = incoming.get("stories", [])
    have_ids = {s["id"] for s in db["stories"]}
    have_urls = {s["url"].rstrip("/") for s in db["stories"]}
    cutoff = datetime.now(timezone.utc) - timedelta(days=KEEP_DAYS)
    added, skipped = [], []
    for raw in incoming:
        try:
            s = check(raw)
        except ValueError as e:
            skipped.append(f"{raw.get('id', '?')}: {e}")
            continue
        if s["id"] in have_ids or s["url"].rstrip("/") in have_urls:
            skipped.append(f"{s['id']}: already stored")
            continue
        if parse_dt(s["published"]) < cutoff:
            skipped.append(f"{s['id']}: older than {KEEP_DAYS} days")
            continue
        have_ids.add(s["id"]); have_urls.add(s["url"].rstrip("/"))
        added.append(s)

    kept = [s for s in db["stories"] + added if (parse_dt(s["published"]) or cutoff) >= cutoff]
    pruned = len(db["stories"]) + len(added) - len(kept)
    kept.sort(key=lambda s: s["published"], reverse=True)

    updated = now_iso()
    sources = [x.strip() for x in args.sources.split(",") if x.strip()] if args.sources else db.get("sources", [])
    failed = [x.strip() for x in args.failed.split(",") if x.strip()] if args.failed else []
    out = {
        "updated": updated,
        "sources": sources,
        "count": len(kept),
        "note": f"{len(added)} new, {len(skipped)} skipped, {pruned} pruned, failed feeds: {', '.join(failed) or 'none'}",
        "stories": kept,
    }
    STORIES.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    write_feed(kept, updated)

    print(out["note"])
    for line in skipped:
        print("  skipped", line)
    if added:
        best = max(added, key=lambda s: s["score"])
        print(f"Brightest new: [{best['score']}/10] {best['title']}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list").set_defaults(fn=cmd_list)
    a = sub.add_parser("add")
    a.add_argument("file")
    a.add_argument("--sources", help="comma-separated names of feeds that worked this run")
    a.add_argument("--failed", help="comma-separated names of feeds that failed")
    a.set_defaults(fn=cmd_add)
    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
