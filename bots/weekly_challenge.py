"""Weekly challenge: release, wrap-up, and the flag-checker data.

Runs daily. Each run:
  1. Rebuilds docs/flags.json (flag hashes for the GitHub Pages checker).
  2. Releases any challenge whose `release` date has arrived (new forum post).
  3. Wraps any challenge whose `wrap` date has arrived (reply in its thread).

A challenge lives in challenges/<slug>/:
  challenge.yml   title, author, category, difficulty, release, wrap, solution_url?
  README.md       the prompt members read
  files/          anything they download (optional)
  flag.sha256     sha256 hex of the exact flag string, nothing else

Solutions (solve.py, writeup) do NOT go in this public repo.
See HANDBOOK.md, "Weekly challenges".
"""

from __future__ import annotations

import json
import os
import re
from datetime import date

import yaml

from common import REPO_ROOT, load_state, now_local, post, role_mention, save_state, truncate

CHALLENGES = REPO_ROOT / "challenges"
FLAGS_JSON = REPO_ROOT / "docs" / "flags.json"
STATE_FILE = "challenges_posted.json"
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def repo_urls() -> tuple[str, str]:
    repo = os.environ.get("GITHUB_REPOSITORY", "OWNER/club-ops")
    owner, name = repo.split("/", 1)
    pages = os.environ.get("PAGES_URL") or f"https://{owner.lower()}.github.io/{name}"
    return f"https://github.com/{repo}", pages.rstrip("/")


def load_challenges() -> list[dict]:
    out = []
    if not CHALLENGES.exists():
        return out
    for d in sorted(p for p in CHALLENGES.iterdir() if p.is_dir()):
        meta_path = d / "challenge.yml"
        if not meta_path.exists():
            continue
        meta = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
        flag_path = d / "flag.sha256"
        meta["slug"] = d.name
        meta["dir"] = d
        meta["sha256"] = flag_path.read_text(encoding="utf-8").strip().lower() if flag_path.exists() else ""
        readme = d / "README.md"
        meta["readme"] = readme.read_text(encoding="utf-8") if readme.exists() else ""
        out.append(meta)
    return out


def build_flags_json(challenges: list[dict], today: date) -> None:
    """Only released challenges are listed, so the checker can't be used to
    probe next week's flag early."""
    data = {}
    for c in challenges:
        if HEX64.match(c["sha256"]) and date.fromisoformat(str(c["release"])) <= today:
            data[c["slug"]] = {"title": c.get("title", c["slug"]), "sha256": c["sha256"]}
    FLAGS_JSON.parent.mkdir(parents=True, exist_ok=True)
    FLAGS_JSON.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def strip_frontmatter_heading(md: str) -> str:
    lines = md.strip().splitlines()
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    return "\n".join(lines).strip()


def main() -> None:
    today = now_local().date()
    repo_url, pages_url = repo_urls()
    posted: dict = load_state(STATE_FILE, {})
    challenges = load_challenges()
    build_flags_json(challenges, today)

    for c in challenges:
        slug = c["slug"]
        release = date.fromisoformat(str(c["release"]))
        wrap = date.fromisoformat(str(c["wrap"]))
        record = posted.get(slug, {})

        if release <= today and "released" not in record and wrap >= today:
            ping, role_ids = role_mention("challenge")
            files_link = f"{repo_url}/tree/main/challenges/{slug}"
            checker = f"{pages_url}/check/?c={slug}"
            body = truncate(strip_frontmatter_heading(c["readme"]), 1400)
            content = (
                f"{ping} **{c.get('title', slug)}**\n"
                f"{c.get('category', 'misc').title()} · {c.get('difficulty', 'beginner').title()} · "
                f"by {c.get('author', 'the club')}\n\n"
                f"{body}\n\n"
                f"**Files:** <{files_link}>\n"
                f"**Check your flag:** <{checker}>\n"
                f"Closes {wrap.strftime('%a %b %-d')}. Hints welcome, spoilers in ||spoiler tags|| only."
            ).strip()
            msg = post("challenge", content=content,
                       thread_name=f"{release.strftime('%b %-d')} · {c.get('title', slug)}",
                       role_ids=role_ids)
            record["released"] = today.isoformat()
            if msg and msg.get("channel_id"):
                record["thread_id"] = msg["channel_id"]  # forum post = its own thread
            posted[slug] = record

        if wrap <= today and "released" in record and "wrapped" not in record:
            text = (
                f"**Challenge closed.** Share how you solved **{c.get('title', slug)}** below "
                "(spoiler tags still appreciated for anyone catching up)."
            )
            if c.get("solution_url"):
                text += f"\nOfficial writeup: <{c['solution_url']}>"
            post("challenge", content=text, thread_id=record.get("thread_id"),
                 thread_name=f"Wrap-up · {c.get('title', slug)}")
            record["wrapped"] = today.isoformat()
            posted[slug] = record

    save_state(STATE_FILE, posted)


if __name__ == "__main__":
    main()
