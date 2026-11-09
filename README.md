# club-ops

Free, club-owned automation for the WCC Cyber Club Discord: weekly challenges, CTF and job radars, security news, and session and deadline reminders.

Everything runs on GitHub Actions and posts through Discord webhooks. No server, no paid accounts, nothing tied to one student.

- **Officers:** read [HANDBOOK.md](HANDBOOK.md).
- **Members:** check flags at the club's GitHub Pages site (`/check/`), share opportunities with **Issues → New issue → Share an opportunity**, and pitch challenges with **Pitch a weekly challenge**.

```
.github/workflows/   one file per bot (schedules live here)
.github/ISSUE_TEMPLATE/  opportunity and challenge-idea forms
bots/                the Python behind each workflow
data/                club-edited config: sessions, deadlines, programs, feeds, Discord wiring
data/state/          what the bots have already posted (written by the bots)
challenges/          weekly challenges (no solutions; those live in the private repo)
docs/                GitHub Pages site and flag checker
```

Run any bot locally without posting: `pip install pyyaml && DRY_RUN=1 python bots/ctf_radar.py`
