"""
check_provider_auth.py — Standalone watchdog for Hermes's model-provider auth

NOT a skill script. Nothing here is invoked by the Hermes agent loop, and
that is the point: the 2026-07-08 incident this exists to catch was the Nous
Portal OAuth token going dead, which made the agent loop itself unable to
reason — every message got a canned ~114-char fallback response in ~0.2-0.7s
with api_calls=0, silently, for the better part of three days, because
nothing outside the broken loop was watching it. A check that depends on the
agent to notice its own brokenness is the same failure mode as trusting an
unverified LLM output; this script is the deterministic, non-LLM trip-wire
for provider auth, the same philosophy as verify_research_data.py.

Run on a schedule OUTSIDE Hermes (Windows Task Scheduler — see
builder-os/README.md for registration), not via /schedule (which schedules
an agent turn, i.e. exactly the thing that can't run when auth is broken).

Detection is two signals, either one triggers an alert:
1. `hermes auth status <provider>` for every provider actually configured
   (model.provider + fallback_providers, deduped) reports logged out.
2. gateway.log has a new "Primary provider auth failed" line since the last
   run (state-tracked by byte offset) — catches failures whose provider
   somehow still reports "logged in" (stale/invalid-but-present token).

Alerts go straight to Telegram via the Bot HTTP API (not through Hermes),
into the Builder OS topic — this is exactly the kind of infra issue that
topic's charter covers. Deduped: only fires on healthy->unhealthy and
unhealthy->healthy transitions, plus a reminder ping every REMINDER_HOURS
if still unhealthy, so a real outage doesn't get lost after the first alert
but a stable outage doesn't spam either.

Usage:
    python check_provider_auth.py              # normal scheduled run
    python check_provider_auth.py --self-test   # force a test alert, verify wiring
"""

import os
import re
import sys
import json
import argparse
import subprocess
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime, timezone

HERMES_ROOT = Path(os.environ.get("LOCALAPPDATA", "")) / "hermes"
CONFIG_PATH = HERMES_ROOT / "config.yaml"
ENV_PATH = HERMES_ROOT / ".env"
GATEWAY_LOG = HERMES_ROOT / "logs" / "gateway.log"
HERMES_EXE = HERMES_ROOT / "hermes-agent" / "venv" / "Scripts" / "hermes.exe"
STATE_PATH = HERMES_ROOT / "builder-os-provider-watchdog-state.json"

ALERT_CHAT_ID = -1004298960232
ALERT_THREAD_ID = 33  # "Builder OS" topic — this project's own ops/infra channel
REMINDER_HOURS = 4
AUTH_FAIL_LOG_MARKER = "Primary provider auth failed"


def _read_env_var(name: str) -> str:
    if not ENV_PATH.exists():
        return ""
    for line in ENV_PATH.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        if k.strip() == name:
            return v.strip().strip('"').strip("'")
    return ""


def _configured_providers() -> list:
    import yaml
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    providers = []
    primary = (cfg.get("model") or {}).get("provider")
    if primary:
        providers.append(primary)
    for p in cfg.get("fallback_providers") or []:
        if isinstance(p, str) and p not in providers:
            providers.append(p)
        elif isinstance(p, dict) and p.get("provider") and p["provider"] not in providers:
            providers.append(p["provider"])
    return providers


def _auth_status(provider: str) -> dict:
    """Returns {"provider": ..., "logged_in": bool, "detail": str}."""
    try:
        proc = subprocess.run(
            [str(HERMES_EXE), "auth", "status", provider],
            capture_output=True, text=True, timeout=30,
        )
    except Exception as e:
        return {"provider": provider, "logged_in": False, "detail": f"status check crashed: {e}"}
    out = (proc.stdout or proc.stderr or "").strip()
    logged_in = bool(re.search(rf"^{re.escape(provider)}:\s*logged in", out, re.IGNORECASE | re.MULTILINE))
    return {"provider": provider, "logged_in": logged_in, "detail": out}


def _load_state() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    # First run ever: seed the offset at the CURRENT end of the log, not 0.
    # Scanning from 0 on a fresh install would replay every historical
    # "auth failed" line (e.g. last week's already-fixed outage) as if new.
    seed_offset = GATEWAY_LOG.stat().st_size if GATEWAY_LOG.exists() else 0
    return {"log_offset": seed_offset, "unhealthy_since": None, "last_alert_at": None, "last_reason": None}


