# Scheduled task prompt

This is the exact instruction the 6-hour Claude scheduled task runs. The task
itself runs on Sonnet and hands the bulk work to Haiku helpers: two read the
news feeds, one translates. It never pushes to GitHub: it uploads one "run
file" to a Google Drive folder, and the GitHub Action in
`.github/workflows/update-site.yml` publishes it within the hour.

The list of news sources lives in `site.json`, so adding or removing a source
needs no change here. If you fork this project, change the repository name and
the Drive folder ID (also in `site.json`).

---

Update the website "Kseniia's Good News". You are the coordinator: hand the feed reading and the translation to Haiku helpers with the Agent tool (model "haiku"), and do the choosing and scoring yourself. You never push to GitHub: you upload one run file to a Google Drive folder and a GitHub Action publishes it. No web searches.

Drive folder ID: 1PQ9DQwWpwxMzSrdW2zXacv0e8vumFiZ0

Step 1. Get the site (you). Run `git clone --depth 1 https://github.com/OriolSansPlanell/kseniias-good-news /tmp/kgn && cd /tmp/kgn && python3 scripts/update_site.py list > /tmp/known.txt`. Do not call add_repo and do not push. The news sources, with their short codes and feed URLs, are in /tmp/kgn/site.json under "sources". Note the current UTC time; "the cutoff" below is that time minus 4 days.

Step 2. Read the feeds (two Haiku helpers, in parallel). Split the sources into two halves. In one message, start two Agent calls, each with model "haiku" and subagent_type "general-purpose", with this prompt (fill in the sources, the cutoff and the output file /tmp/cand-1.json or /tmp/cand-2.json):
  "Read these RSS feeds with WebFetch, one call per feed: <name: feed URL, one per line>. Ask WebFetch for every item's title, exact link, publication date and a 1-2 sentence factual description. Keep only items published after <cutoff, ISO 8601 UTC> whose link does not appear in /tmp/known.txt. Skip weekly roundups, 'Good News in History', horoscopes, quizzes, podcasts and podcast transcripts, sponsored posts and opinion columns. Write a JSON list to <output file>, one object per item: {"source": name, "link": exact URL, "published": ISO 8601 UTC, "title": ..., "description": ...}. For a feed that fails, add {"source": name, "error": short reason} instead; do not try other sites. Do not use web search. Reply with one line giving the number of items kept per source."
  If the Agent tool is unavailable or a helper fails, read its feeds yourself the same way.

Step 3. Choose and score (you). Read /tmp/cand-1.json and /tmp/cand-2.json. Pick at most 15 stories: real news events, a variety of topics, and a spread of continents (stories from Africa, Asia, South America and Oceania are rarer, so prefer them when they are good news). Mongabay, Grist, ScienceDaily and Africanews also carry neutral and bad news: include at most 3 stories scoring below 5 per run. Write /tmp/new_stories.json, a JSON list in which each story has:
   - id: the source's code from site.json + "-" + a short lowercase slug from the headline, letters/digits/hyphens only, max 60 chars.
   - title: a plain, factual English headline in your own words (no clickbait, no exclamation marks).
   - summary: 1-2 English sentences, at most 35 words, in your own words. Never copy sentences from the feed. Give just enough to know what happened; the full story stays at the source.
   - why: one short sentence explaining the score.
   - score: integer 0-10 for how good the news is for people, animals or the planet. 0-1 tragic or harmful; 2-3 bad with a small silver lining; 4 mixed or a useful warning; 5 neutral but interesting; 6-7 good for a community or a field; 8-9 real progress that helps many lives; 10 rare landmark with broad, lasting benefit. Lower the score for early lab results, promises not yet delivered, or benefits limited to few people. Be consistent and sober; most stories land 5-8.
   - category: exactly one of Animals, Environment, Energy, Health, Science, Society, Culture.
   - continent: exactly one of Africa, Asia, Europe, North America, South America, Oceania, Antarctica, Global. Use Global for worldwide, multi-continent, open-ocean or space stories. Central America and the Caribbean are North America; the Middle East is Asia; Russia is Europe.
   - region: the country or area, e.g. "Kenya", "Kerala, India", "Global", "Space".
   - source: the source's name exactly as in site.json.
   - url: the exact article link.
   - published: ISO 8601 UTC, e.g. 2026-10-03T14:00:00Z.
   An empty list [] is fine when nothing is new.

Step 4. Translate (one Haiku helper). Run `cd /tmp/kgn && python3 scripts/update_site.py untranslated --limit 25 > /tmp/backfill.json` (older stories still missing translations). Then start one Agent call with model "haiku" and subagent_type "general-purpose" and this prompt:
  "Translate short news items from English into Catalan (ca), French (fr) and Russian (ru). Read /tmp/new_stories.json (translate all three languages for every item) and /tmp/backfill.json (translate only the languages listed in each item's "missing"). For each item translate its title, summary and why. Keep names, numbers and facts exactly; use a natural, neutral news style; add nothing. Catalan: standard central Catalan. Russian: Cyrillic script. Write one JSON object to /tmp/translations.json shaped {"<id>": {"ca": {"title": ..., "summary": ..., "why": ...}, "fr": {...}, "ru": {...}}}, then check it parses with: python3 -c \"import json; json.load(open('/tmp/translations.json'))\". Reply with one line: how many items you translated."
  If the helper fails, translate the new stories yourself and skip the backfill. If /tmp/translations.json is missing or invalid, write {} to it.

Step 5. Pack and check (you). Run `cd /tmp/kgn && python3 scripts/update_site.py pack /tmp/new_stories.json --translations /tmp/translations.json --out /tmp/run.json --sources "<names of sources that worked, comma-separated>" --failed "<names of sources that failed>"`. If it skips a story for a fixable reason (for example a summary that is too long), fix that story and run it again. Glance at two translations to make sure they make sense.

Step 6. Upload (you). Use the Google Drive create_file tool (load it with ToolSearch "select:mcp__Google_Drive__create_file" if needed): title = the file name pack printed (run-YYYYMMDDTHHMMZ.json), parentId = the Drive folder ID above, textContent = the exact contents of /tmp/run.json, contentMimeType = "application/json", disableConversionToGoogleType = true. Upload it even when it holds no stories, so the site shows the run happened. Check the result's mimeType is application/json and its parentId is the folder ID. If the upload fails, stop and report the exact error.

Step 7. Tidy (you). Use the Google Drive search_files tool with the query `parentId = '1PQ9DQwWpwxMzSrdW2zXacv0e8vumFiZ0' and createdTime < '<now minus 3 days, RFC 3339 UTC>'`, and move each file it returns to the trash with trash_file. Never trash anything outside that folder.

Step 8. Finish with one line: stories in the run file, older stories translated, sources that failed, the file name, and the brightest new headline with its score.
