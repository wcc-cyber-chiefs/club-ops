"""Shared helpers for every club-ops bot.

Everything here uses the Python standard library plus PyYAML, so the
workflows only need `pip install pyyaml`.

Environment variables:
  DRY_RUN=1          Print what would be posted instead of calling Discord.
  CLUB_DATA_DIR      Where the YAML config and state live (default: data/).
  WEBHOOK_*          Discord webhook URLs, injected from GitHub Actions secrets.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("CLUB_DATA_DIR", REPO_ROOT / "data"))
STATE_DIR = DATA_DIR / "state"
DRY_RUN = os.environ.get("DRY_RUN", "").lower() in {"1", "true", "yes"}

# Generic client name. Never put a personal email or name here.
USER_AGENT = "wcc-cyber-club-bot/1.0 (+https://github.com/{})".format(
    os.environ.get("GITHUB_REPOSITORY", "club-ops")
)


# ---------------------------------------------------------------- config

def load_yaml(name: str) -> dict | list:
    """Load data/<name>. Missing or empty files return an empty dict."""
    path = DATA_DIR / name
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def discord_config() -> dict:
    return load_yaml("discord.yml")


def club_tz() -> ZoneInfo:
    return ZoneInfo(discord_config().get("timezone", "America/Chicago"))


def now_local() -> datetime:
    override = os.environ.get("CLUB_NOW")  # for tests: "2026-11-16T09:00"
    if override:
        return datetime.fromisoformat(override).replace(tzinfo=club_tz())
    return datetime.now(club_tz())


# ----------------------------------------------------------------- state

def load_state(name: str, default):
    path = STATE_DIR / name
    if not path.exists():
        return default
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def save_state(name: str, data) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    path = STATE_DIR / name
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, sort_keys=True)
        fh.write("\n")


# ------------------------------------------------------------------ http

def http_get(url: str, timeout: int = 30) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def http_get_json(url: str, timeout: int = 30):
    return json.loads(http_get(url, timeout).decode("utf-8"))


# --------------------------------------------------------------- discord

def role_mention(key: str | None) -> tuple[str, list[str]]:
    """Return ('<@&id>', [id]) for a role key in discord.yml, or ('', [])."""
    if not key:
        return "", []
    role_id = str((discord_config().get("roles") or {}).get(key) or "").strip()
    if not role_id:
        return "", []
    return f"<@&{role_id}>", [role_id]


def channel_settings(channel: str) -> dict:
    channels = discord_config().get("channels") or {}
    if channel not in channels:
        raise KeyError(f"Channel '{channel}' is not defined in data/discord.yml")
    return channels[channel]


def post(
    channel: str,
    content: str = "",
    embeds: list[dict] | None = None,
    thread_name: str | None = None,
    thread_id: str | None = None,
    role_ids: list[str] | None = None,
) -> dict | None:
    """Post to a channel defined in data/discord.yml.

    - Forum channels need thread_name (it becomes the post title).
    - thread_id posts a reply inside an existing thread or forum post.
    - Only the roles in role_ids can be pinged; @everyone/@here and user
      pings in submitted text are always suppressed.

    Returns the created message (Discord JSON) or None in dry-run.
    """
    settings = channel_settings(channel)
    env_name = settings["webhook_secret"]
    payload: dict = {
        "content": content[:2000],
        "allowed_mentions": {"parse": [], "roles": role_ids or []},
    }
    if embeds:
        payload["embeds"] = embeds[:10]
    if settings.get("forum") and not thread_id:
        payload["thread_name"] = (thread_name or "Club post")[:100]

    if DRY_RUN:
        print(f"\n--- DRY RUN: {channel} ({env_name}) thread={thread_id} ---")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return None

    url = os.environ.get(env_name, "").strip()
    if not url:
        # Fail instead of skipping: a skipped post would still be recorded as
        # "done" in the state file and never retried.
        raise RuntimeError(
            f"GitHub secret {env_name} is not set, so nothing was posted to #{channel}. "
            "Add it under Settings > Secrets and variables > Actions (see HANDBOOK.md)."
        )

    query = {"wait": "true"}
    if thread_id:
        query["thread_id"] = thread_id
    full_url = f"{url}?{urllib.parse.urlencode(query)}"
    body = json.dumps(payload).encode("utf-8")

    for attempt in range(5):
        req = urllib.request.Request(
            full_url,
            data=body,
            method="POST",
            headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                time.sleep(1)  # stay well under webhook rate limits
                return json.loads(resp.read().decode("utf-8") or "null")
        except urllib.error.HTTPError as err:
            if err.code == 429:
                retry = json.loads(err.read().decode("utf-8") or "{}").get("retry_after", 2)
                time.sleep(float(retry) + 0.5)
                continue
            detail = err.read().decode("utf-8", "replace")[:300]
            raise RuntimeError(f"Discord returned {err.code} for #{channel}: {detail}") from err
    raise RuntimeError(f"Gave up posting to #{channel} after repeated rate limits")


def truncate(text: str, limit: int) -> str:
    text = (text or "").strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def fail(msg: str) -> None:
    print(f"::error::{msg}")
    sys.exit(1)
