#!/usr/bin/env python3
"""Check and package the calendar (events.json) and the Nobel hub (nobel.json).

Standard library only. Run from the repository root.

  python3 scripts/calendar_data.py check-events new_events.json --out upload.json
      Validate a full events list, drop past events, sort it, and write the
      file to upload to Drive. Prints the Drive file name to use
      (events-YYYYMMDDTHHMMZ.json).

  python3 scripts/calendar_data.py check-nobel new_nobel.json --out upload.json
      Validate the Nobel hub data and write the file to upload. Prints the
      Drive file name to use (nobel-YYYYMMDDTHHMMZ.json).

pull_from_drive.py uses clean_events() and clean_nobel() before replacing
events.json or nobel.json, so a bad upload never breaks the site.
"""
import argparse, json, re, sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVENTS = ROOT / "events.json"
NOBEL = ROOT / "nobel.json"
LANGS = ("ca", "fr", "ru")
EVENT_CATS = ("Sky", "Space", "Awards", "Environment", "Society", "Science")
PRIZES = ("medicine", "physics", "chemistry", "literature", "peace", "economics")
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,79}$")
DAY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MONTH_RE = re.compile(r"^\d{4}-\d{2}$")


class Problem(ValueError):
    pass


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def stamp(prefix):
    n = now_iso().replace("-", "").replace(":", "")[:13]
    return f"{prefix}-{n}Z.json"


def parse_dt(s):
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def words(s):
    return len(str(s or "").split())


def text(v, field, limit_words=None, required=True):
    v = str(v or "").strip()
    if required and not v:
        raise Problem(f"missing {field}")
    if limit_words and words(v) > limit_words:
        raise Problem(f"{field} longer than {limit_words} words")
    return v


def url(v, field="link"):
    v = str(v or "").strip()
    if not v.startswith(("https://", "http://")):
        raise Problem(f"{field} must start with http(s)://")
    return v


# ---------------- events ----------------

def clean_event(e):
    if not isinstance(e, dict):
        raise Problem("not an object")
    out = {"id": str(e.get("id", "")).strip().lower()}
    if not ID_RE.match(out["id"]):
        raise Problem(f"bad id {out['id']!r}")
    d = str(e.get("date", "")).strip()
    if DAY_RE.match(d):
        date.fromisoformat(d)
    elif MONTH_RE.match(d):
        date.fromisoformat(d + "-01")
    else:
        raise Problem("date must be YYYY-MM-DD, or YYYY-MM when only the month is known")
    out["date"] = d
    if e.get("end"):
        end = str(e["end"]).strip()
        if not DAY_RE.match(end) or end < d:
            raise Problem("end must be YYYY-MM-DD on or after date")
        out["end"] = end
    if e.get("at"):
        if not parse_dt(e["at"]):
            raise Problem("at must be an ISO 8601 UTC time")
        out["at"] = parse_dt(e["at"]).isoformat().replace("+00:00", "Z")
    cat = str(e.get("category", "")).strip()
    if cat not in EVENT_CATS:
        raise Problem(f"category {cat!r} not in {EVENT_CATS}")
    out["category"] = cat
    out["title"] = text(e.get("title"), "title", 16)
    out["summary"] = text(e.get("summary"), "summary", 45)
    out["link"] = url(e.get("link"))
    i18n = {}
    for lang in LANGS:
        t = (e.get("i18n") or {}).get(lang)
        if isinstance(t, dict) and t.get("title") and t.get("summary") and words(t["summary"]) <= 70:
            i18n[lang] = {"title": str(t["title"]).strip(), "summary": str(t["summary"]).strip()}
    if i18n:
        out["i18n"] = i18n
    return out


def last_day(e):
    if "end" in e:
        return e["end"]
    if MONTH_RE.match(e["date"]):
        y, m = map(int, e["date"].split("-"))
        nxt = date(y + (m == 12), m % 12 + 1, 1)
        return (nxt - timedelta(days=1)).isoformat()
    return e["date"]


def clean_events(data):
    """Return (clean_data, problems)."""
    items = data.get("events", []) if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise Problem("events must be a list")
    keep_from = (datetime.now(timezone.utc).date() - timedelta(days=2)).isoformat()
    out, problems, seen = [], [], set()
    for raw in items:
        try:
            e = clean_event(raw)
        except (Problem, ValueError) as err:
            problems.append(f"{(raw or {}).get('id', '?') if isinstance(raw, dict) else '?'}: {err}")
            continue
        if e["id"] in seen:
            problems.append(f"{e['id']}: duplicate id")
            continue
        if last_day(e) < keep_from:
            continue
        seen.add(e["id"])
        out.append(e)
    out.sort(key=lambda e: (e["date"] + ("-99" if MONTH_RE.match(e["date"]) else ""), e.get("at", "")))
    return {"updated": now_iso(), "events": out}, problems


