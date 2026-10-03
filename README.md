# Kseniia's Good News

A small, free website that collects positive news from several sources, gives each story a 0–10 goodness score with a short summary, and links to the original article for the full story. It works on phones and can be installed like an app.

There is no server and no database. The site is three static files plus `stories.json`. Every six hours a Claude scheduled task reads the news feeds, scores the new stories, runs `scripts/update_site.py`, and commits the updated `stories.json` and `feed.xml` here. GitHub Pages then republishes the site.

```
news feeds ──► Claude scheduled task (every 6 h) ──► git push stories.json
                                                         │
                         phone / browser ◄── GitHub Pages ◄┘
```

## What's in the repo

| File | What it does |
| --- | --- |
| `index.html` | The whole reader: filters, scores, saved stories, sharing |
| `stories.json` | The current stories (the only file that changes every run) |
| `feed.xml` | An RSS feed of stories scoring 6 or more |
| `sw.js`, `manifest.webmanifest`, `icons/` | Make it installable on phones and readable offline |
| `scripts/update_site.py` | Merges new stories, removes duplicates and stories older than 10 days, writes `stories.json` and `feed.xml` |
| `site.json` | Site name and address, used in the RSS feed |
| `UPDATE_PROMPT.md` | The exact instruction the scheduled task follows |

## Setup, step by step

You need a free GitHub account and about ten minutes.

### 1. Create a GitHub account
Go to [github.com/signup](https://github.com/signup) and create a free account. Remember your username; it becomes part of the site's address.

### 2. Create the repository
1. Click **+** (top right) → **New repository**.
2. Repository name: `kseniias-good-news`.
3. Choose **Public** (GitHub Pages is free for public repositories).
4. Leave "Add a README" **unticked**, so the repository starts empty.
5. Click **Create repository**.

### 3. Let Claude reach GitHub
In claude.ai, open **Settings → Connectors** and connect **GitHub**. When GitHub asks which repositories Claude may access, include `kseniias-good-news`.

### 4. Put the files in the repository
**Easiest:** tell Claude your GitHub username in the chat where this was built. Claude pushes the files for you and checks it can write to the repository, which the scheduled task needs anyway.

**By hand instead:** unzip `kseniias-good-news.zip`. In your new repository click **uploading an existing file**, drag in everything inside the unzipped folder (including the `icons` and `scripts` folders), and click **Commit changes**.

### 5. Turn on GitHub Pages
1. In the repository, open **Settings → Pages**.
2. Under **Build and deployment**, set Source to **Deploy from a branch**.
3. Choose branch **main** and folder **/ (root)**, then **Save**.
4. After a minute or two the page shows your address: `https://YOUR-USERNAME.github.io/kseniias-good-news/`.

### 6. Set the site address
Edit `site.json` and replace `YOUR-GITHUB-NAME` with your username (click the file, then the pencil icon, then **Commit changes**). Claude does this for you in step 4's easy route.

### 7. Switch the scheduled task to the website
Tell Claude the site is live. Claude changes the existing 6-hour scheduled task so it updates this repository using `UPDATE_PROMPT.md`. Wait for the next run (a few minutes past 02:00, 08:00, 14:00 and 20:00 Paris summer time) and check that "Updated … ago" at the top of the page changes.

### 8. Install it on your phone
- **iPhone:** open the address in Safari → Share button → **Add to Home Screen**.
- **Android:** open it in Chrome → **Install app**, or ⋮ → **Add to Home screen**.

### 9. Share it
Send the address to anyone. No account or sign-in is needed to read it. Saved stories are kept on each person's own device.

## Changing things

- **Sources:** edit the feed list in `UPDATE_PROMPT.md` and ask Claude to update the scheduled task with it. Feeds must be readable by Claude's web fetch tool (the BBC's site blocks it, for example).
- **Scoring rules:** edit step 5 of `UPDATE_PROMPT.md` the same way.
- **How long stories stay:** `KEEP_DAYS` at the top of `scripts/update_site.py`.
- **Look and feel:** everything is in `index.html`.
- **Your own domain:** Settings → Pages → Custom domain (optional, paid domain).

## If something goes wrong

- **The page says "Stories didn't load":** check that `stories.json` exists in the repository and that Pages is on (step 5).
- **"Updated" stops moving:** open the scheduled task in Claude and read its last run. The most common cause is that Claude lost access to the repository; reconnect GitHub in claude.ai Settings → Connectors.
- **A story is wrong or shouldn't be there:** delete it from `stories.json` on GitHub (pencil icon → remove the story's `{ … }` block → Commit changes), or ask Claude to.

## Running the script yourself

```
python3 scripts/update_site.py list
python3 scripts/update_site.py add new_stories.json --sources "Positive News,ScienceDaily"
```

Only the Python standard library is needed.

## Costs

GitHub Pages is free for public repositories. Updates use your Claude plan through the scheduled task; nothing else is billed.

## Content

Summaries are written in Claude's own words and kept to a sentence or two; every story links to the original publisher for the full article. The code is under the MIT licence (see `LICENSE`).
