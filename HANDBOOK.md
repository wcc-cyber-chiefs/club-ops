# club-ops Handbook

This repo runs the WCC Cyber Club Discord's automation. It is owned by the club's GitHub organization, not by any one student, and it costs nothing: GitHub Actions on a public repo, GitHub Pages, and Discord webhooks.

If you just became a club officer and someone handed you this, start with **"Your first week as an owner"**.

---

## What runs, and where it posts

| Workflow | When (Central time) | Posts to | What it does |
| --- | --- | --- | --- |
| Opportunity radar | Daily ~8:15 AM, and when `programs.yml` changes | #jobs-postings | New security internships and new-grad roles from the SimplifyJobs lists, plus anything officers add to `data/programs.yml` |
| CTF radar | Mondays ~8:35 AM | #events | Online CTFs in the next 14 days from CTFtime, beginner-friendly ones flagged |
| News digest | Daily ~7:45 AM | #cyber-news | New headlines from a few security feeds, plus new CISA Known Exploited Vulnerabilities |
| Deadline reminders | Daily ~9:05 AM | #announcements, #ncl, #skills-usa... | Reminders 14, 3 and 1 days before each date in `data/calendar.yml` |
| Session reminders | Every 30 min | #announcements | About 3 days before and about 1 hour before each session in `data/sessions.yml` |
| Weekly challenge | Daily ~9:20 AM, and when a challenge is merged | #weekly-challenge | Releases challenges on their `release` date and closes them on their `wrap` date |
| Submission intake | When an officer labels an issue `approved` | #jobs-postings | Posts opportunities members submit through the issue form |
| Validate | Every pull request | — | Catches typos in the data files before they merge |

Any workflow that fails posts a link to its log in **#mods**.

GitHub's clock runs in UTC and scheduled runs can start a few minutes late when GitHub is busy. During daylight saving time (March–November) everything runs an hour later by the clock than listed above.

---

## Who owns what

- **GitHub organization:** at least two owners at all times. One should be the faculty advisor, who stays with the club across graduations.
- **Discord server:** one owner (the current president, or the faculty advisor if there is no student leader). The advisor and at least one officer have Admin.
- **Webhook URLs:** live only in GitHub secrets (Settings → Secrets and variables → Actions). Never in a file, a Discord message or a screenshot.
- **Solutions:** in the **private** `club-solutions` repo, never in this public one.

---

## One-time setup

Whoever sets this up the first time does these steps once. Later officers can skip to "Your first week as an owner."

### 1. Push the code
Create a **public** repo named `club-ops` in the club org, then push this folder to its `main` branch. Create a **private** repo named `club-solutions` and push the solutions folder there.

### 2. Create the Discord channel the bots need
Under **Learning Resources**, create a **Forum** channel named `weekly-challenge`. Everything else already exists.

### 3. Create the webhooks (one per channel)
For each channel below: **Edit Channel → Integrations → Webhooks → New Webhook**, name it `club-ops`, then **Copy Webhook URL**.

| Discord channel | GitHub secret name |
| --- | --- |
| #announcements | `WEBHOOK_ANNOUNCEMENTS` |
| #jobs-postings | `WEBHOOK_JOBS` |
| #events | `WEBHOOK_EVENTS` |
| #ncl | `WEBHOOK_NCL` |
| #skills-usa | `WEBHOOK_SKILLSUSA` |
| #cyber-news | `WEBHOOK_NEWS` |
| #weekly-challenge | `WEBHOOK_CHALLENGE` |
| #mods | `WEBHOOK_MODS` |

In the `club-ops` repo: **Settings → Secrets and variables → Actions → New repository secret**. Paste each URL under its name. Do one channel at a time so you never have a webhook URL sitting in a notes app.

### 4. Turn on the flag checker website
**Settings → Pages → Build and deployment → Source: Deploy from a branch → Branch: `main`, folder `/docs` → Save.** After a minute it's live at `https://<org-name>.github.io/club-ops/`.

### 5. Create the issue labels
**Issues → Labels → New label**, three times: `approved`, `opportunity`, `challenge-idea`.

