"""Check the data files and challenges before a pull request merges.

Runs on every PR (validate workflow). Prints every problem it finds and
exits non-zero if there are any, so typos get caught in review instead
of at 8 a.m. when the bot runs.
"""

from __future__ import annotations

import re
import sys
from datetime import date, datetime

import yaml

from common import DATA_DIR, REPO_ROOT

errors: list[str] = []
CHANNELS = set()
ROLES = set()


def err(where: str, msg: str) -> None:
    errors.append(f"{where}: {msg}")


def load(name: str):
    path = DATA_DIR / name
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except FileNotFoundError:
        err(name, "file is missing")
    except yaml.YAMLError as exc:
        err(name, f"is not valid YAML ({exc})")
    except ValueError as exc:  # PyYAML rejects impossible dates like 2026-13-40
        err(name, f"has an invalid date ({exc})")
    return {}


def check_date(where: str, value, fmt: str | None = None) -> None:
    try:
        if fmt:
            datetime.strptime(str(value), fmt)
        elif not isinstance(value, date):
            date.fromisoformat(str(value))
    except ValueError:
        err(where, f"'{value}' is not a valid date ({fmt or 'YYYY-MM-DD'})")


def unique_ids(name: str, rows: list) -> None:
    seen = set()
    for i, row in enumerate(rows):
        rid = (row or {}).get("id")
        if not rid:
            err(f"{name}[{i}]", "missing id")
        elif rid in seen:
            err(f"{name}[{i}]", f"duplicate id '{rid}'")
        seen.add(rid)


def main() -> None:
    discord = load("discord.yml")
    CHANNELS.update((discord.get("channels") or {}).keys())
    ROLES.update((discord.get("roles") or {}).keys())
    for role, value in (discord.get("roles") or {}).items():
        if value and not re.fullmatch(r"\d{15,21}", str(value)):
            err("discord.yml", f"role '{role}' should be a numeric Discord role ID")
    for ch, cfg in (discord.get("channels") or {}).items():
        if not str((cfg or {}).get("webhook_secret", "")).startswith("WEBHOOK_"):
            err("discord.yml", f"channel '{ch}' webhook_secret should be a secret NAME like WEBHOOK_X")
    if "discord.com/api/webhooks" in (DATA_DIR / "discord.yml").read_text(encoding="utf-8"):
        err("discord.yml", "contains a webhook URL. Remove it and store it as a GitHub secret.")

    items = (load("calendar.yml").get("items") or [])
    unique_ids("calendar.yml items", items)
    for i, it in enumerate(items):
        where = f"calendar.yml '{it.get('id', i)}'"
        for field in ("title", "date"):
            if not it.get(field):
                err(where, f"missing {field}")
        if it.get("date"):
            check_date(where, it["date"])
        if it.get("channel", "announcements") not in CHANNELS:
            err(where, f"channel '{it.get('channel')}' is not in discord.yml")
        if it.get("role") and it["role"] not in ROLES:
            err(where, f"role '{it['role']}' is not in discord.yml")

    sessions = (load("sessions.yml").get("sessions") or [])
    unique_ids("sessions.yml", sessions)
    for i, s in enumerate(sessions):
        where = f"sessions.yml '{s.get('id', i)}'"
        if not s.get("title"):
            err(where, "missing title")
        check_date(where, s.get("start", ""), "%Y-%m-%d %H:%M")

    programs = (load("programs.yml").get("programs") or [])
    unique_ids("programs.yml", programs)
    for i, p in enumerate(programs):
        where = f"programs.yml '{p.get('id', i)}'"
        if not str(p.get("url", "")).startswith(("http://", "https://")):
            err(where, "url must start with http:// or https://")
        if p.get("deadline"):
            check_date(where, p["deadline"])

    challenges = REPO_ROOT / "challenges"
    for d in sorted(p for p in challenges.iterdir() if p.is_dir()) if challenges.exists() else []:
        where = f"challenges/{d.name}"
        meta_path = d / "challenge.yml"
        if not meta_path.exists():
            err(where, "missing challenge.yml")
            continue
        meta = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
        for field in ("title", "release", "wrap"):
            if not meta.get(field):
                err(where, f"challenge.yml missing {field}")
        if meta.get("release") and meta.get("wrap"):
            check_date(where, meta["release"])
            check_date(where, meta["wrap"])
            try:
                if date.fromisoformat(str(meta["wrap"])) < date.fromisoformat(str(meta["release"])):
                    err(where, "wrap is before release")
            except ValueError:
                pass
        if not (d / "README.md").exists():
            err(where, "missing README.md")
        flag = d / "flag.sha256"
        if not flag.exists() or not re.fullmatch(r"[0-9a-f]{64}", flag.read_text(encoding="utf-8").strip()):
            err(where, "flag.sha256 must hold one lowercase sha256 hex string (see HANDBOOK.md)")
        for leaked in ("solve.py", "SOLUTION.md", "flag.txt"):
            if (d / leaked).exists():
                err(where, f"{leaked} must not be in this public repo; keep solutions in the private solutions repo")

    if errors:
        print("Found problems:\n" + "\n".join(f"  - {e}" for e in errors))
        sys.exit(1)
    print("All club-ops data files look good.")


if __name__ == "__main__":
    main()
