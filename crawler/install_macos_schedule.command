#!/bin/bash

set -euo pipefail

LABEL="ca.narulabs.jobmap.crawler"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON_BIN="$PROJECT_ROOT/crawler/.venv/bin/python"
CURRENT_USER="$(id -un)"
USER_HOME="$(dscl . -read "/Users/$CURRENT_USER" NFSHomeDirectory | awk '{print $2}')"
KEYCHAIN_SERVICE="ca.narulabs.jobmap.database-url"
BRIDGE_BASE_URL_KEYCHAIN_SERVICE="ca.narulabs.jobmap.codex-bridge-base-url"
BRIDGE_API_KEY_KEYCHAIN_SERVICE="ca.narulabs.jobmap.codex-bridge-api-key"
RUNTIME_ROOT="$USER_HOME/Library/Application Support/JobMap/runtime"
RUNTIME_CRAWLER_DIR="$RUNTIME_ROOT/crawler"
RUNTIME_PYTHON_BIN="$RUNTIME_CRAWLER_DIR/.venv/bin/python"
RUNTIME_RUNNER_BIN="$RUNTIME_CRAWLER_DIR/run_scheduled.sh"
PLIST_PATH="$USER_HOME/Library/LaunchAgents/$LABEL.plist"
LOG_DIR="$USER_HOME/Library/Logs/JobMap"
STDOUT_PATH="$LOG_DIR/crawler.log"
STDERR_PATH="$LOG_DIR/crawler-error.log"
LOCK_PATH="$USER_HOME/Library/Caches/JobMap/production-crawler.lock"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Crawler virtual environment is missing: $PYTHON_BIN" >&2
  exit 1
fi

if [[ ! -x "$PROJECT_ROOT/crawler/run_scheduled.sh" ]]; then
  echo "Scheduled runner is not executable: $PROJECT_ROOT/crawler/run_scheduled.sh" >&2
  exit 1
fi

if [[ "${1:-}" == "--dry-run" ]]; then
  echo "label=$LABEL"
  echo "interval_seconds=21600"
  echo "project_root=$PROJECT_ROOT"
  echo "source_python=$PYTHON_BIN"
  echo "runtime_root=$RUNTIME_ROOT"
  echo "runtime_python=$RUNTIME_PYTHON_BIN"
  echo "runtime_runner=$RUNTIME_RUNNER_BIN"
  echo "keychain_service=$KEYCHAIN_SERVICE"
  echo "bridge_base_url_keychain_service=$BRIDGE_BASE_URL_KEYCHAIN_SERVICE"
  echo "bridge_api_key_keychain_service=$BRIDGE_API_KEY_KEYCHAIN_SERVICE"
  echo "lock=$LOCK_PATH"
  echo "plist=$PLIST_PATH"
  exit 0
fi

scheduler_lock_is_held() {
  "$PYTHON_BIN" - "$LOCK_PATH" <<'PY'
import fcntl
import sys
from pathlib import Path

lock_path = Path(sys.argv[1])
lock_path.parent.mkdir(parents=True, exist_ok=True)
with lock_path.open("a+", encoding="utf-8") as lock_file:
    try:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit(0)
    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
raise SystemExit(1)
PY
}

read_env_value() {
  "$PYTHON_BIN" - "$PROJECT_ROOT/.env.local" "$PROJECT_ROOT/crawler/.env" "$1" <<'PY'
import sys
from pathlib import Path

from dotenv import dotenv_values

value = ""
for filename in sys.argv[1:3]:
    path = Path(filename)
    if not path.exists():
        continue
    candidate = dotenv_values(path).get(sys.argv[3])
    if candidate:
        value = str(candidate).strip()
        break
print(value, end="")
PY
}

