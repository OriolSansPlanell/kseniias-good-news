# Kseniia's Good News

A small, free website that collects positive news from ten sources, gives each story a 0–10 goodness score with a short summary, and links to the original article for the full story. It reads in English, Catalan, French and Russian, shows a world map coloured by how good each continent's news has been, works on phones and can be installed like an app.

Live at **https://oriolsansplanell.github.io/kseniias-good-news/**

## How it works

There is no server and no database. The site is a few static files plus `stories.json`.

```
news feeds ──► Claude scheduled task (every 6 h) ──► run file in a Google Drive folder
                                                              │
                     GitHub Action (every hour) ◄─────────────┘
                     merges it into stories.json, commits, publishes
                                   │
        phone / browser ◄── GitHub Pages
```

1. Every six hours a Claude scheduled task runs. Sonnet coordinates: two Haiku helpers read the news feeds in parallel, Sonnet picks and scores the stories and writes the English summaries, and a third Haiku helper translates them into Catalan, French and Russian (and fills in translations missing from older stories). The task then uploads one small file (`run-YYYYMMDDTHHMMZ.json`) to a Google Drive folder. It never needs write access to GitHub.
2. Every hour a GitHub Action looks in that folder. If there is a newer run file, it merges the stories into `stories.json` and `feed.xml`, commits them, and publishes the site.
3. The Claude task also deletes run files older than three days, so the folder stays small.

## What's in the repo

| File | What it does |
| --- | --- |
| `index.html` | The whole reader: four languages, filters by score, topic and continent, the world panel, saved stories, sharing |
| `world.json` | Simplified continent outlines for the map (from Natural Earth, public domain) |
| `stories.json` | The current stories |
| `feed.xml` | An RSS feed of stories scoring 6 or more |
| `sw.js`, `manifest.webmanifest`, `icons/` | Make it installable on phones and readable offline |
| `scripts/update_site.py` | Checks stories, removes duplicates and stories older than 10 days, writes `stories.json` and `feed.xml` |
| `scripts/pull_from_drive.py` | Reads run files from the Drive folder and merges them (used by the Action) |
| `.github/workflows/update-site.yml` | The hourly Action: import, commit, publish |
| `site.json` | Site name, address, Drive folder ID and the list of news sources |
| `scripts/build_map.py` | Rebuilds `world.json` (only needed to change the map) |
| `UPDATE_PROMPT.md` | The exact instruction the Claude scheduled task follows |

## Setup, step by step

The repository, the Drive folder and the scheduled task are already set up. These are the four steps left. Together they take about ten minutes.

### Step 1. Share the Drive folder by link
The GitHub Action reads the folder without signing in, so the folder must be viewable by link.

1. Open the folder **Kseniia's Good News - runs**: https://drive.google.com/drive/folders/1PQ9DQwWpwxMzSrdW2zXacv0e8vumFiZ0
2. Click the folder name at the top → **Share** → **Share**.
3. Under **General access**, change **Restricted** to **Anyone with the link**, keep the role as **Viewer**, and click **Done**.

The folder only ever holds these small story files, which end up on the public website anyway.

### Step 2. Create a Google API key (free)
1. Go to https://console.cloud.google.com/ and sign in with the same Google account.
2. If asked, accept the terms. At the top, click the project picker → **New project**, name it `good-news`, click **Create**, and make sure it is selected.
3. Open https://console.cloud.google.com/apis/library/drive.googleapis.com and click **Enable**.
4. Open https://console.cloud.google.com/apis/credentials → **+ Create credentials** → **API key**. Copy the key it shows.
5. Recommended: click **Edit API key** (or the key's name). Under **API restrictions**, choose **Restrict key**, tick **Google Drive API**, and **Save**. The key then can't be used for anything else.

No billing account or card is needed for this.

### Step 3. Give the key to GitHub
1. In the repository, open **Settings → Secrets and variables → Actions**.
2. Click **New repository secret**.
3. Name: `DRIVE_API_KEY`. Secret: paste the key. Click **Add secret**.

GitHub keeps the secret hidden, even in logs.

### Step 4. Let the Action publish the site
1. In the repository, open **Settings → Pages**.
2. Under **Build and deployment → Source**, choose **GitHub Actions** instead of "Deploy from a branch".
3. Open the **Actions** tab, click **Update site** on the left, then **Run workflow → Run workflow**.
4. After about a minute the run shows a green tick, and the site is live again with any stories waiting in Drive.

You may see one failed (red) run from before step 4. That's expected and can be ignored.

### Check it's working
- The top of the site says "Updated … ago". After each 6-hour Claude run (a few minutes past 02:00, 08:00, 14:00 and 20:00 Paris summer time), it resets within the hour.
- The **Actions** tab lists one run per hour; most say nothing changed and finish in seconds.

### Install it on your phone
- **iPhone:** open the address in Safari → Share button → **Add to Home Screen**.
- **Android:** open it in Chrome → **Install app**, or ⋮ → **Add to Home screen**.

### Share it
Send the address to anyone. No account or sign-in is needed to read it. Saved stories are kept on each person's own device.

## Changing things

- **Sources:** edit the `sources` list in `site.json` (name, short code, feed URL). The scheduled task reads it on every run, so nothing else needs changing. Feeds must be readable by Claude's web fetch tool (the BBC and The Guardian block it, for example).
- **Scoring rules or the model split:** edit `UPDATE_PROMPT.md` and ask Claude to update the scheduled task with it.
- **Wording in the four languages:** the `T` table near the top of the script in `index.html`.
- **How long stories stay:** `KEEP_DAYS` at the top of `scripts/update_site.py`.
- **How often the site checks Drive:** the `cron` line in `.github/workflows/update-site.yml`.
- **Look and feel:** everything is in `index.html`. Any edit you commit to `main` republishes the site.
- **Your own domain:** Settings → Pages → Custom domain (optional, paid domain).

## If something goes wrong

- **The site doesn't update:** open the **Actions** tab and click the latest run. A "Drive request failed (403)" message means the folder isn't shared by link (step 1) or the key doesn't have the Drive API enabled (step 2). "Missing DRIVE_API_KEY" means step 3 is missing.
- **No new run files appear in the Drive folder:** open the scheduled task in Claude and read its last run. If Google Drive was disconnected, reconnect it in claude.ai Settings → Connectors.
- **The page says "Stories didn't load":** check Settings → Pages is set to GitHub Actions and the last Action run is green.
- **A story is wrong or shouldn't be there:** delete it from `stories.json` on GitHub (pencil icon → remove the story's `{ … }` block → Commit changes). Also delete the run file in Drive that contains it, or it comes back at the next import.

## Running the scripts yourself

```
python3 scripts/update_site.py list
python3 scripts/update_site.py pack new_stories.json --out run.json --sources "Positive News"
python3 scripts/update_site.py add new_stories.json
python3 scripts/pull_from_drive.py --dir folder_with_run_files
```

Only the Python standard library is needed.

## Costs

Free. GitHub Pages and Actions are free for public repositories, the Google API key has no cost for this use, and the Claude scheduled task runs on your existing Claude plan.

## Content

Summaries are written in Claude's own words and kept to a sentence or two; every story links to the original publisher for the full article. The code is under the MIT licence (see `LICENSE`).
