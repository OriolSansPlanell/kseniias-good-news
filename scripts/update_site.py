#!/usr/bin/env python3
"""Maintain stories.json and feed.xml for Kseniia's Good News.

Standard library only. Run from the repository root.

  python3 scripts/update_site.py list
      Print the id and url of every stored story (one per line).

  python3 scripts/update_site.py untranslated [--limit 30]
      Print, as JSON, stored stories that still lack a Catalan, French or
      Russian version (id, title, summary, why), for the translation step.

  python3 scripts/update_site.py pack new_stories.json --out run.json
          [--translations translations.json] [--sources "A,B"] [--failed "C"]
      Check new stories against the rules and against stories.json, attach
      their translations, and write a "run file" holding only valid,
      not-yet-stored stories plus translations for stored ones.
      stories.json is not changed. The Claude task uploads this to Drive.

  python3 scripts/update_site.py add new_stories.json [--translations t.json] ...
      Merge straight into stories.json (for local use and tests).

scripts/pull_from_drive.py uses merge() to apply run files from Drive.
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
LANGS = ("ca", "fr", "ru")
CATEGORIES = {"Animals", "Environment", "Energy", "Health", "Science", "Society", "Culture"}
CONTINENTS = {"Africa", "Asia", "Europe", "North America", "South America", "Oceania", "Antarctica", "Global"}
REQUIRED = ["id", "title", "summary", "why", "source", "url", "score", "category", "region", "published"]
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,79}$")

# Region (country or area) -> continent, used when a story has no continent.
_C = {
    "Africa": "Africa Algeria Angola Benin Botswana Burkina Burundi Cameroon Cape-Verde Chad Comoros Congo DRC "
              "Djibouti Egypt Eritrea Eswatini Ethiopia Gabon Gambia Ghana Guinea Ivory-Coast Cote-d'Ivoire Kenya "
              "Lesotho Liberia Libya Madagascar Malawi Mali Mauritania Mauritius Morocco Mozambique Namibia Niger "
              "Nigeria Rwanda Senegal Seychelles Sierra-Leone Somalia South-Africa South-Sudan Sudan Tanzania Togo "
              "Tunisia Uganda Zambia Zimbabwe Sahel",
    "Asia": "Asia Afghanistan Armenia Azerbaijan Bahrain Bangladesh Bhutan Brunei Cambodia China Georgia Hong-Kong "
            "India Indonesia Iran Iraq Israel Japan Jordan Kazakhstan Kuwait Kyrgyzstan Laos Lebanon Malaysia "
            "Maldives Mongolia Myanmar Nepal North-Korea Oman Pakistan Palestine Gaza Philippines Qatar "
            "Saudi-Arabia Singapore South-Korea Korea Sri-Lanka Syria Taiwan Tajikistan Thailand Timor-Leste "
            "Turkey Turkmenistan UAE United-Arab-Emirates Uzbekistan Vietnam Yemen Middle-East Arabian-Sea Himalaya",
    "Europe": "Europe EU Albania Andorra Austria Belarus Belgium Bosnia Bulgaria Croatia Cyprus Czechia "
              "Czech-Republic Denmark Estonia Finland France Germany Greece Hungary Iceland Ireland Italy Kosovo "
              "Latvia Liechtenstein Lithuania Luxembourg Malta Moldova Monaco Montenegro Netherlands "
              "North-Macedonia Norway Poland Portugal Romania Russia San-Marino Serbia Slovakia Slovenia Spain "
              "Catalonia Sweden Switzerland Ukraine UK United-Kingdom Britain England Scotland Wales "
              "Northern-Ireland Vatican",
    "North America": "North-America USA US United-States America Canada Mexico Greenland Guatemala Belize Honduras "
                     "El-Salvador Nicaragua Costa-Rica Panama Cuba Haiti Dominican-Republic Jamaica Bahamas "
                     "Barbados Trinidad Puerto-Rico Caribbean Central-America California Alaska Hawaii",
    "South America": "South-America Latin-America Argentina Bolivia Brazil Chile Colombia Ecuador Guyana Paraguay "
                     "Peru Suriname Uruguay Venezuela Amazon Galapagos Galápagos Patagonia",
    "Oceania": "Oceania Australia New-Zealand Fiji Papua-New-Guinea Samoa Solomon-Islands Tonga Vanuatu Kiribati "
               "Micronesia Palau Pacific Tasmania",
    "Antarctica": "Antarctica Antarctic Southern-Ocean",
    "Global": "Global World Worldwide International Space Moon Mars Ocean Oceans Arctic",
}
REGION_TO_CONTINENT = {w.replace("-", " ").lower(): c for c, words in _C.items() for w in words.split()}
_BY_LENGTH = sorted(REGION_TO_CONTINENT.items(), key=lambda kv: -len(kv[0]))


def continent_for(region):
    """Best-effort continent for a region string such as 'Kenya' or 'Greece / USA'."""
    text = str(region or "").lower()
    parts = [p.strip() for p in re.split(r"[/,;&+]| and ", text) if p.strip()]
    found = []
    for p in parts:
        hit = REGION_TO_CONTINENT.get(p) or next(
            (c for k, c in _BY_LENGTH if re.search(r"\b" + re.escape(k) + r"\b", p)), None)
        if hit and hit not in found:
            found.append(hit)
    return found[0] if len(found) == 1 else "Global"


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_dt(s):
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def load_db():
    if STORIES.exists():
        db = json.loads(STORIES.read_text(encoding="utf-8"))
    else:
        db = {"updated": None, "sources": [], "stories": []}
    for s in db["stories"]:
        if s.get("continent") not in CONTINENTS:
            s["continent"] = continent_for(s.get("region"))
    return db


def clean_translation(t):
    """Return a cleaned {title, summary, why} dict, or None if unusable."""
    if not isinstance(t, dict):
        return None
    title, summary = str(t.get("title", "")).strip(), str(t.get("summary", "")).strip()
    if not title or not summary or len(summary.split()) > 70 or len(title) > 200:
        return None
    out = {"title": title, "summary": summary}
    why = str(t.get("why", "")).strip()
    if why:
        out["why"] = why
    return out


def clean_i18n(value):
    out = {}
    if isinstance(value, dict):
        for lang in LANGS:
            t = clean_translation(value.get(lang))
            if t:
                out[lang] = t
    return out


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
    s["continent"] = story.get("continent") or continent_for(s["region"])
    if s["continent"] not in CONTINENTS:
        raise ValueError(f"continent {s['continent']!r} not in {sorted(CONTINENTS)}")
    if not str(s["url"]).startswith(("https://", "http://")):
        raise ValueError("url must start with http(s)://")
    if parse_dt(s["published"]) is None:
        raise ValueError("published is not an ISO date")
    if len(str(s["summary"]).split()) > 45:
        raise ValueError("summary longer than 45 words")
    s["added"] = story.get("added") or now_iso()
    i18n = clean_i18n(story.get("i18n"))
    if i18n:
        s["i18n"] = i18n
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
            f"      <category>{escape(s.get('continent', 'Global'))}</category>\n"
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


def split_list(value):
    return [x.strip() for x in value.split(",") if x.strip()] if value else []


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8")) if path else None


def read_stories(path):
    data = read_json(path)
    return data.get("stories", []) if isinstance(data, dict) else (data or [])


def filter_new(db, incoming):
    """Validate incoming stories; return (new_valid_stories, skipped_reasons)."""
    have_ids = {s["id"] for s in db["stories"]}
    have_urls = {s["url"].rstrip("/") for s in db["stories"]}
    cutoff = datetime.now(timezone.utc) - timedelta(days=KEEP_DAYS)
    added, skipped = [], []
    for raw in incoming:
        if not isinstance(raw, dict):
            skipped.append("?: not a story object")
            continue
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
    return added, skipped


def apply_translations(stories, translations):
    """Add translations ({id: {lang: {...}}}) to matching stories. Returns how many were added."""
    by_id = {s["id"]: s for s in stories}
    n = 0
    for sid, langs in (translations or {}).items():
        s = by_id.get(str(sid).lower())
        if not s:
            continue
        for lang, t in clean_i18n(langs).items():
            if lang not in s.setdefault("i18n", {}):
                s["i18n"][lang] = t
                n += 1
        if not s["i18n"]:
            del s["i18n"]
    return n


def merge(incoming, sources=None, failed=None, updated=None, last_run=None, translations=None):
    """Merge stories into stories.json and rewrite feed.xml. Returns a summary dict."""
    db = load_db()
    added, skipped = filter_new(db, incoming)
    cutoff = datetime.now(timezone.utc) - timedelta(days=KEEP_DAYS)
    kept = [s for s in db["stories"] + added if (parse_dt(s["published"]) or cutoff) >= cutoff]
    pruned = len(db["stories"]) + len(added) - len(kept)
    kept.sort(key=lambda s: s["published"], reverse=True)
    translated = apply_translations(kept, translations)
    updated = updated or now_iso()
    failed = failed or []
    out = {
        "updated": updated,
        "sources": sources or db.get("sources", []),
        "count": len(kept),
        "last_run": last_run or db.get("last_run"),
        "note": f"{len(added)} new, {len(skipped)} skipped, {pruned} pruned, {translated} translations added, "
                f"failed feeds: {', '.join(failed) or 'none'}",
        "stories": kept,
    }
    STORIES.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    write_feed(kept, updated)
    return {"added": added, "skipped": skipped, "pruned": pruned, "note": out["note"]}


def report(result):
    print(result["note"])
    for line in result["skipped"]:
        print("  skipped", line)
    if result["added"]:
        best = max(result["added"], key=lambda s: s["score"])
        print(f"Brightest new: [{best['score']}/10] {best['title']}")


def cmd_list(_):
    for s in load_db()["stories"]:
        print(s["id"], s["url"])


def cmd_untranslated(args):
    rows = [{"id": s["id"], "title": s["title"], "summary": s["summary"], "why": s["why"],
             "missing": [l for l in LANGS if l not in s.get("i18n", {})]}
            for s in load_db()["stories"] if any(l not in s.get("i18n", {}) for l in LANGS)]
    print(json.dumps(rows[: args.limit], ensure_ascii=False, indent=1))


def cmd_add(args):
    report(merge(read_stories(args.file), split_list(args.sources), split_list(args.failed),
                 translations=read_json(args.translations)))


def cmd_pack(args):
    db = load_db()
    added, skipped = filter_new(db, read_stories(args.file))
    translations = read_json(args.translations) or {}
    if not isinstance(translations, dict):
        raise SystemExit("translations file must be a JSON object {id: {ca: {...}, fr: {...}, ru: {...}}}")
    apply_translations(added, translations)
    new_ids = {s["id"] for s in added}
    stored_ids = {s["id"] for s in db["stories"]}
    backfill = {}
    for sid, langs in translations.items():
        sid = str(sid).lower()
        if sid in stored_ids and sid not in new_ids:
            clean = clean_i18n(langs)
            if clean:
                backfill[sid] = clean
    missing = [s["id"] for s in added if any(l not in s.get("i18n", {}) for l in LANGS)]
    run_at = now_iso()
    run = {"run_at": run_at, "sources": split_list(args.sources), "failed": split_list(args.failed),
           "stories": added, "translations": backfill}
    Path(args.out).write_text(json.dumps(run, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    name = f"run-{run_at.replace('-', '').replace(':', '')[:13]}Z.json"
    print(f"{len(added)} stories ready, {len(skipped)} skipped, translations for {len(backfill)} older stories. "
          f"Upload {args.out} as {name}")
    for line in skipped:
        print("  skipped", line)
    if missing:
        print("  new stories without all three translations:", ", ".join(missing))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list").set_defaults(fn=cmd_list)
    u = sub.add_parser("untranslated")
    u.add_argument("--limit", type=int, default=30)
    u.set_defaults(fn=cmd_untranslated)
    for name, fn in (("add", cmd_add), ("pack", cmd_pack)):
        a = sub.add_parser(name)
        a.add_argument("file")
        a.add_argument("--translations", help="JSON object {id: {ca|fr|ru: {title, summary, why}}}")
        a.add_argument("--sources", help="comma-separated names of feeds that worked this run")
        a.add_argument("--failed", help="comma-separated names of feeds that failed")
        if name == "pack":
            a.add_argument("--out", required=True, help="where to write the run file")
        a.set_defaults(fn=fn)
    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
