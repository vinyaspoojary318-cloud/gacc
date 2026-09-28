"""Shared helpers for gacc."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.theme import Theme

THEME = Theme(
    {
        "info": "cyan",
        "success": "bold green",
        "warn": "yellow",
        "error": "bold red",
        "muted": "dim",
        "accent": "bold cyan",
        "cmd": "bold white",
    }
)

console = Console(theme=THEME)
EXPLAIN: bool = False


def set_explain(value: bool) -> None:
    global EXPLAIN
    EXPLAIN = value


def is_explain() -> bool:
    return EXPLAIN


def run(
    cmd: list[str],
    *,
    check: bool = True,
    capture: bool = True,
    input_text: str | None = None,
) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, check=check, capture_output=capture, text=True, input=input_text
    )


def ensure_gh() -> None:
    if shutil.which("gh") is None:
        console.print(
            Panel(
                "[error]GitHub CLI ([cyan]gh[/]) is not installed.[/]\n\n"
                "Install it:\n"
                "  [cmd]brew install gh[/]          [muted]# macOS[/]\n"
                "  [cmd]https://cli.github.com/[/]  [muted]# all platforms[/]",
                title="[error]Missing dependency[/]",
                border_style="red",
            )
        )
        raise typer.Exit(1)


def ok(msg: str) -> None:
    console.print(f"[success]✓[/] {msg}")


def fail(msg: str) -> None:
    console.print(f"[error]✗[/] {msg}")


def info(msg: str) -> None:
    console.print(f"[info]→[/] {msg}")


def muted(msg: str) -> None:
    console.print(f"[muted]{msg}[/]")


def would(cmd: list[str] | str) -> None:
    if isinstance(cmd, list):
        cmd = " ".join(cmd)
    console.print(f"  [muted]would run:[/] [cmd]{cmd}[/]")


def gh_auth_status() -> list[dict]:
    ensure_gh()
    try:
        result = run(["gh", "auth", "status", "--json", "hosts"], check=False)
        if result.returncode != 0:
            return parse_auth_status_text()
        data = json.loads(result.stdout)
        accounts: list[dict] = []
        for host, info_list in data.get("hosts", {}).items():
            for user in info_list:
                accounts.append(
                    {
                        "host": host,
                        "user": user.get("login") or user.get("username") or "unknown",
                        "active": user.get("active", False),
                        "token": user.get("tokenSource", ""),
                    }
                )
        return accounts
    except (json.JSONDecodeError, KeyError, TypeError):
        return parse_auth_status_text()


def parse_auth_status_text() -> list[dict]:
    result = run(["gh", "auth", "status"], check=False)
    accounts: list[dict] = []
    for line in (result.stdout + result.stderr).splitlines():
        line = line.strip()
        if "Logged in to" in line:
            parts = line.split()
            try:
                idx = parts.index("account")
                user = parts[idx + 1]
                host = "github.com"
                if "to" in parts:
                    host = parts[parts.index("to") + 1]
                accounts.append(
                    {"host": host, "user": user, "active": True, "token": ""}
                )
            except (ValueError, IndexError):
                pass
    if not accounts:
        try:
            r = run(["gh", "api", "user", "--jq", ".login"], check=False)
            if r.returncode == 0 and r.stdout.strip():
                accounts.append(
                    {
                        "host": "github.com",
                        "user": r.stdout.strip(),
                        "active": True,
                        "token": "",
                    }
                )
        except Exception:
            pass
    return accounts


def current_user() -> str | None:
    for acc in gh_auth_status():
        if acc.get("active"):
            return acc["user"]
    try:
        r = run(["gh", "api", "user", "--jq", ".login"], check=False)
        if r.returncode == 0:
            return r.stdout.strip()
    except Exception:
        pass
    return None


def switch_user(username: str) -> bool:
    if EXPLAIN:
        would(["gh", "auth", "switch", "--user", username])
        return True
    result = run(
        ["gh", "auth", "switch", "--user", username], check=False, capture=True
    )
    if result.returncode != 0:
        result = run(
            [
                "gh",
                "auth",
                "switch",
                "--hostname",
                "github.com",
                "--user",
                username,
            ],
            check=False,
            capture=True,
        )
    return result.returncode == 0


def git_identity(path: Path | None = None) -> tuple[str | None, str | None]:
    name = run(["git", "config", "--get", "user.name"], check=False)
    email = run(["git", "config", "--get", "user.email"], check=False)
    n = name.stdout.strip() if name.returncode == 0 else None
    e = email.stdout.strip() if email.returncode == 0 else None
    return n, e


def remote_owner(path: Path | None = None) -> str | None:
    r = run(["git", "remote", "get-url", "origin"], check=False)
    if r.returncode != 0 or not r.stdout.strip():
        return None
    url = r.stdout.strip()
    m = re.search(r"github\.com[:/]([^/]+)/", url)
    return m.group(1) if m else None


def account_guard(
    *,
    expected: str | None = None,
    path: Path | None = None,
    action: str = "continue",
    force: bool = False,
) -> str | None:
    active = current_user()
    if not active:
        fail("No authenticated GitHub account.")
        muted("Run: gacc login")
        if not force and not EXPLAIN:
            raise typer.Exit(1)
        return None

    remote = remote_owner(path)
    issues: list[str] = []

    if expected and active.lower() != expected.lower():
        issues.append(
            f"Active account is [accent]{active}[/], but you asked for [accent]{expected}[/]."
        )
    if remote and active.lower() != remote.lower():
        issues.append(
            f"Repo remote owner looks like [accent]{remote}[/], "
            f"but active account is [accent]{active}[/]."
        )

    if not issues:
        return active

    console.print(
        Panel(
            "\n".join(issues)
            + f"\n\n[muted]About to:[/] {action}\n"
            + f"[muted]Active:[/]  [accent]{active}[/]",
            title="[warn]Account guard[/]",
            border_style="yellow",
        )
    )

    if EXPLAIN:
        muted("(explain mode — not blocking)")
        return active
    if force:
        muted("Continuing because --force was set.")
        return active
    if not typer.confirm("Continue anyway?", default=False):
        muted("Aborted. Switch with: gacc use <username>")
        raise typer.Exit(1)
    return active
