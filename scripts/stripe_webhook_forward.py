#!/usr/bin/env python3
"""Run the local Stripe CLI webhook forwarder for the backend."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_EVENTS = ",".join(
    [
        "checkout.session.completed",
        "payment_intent.payment_failed",
        "checkout.session.expired",
        "charge.refunded",
    ]
)
DEFAULT_BACKEND_PORT = "8000"
WEBHOOK_PATH = "/v1/webhooks/stripe"


def _read_env_file(path: Path) -> dict[str, str]:
    """Read simple KEY=value pairs without executing the file as shell code."""
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line.removeprefix("export ").strip()
        key, separator, value = line.partition("=")
        if not separator:
            continue
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        values[key] = value
    return values


def _setting(name: str, env_file_values: dict[str, str], default: str) -> str:
    return os.environ.get(name) or env_file_values.get(name) or default


def _stripe_bin(env_file_values: dict[str, str], explicit: str | None) -> str:
    configured = explicit or _setting("STRIPE_CLI_BIN", env_file_values, "stripe")
    resolved = shutil.which(configured)
    if resolved:
        return resolved

    print(
        "Stripe CLI was not found. Install it, then run `stripe login` before forwarding webhooks.",
        file=sys.stderr,
    )
    print("macOS install: brew install stripe/stripe-cli/stripe", file=sys.stderr)
    raise SystemExit(127)


def _default_forward_to(env_file_values: dict[str, str]) -> str:
    backend_port = _setting("BACKEND_PORT", env_file_values, DEFAULT_BACKEND_PORT)
    return f"http://127.0.0.1:{backend_port}{WEBHOOK_PATH}"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Forward Stripe CLI webhook events to the local FastAPI backend.",
    )
    parser.add_argument(
        "command",
        choices=("listen", "secret"),
        nargs="?",
        default="listen",
        help="`secret` prints the local webhook secret; `listen` forwards events.",
    )
    parser.add_argument(
        "--env-file",
        default=".env",
        help="Env file to read for helper defaults. Environment variables still win.",
    )
    parser.add_argument(
        "--stripe-bin",
        default=None,
        help="Stripe CLI executable. Defaults to STRIPE_CLI_BIN or `stripe`.",
    )
    parser.add_argument(
        "--forward-to",
        default=None,
        help="Webhook destination. Defaults to STRIPE_WEBHOOK_FORWARD_TO or local backend.",
    )
    parser.add_argument(
        "--events",
        default=None,
        help="Comma-separated Stripe event list. Defaults to STRIPE_WEBHOOK_EVENTS.",
    )
    parser.add_argument(
        "--allow-update-check",
        action="store_true",
        help="Let Stripe CLI check for updates. Default adds --skip-update.",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    env_file_values = _read_env_file(Path(args.env_file))
    stripe_bin = _stripe_bin(env_file_values, args.stripe_bin)

    if args.command == "secret":
        return subprocess.run([stripe_bin, "listen", "--print-secret"], check=False).returncode

    forward_to = args.forward_to or _setting(
        "STRIPE_WEBHOOK_FORWARD_TO",
        env_file_values,
        _default_forward_to(env_file_values),
    )
    events = args.events or _setting("STRIPE_WEBHOOK_EVENTS", env_file_values, DEFAULT_EVENTS)

    command = [stripe_bin, "listen"]
    if not args.allow_update_check:
        command.append("--skip-update")
    command.extend(["--events", events, "--forward-to", forward_to])

    print(f"Forwarding Stripe webhooks to {forward_to}", file=sys.stderr)
    print(f"Events: {events}", file=sys.stderr)
    print("Backend STRIPE_WEBHOOK_SECRET must match `make stripe-webhook-secret`.", file=sys.stderr)
    return subprocess.run(command, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
