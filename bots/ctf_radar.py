"""Weekly digest of upcoming online CTFs from the CTFtime API, posted to #events.

CTFtime's API terms allow data use but not running a clone of the site, so
this posts one short digest a week that links back to each event page.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from common import club_tz, http_get_json, load_yaml, now_local, post, role_mention, save_state, truncate

API = "https://ctftime.org/api/v1/events/?limit=100&start={start}&finish={finish}"


def fmt_when(iso: str) -> str:
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(club_tz())
    return dt.strftime("%a %b %-d, %-I:%M %p")


def duration_hours(ev: dict) -> int:
    start = datetime.fromisoformat(ev["start"].replace("Z", "+00:00"))
    finish = datetime.fromisoformat(ev["finish"].replace("Z", "+00:00"))
    return round((finish - start).total_seconds() / 3600)


def main() -> None:
    cfg = load_yaml("feeds.yml").get("ctftime", {})
    days = int(cfg.get("days_ahead", 14))
    beginner_max = float(cfg.get("beginner_max_weight", 25))
    max_events = int(cfg.get("max_events", 15))

    now = now_local()
    start, finish = int(now.timestamp()), int((now + timedelta(days=days)).timestamp())
    events = http_get_json(API.format(start=start, finish=finish))

    if cfg.get("online_only", True):
        events = [e for e in events if not e.get("onsite")]
    events.sort(key=lambda e: e["start"])

    lines = []
    for ev in events[:max_events]:
        weight = float(ev.get("weight") or 0)
        tag = " · **beginner-friendly**" if weight <= beginner_max else ""
        restriction = ev.get("restrictions") or "Open"
        url = ev.get("ctftime_url") or ev.get("url")
        lines.append(
            f"**[{truncate(ev.get('title', 'CTF'), 80)}]({url})**\n"
            f"{fmt_when(ev['start'])} CT · {duration_hours(ev)}h · {ev.get('format', '')} · "
            f"{restriction} · weight {weight:g}{tag}"
        )

    ping, role_ids = role_mention("ctf")
    if lines:
        embed = {
            "title": f"Upcoming online CTFs — next {days} days",
            "description": truncate("\n\n".join(lines), 4000),
            "footer": {"text": "Data from CTFtime.org · officers pick the club's CTF of the month from this list"},
        }
        post("events", content=f"{ping} Weekly CTF radar".strip(), embeds=[embed],
             thread_name="Weekly CTF radar", role_ids=role_ids)
    else:
        print("No upcoming online CTFs in range.")

    # Heartbeat: a commit every week keeps GitHub from auto-disabling
    # scheduled workflows after 60 days without repository activity.
    save_state("heartbeat.json", {"last_ctf_radar": now.isoformat(timespec="minutes"),
                                  "events_listed": len(lines)})


if __name__ == "__main__":
    main()
