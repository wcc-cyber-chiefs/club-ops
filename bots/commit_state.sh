#!/usr/bin/env bash
# Commit bot state (dedupe records, flag hashes) back to the repo.
# These commits also count as repository activity, which keeps GitHub from
# auto-disabling the scheduled workflows after 60 quiet days.
set -euo pipefail

git config user.name "club-ops-bot"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

git add data/state docs/flags.json 2>/dev/null || true
if git diff --cached --quiet; then
  echo "No state changes."
  exit 0
fi

git commit -m "bot: update state (${GITHUB_WORKFLOW:-manual})"

# Several workflows can finish at the same moment; rebase and retry.
for attempt in 1 2 3 4 5; do
  if git pull --rebase --quiet && git push --quiet; then
    echo "State pushed."
    exit 0
  fi
  echo "Push attempt $attempt failed; retrying."
  sleep $((attempt * 5))
done
echo "::error::Could not push state after 5 attempts"
exit 1
