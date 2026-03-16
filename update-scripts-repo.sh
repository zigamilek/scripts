#!/bin/bash

set -euo pipefail

# Resolve the repo root from the script location so cron can call it without
# relying on the current working directory.
if [ -z "${REPO:-}" ]; then
  _sp="${BASH_SOURCE[0]}"
  [[ "$_sp" != /* ]] && _sp="$(pwd)/$_sp"
  _script_dir="$(cd "$(dirname "$_sp")" 2>/dev/null && pwd)" || true
  [ -n "${_script_dir:-}" ] && REPO="$(cd "${_script_dir}" && pwd)" || true
fi

REPO="${REPO:-/home/ziga/git/scripts}"
REMOTE="${REMOTE:-origin}"
BRANCH="${BRANCH:-}"

cd "$REPO"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Not a git repository: $REPO" >&2
  exit 1
fi

if [ -z "$BRANCH" ]; then
  BRANCH="$(git symbolic-ref --quiet --short HEAD || true)"
fi

if [ -z "$BRANCH" ]; then
  echo "Repository is in detached HEAD state: $REPO" >&2
  exit 1
fi

git update-index -q --refresh

if ! git diff --quiet --ignore-submodules -- || ! git diff --cached --quiet --ignore-submodules --; then
  echo "Skipping pull for $REPO because tracked changes exist."
  exit 0
fi

git fetch --quiet --prune "$REMOTE"

REMOTE_REF="$REMOTE/$BRANCH"
if ! git rev-parse --verify "$REMOTE_REF" >/dev/null 2>&1; then
  echo "Remote ref not found: $REMOTE_REF" >&2
  exit 1
fi

LOCAL_HEAD="$(git rev-parse HEAD)"
REMOTE_HEAD="$(git rev-parse "$REMOTE_REF")"

if [ "$LOCAL_HEAD" = "$REMOTE_HEAD" ]; then
  exit 0
fi

if git merge-base --is-ancestor "$LOCAL_HEAD" "$REMOTE_HEAD"; then
  echo "Updating $REPO from $LOCAL_HEAD to $REMOTE_HEAD"
  git pull --ff-only "$REMOTE" "$BRANCH"
  exit 0
fi

if git merge-base --is-ancestor "$REMOTE_HEAD" "$LOCAL_HEAD"; then
  echo "Skipping pull for $REPO because local branch '$BRANCH' is ahead of $REMOTE_REF."
  exit 0
fi

echo "Cannot fast-forward $REPO because local and remote history diverged." >&2
exit 1