prompt_database_url() {
  if [[ ! -t 0 ]]; then
    echo "A working production DATABASE_URL is required in macOS Keychain service $KEYCHAIN_SERVICE." >&2
    exit 1
  fi
  read -r -s -p "Paste the production Supabase DATABASE_URL: " DATABASE_URL
  echo
  if [[ "$DATABASE_URL" != postgresql://* && "$DATABASE_URL" != postgres://* ]]; then
    echo "DATABASE_URL must start with postgresql:// or postgres://" >&2
    unset DATABASE_URL
    exit 1
  fi
}

prompt_database_password() {
  if [[ ! -t 0 ]]; then
    echo "A current Supabase database password is required to repair the stored pooler URL." >&2
    exit 1
  fi
  read -r -s -p "Paste the current Supabase Database password: " DATABASE_PASSWORD
  echo
  if [[ -z "$DATABASE_PASSWORD" ]]; then
    echo "Database password cannot be empty." >&2
    exit 1
  fi
  if [[ "$DATABASE_PASSWORD" == *'[YOUR-PASSWORD]'* ]]; then
    echo "Enter the actual password chosen during reset, without [YOUR-PASSWORD] or brackets." >&2
    unset DATABASE_PASSWORD
    exit 1
  fi
  DATABASE_URL="$(CURRENT_DATABASE_URL="$DATABASE_URL" DATABASE_PASSWORD="$DATABASE_PASSWORD" "$PYTHON_BIN" -c '
import os
from urllib.parse import quote, urlsplit, urlunsplit

current = urlsplit(os.environ["CURRENT_DATABASE_URL"])
username = quote(current.username or "", safe=".")
password = quote(os.environ["DATABASE_PASSWORD"], safe="")
host = current.hostname or ""
if ":" in host and not host.startswith("["):
    host = "[%s]" % host
port = ":%s" % current.port if current.port else ""
print(urlunsplit((current.scheme, "%s:%s@%s%s" % (username, password, host, port), current.path, current.query, current.fragment)), end="")
')"
  unset DATABASE_PASSWORD
}

database_url_works() {
  printf '%s' "$1" | "$PYTHON_BIN" -c '
import sys
import psycopg2

url = sys.stdin.read()
try:
    with psycopg2.connect(url, connect_timeout=10) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
except Exception:
    raise SystemExit(1)
' >/dev/null 2>&1
}

DATABASE_URL="$(/usr/bin/security find-generic-password -a "$CURRENT_USER" -s "$KEYCHAIN_SERVICE" -w 2>/dev/null || true)"
if [[ -z "$DATABASE_URL" ]]; then
  prompt_database_url
elif ! database_url_works "$DATABASE_URL"; then
  echo "The production DATABASE_URL stored in macOS Keychain could not authenticate." >&2
  prompt_database_password
fi

if ! database_url_works "$DATABASE_URL"; then
  echo "The supplied database password could not authenticate. Reset or verify it in Supabase and retry." >&2
  unset DATABASE_URL
  exit 1
fi

if ! /usr/bin/security find-generic-password -a "$CURRENT_USER" -s "$KEYCHAIN_SERVICE" -w >/dev/null 2>&1 ||
   [[ "$(/usr/bin/security find-generic-password -a "$CURRENT_USER" -s "$KEYCHAIN_SERVICE" -w)" != "$DATABASE_URL" ]]; then
  /usr/bin/security add-generic-password -U -a "$CURRENT_USER" -s "$KEYCHAIN_SERVICE" -w "$DATABASE_URL" -T /usr/bin/security
fi
unset DATABASE_URL

if ! /usr/bin/security find-generic-password -a "$CURRENT_USER" -s "$BRIDGE_BASE_URL_KEYCHAIN_SERVICE" -w >/dev/null 2>&1; then
  BRIDGE_BASE_URL="$(read_env_value CODEX_BRIDGE_BASE_URL)"
  BRIDGE_BASE_URL="${BRIDGE_BASE_URL:-http://127.0.0.1:3333}"
  /usr/bin/security add-generic-password -U -a "$CURRENT_USER" -s "$BRIDGE_BASE_URL_KEYCHAIN_SERVICE" -w "$BRIDGE_BASE_URL" -T /usr/bin/security
  unset BRIDGE_BASE_URL
fi

if ! /usr/bin/security find-generic-password -a "$CURRENT_USER" -s "$BRIDGE_API_KEY_KEYCHAIN_SERVICE" -w >/dev/null 2>&1; then
  BRIDGE_API_KEY="$(read_env_value CODEX_BRIDGE_API_KEY)"
  if [[ -z "$BRIDGE_API_KEY" ]]; then
    if [[ ! -t 0 ]]; then
      echo "Codex Bridge API key is missing from the project environment and macOS Keychain." >&2
      exit 1
    fi
    read -r -s -p "Paste the local Codex Bridge API key: " BRIDGE_API_KEY
    echo
  fi
  /usr/bin/security add-generic-password -U -a "$CURRENT_USER" -s "$BRIDGE_API_KEY_KEYCHAIN_SERVICE" -w "$BRIDGE_API_KEY" -T /usr/bin/security
  unset BRIDGE_API_KEY
fi

if scheduler_lock_is_held; then
  echo "A production crawl is currently running. Wait for it to finish, then rerun the installer." >&2
  exit 1
fi

mkdir -p "$USER_HOME/Library/LaunchAgents" "$LOG_DIR" "$RUNTIME_CRAWLER_DIR"
/usr/bin/rsync -a \
  --exclude '.env' \
  --exclude '.env.*' \
  --exclude '.pytest_cache' \
  --exclude '__pycache__' \
  --exclude 'tests' \
  "$PROJECT_ROOT/crawler/" "$RUNTIME_CRAWLER_DIR/"
chmod 700 "$RUNTIME_ROOT" "$RUNTIME_CRAWLER_DIR" "$RUNTIME_RUNNER_BIN"

if [[ ! -x "$RUNTIME_PYTHON_BIN" ]]; then
  echo "Installed crawler Python is missing: $RUNTIME_PYTHON_BIN" >&2
  exit 1
fi

cat > "$PLIST_PATH" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>$RUNTIME_RUNNER_BIN</string>
  </array>
  <key>WorkingDirectory</key>
  <string>$RUNTIME_ROOT</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>HOME</key>
    <string>$USER_HOME</string>
    <key>PATH</key>
    <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
  </dict>
  <key>RunAtLoad</key>
  <true/>
  <key>StartInterval</key>
  <integer>21600</integer>
  <key>ProcessType</key>
  <string>Background</string>
  <key>ThrottleInterval</key>
  <integer>60</integer>
  <key>Umask</key>
  <integer>63</integer>
  <key>StandardOutPath</key>
  <string>$STDOUT_PATH</string>
  <key>StandardErrorPath</key>
  <string>$STDERR_PATH</string>
</dict>
</plist>
PLIST

plutil -lint "$PLIST_PATH"
launchctl bootout "gui/$UID" "$PLIST_PATH" 2>/dev/null || true
launchctl bootstrap "gui/$UID" "$PLIST_PATH"

echo "Installed $LABEL (every 6 hours)."
echo "Runtime: $RUNTIME_ROOT"
echo "Logs: $STDOUT_PATH"
echo "Errors: $STDERR_PATH"
