"""gacc – GitHub Account CLI.

Talk to GitHub in plain English — and never ship under the wrong account.
Built on the official GitHub CLI (gh).
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional

import typer
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from gacc.helpers import (
    account_guard,
    console,
    current_user,
    ensure_gh,
    fail,
    gh_auth_status,
    git_identity,
    info,
    is_explain,
    muted,
    ok,
    remote_owner,
    run,
    set_explain,
    switch_user,
    would,
)
from gacc.nl import parse_natural

app = typer.Typer(
    name="gacc",
    help=(
        "Talk to GitHub in plain English — and never ship under the wrong account.\n\n"
        "[dim]Examples:[/] [cyan]gacc \"create a public repo called my-app\"[/]  ·  "
        "[cyan]gacc ship my-app --public[/]  ·  [cyan]gacc check[/]"
    ),
    add_completion=False,
    no_args_is_help=False,
    rich_markup_mode="rich",
)


def _show_banner() -> None:
    title = Text()
    title.append("gacc", style="bold cyan")
    title.append("  ·  ", style="dim")
    title.append("GitHub Account CLI", style="white")
    console.print(
        Panel(
            "[muted]Plain English · Account guard · Ship in one command[/]\n"
            '[cyan]gacc "create a public repo called my-app"[/]  ·  '
            "[cyan]gacc ship my-app --public[/]  ·  [cyan]gacc check[/]",
            title=title,
            border_style="cyan",
            padding=(0, 2),
        )
    )


def _run_natural(text: str) -> None:
    parsed = parse_natural(text)
    if not parsed:
        console.print(
            Panel(
                f"[warn]I didn't understand:[/] [cmd]{text}[/]\n\n"
                "[muted]Try:[/]\n"
                '  [cyan]gacc "who am I"[/]\n'
                '  [cyan]gacc "check account"[/]\n'
                '  [cyan]gacc "list my accounts"[/]\n'
                '  [cyan]gacc "switch to myusername"[/]\n'
                '  [cyan]gacc "create a public repo called my-app"[/]\n'
                '  [cyan]gacc "ship this as public repo my-app"[/]\n'
                '  [cyan]gacc "login"[/]',
                title="[warn]Unknown request[/]",
                border_style="yellow",
            )
        )
        raise typer.Exit(1)

    cmd, kwargs = parsed
    info(f"Understood: [accent]{cmd}[/] {kwargs if kwargs else ''}")
    if is_explain():
        muted("(explain / dry-run mode — no changes will be made)")

    if cmd == "status":
        status()
    elif cmd == "check":
        check()
    elif cmd == "list":
        list_accounts()
    elif cmd == "login":
        login()
    elif cmd == "use":
        use(kwargs["username"])
    elif cmd == "create":
        name = kwargs.get("name") or typer.prompt("Repository name")
        create(
            name=name,
            public=bool(kwargs.get("public")),
            description=kwargs.get("description"),
            account=kwargs.get("account"),
            force=False,
        )
    elif cmd == "ship":
        ship(
            name=kwargs.get("name"),
            public=bool(kwargs.get("public")),
            account=kwargs.get("account"),
            force=False,
        )
    elif cmd == "help":
        _show_banner()
        console.print(app.get_help())


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    request: Optional[str] = typer.Argument(
        None,
        help='Plain English request, e.g. "create a public repo called my-app"',
    ),
    explain: bool = typer.Option(
        False,
        "--explain",
        "--dry-run",
        help="Show what would run without making changes",
    ),
) -> None:
    """gacc – talk to GitHub in plain English; never ship under the wrong account."""
    set_explain(explain)

    if ctx.invoked_subcommand is not None:
        return
    if request:
        _run_natural(request)
        return
    _show_banner()
    console.print(ctx.get_help())
    console.print()
    muted("Examples:")
    console.print('  [cyan]gacc "who am I"[/]')
    console.print('  [cyan]gacc "check account"[/]')
    console.print('  [cyan]gacc "list accounts"[/]')
    console.print('  [cyan]gacc "switch to octocat"[/]')
    console.print('  [cyan]gacc "create a public repo called hello"[/]')
    console.print("  [cyan]gacc ship my-app --public[/]")
    console.print("  [cyan]gacc create my-app --public --explain[/]")


@app.command()
def status() -> None:
    """Show the currently active GitHub account."""
    ensure_gh()
    user = current_user()
    if user:
        console.print(
            Panel(
                f"[success]Active account[/]\n\n[accent]{user}[/]",
                border_style="green",
                padding=(0, 2),
            )
        )
    else:
        fail("No authenticated GitHub account found.")
        muted("Run: gacc login   or   gh auth login")
        raise typer.Exit(1)


@app.command()
def check(
    path: Path = typer.Option(
        Path("."),
        "--path",
        "-p",
        help="Repo path to check against",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
) -> None:
    """Check whether the active account matches this repo (account guard)."""
    ensure_gh()
    active = current_user()
    if not active:
        fail("No authenticated GitHub account.")
        muted("Run: gacc login")
        raise typer.Exit(1)

    git_name, git_email = git_identity(path)
    owner = remote_owner(path)

    table = Table(show_header=False, border_style="dim", box=None, padding=(0, 2))
    table.add_column("Key", style="muted")
    table.add_column("Value", style="accent")
    table.add_row("Active gh account", active)
    table.add_row("Git user.name", git_name or "—")
    table.add_row("Git user.email", git_email or "—")
    table.add_row("Remote owner", owner or "— (no origin)")

    ok_match = True
    notes: list[str] = []
    if owner and active.lower() != owner.lower():
        ok_match = False
        notes.append(
            f"Remote owner [accent]{owner}[/] ≠ active account [accent]{active}[/]. "
            f"Switch with: [cmd]gacc use {owner}[/]"
        )
    if not owner:
        notes.append("[muted]No origin remote — nothing to mismatch yet.[/]")

    border = "green" if ok_match else "yellow"
    title = "[success]Looks good[/]" if ok_match else "[warn]Possible mismatch[/]"
    console.print(Panel(table, title=title, border_style=border))
    for n in notes:
        console.print(f"  {n}")


@app.command("list")
def list_accounts() -> None:
    """List all authenticated GitHub accounts."""
    ensure_gh()
    accounts = gh_auth_status()
    if not accounts:
        fail("No authenticated accounts found.")
        muted("Run: gacc login   or   gh auth login")
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
    ensure_gh()
    info(f"Switching to [accent]{username}[/]...")
    if not switch_user(username):
        fail(f"Failed to switch to '{username}'.")
        muted("Make sure the account is authenticated: gh auth login")
        raise typer.Exit(1)
    if is_explain():
        ok(f"Would switch to [accent]{username}[/]")
    else:
        ok(f"Switched to [accent]{username}[/]")


@app.command()
def login() -> None:
    """Add / authenticate a new GitHub account (wraps `gh auth login`)."""
    ensure_gh()
    if is_explain():
        would("gh auth login")
        return
    info("Starting GitHub authentication...")
    result = subprocess.run(["gh", "auth", "login"])
    if result.returncode != 0:
        fail("Authentication failed or was cancelled.")
        raise typer.Exit(result.returncode)
    ok("Authentication complete.")


@app.command()
def create(
    name: str = typer.Argument(..., help="Name of the new repository"),
    public: bool = typer.Option(
        False, "--public", help="Create a public repository (default is private)"
    ),
    description: Optional[str] = typer.Option(
        None, "--description", "-d", help="Repository description"
    ),
    account: Optional[str] = typer.Option(
        None, "--account", "-a", help="GitHub account (username) to use"
    ),
    source: Path = typer.Option(
        Path("."),
        "--source",
        "-s",
        help="Local path (default: current directory)",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
    push: bool = typer.Option(
        True, "--push/--no-push", help="Push after create (default: yes)"
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Skip account-guard confirmation"
    ),
) -> None:
    """Create a new GitHub repository (with account guard)."""
    ensure_gh()

    if account:
        info(f"Using account [accent]{account}[/]...")
        if not switch_user(account):
            fail(f"Could not switch to account '{account}'.")
            muted("Authenticate it first: gacc login")
            raise typer.Exit(1)

    current = account_guard(
        expected=account,
        path=source,
        action=f"create repo [accent]{name}[/]",
        force=force,
    )

    if not (source / ".git").exists():
        console.print(f"[warn]No git repository in[/] [cmd]{source}[/]")
        if is_explain():
            would("git init")
        elif typer.confirm("Run git init?", default=True):
            run(["git", "init"], check=True)
            ok("Initialized empty Git repository.")
        else:
            muted("Aborted.")
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
        "--public" if public else "--private",
    ]
    if description:
        cmd.extend(["--description", description])
    if push:
        cmd.append("--push")

    if is_explain():
        would(cmd)
        vis = "public" if public else "private"
        ok(
            f"Would create [accent]{name}[/] ([cmd]{vis}[/]) "
            f"under [accent]{current or '?'}[/]"
        )
        return

    muted(f"$ {' '.join(cmd)}")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        fail("Failed to create repository.")
        raise typer.Exit(result.returncode)

    vis = "public" if public else "private"
    ok(f"Repository [accent]{name}[/] created ([cmd]{vis}[/])")
    if current:
        url = f"https://github.com/{current}/{name}"
        console.print(f"  [info]→[/] [link={url}]{url}[/link]")


@app.command()
def ship(
    name: Optional[str] = typer.Argument(
        None, help="Repository name (default: current folder name)"
    ),
    public: bool = typer.Option(
        False, "--public", help="Create a public repository (default is private)"
    ),
    account: Optional[str] = typer.Option(
        None, "--account", "-a", help="GitHub account to ship under"
    ),
    message: str = typer.Option(
        "Initial commit", "--message", "-m", help="Commit message if needed"
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Skip account-guard confirmation"
    ),
    source: Path = typer.Option(
        Path("."),
        "--source",
        "-s",
        help="Project directory",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
) -> None:
    """One-shot: init → commit (if needed) → create repo → push."""
    ensure_gh()

    repo_name = name or source.name
    info(f"Shipping [accent]{repo_name}[/]...")

    if account:
        info(f"Using account [accent]{account}[/]...")
        if not switch_user(account):
            fail(f"Could not switch to '{account}'.")
            raise typer.Exit(1)

    current = account_guard(
        expected=account,
        path=source,
        action=f"ship [accent]{repo_name}[/]",
        force=force,
    )

    if not (source / ".git").exists():
        if is_explain():
            would(["git", "-C", str(source), "init"])
        else:
            run(["git", "init"], check=True)
            ok("git init")

    head = run(["git", "rev-parse", "HEAD"], check=False)
    if head.returncode != 0:
        if is_explain():
            would(["git", "add", "-A"])
            would(["git", "commit", "-m", message])
        else:
            run(["git", "add", "-A"], check=False)
            c = run(["git", "commit", "-m", message], check=False)
            if c.returncode == 0:
                ok(f"Committed: [cmd]{message}[/]")
            else:
                run(["git", "commit", "--allow-empty", "-m", message], check=False)
                ok(f"Empty commit: [cmd]{message}[/]")

    cmd = [
        "gh",
        "repo",
        "create",
        repo_name,
        "--source",
        str(source),
        "--remote",
        "origin",
        "--public" if public else "--private",
        "--push",
    ]

    if is_explain():
        would(cmd)
        vis = "public" if public else "private"
        ok(
            f"Would ship [accent]{repo_name}[/] ([cmd]{vis}[/]) "
            f"under [accent]{current or '?'}[/]"
        )
        return

    muted(f"$ {' '.join(cmd)}")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        fail("Ship failed (gh repo create).")
        raise typer.Exit(result.returncode)

    vis = "public" if public else "private"
    ok(f"Shipped [accent]{repo_name}[/] ([cmd]{vis}[/])")
    if current:
        url = f"https://github.com/{current}/{repo_name}"
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
        ..., help='Plain English, e.g. "create a public repo called my-app"'
    ),
) -> None:
    """Do something in plain English (same as: gacc \"your request\")."""
    _run_natural(request)


if __name__ == "__main__":
    app()
