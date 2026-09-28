"""gacc – GitHub Account CLI.

Manage multiple GitHub accounts and create + push repositories from the terminal.
Supports plain-English commands. Built on the official GitHub CLI (gh).
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
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

app = typer.Typer(
    name="gacc",
    help=(
        "Manage multiple GitHub accounts and create + push repos from the terminal.\n\n"
        "[dim]Tip: use plain English — e.g.[/] [cyan]gacc \"create a public repo called my-app\"[/]"
    ),
    add_completion=False,
    no_args_is_help=False,
    rich_markup_mode="rich",
)


def _run(
    cmd: list[str],
    *,
    check: bool = True,
    capture: bool = True,
    input_text: str | None = None,
) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        check=check,
        capture_output=capture,
        text=True,
        input=input_text,
    )


def _ensure_gh() -> None:
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


def _ok(msg: str) -> None:
    console.print(f"[success]✓[/] {msg}")


def _fail(msg: str) -> None:
    console.print(f"[error]✗[/] {msg}")


def _info(msg: str) -> None:
    console.print(f"[info]→[/] {msg}")


def _muted(msg: str) -> None:
    console.print(f"[muted]{msg}[/]")


def _gh_auth_status() -> list[dict]:
    _ensure_gh()
    try:
        result = _run(["gh", "auth", "status", "--json", "hosts"], check=False)
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
                    host = parts[parts.index("to") + 1]
                accounts.append(
                    {"host": host, "user": user, "active": True, "token": ""}
                )
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
    for acc in _gh_auth_status():
        if acc.get("active"):
            return acc["user"]
    try:
        r = _run(["gh", "api", "user", "--jq", ".login"], check=False)
        if r.returncode == 0:
            return r.stdout.strip()
    except Exception:
        pass
    return None


def _switch_user(username: str) -> bool:
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
    return result.returncode == 0


def _parse_natural(text: str) -> tuple[str, dict] | None:
    t = text.strip().lower()
    t = re.sub(r"[\"'`]", "", t)
    t = re.sub(r"\s+", " ", t)

    if re.search(
        r"\b(status|who am i|current account|which account|active account)\b", t
    ):
        return "status", {}

    if re.search(
        r"\b(list|show|see)\b.*\b(accounts?|users?|logins?)\b"
        r"|\b(accounts?|users?)\b.*\b(list|show)\b"
        r"|\bmy accounts\b",
        t,
    ):
        return "list", {}

    if re.search(
        r"\b(login|log in|sign in|authenticate|add account|new account)\b", t
    ):
        return "login", {}

    m = re.search(
        r"(?:switch|use|change|set)\s+(?:to\s+)?(?:account\s+)?([a-zA-Z0-9][a-zA-Z0-9-]{0,38})",
        t,
    )
    if m and not re.search(r"\b(repo|project|repository)\b", t):
        return "use", {"username": m.group(1)}

    m = re.search(
        r"(?:account|user)\s+([a-zA-Z0-9][a-zA-Z0-9-]{0,38})",
        t,
    )
    if m and re.search(r"\b(switch|use|change|set)\b", t):
        return "use", {"username": m.group(1)}

    if re.search(r"\b(create|make|new|init)\b", t) and re.search(
        r"\b(repo|repository|project)\b", t
    ):
        public = bool(re.search(r"\bpublic\b", t))
        private = bool(re.search(r"\bprivate\b", t))
        if private:
            public = False

        name = None
        for pat in (
            r"(?:called|named|name)\s+([a-zA-Z0-9._-]+)",
            r"(?:repo|repository|project)\s+(?:called\s+|named\s+)?([a-zA-Z0-9._-]+)",
            r"(?:create|make|new)\s+([a-zA-Z0-9._-]+)(?:\s+repo|\s+repository|\s+project)?",
        ):
            m = re.search(pat, t)
            if m:
                candidate = m.group(1)
                if candidate not in ("a", "an", "the", "public", "private", "repo", "repository", "project"):
                    name = candidate
                    break

        account = None
        m = re.search(
            r"(?:with|using|under|as)\s+(?:account\s+)?([a-zA-Z0-9][a-zA-Z0-9-]{0,38})",
            t,
        )
        if m:
            account = m.group(1)

        description = None
        m = re.search(r"(?:description|desc|about)\s+[\"']?(.+?)[\"']?\s*$", text.strip(), re.I)
        if m:
            description = m.group(1).strip()

        return "create", {
            "name": name,
            "public": public,
            "account": account,
            "description": description,
        }

    if re.search(r"\b(version|help|what can you do|how do i)\b", t):
        return "help", {}

    return None


def _run_natural(text: str) -> None:
    parsed = _parse_natural(text)
    if not parsed:
        console.print(
            Panel(
                f"[warn]I didn't understand:[/] [cmd]{text}[/]\n\n"
                "[muted]Try things like:[/]\n"
                '  [cyan]gacc "who am I"[/]\n'
                '  [cyan]gacc "list my accounts"[/]\n'
                '  [cyan]gacc "switch to myusername"[/]\n'
                '  [cyan]gacc "create a public repo called my-app"[/]\n'
                '  [cyan]gacc "login"[/]\n\n'
                "Or use commands: [cmd]gacc status[/], [cmd]gacc list[/], "
                "[cmd]gacc use <user>[/], [cmd]gacc create <name>[/]",
                title="[warn]Unknown request[/]",
                border_style="yellow",
            )
        )
        raise typer.Exit(1)

    cmd, kwargs = parsed
    _info(f"Understood: [accent]{cmd}[/] {kwargs if kwargs else ''}")

    if cmd == "status":
        status()
    elif cmd == "list":
        list_accounts()
    elif cmd == "login":
        login()
    elif cmd == "use":
        use(kwargs["username"])
    elif cmd == "create":
        name = kwargs.get("name")
        if not name:
            name = typer.prompt("Repository name")
        create(
            name=name,
            public=bool(kwargs.get("public")),
            description=kwargs.get("description"),
            account=kwargs.get("account"),
        )
    elif cmd == "help":
        _show_banner()
        console.print(app.get_help())


def _show_banner() -> None:
    title = Text()
    title.append("gacc", style="bold cyan")
    title.append("  ·  ", style="dim")
    title.append("GitHub Account CLI", style="white")
    console.print(
        Panel(
            "[muted]Switch accounts · Create repos · Push code[/]\n"
            '[muted]Plain English works:[/] [cyan]gacc "create a public repo called my-app"[/]',
            title=title,
            border_style="cyan",
            padding=(0, 2),
        )
    )


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    request: Optional[str] = typer.Argument(
        None,
        help='Plain English request, e.g. "create a public repo called my-app"',
    ),
) -> None:
    """gacc – GitHub accounts & repos from the terminal (plain English supported)."""
    if ctx.invoked_subcommand is not None:
        return
    if request:
        _run_natural(request)
        return
    _show_banner()
    console.print(ctx.get_help())
    console.print()
    _muted("Examples:")
    console.print('  [cyan]gacc "who am I"[/]')
    console.print('  [cyan]gacc "list accounts"[/]')
    console.print('  [cyan]gacc "switch to octocat"[/]')
    console.print('  [cyan]gacc "create a public repo called hello"[/]')
    console.print("  [cyan]gacc status[/]  ·  [cyan]gacc list[/]  ·  [cyan]gacc create my-app --public[/]")


@app.command()
def status() -> None:
    """Show the currently active GitHub account."""
    _ensure_gh()
    user = _current_user()
    if user:
        console.print(
            Panel(
                f"[success]Active account[/]\n\n[accent]{user}[/]",
                border_style="green",
                padding=(0, 2),
            )
        )
    else:
        _fail("No authenticated GitHub account found.")
        _muted("Run: gacc login   or   gh auth login")
        raise typer.Exit(1)


@app.command("list")
def list_accounts() -> None:
    """List all authenticated GitHub accounts."""
    _ensure_gh()
    accounts = _gh_auth_status()
    if not accounts:
        _fail("No authenticated accounts found.")
        _muted("Run: gacc login   or   gh auth login")
        raise typer.Exit(1)

    table = Table(
        title="GitHub Accounts",
        show_header=True,
        header_style="bold cyan",
        border_style="dim",
        title_style="bold",
    )
    table.add_column("User", style="cyan", no_wrap=True)
    table.add_column("Host", style="muted")
    table.add_column("Active", justify="center")

    for acc in accounts:
        active = "[success]✓[/]" if acc.get("active") else "[muted]—[/]"
        table.add_row(acc.get("user", "?"), acc.get("host", "github.com"), active)

    console.print(table)


@app.command()
def use(
    username: str = typer.Argument(..., help="GitHub username to switch to"),
) -> None:
    """Switch the active GitHub account."""
    _ensure_gh()
    _info(f"Switching to [accent]{username}[/]...")
    if not _switch_user(username):
        _fail(f"Failed to switch to '{username}'.")
        _muted("Make sure the account is authenticated: gh auth login")
        raise typer.Exit(1)
    _ok(f"Switched to [accent]{username}[/]")


@app.command()
def login() -> None:
    """Add / authenticate a new GitHub account (wraps `gh auth login`)."""
    _ensure_gh()
    _info("Starting GitHub authentication...")
    result = subprocess.run(["gh", "auth", "login"])
    if result.returncode != 0:
        _fail("Authentication failed or was cancelled.")
        raise typer.Exit(result.returncode)
    _ok("Authentication complete.")


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
        help="Push local commits after creating the remote (default: yes)",
    ),
) -> None:
    """Create a new GitHub repository and optionally push the current folder."""
    _ensure_gh()

    if account:
        _info(f"Using account [accent]{account}[/]...")
        if not _switch_user(account):
            _fail(f"Could not switch to account '{account}'.")
            _muted("Authenticate it first: gacc login")
            raise typer.Exit(1)

    current = _current_user()
    if current:
        _info(f"Creating under [accent]{current}[/]")

    git_dir = source / ".git"
    if not git_dir.exists():
        console.print(f"[warn]No git repository in[/] [cmd]{source}[/]")
        if typer.confirm("Run git init?", default=True):
            _run(["git", "init"], check=True)
            _ok("Initialized empty Git repository.")
        else:
            _muted("Aborted.")
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
    cmd.append("--public" if public else "--private")
    if description:
        cmd.extend(["--description", description])
    if push:
        cmd.append("--push")

    _muted(f"$ {' '.join(cmd)}")
    result = subprocess.run(cmd)

    if result.returncode != 0:
        _fail("Failed to create repository.")
        raise typer.Exit(result.returncode)

    vis = "public" if public else "private"
    _ok(f"Repository [accent]{name}[/] created ([cmd]{vis}[/])")
    if current:
        url = f"https://github.com/{current}/{name}"
        console.print(f"  [info]→[/] [link={url}]{url}[/link]")


@app.command()
def version() -> None:
    """Show gacc version."""
    from gacc import __version__

    console.print(
        Panel(
            f"[accent]gacc[/] [cmd]{__version__}[/]",
            border_style="cyan",
            padding=(0, 2),
        )
    )


@app.command("ask")
def ask(
    request: str = typer.Argument(
        ...,
        help='Plain English, e.g. "create a public repo called my-app"',
    ),
) -> None:
    """Do something in plain English (same as: gacc \"your request\")."""
    _run_natural(request)


if __name__ == "__main__":
    app()
