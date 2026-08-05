"""Run one production crawl from a local, non-interactive scheduler."""

from __future__ import annotations

import fcntl
import json
import os
from pathlib import Path
from typing import Any, Callable, Dict

from api import run_enabled_sources


DEFAULT_LOCK_PATH = Path.home() / "Library" / "Caches" / "JobMap" / "production-crawler.lock"


def _validate_environment() -> None:
    missing = [
        key
        for key in ("DATABASE_URL", "CODEX_BRIDGE_BASE_URL", "CODEX_BRIDGE_API_KEY")
        if not os.getenv(key, "").strip()
    ]
    if missing:
        raise RuntimeError("Missing required production environment variables: %s" % ", ".join(missing))


def run_once(
    runner: Callable[..., Dict[str, Any]] = run_enabled_sources,
    lock_path: Path = DEFAULT_LOCK_PATH,
) -> Dict[str, Any]:
    """Run one crawl, or return a skipped result when another run owns the lock."""

    _validate_environment()
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as lock_file:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {"status": "skipped", "reason": "already_running"}

        return runner(trigger_type="cron")


def exit_code_for_result(result: Dict[str, Any]) -> int:
    if result.get("status") not in {"ok", "partial", "skipped"}:
        return 1
    translation = result.get("title_translation")
    if translation and translation.get("status") != "ok":
        return 1
    return 0


def main() -> int:
    try:
        result = run_once()
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")), flush=True)
        return exit_code_for_result(result)
    except Exception as exc:
        print(json.dumps({"status": "failed", "error": str(exc)[:500]}, ensure_ascii=False), flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
