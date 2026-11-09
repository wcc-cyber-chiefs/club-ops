"""Post a failure alert to #mods. Called by every workflow's `if: failure()` step."""

import os

from common import post

repo = os.environ.get("GITHUB_REPOSITORY", "")
run = f"https://github.com/{repo}/actions/runs/{os.environ.get('GITHUB_RUN_ID', '')}"
workflow = os.environ.get("GITHUB_WORKFLOW", "A workflow")

try:
    post("mods", content=(
        f"**{workflow}** failed. Log: <{run}>\n"
        "Usually a feed changed or a webhook was deleted. HANDBOOK.md, \"When something breaks\", covers the fixes."
    ))
except Exception as exc:  # never fail the failure handler
    print(f"::warning::Could not post failure alert: {exc}")
