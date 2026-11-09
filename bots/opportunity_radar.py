"""Post new security internships/jobs and curated programs to #jobs-postings.

Sources:
  1. SimplifyJobs listings.json feeds (data/feeds.yml), filtered by keyword.
  2. data/programs.yml, hand-curated by officers and alumni.

State: data/state/seen_opportunities.json (ids already posted or skipped).
"""

from __future__ import annotations

import re
import time
from datetime import datetime, timezone

from common import http_get_json, load_state, load_yaml, post, role_mention, save_state, truncate

STATE_FILE = "seen_opportunities.json"


def keyword_match(title: str, include: list[str], exclude: list[str]) -> bool:
    t = title.lower()
    if any(x.lower() in t for x in exclude):
        return False
    for term in include:
        term = term.lower()
        # Short terms (soc, iam, grc) must be whole words so "Social" or
        # "Associate" don't match.
        if len(term) <= 4:
            if re.search(rf"\b{re.escape(term)}\b", t):
                return True
        elif term in t:
            return True
    return False


def listing_key(item: dict) -> str:
    return str(item.get("id") or item.get("url") or f"{item.get('company_name')}|{item.get('title')}")


def fetch_listings(sources: list[dict]) -> list[tuple[dict, dict]]:
    out = []
    for src in sources:
        try:
            data = http_get_json(src["url"])
        except Exception as exc:  # one bad feed shouldn't stop the rest
            print(f"::warning::Could not fetch {src.get('name')}: {exc}")
            continue
        if isinstance(data, dict):
            data = data.get("listings") or data.get("data") or []
        for item in data:
            if isinstance(item, dict):
                out.append((src, item))
    return out


def listing_embed(src: dict, item: dict) -> dict:
    locations = item.get("locations") or []
    if isinstance(locations, str):
        locations = [locations]
    terms = item.get("terms") or []
    if isinstance(terms, str):
        terms = [terms]
    fields = []
    if locations:
        fields.append({"name": "Location", "value": truncate(", ".join(locations), 200), "inline": True})
    if terms:
        fields.append({"name": "Term", "value": truncate(", ".join(terms), 100), "inline": True})
    posted = item.get("date_posted")
    if isinstance(posted, (int, float)):
        fields.append({
            "name": "Posted",
            "value": datetime.fromtimestamp(posted, tz=timezone.utc).strftime("%b %d, %Y"),
            "inline": True,
        })
    return {
        "title": truncate(f"{item.get('company_name', 'Unknown')} — {item.get('title', 'Role')}", 250),
        "url": item.get("url") or src.get("repo"),
        "fields": fields,
        "footer": {"text": f"Source: {src.get('name')} (SimplifyJobs)"},
    }


def program_embed(p: dict) -> dict:
    fields = [{"name": "Type", "value": str(p.get("type", "opportunity")).title(), "inline": True}]
    if p.get("deadline"):
        fields.append({"name": "Deadline", "value": str(p["deadline"]), "inline": True})
    if p.get("location"):
        fields.append({"name": "Location", "value": truncate(str(p["location"]), 200), "inline": True})
    return {
        "title": truncate(f"{p.get('org', '')} — {p.get('title', '')}".strip(" —"), 250),
        "url": p.get("url"),
        "description": truncate(str(p.get("notes", "")), 500) or None,
        "fields": fields,
        "footer": {"text": "Curated by the club (data/programs.yml)"},
    }


def main() -> None:
    feeds = load_yaml("feeds.yml").get("opportunities", {})
    include = feeds.get("include", [])
    exclude = feeds.get("exclude", [])
    max_age = int(feeds.get("max_age_days", 14)) * 86400
    max_posts = int(feeds.get("max_posts_per_run", 8))

    seen: list[str] = load_state(STATE_FILE, [])
    seen_set = set(seen)
    now = time.time()

    to_post: list[dict] = []

    # Curated programs first: these are the highest-signal posts.
    for p in (load_yaml("programs.yml").get("programs") or []):
        key = f"program:{p.get('id')}"
        if p.get("id") and key not in seen_set:
            to_post.append({"key": key, "embed": program_embed(p)})

    for src, item in fetch_listings(feeds.get("sources", [])):
        key = listing_key(item)
        if key in seen_set:
            continue
        if item.get("active") is False or item.get("is_visible") is False:
            continue
        if not keyword_match(str(item.get("title", "")), include, exclude):
            continue
        posted = item.get("date_posted")
        if isinstance(posted, (int, float)) and now - posted > max_age:
            seen_set.add(key)  # too old: remember so we never post it
            seen.append(key)
            continue
        to_post.append({"key": key, "embed": listing_embed(src, item)})

    if not to_post:
        print("No new opportunities.")
        save_state(STATE_FILE, seen[-5000:])
        return

    batch, overflow = to_post[:max_posts], to_post[max_posts:]
    ping, role_ids = role_mention("opportunities")
    intro = f"{ping} {len(batch)} new opportunit{'y' if len(batch) == 1 else 'ies'}".strip()

    # Discord allows 10 embeds per message; send in groups.
    for i in range(0, len(batch), 10):
        group = batch[i:i + 10]
        post(
            "jobs",
            content=intro if i == 0 else "",
            embeds=[g["embed"] for g in group],
            thread_name=intro.replace(ping, "").strip() or "New opportunities",
            role_ids=role_ids if i == 0 else [],
        )

    if overflow:
        repos = sorted({s.get("repo") for s in feeds.get("sources", []) if s.get("repo")})
        post("jobs", content=(
            f"+{len(overflow)} more matching roles today. Browse the full lists: "
            + " · ".join(f"<{r}>" for r in repos)
        ), thread_name="More matching roles")

    for entry in to_post:  # overflow counts as handled so it isn't re-posted tomorrow
        seen.append(entry["key"])
    save_state(STATE_FILE, seen[-5000:])
    print(f"Posted {len(batch)}, summarized {len(overflow)}.")


if __name__ == "__main__":
    main()
