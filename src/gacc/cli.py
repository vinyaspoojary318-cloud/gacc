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
    clear_activity,
    console,
    current_user,
    ensure_gh,
    fail,
    gh_auth_status,
    git_identity,
    info,
    is_explain,
    log_step,
    muted,
    ok,
    remote_owner,
    run,
    set_explain,
    show_summary,
    switch_user,
    would,
)
from gacc.banner import render_banner
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
    """Ice Bear startup screen — shown when gacc runs with no args."""
    render_banner(console)


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
    clear_activity()

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
    clear_activity()
    ensure_gh()
    user = current_user()
    if user:
        log_step("Checked active account", detail=user, meta={"account": user})
        console.print(
            Panel(
                f"[success]Active account[/]\n\n[accent]{user}[/]",
                border_style="green",
                padding=(0, 2),
            )
        )
        show_summary("What happened")
    else:
        log_step("Checked active account", detail="none found", ok=False)
        fail("No authenticated GitHub account found.")
        muted("Run: gacc login   or   gh auth login")
        show_summary("What happened")
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
    clear_activity()
    ensure_gh()
    active = current_user()
    if not active:
        log_step("Checked active account", detail="none found", ok=False)
        fail("No authenticated GitHub account.")
        muted("Run: gacc login")
        show_summary("What happened")
        raise typer.Exit(1)

    git_name, git_email = git_identity(path)
    owner = remote_owner(path)

    log_step("Read active gh account", detail=active, meta={"account": active})
    log_step("Read git user.name", detail=git_name or "(not set)")
    log_step("Read git user.email", detail=git_email or "(not set)")
    log_step("Read remote owner", detail=owner or "(no origin)")

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
        log_step(
            "Account match check",
            detail=f"mismatch: active={active}, remote={owner}",
            ok=False,
        )
    else:
        log_step("Account match check", detail="OK" if owner else "no remote to compare")
    if not owner:
        notes.append("[muted]No origin remote — nothing to mismatch yet.[/]")

    border = "green" if ok_match else "yellow"
    title = "[success]Looks good[/]" if ok_match else "[warn]Possible mismatch[/]"
    console.print(Panel(table, title=title, border_style=border))
    for n in notes:
        console.print(f"  {n}")
    show_summary("What happened")


@app.command("list")
def list_accounts() -> None:
    """List all authenticated GitHub accounts."""
    clear_activity()
    ensure_gh()
    accounts = gh_auth_status()
    if not accounts:
        log_step("Listed accounts", detail="none found", ok=False)
        fail("No authenticated accounts found.")
        muted("Run: gacc login   or   gh auth login")
        show_summary("What happened")
        raise typer.Exit(1)

    names = [a.get("user", "?") for a in accounts]
    log_step(
        "Listed authenticated accounts",
        detail=f"{len(accounts)} account(s): {', '.join(names)}",
    )

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
    show_summary("What happened")


@app.command()
def use(
    username: str = typer.Argument(..., help="GitHub username to switch to"),
) -> None:
    """Switch the active GitHub account."""
    clear_activity()
    ensure_gh()
    before = current_user()
    if before:
        log_step("Previous active account", detail=before, meta={"account": before})
    info(f"Switching to [accent]{username}[/]...")
    if not switch_user(username):
        log_step("Switch account", detail=f"failed → {username}", ok=False)
        fail(f"Failed to switch to '{username}'.")
        muted("Make sure the account is authenticated: gh auth login")
        show_summary("What happened")
        raise typer.Exit(1)
    log_step(
        "Switched active account",
        detail=f"{before or '?'} → {username}",
        meta={"account": username},
    )
    if is_explain():
        ok(f"Would switch to [accent]{username}[/]")
    else:
        ok(f"Switched to [accent]{username}[/]")
    show_summary("What happened")


