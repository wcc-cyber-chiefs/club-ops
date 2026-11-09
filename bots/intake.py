"""Post an approved opportunity submission (GitHub issue form) to #jobs-postings.

Triggered when an officer adds the `approved` label to an issue that carries
the `opportunity` label. Only people with triage access can add labels, so
the label is the approval gate. Afterwards the bot comments and closes the
issue.

The issue text is untrusted input: it is read from the event file (never
interpolated into a shell), length-limited, and posted with all mentions
suppressed.
"""

from __future__ import annotations

import json
import os
import re
import urllib.request

from common import DRY_RUN, USER_AGENT, post, role_mention, truncate

FIELD = re.compile(r"^###\s+(.+?)\s*$", re.M)


def parse_form(body: str) -> dict:
    """GitHub issue forms render as '### Label\\n\\nvalue' blocks."""
    out = {}
    parts = FIELD.split(body or "")
    for label, value in zip(parts[1::2], parts[2::2]):
        value = value.strip()
        out[label.strip().lower()] = "" if value == "_No response_" else value
    return out


def safe_url(url: str) -> str | None:
    url = (url or "").strip()
    return url if re.match(r"^https?://[^\s<>]+$", url) else None


def github_api(method: str, path: str, payload: dict) -> None:
    if DRY_RUN:
        print(f"DRY RUN GitHub {method} {path}: {payload}")
        return
    req = urllib.request.Request(
        f"https://api.github.com/repos/{os.environ['GITHUB_REPOSITORY']}{path}",
        data=json.dumps(payload).encode(),
        method=method,
        headers={
            "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
            "Accept": "application/vnd.github+json",
            "User-Agent": USER_AGENT,
        },
    )
    urllib.request.urlopen(req, timeout=30).read()


def main() -> None:
    with open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8") as fh:
        event = json.load(fh)
    issue = event["issue"]
    labels = {l["name"] for l in issue.get("labels", [])}
    if event.get("label", {}).get("name") != "approved" or "opportunity" not in labels:
        print("Not an approved opportunity; nothing to do.")
        return

    f = parse_form(issue.get("body", ""))
    url = safe_url(f.get("link", ""))
    if not url:
        github_api("POST", f"/issues/{issue['number']}/comments",
                   {"body": "The link field needs a full http(s) URL. Edit the issue, then re-add `approved`."})
        return

    fields = [{"name": "Type", "value": truncate(f.get("type", "Opportunity"), 50), "inline": True}]
    for label, name in (("deadline", "Deadline"), ("location", "Location")):
        if f.get(label):
            fields.append({"name": name, "value": truncate(f[label], 100), "inline": True})
    embed = {
        "title": truncate(f"{f.get('organization', '')} — {f.get('title', 'Opportunity')}".strip(" —"), 250),
        "url": url,
        "description": truncate(f.get("why it's a good fit", ""), 800) or None,
        "fields": fields,
        "footer": {"text": f"Shared by {issue['user']['login']} via the opportunity form"},
    }
    ping, role_ids = role_mention("opportunities")
    post("jobs", content=f"{ping} Shared by a member".strip(), embeds=[embed],
         thread_name=truncate(f.get("title", "Opportunity"), 90), role_ids=role_ids)

    github_api("POST", f"/issues/{issue['number']}/comments",
               {"body": "Posted to #jobs-postings. Thanks for sharing!"})
    github_api("PATCH", f"/issues/{issue['number']}", {"state": "closed", "state_reason": "completed"})


if __name__ == "__main__":
    main()