# ---------------- nobel ----------------

def clean_prize(p):
    if not isinstance(p, dict):
        raise Problem("not an object")
    pid = str(p.get("id", "")).strip()
    if pid not in PRIZES:
        raise Problem(f"id {pid!r} not in {PRIZES}")
    at = parse_dt(p.get("at"))
    if not at:
        raise Problem(f"{pid}: at must be an ISO 8601 UTC time")
    status = p.get("status", "upcoming")
    if status not in ("upcoming", "announced"):
        raise Problem(f"{pid}: status must be upcoming or announced")
    out = {"id": pid, "at": at.isoformat().replace("+00:00", "Z"), "status": status}
    if status == "announced":
        laureates = []
        for l in p.get("laureates") or []:
            if not isinstance(l, dict) or not str(l.get("name", "")).strip():
                raise Problem(f"{pid}: every laureate needs a name")
            laureates.append({
                "name": str(l["name"]).strip(),
                "info": text(l.get("info"), f"{pid} laureate info", 30, required=False),
                "profile": text(l.get("profile"), f"{pid} laureate profile", 120, required=False),
            })
        if not laureates:
            raise Problem(f"{pid}: announced but no laureates")
        out["laureates"] = laureates
        out["motivation"] = text(p.get("motivation"), f"{pid} motivation", 60)
        out["explainer"] = text(p.get("explainer"), f"{pid} explainer", 320, required=False)
        out["why"] = text(p.get("why"), f"{pid} why", 90, required=False)
        out["sources"] = [{"title": str(s.get("title", "")).strip() or "Source", "url": url(s.get("url"), f"{pid} source")}
                          for s in (p.get("sources") or []) if isinstance(s, dict) and s.get("url")]
        out["updated"] = p.get("updated") or now_iso()
        i18n = {}
        for lang in LANGS:
            t = (p.get("i18n") or {}).get(lang)
            if not isinstance(t, dict) or not t.get("motivation"):
                continue
            tt = {k: str(t[k]).strip() for k in ("motivation", "explainer", "why") if t.get(k)}
            profiles = t.get("profiles") or {}
            if isinstance(profiles, dict):
                tt["profiles"] = {str(k): {kk: str(vv).strip() for kk, vv in (v.items() if isinstance(v, dict) else [("profile", v)]) if kk in ("info", "profile") and vv}
                                  for k, v in profiles.items()}
            i18n[lang] = tt
        if i18n:
            out["i18n"] = i18n
    return out


def clean_nobel(data):
    if not isinstance(data, dict):
        raise Problem("nobel data must be an object")
    prizes, problems = [], []
    for raw in data.get("prizes") or []:
        try:
            prizes.append(clean_prize(raw))
        except Problem as err:
            problems.append(str(err))
    ids = [p["id"] for p in prizes]
    if len(set(ids)) != len(ids):
        raise Problem("duplicate prize ids")
    if not prizes:
        raise Problem("no valid prizes")
    prizes.sort(key=lambda p: p["at"])
    out = {"year": int(data.get("year") or datetime.now().year), "ceremony": str(data.get("ceremony") or ""),
           "updated": now_iso(), "prizes": prizes}
    return out, problems


# ---------------- CLI ----------------

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("check-events", "check-nobel"):
        a = sub.add_parser(name)
        a.add_argument("file")
        a.add_argument("--out", required=True)
    args = ap.parse_args()
    data = json.loads(Path(args.file).read_text(encoding="utf-8"))
    try:
        if args.cmd == "check-events":
            clean, problems = clean_events(data)
            missing = [e["id"] for e in clean["events"] if any(l not in e.get("i18n", {}) for l in LANGS)]
            summary = f"{len(clean['events'])} events kept"
            name = stamp("events")
        else:
            clean, problems = clean_nobel(data)
            missing = [p["id"] for p in clean["prizes"] if p["status"] == "announced" and any(l not in p.get("i18n", {}) for l in LANGS)]
            summary = f"{sum(p['status'] == 'announced' for p in clean['prizes'])} of {len(clean['prizes'])} prizes announced"
            name = stamp("nobel")
    except Problem as err:
        raise SystemExit(f"Not usable: {err}")
    Path(args.out).write_text(json.dumps(clean, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{summary}. Upload {args.out} as {name}")
    for p in problems:
        print("  problem:", p)
    if missing:
        print("  missing translations:", ", ".join(missing))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
