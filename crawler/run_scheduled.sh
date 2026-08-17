#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CURRENT_USER="$(id -un)"
KEYCHAIN_SERVICE="ca.narulabs.jobmap.database-url"
BRIDGE_BASE_URL_KEYCHAIN_SERVICE="ca.narulabs.jobmap.codex-bridge-base-url"
BRIDGE_API_KEY_KEYCHAIN_SERVICE="ca.narulabs.jobmap.codex-bridge-api-key"

unset GITHUB_PAT_TOKEN OPENAI_API_KEY ANTHROPIC_API_KEY VERCEL_TOKEN

DATABASE_URL="$(/usr/bin/security find-generic-password -a "$CURRENT_USER" -s "$KEYCHAIN_SERVICE" -w)"
CODEX_BRIDGE_BASE_URL="$(/usr/bin/security find-generic-password -a "$CURRENT_USER" -s "$BRIDGE_BASE_URL_KEYCHAIN_SERVICE" -w)"
CODEX_BRIDGE_API_KEY="$(/usr/bin/security find-generic-password -a "$CURRENT_USER" -s "$BRIDGE_API_KEY_KEYCHAIN_SERVICE" -w)"
export DATABASE_URL
export CODEX_BRIDGE_BASE_URL
export CODEX_BRIDGE_API_KEY
export CRAWLER_MAX_POSTS_PER_REGION="${CRAWLER_MAX_POSTS_PER_REGION:-3}"
export OURVANCOUVER_MAX_POSTS_PER_REGION="${OURVANCOUVER_MAX_POSTS_PER_REGION:-15}"
export CASMO_MAX_POSTS_PER_REGION="${CASMO_MAX_POSTS_PER_REGION:-25}"

exec "$PROJECT_ROOT/crawler/.venv/bin/python" "$PROJECT_ROOT/crawler/run_scheduled.py"
