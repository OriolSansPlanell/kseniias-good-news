# Calendar refresh prompt

The scheduled task "Kseniia's Good News: calendar refresh" runs this every
Monday morning. It keeps `events.json` (the "Coming up" list in the Calendar
tab) covering the next three months, in four languages, and uploads an
`events-…json` file to the Drive folder for the GitHub Action to publish.

---

Refresh the "Coming up" calendar of the website "Kseniia's Good News". You prepare one file and upload it to a Google Drive folder; a GitHub Action publishes it. Keep it efficient: at most about 10 web searches.

Drive folder ID: 1PQ9DQwWpwxMzSrdW2zXacv0e8vumFiZ0

Step 1. Run `git clone --depth 1 https://github.com/OriolSansPlanell/kseniias-good-news /tmp/kgn` (read-only; do not call add_repo, do not push) and read /tmp/kgn/events.json. Note today's date; the window is today to three months from today.

Step 2. Research, with WebSearch in standard mode, notable positive or uplifting events in the window:
 - Sky: meteor shower peaks, eclipses, supermoons, planets at opposition or close together, bright comets.
 - Space: launches, arrivals, landings and milestones of science or crewed missions (not routine satellite launches).
 - Awards: major prize announcements and ceremonies (Nobel, Earthshot, Right Livelihood and similar).
 - Environment and Society: big climate, nature or humanitarian conferences, and UN international days with a positive theme.
 - Science: notable science events open to the public.
 Check every date on an official or reputable page. If only the month is known, use "YYYY-MM". Re-check events already in the list whose dates can move (launches, arrivals) and fix them.

Step 3. Build the full new list: keep existing events that are still upcoming and correct (with their translations), update changed ones, add new ones, and drop anything past. Aim for 20-35 events, spread across categories and across the world. Each event is {"id": short-slug-with-year, "date": "YYYY-MM-DD" or "YYYY-MM", "end": optional "YYYY-MM-DD", "at": optional exact UTC time for launches, "category": one of Sky, Space, Awards, Environment, Society, Science, "title": at most 12 words, "summary": at most 35 words in your own words, "link": the page you checked the date on, "i18n": {...}}.

Step 4. Translate (one Haiku helper) the title and summary of new or changed events. Write them to /tmp/events_en.json, then start one Agent call with model "haiku" and subagent_type "general-purpose": "Translate the title and summary of each event in /tmp/events_en.json from English into Catalan (ca), French (fr) and Russian (ru). Keep names, numbers and dates exactly; natural, neutral style. Write /tmp/events_tr.json shaped {"<id>": {"ca": {"title": ..., "summary": ...}, "fr": {...}, "ru": {...}}} and check it parses with python3 -c \"import json; json.load(open('/tmp/events_tr.json'))\". Reply with one line." Put the translations into each event's "i18n". If the helper fails, translate yourself.

Step 5. Write the list to /tmp/events_new.json and run `cd /tmp/kgn && python3 scripts/calendar_data.py check-events /tmp/events_new.json --out /tmp/events_upload.json`. Fix any problem it prints and run it again.

Step 6. Upload with the Google Drive create_file tool (load it with ToolSearch "select:mcp__Google_Drive__create_file" if needed): title = the file name the check printed (events-YYYYMMDDTHHMMZ.json), parentId = the folder ID above, textContent = the exact contents of /tmp/events_upload.json, contentMimeType = "application/json", disableConversionToGoogleType = true.

Step 7. Finish with one line: how many events were added, changed and removed.
