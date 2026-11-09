"""Deadline and session reminders.

  python reminders.py deadlines   # daily: data/calendar.yml
  python reminders.py sessions    # every 30 min: data/sessions.yml

Both are idempotent: data/state/reminders_sent.json records what went out,
so a late or repeated run never double-posts.
"""

from __future__ import annotations

import sys
from datetime import date, datetime

from common import club_tz, fail, load_state, load_yaml, now_local, post, role_mention, save_state, truncate

STATE_FILE = "reminders_sent.json"
DEFAULT_REMIND_DAYS = [14, 3, 1]


def as_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def run_deadlines(sent: dict) -> None:
    today = now_local().date()
    for item in (load_yaml("calendar.yml").get("items") or []):
        item_id = item.get("id")
        if not item_id:
            continue
        days_left = (as_date(item["date"]) - today).days
        if days_left < 0:
            continue
        thresholds = sorted(item.get("remind_days") or DEFAULT_REMIND_DAYS)
        due = [t for t in thresholds if days_left <= t]
        if not due:
            continue
        tightest = min(due)  # if a run was missed, send only the most urgent one
        key = f"deadline:{item_id}:{tightest}"
        if key in sent:
            continue

        when = "today" if days_left == 0 else ("tomorrow" if days_left == 1 else f"in {days_left} days")
        ping, role_ids = role_mention(item.get("role"))
        desc = truncate(str(item.get("notes", "")), 500)
        embed = {
            "title": truncate(item["title"], 250),
            "url": item.get("url"),
            "description": desc or None,
            "fields": [{"name": "Date", "value": as_date(item["date"]).strftime("%a %b %-d, %Y"), "inline": True}],
        }
        post(item.get("channel", "announcements"),
             content=f"{ping} Reminder: **{item['title']}** is {when}.".strip(),
             embeds=[embed], thread_name=item["title"], role_ids=role_ids)
        for t in thresholds:  # mark this and every wider threshold as handled
            if t >= tightest:
                sent[f"deadline:{item_id}:{t}"] = today.isoformat()


def run_sessions(sent: dict) -> None:
    now = now_local()
    tz = club_tz()
    for s in (load_yaml("sessions.yml").get("sessions") or []):
        sid = s.get("id")
        if not sid:
            continue
        start = datetime.strptime(str(s["start"]), "%Y-%m-%d %H:%M").replace(tzinfo=tz)
        minutes_until = (start - now).total_seconds() / 60
        if minutes_until <= 0:
            continue

        ping, role_ids = role_mention("sessions")
        when = start.strftime("%A %b %-d at %-I:%M %p CT")
        fields = [{"name": "When", "value": when, "inline": True},
                  {"name": "Where", "value": s.get("where", "Discord"), "inline": True}]
        if s.get("presenter"):
            fields.append({"name": "Presenter", "value": s["presenter"], "inline": True})
        embed = {
            "title": truncate(s["title"], 250),
            "url": s.get("event_url") or None,
            "description": truncate(str(s.get("description", "")), 1000) or None,
            "fields": fields,
        }

        if minutes_until <= 75 and f"session:{sid}:soon" not in sent:
            post("announcements", content=f"{ping} Starting in about an hour: **{s['title']}**".strip(),
                 embeds=[embed], role_ids=role_ids)
            sent[f"session:{sid}:soon"] = now.isoformat(timespec="minutes")
            sent[f"session:{sid}:announce"] = sent.get(f"session:{sid}:announce", "skipped")
        elif minutes_until <= 72 * 60 and f"session:{sid}:announce" not in sent:
            post("announcements", content=f"{ping} Next club session: **{s['title']}**, {when}".strip(),
                 embeds=[embed], role_ids=role_ids)
            sent[f"session:{sid}:announce"] = now.isoformat(timespec="minutes")


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    sent: dict = load_state(STATE_FILE, {})
    if mode == "deadlines":
        run_deadlines(sent)
    elif mode == "sessions":
        run_sessions(sent)
    else:
        fail("usage: reminders.py deadlines|sessions")
    save_state(STATE_FILE, sent)


if __name__ == "__main__":
    main()
