# Nobel live coverage prompt

The scheduled task "Kseniia's Good News: Nobel live" runs this every hour from
11:55 to 15:55 (Paris time) on 5–9 and 12 October. It fills `nobel.json` with
the laureates, short profiles and a plain-language explanation, translated
into Catalan, French and Russian. It uploads a `nobel-…json` file to the Drive
folder; the GitHub Action (every 10 minutes on those days) publishes it.
On runs with nothing new it stops without uploading, so extra runs cost little.

---

Update the Nobel Prize live coverage of the website "Kseniia's Good News". You prepare one file and upload it to a Google Drive folder; a GitHub Action publishes it within about 10 minutes. Be efficient: no work on prizes that are already complete.

Drive folder ID: 1PQ9DQwWpwxMzSrdW2zXacv0e8vumFiZ0

Step 1. Read the current state. Run `git clone --depth 1 https://github.com/OriolSansPlanell/kseniias-good-news /tmp/kgn` (read-only; do not call add_repo, do not push) and read /tmp/kgn/nobel.json. It lists six prizes (id, at = announcement time in UTC, status, and for announced prizes: laureates, motivation, explainer, why, sources, i18n). Note the current UTC time.

Step 2. Decide what needs work. Only prizes whose "at" time has passed count:
 - status "upcoming": find out whether the laureates are announced (step 3).
 - status "announced" but missing the explainer, the why, a laureate profile, or any of the ca/fr/ru translations: complete it (steps 4-5).
 - already complete: only fix clear factual errors, otherwise leave it alone.
 If nothing needs work, reply "Nothing to update" and stop without uploading anything.

Step 3. Find the winners. Use WebSearch for "<year> Nobel Prize in <field> laureates" (for Peace: "<year> Nobel Peace Prize"), then open the official press release on nobelprize.org (or nobelpeaceprize.org for Peace) with WebFetch. If the official site cannot be fetched, use at least two reputable news reports (for example Reuters, AP, BBC, Nature, Science, Le Monde) and make sure they agree. Never guess: if the announcement is not confirmed yet, leave the prize "upcoming".

Step 4. Write each newly announced or incomplete prize in English, in your own words (never copy sentences):
 - laureates: a list of {"name": full name, "info": "born <year>, <country> · <current affiliation>" (at most 30 words), "profile": 2-4 sentences on who they are and how they got here (at most 90 words)}. For an organisation, info is what it is and where it is based.
 - motivation: what the prize is for in plain language, at most 35 words. You may quote a short key phrase of the official citation in quotation marks.
 - explainer: 120-220 words explaining the work to a curious 15-year-old: the problem, what they found or did, and a simple everyday analogy. Literature: what the author writes and why readers value it. Peace: what the laureate did and for whom.
 - why: 1-3 sentences on why it matters for people today, at most 70 words.
 - sources: 2-4 {"title": ..., "url": ...} links you actually used.
 - status: "announced"; updated: the current UTC time.
 Stick strictly to what the sources say.

Step 5. Translate (one Haiku helper). Write the English texts of the prizes you changed to /tmp/nobel_en.json, then start one Agent call with model "haiku" and subagent_type "general-purpose" and this prompt: "Translate the Nobel Prize texts in /tmp/nobel_en.json from English into Catalan (ca), French (fr) and Russian (ru): for each prize its motivation, explainer and why, and for each laureate its info and profile. Keep names, numbers and facts exactly; clear, natural, neutral style; add nothing. Write /tmp/nobel_tr.json shaped {"<prize id>": {"ca": {"motivation": ..., "explainer": ..., "why": ..., "profiles": {"<exact laureate name>": {"info": ..., "profile": ...}}}, "fr": {...}, "ru": {...}}}, then check it parses with python3 -c \"import json; json.load(open('/tmp/nobel_tr.json'))\". Reply with one line." Put each prize's translations into that prize as "i18n". If the helper fails, translate yourself.

Step 6. Check. Write the whole updated object (year, ceremony, and all six prizes; untouched prizes exactly as they were) to /tmp/nobel_new.json and run `cd /tmp/kgn && python3 scripts/calendar_data.py check-nobel /tmp/nobel_new.json --out /tmp/nobel_upload.json`. Fix any problem it prints and run it again.

Step 7. Upload with the Google Drive create_file tool (load it with ToolSearch "select:mcp__Google_Drive__create_file" if needed): title = the file name the check printed (nobel-YYYYMMDDTHHMMZ.json), parentId = the folder ID above, textContent = the exact contents of /tmp/nobel_upload.json, contentMimeType = "application/json", disableConversionToGoogleType = true. If the upload fails, stop and report the exact error.

Step 8. Finish with one line: which prizes changed and the laureates' names.
