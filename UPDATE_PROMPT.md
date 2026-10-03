# Scheduled task prompt

This is the exact instruction the 6-hour Claude scheduled task runs. If you
fork this project, replace `OriolSansPlanell` with your own GitHub username.

---

Update the website "Kseniia's Good News", which lives in the GitHub repository OriolSansPlanell/kseniias-good-news and is served by GitHub Pages. Keep this run lightweight: no web searches, only the feed fetches below.

1. Get the repository. Do this before anything else, and do not clone or touch git until it succeeds:
   a. Call the add_repo tool (mcp__claude-code-remote__add_repo; load it with ToolSearch "select:mcp__claude-code-remote__add_repo" if it isn't listed) with owner "OriolSansPlanell", repo "kseniias-good-news", access "push". Use exactly that capitalisation.
   b. Wait for its result. If it says the repo was added, clone with exactly the clone command or clone_url it returns, then cd into the clone. If it is refused, needs approval, or errors, stop and report its exact message; do not clone the public URL yourself, because pushing from such a clone is denied.
   c. Run: git config user.name "Good News bot" && git config user.email "goodnews-bot@users.noreply.github.com"
   d. Check write access right away with `git push --dry-run origin HEAD:main`. If it fails, stop and report the exact error.

2. Run `python3 scripts/update_site.py list` to see which stories are already stored (id and url).

3. Fetch these RSS feeds with WebFetch, asking for each item's title, exact link, publication date and a 1–2 sentence factual description:
   - https://www.positive.news/feed/
   - https://www.goodnewsnetwork.org/feed/
   - https://reasonstobecheerful.world/feed/
   - https://www.sciencedaily.com/rss/top/science.xml
   If a feed fails, skip it and note its name. Do not work around a blocked site.

4. Keep only items published in the last 4 days whose link is not already stored. Skip weekly roundups, "Good News in History", horoscopes, quizzes, sponsored posts and items without a real news event. Take at most 15 new stories, favouring variety of topic and region.

5. Write the new stories as a JSON list to a file outside the repository (e.g. /tmp/new_stories.json). Each story has:
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

6. Run `python3 scripts/update_site.py add /tmp/new_stories.json --sources "<feeds that worked, comma-separated>" --failed "<feeds that failed>"`. It validates, removes duplicates, drops stories older than 10 days and rewrites stories.json and feed.xml. If it reports a story as skipped for a fixable reason (for example a summary that is too long), fix that story and run the command again.

7. Commit and push: `git add stories.json feed.xml && git commit -m "Update stories $(date -u +%Y-%m-%dT%H:%MZ)" && git push`. If the push is rejected because the remote moved, run `git pull --rebase` and push once more. Change no other files.

8. Finish with one line: the script's summary line and the brightest new headline with its score.
