#!/bin/bash

set -euo pipefail

LABEL="ca.narulabs.jobmap.crawler"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON_BIN="$PROJECT_ROOT/crawler/.venv/bin/python"
RUNNER_BIN="$PROJECT_ROOT/crawler/run_scheduled.sh"
CURRENT_USER="$(id -un)"
USER_HOME="$(dscl . -read "/Users/$CURRENT_USER" NFSHomeDirectory | awk '{print $2}')"
KEYCHAIN_SERVICE="ca.narulabs.jobmap.database-url"
PLIST_PATH="$USER_HOME/Library/LaunchAgents/$LABEL.plist"
LOG_DIR="$USER_HOME/Library/Logs/JobMap"
STDOUT_PATH="$LOG_DIR/crawler.log"
STDERR_PATH="$LOG_DIR/crawler-error.log"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Crawler virtual environment is missing: $PYTHON_BIN" >&2
  exit 1
fi

if [[ ! -x "$RUNNER_BIN" ]]; then
  echo "Scheduled runner is not executable: $RUNNER_BIN" >&2
  exit 1
fi

if [[ "${1:-}" == "--dry-run" ]]; then
  echo "label=$LABEL"
  echo "interval_seconds=21600"
  echo "project_root=$PROJECT_ROOT"
  echo "python=$PYTHON_BIN"
  echo "runner=$RUNNER_BIN"
  echo "keychain_service=$KEYCHAIN_SERVICE"
  echo "plist=$PLIST_PATH"
  exit 0
fi

if ! /usr/bin/security find-generic-password -a "$CURRENT_USER" -s "$KEYCHAIN_SERVICE" -w >/dev/null 2>&1; then
  if [[ ! -t 0 ]]; then
    echo "Production DATABASE_URL is missing from macOS Keychain service $KEYCHAIN_SERVICE." >&2
    exit 1
  fi
  read -r -s -p "Paste the production Supabase DATABASE_URL: " DATABASE_URL
  echo
  if [[ "$DATABASE_URL" != postgresql://* && "$DATABASE_URL" != postgres://* ]]; then
    echo "DATABASE_URL must start with postgresql:// or postgres://" >&2
    unset DATABASE_URL
    exit 1
  fi
  /usr/bin/security add-generic-password -U -a "$CURRENT_USER" -s "$KEYCHAIN_SERVICE" -w "$DATABASE_URL" -T /usr/bin/security
  unset DATABASE_URL
fi

mkdir -p "$USER_HOME/Library/LaunchAgents" "$LOG_DIR"

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
    <string>$RUNNER_BIN</string>
  </array>
  <key>WorkingDirectory</key>
  <string>$PROJECT_ROOT</string>
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
echo "Logs: $STDOUT_PATH"
echo "Errors: $STDERR_PATH"