def _save_state(state: dict) -> None:
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _scan_log_for_new_auth_failures(state: dict) -> list:
    """Read only the bytes appended since the last run (cheap, no full-file
    rescan) and return any new auth-failure lines found in that span."""
    if not GATEWAY_LOG.exists():
        return []
    size = GATEWAY_LOG.stat().st_size
    offset = state.get("log_offset") or 0
    if offset > size:
        offset = 0  # log was rotated/truncated since last run
    hits = []
    with open(GATEWAY_LOG, "r", encoding="utf-8", errors="replace") as f:
        f.seek(offset)
        for line in f:
            if AUTH_FAIL_LOG_MARKER in line:
                hits.append(line.strip())
    state["log_offset"] = size
    return hits


def _send_telegram(text: str) -> bool:
    token = _read_env_var("TELEGRAM_BOT_TOKEN")
    if not token:
        print("check_provider_auth: TELEGRAM_BOT_TOKEN not found in .env — cannot alert", file=sys.stderr)
        return False
    payload = json.dumps({
        "chat_id": ALERT_CHAT_ID,
        "message_thread_id": ALERT_THREAD_ID,
        "text": text,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status == 200
    except urllib.error.URLError as e:
        print(f"check_provider_auth: Telegram send failed: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true",
                        help="Send a test alert regardless of health state, to verify wiring")
    args = parser.parse_args()

    now = datetime.now(timezone.utc)
    state = _load_state()

    if args.self_test:
        ok = _send_telegram(
            "🔧 check_provider_auth.py self-test: watchdog is installed and can reach "
            f"Telegram. ({now.isoformat(timespec='seconds')})"
        )
        print(json.dumps({"self_test": True, "sent": ok}))
        sys.exit(0 if ok else 1)

    providers = _configured_providers()
    statuses = [_auth_status(p) for p in providers]
    logged_out = [s for s in statuses if not s["logged_in"]]
    log_hits = _scan_log_for_new_auth_failures(state)

    unhealthy = bool(logged_out) or bool(log_hits)
    reasons = [f"{s['provider']}: {s['detail']}" for s in logged_out]
    if log_hits:
        reasons.append(f"{len(log_hits)} new 'auth failed' line(s) in gateway.log")
    reason_text = "; ".join(reasons) if reasons else None

    was_unhealthy = state.get("unhealthy_since") is not None

    if unhealthy and not was_unhealthy:
        state["unhealthy_since"] = now.isoformat()
        state["last_alert_at"] = now.isoformat()
        state["last_reason"] = reason_text
        _send_telegram(
            "🔴 Provider auth watchdog: Hermes's model provider looks broken.\n\n"
            f"{reason_text}\n\n"
            "Symptom to expect meanwhile: every message gets a fast, generic fallback "
            "reply instead of a real response (the agent can't actually reason while "
            "this is broken). Check `hermes auth status <provider>` and re-login if "
            "logged out."
        )
    elif unhealthy and was_unhealthy:
        last_alert = state.get("last_alert_at")
        hours_since = 999.0
        if last_alert:
            hours_since = (now - datetime.fromisoformat(last_alert)).total_seconds() / 3600
        if hours_since >= REMINDER_HOURS:
            state["last_alert_at"] = now.isoformat()
            state["last_reason"] = reason_text
            since = state.get("unhealthy_since", "unknown")
            _send_telegram(
                f"🔴 Provider auth watchdog: still broken since {since}.\n\n{reason_text}"
            )
    elif not unhealthy and was_unhealthy:
        since = state.get("unhealthy_since", "unknown")
        state["unhealthy_since"] = None
        state["last_alert_at"] = None
        state["last_reason"] = None
        _send_telegram(f"🟢 Provider auth watchdog: recovered (was broken since {since}).")

    _save_state(state)
    print(json.dumps({
        "checked_providers": providers,
        "unhealthy": unhealthy,
        "reasons": reasons,
        "log_hits": len(log_hits),
    }, indent=2))


if __name__ == "__main__":
    main()