@app.command()
def login() -> None:
    """Add / authenticate a new GitHub account (wraps `gh auth login`)."""
    clear_activity()
    ensure_gh()
    if is_explain():
        would("gh auth login")
        log_step("Authenticate new account", detail="gh auth login (dry-run)")
        show_summary("What would happen")
        return
    info("Starting GitHub authentication...")
    log_step("Started GitHub login flow", detail="gh auth login")
    result = subprocess.run(["gh", "auth", "login"])
    if result.returncode != 0:
        log_step("Authentication", detail="failed or cancelled", ok=False)
        fail("Authentication failed or was cancelled.")
        show_summary("What happened")
        raise typer.Exit(result.returncode)
    user = current_user()
    log_step(
        "Authentication complete",
        detail=user or "ok",
        meta={"account": user} if user else None,
    )
    ok("Authentication complete.")
    if user:
        ok(f"Active account is now [accent]{user}[/]")
    show_summary("What happened")


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
    clear_activity()
    ensure_gh()
    vis = "public" if public else "private"
    log_step("Create repository requested", detail=f"{name} ({vis})")

    if account:
        info(f"Using account [accent]{account}[/]...")
        if not switch_user(account):
            log_step("Switch account", detail=f"failed → {account}", ok=False)
            fail(f"Could not switch to account '{account}'.")
            muted("Authenticate it first: gacc login")
            show_summary("What happened")
            raise typer.Exit(1)
        log_step("Switched account", detail=account, meta={"account": account})

    current = account_guard(
        expected=account,
        path=source,
        action=f"create repo [accent]{name}[/]",
        force=force,
    )
    if current:
        log_step("Account guard passed", detail=current, meta={"account": current})

    if not (source / ".git").exists():
        console.print(f"[warn]No git repository in[/] [cmd]{source}[/]")
        if is_explain():
            would("git init")
            log_step("git init", detail=str(source))
        elif typer.confirm("Run git init?", default=True):
            run(["git", "init"], check=True)
            log_step("Initialized git repo", detail=str(source))
            ok("Initialized empty Git repository.")
        else:
            log_step("git init", detail="aborted by user", ok=False)
            muted("Aborted.")
            show_summary("What happened")
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
        log_step(
            "Would create + push repo",
            detail=f"{name} ({vis}) under {current or '?'}",
            meta={
                "account": current,
                "url": f"https://github.com/{current}/{name}" if current else None,
            },
        )
        ok(
            f"Would create [accent]{name}[/] ([cmd]{vis}[/]) "
            f"under [accent]{current or '?'}[/]"
        )
        show_summary("What would happen")
        return

    muted(f"$ {' '.join(cmd)}")
    log_step("Running gh repo create", detail=" ".join(cmd))
    result = subprocess.run(cmd)
    if result.returncode != 0:
        log_step("Create repository", detail="failed", ok=False)
        fail("Failed to create repository.")
        show_summary("What happened")
        raise typer.Exit(result.returncode)

    url = f"https://github.com/{current}/{name}" if current else None
    log_step(
        "Repository created",
        detail=f"{name} ({vis})" + (" + pushed" if push else ""),
        meta={"account": current, "url": url},
    )
    if push:
        log_step("Pushed to origin", detail="remote: origin")
    ok(f"Repository [accent]{name}[/] created ([cmd]{vis}[/])")
    if url:
        console.print(f"  [info]→[/] [link={url}]{url}[/link]")
    show_summary("What happened on your account")


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
    clear_activity()
    ensure_gh()

    repo_name = name or source.name
    vis = "public" if public else "private"
    info(f"Shipping [accent]{repo_name}[/]...")
    log_step("Ship requested", detail=f"{repo_name} ({vis})")

    if account:
        info(f"Using account [accent]{account}[/]...")
        if not switch_user(account):
            log_step("Switch account", detail=f"failed → {account}", ok=False)
            fail(f"Could not switch to '{account}'.")
            show_summary("What happened")
            raise typer.Exit(1)
        log_step("Switched account", detail=account, meta={"account": account})

    current = account_guard(
        expected=account,
        path=source,
        action=f"ship [accent]{repo_name}[/]",
        force=force,
    )
    if current:
        log_step("Account guard passed", detail=current, meta={"account": current})

    if not (source / ".git").exists():
        if is_explain():
            would(["git", "-C", str(source), "init"])
            log_step("git init", detail=str(source))
        else:
            run(["git", "init"], check=True)
            log_step("Initialized git repo", detail=str(source))
            ok("git init")

    head = run(["git", "rev-parse", "HEAD"], check=False)
    if head.returncode != 0:
        if is_explain():
            would(["git", "add", "-A"])
            would(["git", "commit", "-m", message])
            log_step("Would commit", detail=message)
        else:
            run(["git", "add", "-A"], check=False)
            c = run(["git", "commit", "-m", message], check=False)
            if c.returncode == 0:
                log_step("Created commit", detail=message)
                ok(f"Committed: [cmd]{message}[/]")
            else:
                run(["git", "commit", "--allow-empty", "-m", message], check=False)
                log_step("Created empty commit", detail=message)
                ok(f"Empty commit: [cmd]{message}[/]")
    else:
        log_step("Existing commits found", detail="skipping new commit")

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
        log_step(
            "Would create + push repo",
            detail=f"{repo_name} ({vis}) under {current or '?'}",
            meta={
                "account": current,
                "url": f"https://github.com/{current}/{repo_name}" if current else None,
            },
        )
        ok(
            f"Would ship [accent]{repo_name}[/] ([cmd]{vis}[/]) "
            f"under [accent]{current or '?'}[/]"
        )
        show_summary("What would happen")
        return

    muted(f"$ {' '.join(cmd)}")
    log_step("Running gh repo create --push", detail=" ".join(cmd))
    result = subprocess.run(cmd)
    if result.returncode != 0:
        log_step("Ship", detail="gh repo create failed", ok=False)
        fail("Ship failed (gh repo create).")
        show_summary("What happened")
        raise typer.Exit(result.returncode)

    url = f"https://github.com/{current}/{repo_name}" if current else None
    log_step(
        "Repository created on GitHub",
        detail=f"{repo_name} ({vis})",
        meta={"account": current, "url": url},
    )
    log_step("Pushed to origin", detail="remote: origin")
    ok(f"Shipped [accent]{repo_name}[/] ([cmd]{vis}[/])")
    if url:
        console.print(f"  [info]→[/] [link={url}]{url}[/link]")
    show_summary("What happened on your account")


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
