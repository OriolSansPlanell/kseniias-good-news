#!/usr/bin/env python3
"""Apply new files from the Google Drive folder to the site's data.

nobel-*.json and events-*.json files replace nobel.json and events.json (newest valid one wins).

Run by the GitHub Action (.github/workflows/update-site.yml). Standard library only.

Each run of the Claude scheduled task uploads one file named
run-YYYYMMDDTHHMMZ.json to the Drive folder. This script lists the folder,
and if there is a run file newer than the last one applied (stories.json
"last_run"), merges every run file in the folder into stories.json (merging
is safe to repeat: stories already stored are skipped) and rewrites feed.xml.

  DRIVE_API_KEY=... python3 scripts/pull_from_drive.py      # folder id from site.json
  python3 scripts/pull_from_drive.py --dir some/folder      # test with local files

Prints "changed=true" or "changed=false" on its last line, and appends the
same to $GITHUB_OUTPUT when that is set.
"""
import argparse, json, os, re, sys, urllib.error, urllib.parse, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import update_site  # noqa: E402
import calendar_data  # noqa: E402

API = "https://www.googleapis.com/drive/v3/files"
NAME_RE = re.compile(r"^(run|events|nobel)-\d{8}T\d{4}Z\.json$")


def get(url, params):
    full = url + "?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(full, timeout=30) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:500]
        safe = full.replace(params.get("key", "") or "\0", "***")
        raise SystemExit(f"Drive request failed ({e.code}) for {safe}\n{body}\n"
                         "Check that the folder is shared as 'Anyone with the link' "
                         "and that the API key has the Google Drive API enabled.")


def list_drive(folder, key):
    files, token = [], None
    while True:
        params = {"q": f"'{folder}' in parents and trashed = false", "key": key,
                  "fields": "nextPageToken, files(id, name, mimeType)", "pageSize": 1000}
        if token:
            params["pageToken"] = token
        page = json.loads(get(API, params))
        files += page.get("files", [])
        token = page.get("nextPageToken")
        if not token:
            return files


def read_drive(f, key):
    if f["mimeType"].startswith("application/vnd.google-apps"):
        return get(f"{API}/{f['id']}/export", {"mimeType": "text/plain", "key": key})
    return get(f"{API}/{f['id']}", {"alt": "media", "key": key})


def apply_replacement(kind, names, load, target, clean_fn):
    """Replace events.json or nobel.json with the newest valid upload. Returns True if changed."""
    if not names:
        return False
    current = json.loads(target.read_text(encoding="utf-8")) if target.exists() else {}
    newest = names[-1]
    if newest <= (current.get("source_file") or ""):
        print(f"{kind}: newest {newest} already applied")
        return False
    for n in reversed(names):  # newest first; fall back to an older file if the newest is broken
        if n <= (current.get("source_file") or ""):
            break
        try:
            clean, problems = clean_fn(json.loads(load(n).decode("utf-8-sig")))
        except Exception as e:
            print(f"{kind}: ignoring {n} ({e})")
            continue
        for pr in problems:
            print(f"{kind}: {n}: dropped {pr}")
        clean["source_file"] = n
        target.write_text(json.dumps(clean, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"{kind}: applied {n}")
        return True
    return False


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dir", help="read files from this local folder instead of Drive")
    args = p.parse_args()

    if args.dir:
        all_names = sorted(n for n in os.listdir(args.dir) if NAME_RE.match(n))
        load = lambda n: Path(args.dir, n).read_bytes()
    else:
        key = os.environ.get("DRIVE_API_KEY", "").strip()
        site = json.loads(update_site.SITE.read_text(encoding="utf-8"))
        folder = os.environ.get("DRIVE_FOLDER_ID", "").strip() or site.get("drive_folder_id", "")
        if not key or not folder:
            raise SystemExit("Missing DRIVE_API_KEY secret or drive_folder_id in site.json.")
        by_name = {f["name"]: f for f in list_drive(folder, key) if NAME_RE.match(f["name"])}
        if not any(n.startswith("run-") for n in by_name):
            raise SystemExit("No run files are visible in the Drive folder. The Claude task keeps at least "
                             "one there, so the folder is most likely not shared as 'Anyone with the link "
                             "(Viewer)'. Share it that way and run this workflow again.")
        all_names = sorted(by_name)
        load = lambda n: read_drive(by_name[n], key)

    names = [n for n in all_names if n.startswith("run-")]
    changed_events = apply_replacement("events", [n for n in all_names if n.startswith("events-")], load,
                                       calendar_data.EVENTS, calendar_data.clean_events)
    changed_nobel = apply_replacement("nobel", [n for n in all_names if n.startswith("nobel-")], load,
                                      calendar_data.NOBEL, calendar_data.clean_nobel)

    db = update_site.load_db()
    newest = names[-1] if names else None
    print(f"{len(names)} run files in folder; newest {newest}; last applied {db.get('last_run')}")
    changed_stories = bool(newest) and newest > (db.get("last_run") or "")

    if changed_stories:
        stories, latest, translations = [], {}, {}
        for n in names:
            try:
                run = json.loads(load(n).decode("utf-8-sig"))
            except Exception as e:
                print(f"  ignoring {n}: not valid JSON ({e})")
                continue
            stories += run.get("stories", []) if isinstance(run, dict) else []
            if isinstance(run, dict) and isinstance(run.get("translations"), dict):
                for sid, langs in run["translations"].items():
                    translations.setdefault(sid, {}).update(langs if isinstance(langs, dict) else {})
            if n == newest and isinstance(run, dict):
                latest = run
        result = update_site.merge(
            stories,
            sources=latest.get("sources") or None,
            failed=latest.get("failed") or [],
            updated=latest.get("run_at") or None,
            last_run=newest,
            translations=translations,
        )
        update_site.report(result)

    changed = changed_stories or changed_events or changed_nobel
    line = f"changed={'true' if changed else 'false'}"
    print(line)
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as fh:
            fh.write(line + "\n")


if __name__ == "__main__":
    main()
