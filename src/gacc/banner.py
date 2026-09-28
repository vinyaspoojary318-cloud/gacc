"""Ice Bear startup banner for gacc."""

from __future__ import annotations

from rich.align import Align
from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text

# Cool Ice Bear (sunglasses) — terminal-safe ASCII
ICE_BEAR = r"""
            ╭─────────────╮
         ╭──╯             ╰──╮
        ╱   ┌───┐   ┌───┐    ╲
       │    │███│   │███│     │
       │    └───┘   └───┘     │
       │         ●            │
        ╲        ───         ╱
         ╰──╮           ╭───╯
            ╰───────────╯
"""

ICE_BEAR_MINI = r"""
   ╭──────╮
  ╱ ■  ■  ╲
 │    ●    │
  ╲  ───  ╱
   ╰──────╯
"""


def render_banner(console: Console) -> None:
    """Print the distinctive Ice Bear startup screen."""
    art = Text(ICE_BEAR, style="bold white")
    tagline = Text()
    tagline.append("gacc", style="bold cyan")
    tagline.append("  ·  ", style="dim")
    tagline.append("GitHub Account CLI", style="white")

    subtitle = Text.from_markup(
        "[dim]Plain English · Account guard · Ship in one command[/]\n"
        "[dim]Stay cool. Never ship under the wrong account.[/]"
    )

    examples = Text.from_markup(
        '[cyan]gacc "create a public repo called my-app"[/]\n'
        "[cyan]gacc ship my-app --public[/]   ·   [cyan]gacc check[/]"
    )

    body = Group(
        Align.center(art),
        Align.center(tagline),
        Text(""),
        Align.center(subtitle),
        Text(""),
        Align.center(examples),
    )

    console.print(
        Panel(
            body,
            border_style="cyan",
            padding=(0, 2),
            title="[bold cyan]❄ Ice Bear[/]",
            subtitle="[dim]v0.3.2[/]",
            subtitle_align="right",
        )
    )
    console.print()


def render_mini(console: Console) -> None:
    """Smaller mark used above command results."""
    console.print(
        Text.from_markup(
            "[bold white]   ╭──╮[/]  [bold cyan]gacc[/] [dim]· stay cool[/]\n"
            "[bold white]  ╱■■ ■■╲[/]\n"
            "[bold white] │   ●   │[/]\n"
            "[bold white]  ╲ ─── ╱[/]\n"
            "[bold white]   ╰──╯[/]"
        )
    )
