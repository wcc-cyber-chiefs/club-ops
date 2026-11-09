"""Daily security news digest for #cyber-news.

Reads the RSS/Atom feeds and the CISA Known Exploited Vulnerabilities
catalog listed in data/feeds.yml, and posts one short digest of items
that haven't been posted before.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

from common import http_get, http_get_json, load_state, load_yaml, post, save_state, truncate

STATE_FILE = "news_seen.json"
ATOM = "{http://www.w3.org/2005/Atom}"


def parse_feed(raw: bytes) -> list[dict]:
    root = ET.fromstring(raw)
    items = []
    for it in root.iter("item"):  # RSS 2.0
        items.append({"title": (it.findtext("title") or "").strip(),
                      "link": (it.findtext("link") or "").strip()})
    for it in root.iter(f"{ATOM}entry"):  # Atom
        link = it.find(f"{ATOM}link")
        items.append({"title": (it.findtext(f"{ATOM}title") or "").strip(),
                      "link": (link.get("href") if link is not None else "").strip()})
    return [i for i in items if i["title"] and i["link"]]


def main() -> None:
    cfg = load_yaml("feeds.yml").get("news", {})
    max_items = int(cfg.get("max_items", 8))
    state = load_state(STATE_FILE, {"links": [], "kev": []})
    seen_links = set(state["links"])
    first_run = not state["links"]

    fresh = []
    for feed in cfg.get("rss", []):
        try:
            items = parse_feed(http_get(feed["url"]))
        except Exception as exc:
            print(f"::warning::Could not read {feed.get('name')}: {exc}")
            continue
        for it in items[:10]:  # feeds list newest first
            if it["link"] not in seen_links:
                fresh.append({**it, "source": feed.get("name", "")})
                seen_links.add(it["link"])

    kev_lines = []
    kev_cfg = cfg.get("cisa_kev") or {}
    if kev_cfg.get("enabled"):
        try:
            catalog = http_get_json(kev_cfg["url"]).get("vulnerabilities", [])
            known = set(state["kev"])
            new = [v for v in catalog if v.get("cveID") not in known]
            if known:  # first run only records the catalog, posts nothing
                for v in sorted(new, key=lambda v: v.get("dateAdded", ""), reverse=True)[:5]:
                    kev_lines.append(
                        f"[{v['cveID']}](https://nvd.nist.gov/vuln/detail/{v['cveID']}) — "
                        f"{truncate(v.get('vendorProject', '') + ' ' + v.get('product', ''), 60)}: "
                        f"{truncate(v.get('vulnerabilityName', ''), 90)}"
                    )
            state["kev"] = sorted(known | {v.get("cveID") for v in catalog if v.get("cveID")})
        except Exception as exc:
            print(f"::warning::Could not read CISA KEV: {exc}")

    state["links"] = list(seen_links)[-3000:]

    if first_run:
        # Don't dump a backlog into the channel on day one.
        print(f"First run: recorded {len(seen_links)} links, posting nothing.")
        save_state(STATE_FILE, state)
        return

    embeds = []
    if fresh:
        lines = [f"[{truncate(i['title'], 110)}]({i['link']}) · {i['source']}" for i in fresh[:max_items]]
        embeds.append({"title": "Today in security news", "description": truncate("\n".join(lines), 4000)})
    if kev_lines:
        embeds.append({"title": "New in CISA Known Exploited Vulnerabilities",
                       "description": truncate("\n".join(kev_lines), 4000),
                       "footer": {"text": "Actively exploited in the wild: good detection-rule practice"}})
    if embeds:
        post("news", content="", embeds=embeds, thread_name="Daily security digest")
    else:
        print("Nothing new.")
    save_state(STATE_FILE, state)


if __name__ == "__main__":
    main()
