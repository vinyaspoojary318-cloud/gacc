"""gacc – GitHub Account CLI.

Manage multiple GitHub accounts and create + push repositories from the terminal.
Built on top of the official GitHub CLI (gh).
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    name="gacc",
    help="Manage multiple GitHub accounts and create + push repositories from the terminal.",
    add_completion=False,
    no_args_is_help=True,
)
console = Console()


def _run(
    cmd: list[str],
    *,
    check: bool = True,
    capture: bool = True,
    input_text: str | None = None,
) -> subprocess.CompletedProcess:
    """Run a subprocess command."""
    return subprocess.run(
        cmd,
        check=check,
        capture_output=capture,
        text=True,
        input=input_text,
    )


def _ensure_gh() -> None:
    """Ensure the GitHub CLI (gh) is installed and available."""
    if shutil.which("gh") is None:
        console.print(
            "[bold red]Error:[/] GitHub CLI ([cyan]gh[/]) is not installed.\n"
            "Install it from https://cli.github.com/",
            style="red",
        )
        raise typer.Exit(1)


def _gh_auth_status() -> list[dict]:
    """Return list of authenticated accounts from `gh auth status --json`."""
    _ensure_gh()
    try:
        result = _run(
            ["gh", "auth", "status", "--json", "hosts"],
            check=False,
        )
        if result.returncode != 0:
            return _parse_auth_status_text()
        data = json.loads(result.stdout)
        accounts: list[dict] = []
        for host, info in data.get("hosts", {}).items():
            for user in info:
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
        return _parse_auth_status_text()


def _parse_auth_status_text() -> list[dict]:
    """Fallback parser for older gh versions without JSON support."""
    result = _run(["gh", "auth", "status"], check=False)
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
                    to_idx = parts.index("to")
                    host = parts[to_idx + 1]
                accounts.append({"host": host, "user": user, "active": True, "token": ""})
            except (ValueError, IndexError):
                pass

    if not accounts:
        try:
            r = _run(["gh", "api", "user", "--jq", ".login"], check=False)
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


def _current_user() -> str | None:
    """Return the currently active GitHub username."""
    accounts = _gh_auth_status()
    for acc in accounts:
        if acc.get("active"):
            return acc["user"]
    try:
        r = _run(["gh", "api", "user", "--jq", ".login"], check=False)
        if r.returncode == 0:
            return r.stdout.strip()
    except Exception:
        pass
    return None


@app.command()
def status() -> None:
    """Show the currently active GitHub account."""
    _ensure_gh()
    user = _current_user()
    if user:
        console.print(f"[bold green]Active account:[/] [cyan]{user}[/]")
    else:
        console.print(
            "[yellow]No authenticated GitHub account found.[/]\n"
            "Run [cyan]gacc login[/] or [cyan]gh auth login[/] to authenticate.",
        )
        raise typer.Exit(1)


@app.command("list")
def list_accounts() -> None:
    """List all authenticated GitHub accounts."""
    _ensure_gh()
    accounts = _gh_auth_status()
    if not accounts:
        console.print(
            "[yellow]No authenticated accounts found.[/]\n"
            "Run [cyan]gacc login[/] or [cyan]gh auth login[/] to add one.",
        )
        raise typer.Exit(1)

    table = Table(title="GitHub Accounts", show_header=True, header_style="bold")
    table.add_column("User", style="cyan")
    table.add_column("Host")
    table.add_column("Active", justify="center")

    for acc in accounts:
        active = "✓" if acc.get("active") else ""
        table.add_row(acc.get("user", "?"), acc.get("host", "github.com"), active)

    console.print(table)


@app.command()
def use(
    username: str = typer.Argument(..., help="GitHub username to switch to"),
) -> None:
    """Switch the active GitHub account."""
    _ensure_gh()
    console.print(f"Switching to account [cyan]{username}[/]...")
    result = _run(
        ["gh", "auth", "switch", "--user", username],
        check=False,
        capture=True,
    )
    if result.returncode != 0:
        result = _run(
            ["gh", "auth", "switch", "--hostname", "github.com", "--user", username],
            check=False,
            capture=True,
        )
    if result.returncode != 0:
        console.print(
            f"[bold red]Failed to switch to '{username}'.[/]\n"
            f"{result.stderr or result.stdout}\n"
            "Make sure the account is authenticated: [cyan]gh auth login[/]",
        )
        raise typer.Exit(1)

    console.print(f"[bold green]✓[/] Switched to [cyan]{username}[/]")


@app.command()
def login() -> None:
    """Add / authenticate a new GitHub account (wraps `gh auth login`)."""
    _ensure_gh()
    console.print("Starting GitHub authentication...")
    result = subprocess.run(["gh", "auth", "login"])
    if result.returncode != 0:
        console.print("[bold red]Authentication failed or was cancelled.[/]")
        raise typer.Exit(result.returncode)
    console.print("[bold green]✓[/] Authentication complete.")


@app.command()
def create(
    name: str = typer.Argument(..., help="Name of the new repository"),
    public: bool = typer.Option(
        False,
        "--public",
        help="Create a public repository (default is private)",
    ),
    description: Optional[str] = typer.Option(
        None,
        "--description",
        "-d",
        help="Repository description",
    ),
    account: Optional[str] = typer.Option(
        None,
        "--account",
        "-a",
        help="GitHub account (username) to use for creation",
    ),
    source: Path = typer.Option(
        Path("."),
        "--source",
        "-s",
        help="Local path to use as the repository source (default: current directory)",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
    push: bool = typer.Option(
        True,
        "--push/--no-push",
        help="Push the local commits after creating the remote (default: yes)",
    ),
) -> None:
    """Create a new GitHub repository and optionally push the current folder."""
    _ensure_gh()

    if account:
        console.print(f"Using account [cyan]{account}[/]...")
        result = _run(
            ["gh", "auth", "switch", "--user", account],
            check=False,
        )
        if result.returncode != 0:
            result = _run(
                ["gh", "auth", "switch", "--hostname", "github.com", "--user", account],
                check=False,
            )
        if result.returncode != 0:
            console.print(
                f"[bold red]Could not switch to account '{account}'.[/]\n"
                "Authenticate it first with [cyan]gacc login[/] or [cyan]gh auth login[/].",
            )
            raise typer.Exit(1)

    current = _current_user()
    if current:
        console.print(f"Creating repo under [cyan]{current}[/]...")

    git_dir = source / ".git"
    if not git_dir.exists():
        console.print(f"[yellow]No git repository found in {source}.[/]")
        if typer.confirm("Run [cyan]git init[/]?", default=True):
            _run(["git", "init"], check=True)
            console.print("[green]✓[/] Initialized empty Git repository.")
        else:
            console.print("Aborted.")
            raise typer.Exit(1)

    cmd = [
        "gh",
        "repo",
        "create",
        name,
        "--source",
        str(source),
        "--remote",
        "origin",
    ]

    if public:
        cmd.append("--public")
    else:
        cmd.append("--private")

    if description:
        cmd.extend(["--description", description])

    if push:
        cmd.append("--push")

    console.print(f"Running: [dim]{' '.join(cmd)}[/]")
    result = subprocess.run(cmd)

    if result.returncode != 0:
        console.print("[bold red]Failed to create repository.[/]")
        raise typer.Exit(result.returncode)

    console.print(f"[bold green]✓[/] Repository [cyan]{name}[/] created successfully!")
    if current:
        console.print(f"  → https://github.com/{current}/{name}")


@app.command()
def version() -> None:
    """Show gacc version."""
    from gacc import __version__

    console.print(f"gacc {__version__}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