### 6. Add the ping roles (optional but recommended)
In Discord, create opt-in roles `@session-pings`, `@challenge-pings`, `@ctf-pings`, `@opportunity-pings` and hand them out through **Server Settings → Onboarding** (or a pinned message in #welcome-and-rules). Then turn on **User Settings → Advanced → Developer Mode**, right-click each role → **Copy Role ID**, and paste the IDs into `data/discord.yml` under `roles:`. Empty IDs are fine; the bots just won't ping.

### 7. Test every workflow
**Actions tab → pick a workflow → Run workflow.** Run each once and check its channel. The news digest posts nothing on its very first run on purpose (it records what already exists so it doesn't flood the channel).

---

## Your first week as an owner

1. Make sure you're an **Owner** in the GitHub org (org page → People) and an **Admin** in Discord.
2. Read this handbook top to bottom (10 minutes).
3. Add next semester's sessions to `data/sessions.yml` and known deadlines to `data/calendar.yml` by pull request. Watch the **Validate** check go green, then merge.
4. Open the **Actions** tab. If any workflow shows "This scheduled workflow is disabled because there hasn't been activity…", click **Enable workflow**.
5. Queue at least four weekly challenges (see below).

---

## Everyday tasks

All of these are edits to files in `data/` or `challenges/`. Use a pull request so the Validate check runs; you can do it all in the GitHub website (open the file → pencil icon → "Create a new branch and start a pull request").

### Add a session
Add an entry to `data/sessions.yml`. Time is club time, 24-hour: `start: "2026-11-18 18:00"`. Create a matching Discord event and paste its link into `event_url`.

### Add a deadline or competition date
Add an entry to `data/calendar.yml`. Pick the channel it belongs in (`ncl`, `skills-usa`, `announcements`...). Never change an `id` after it has posted.

### Add an apprenticeship, scholarship or local opportunity
Add an entry to `data/programs.yml`. It posts to #jobs-postings right after you merge. This is the most valuable thing an officer or alum can do here: the automatic feeds only catch big-company internships.

### Approve a member's opportunity
Members use **Issues → New issue → Share an opportunity**. Check the link is real and relevant, then add the **`approved`** label. The bot posts it and closes the issue. Not a fit? Comment why and close it.

### Weekly challenges
Each challenge is a folder in `challenges/` named `YYYY-MM-DD-short-name` (the release Monday):

```
challenges/2026-11-30-log-hunt/
  challenge.yml   title, author, category, difficulty, release (Monday), wrap (Sunday)
  README.md       the prompt members read
  files/          what they download (optional)
  flag.sha256     made by bots/hash_flag.py; never the flag itself
```

1. Write the challenge and its `solve.py` + `SOLUTION.md` in the **private** `club-solutions` repo first.
2. Run `python bots/hash_flag.py challenges/<slug>` to create `flag.sha256`. It asks for the flag with hidden input.
3. Run the challenge's `solve.py` and confirm the sha256 it prints matches `flag.sha256`.
4. Open a pull request with the challenge folder (no solution files: Validate blocks them).
5. Merge any time before its release date. The bot posts it on release day and closes it on wrap day.
6. After it wraps, publish the writeup and set `solution_url` in its `challenge.yml`.

Flags use the format `WCC{...}` and should end with a random suffix (like `_4e9b`) so nobody can guess them from the public hash. This repo is public, so a determined member could read a queued challenge before release. That's acceptable for a club; if it matters for one, merge it the morning it releases.

**Before you leave for a break, queue challenges through the first two weeks of next semester.** A server that goes silent over break is hard to restart.

---

## Semester checklists

### August (fall start)
- [ ] Enable any disabled workflows (Actions tab).
- [ ] In `data/feeds.yml`, bump the SimplifyJobs repo to the new season (e.g. `Summer2027-Internships` → `Summer2028-Internships`). Open the new repo first to confirm it exists and copy the Raw URL of its `.github/scripts/listings.json`.
- [ ] Confirm GitHub org owners and Discord admins are current students or the advisor. Remove graduates (move them to the @Alumni role in Discord).
- [ ] Load the semester's sessions and deadlines.

### January (spring start)
- [ ] Enable any disabled workflows.
- [ ] Load the semester's sessions and deadlines.
- [ ] Check which channels got no activity last month and consider archiving them.

---

## When something breaks

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| #mods says a workflow failed | A feed changed or a webhook was deleted | Open the log link. A 404 on a feed → update its URL in `data/feeds.yml`. "Discord returned 401/404" → recreate that channel's webhook and update the secret |
| Nothing posts at all for weeks | Scheduled workflows were auto-disabled | Actions tab → each workflow → **Enable workflow** |
| Log says "WEBHOOK_X is not set" | Secret missing or misspelled | Re-add it under the exact name in the table above |
| "Save state" step fails with 403 | Actions can't push | Settings → Actions → General → Workflow permissions → **Read and write** |
| "Save state" fails after you protected `main` | Branch protection blocks the bot | Add a bypass for GitHub Actions, or remove the "require PR" rule |
| Bot posted something twice | State file was edited or a push failed | Harmless; check the "Save state" step in the log |
| A webhook URL got pasted publicly | Anyone can post as the bot | Discord: delete that webhook, create a new one, update the secret. Do it right away |
| CTF radar fails with 403 | CTFtime blocked the request | Usually temporary. If it persists, check ctftime.org/api for changes |

To pause any bot: Actions tab → the workflow → "…" menu → **Disable workflow**.

---

## Handing off to the next leader

Do this before you leave, ideally a few weeks before:

1. Add the next leader as a GitHub org **Owner** (org → People → Invite member → Owner).
2. Make them a Discord **Admin**. On your last week, transfer server ownership: Server Settings → Members → your successor → "…" → Transfer Ownership. If there's no student leader, transfer it to the faculty advisor.
3. Have them merge one data-file change and run one workflow manually while you watch.
4. Queue challenges and deadlines past your graduation.
5. Remove yourself as an owner and admin. Take the @Alumni role and keep helping in #jobs-postings if you like.

Nothing here should ever depend on a personal account, a personal computer or a paid service. If you add something new, keep it that way.
