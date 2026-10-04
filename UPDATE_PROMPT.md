# Scheduled task prompt

This is the exact instruction the 6-hour Claude scheduled task runs. It never
pushes to GitHub: it uploads one "run file" to a Google Drive folder, and the
GitHub Action in `.github/workflows/update-site.yml` picks it up within the
hour. If you fork this project, change the repository name and the Drive
folder ID (also in `site.json`).

---

Update the website "Kseniia's Good News". You do not push to GitHub. You prepare the new stories and upload them as one file to a Google Drive folder; a GitHub Action publishes them. Keep this run lightweight: no web searches, only the feed fetches below.

Drive folder ID: 1PQ9DQwWpwxMzSrdW2zXacv0e8vumFiZ0

1. Get the current site, read-only: `git clone --depth 1 https://github.com/OriolSansPlanell/kseniias-good-news /tmp/kgn && cd /tmp/kgn`. Do not call add_repo and do not push. Then run `python3 scripts/update_site.py list` to see which stories are already stored (id and url).

2. Fetch these RSS feeds with WebFetch, asking for each item's title, exact link, publication date and a 1–2 sentence factual description:
   - https://www.positive.news/feed/
   - https://www.goodnewsnetwork.org/feed/
   - https://reasonstobecheerful.world/feed/
   - https://www.sciencedaily.com/rss/top/science.xml
   If a feed fails, skip it and note its name. Do not work around a blocked site.

3. Keep only items published in the last 4 days whose link is not already stored. Skip weekly roundups, "Good News in History", horoscopes, quizzes, sponsored posts and items without a real news event. Take at most 15 new stories, favouring variety of topic and region.

4. Write the new stories as a JSON list to /tmp/new_stories.json. Each story has:
   - id: source prefix (pn, gnn, rtbc, sd) + "-" + a short lowercase slug from the headline, letters/digits/hyphens only, max 60 chars.
   - title: a plain, factual headline in your own words (no clickbait, no exclamation marks).
   - summary: 1–2 sentences, at most 35 words, in your own words. Never copy sentences from the feed. Give just enough to know what happened; the full story stays at the source.
   - why: one short sentence explaining the score.
   - score: integer 0–10 for how good the news is for people, animals or the planet. 0–1 tragic or harmful; 2–3 bad with a small silver lining; 4 mixed or a useful warning; 5 neutral but interesting; 6–7 good for a community or a field; 8–9 real progress that helps many lives; 10 rare landmark with broad, lasting benefit. Lower the score for early lab results, promises not yet delivered, or benefits limited to few people. Be consistent and sober; most stories land 5–8.
   - category: exactly one of Animals, Environment, Energy, Health, Science, Society, Culture.
   - region: country or area, or "Global" / "Space".
   - source: Positive News, Good News Network, Reasons to be Cheerful, or ScienceDaily.
   - url: the exact article link from the feed.
   - published: the item's date as ISO 8601 UTC (e.g. 2026-10-03T14:00:00Z).
   An empty list [] is fine when nothing is new.

5. Run `python3 scripts/update_site.py pack /tmp/new_stories.json --out /tmp/run.json --sources "<feeds that worked, comma-separated>" --failed "<feeds that failed>"`. It validates the stories, drops ones already stored, and prints the file name to use. If it skips a story for a fixable reason (for example a summary that is too long), fix that story and run it again.

6. Upload the run file with the Google Drive create_file tool (load it with ToolSearch "select:mcp__Google_Drive__create_file" if needed): title = the file name pack printed (run-YYYYMMDDTHHMMZ.json), parentId = the Drive folder ID above, textContent = the exact contents of /tmp/run.json, contentMimeType = "application/json", disableConversionToGoogleType = true. Upload it even when it holds no stories, so the site shows the run happened. Check the result's mimeType is application/json and its parentId is the folder ID. If the upload fails, stop and report the exact error.

7. Tidy the folder: use the Google Drive search_files tool with the query `parentId = '1PQ9DQwWpwxMzSrdW2zXacv0e8vumFiZ0' and createdTime < '<now minus 3 days, RFC 3339 UTC>'`, and move each file it returns to the trash with trash_file. Never trash anything outside that folder.

8. Finish with one line: how many stories went into the run file, the name of the file, and the brightest new headline with its score.
