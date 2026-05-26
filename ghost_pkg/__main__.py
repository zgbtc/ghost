"""Ghost CLI entrypoint."""

from __future__ import annotations

import sys
from typing import Optional

import typer
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from rich.console import Console

from ghost.agent import Ghost
from ghost.config import config


app = typer.Typer(
    add_completion=False,
    help="Ghost — your digital twin. Self-evolving desktop AI agent.",
    context_settings={"help_option_names": ["-h", "--help"]},
)
console = Console()


def _user_asker_factory(prompt_session: PromptSession):
    def ask(question: str) -> str:
        console.print(f"[bold yellow]ghost asks:[/bold yellow] {question}")
        try:
            return prompt_session.prompt("> ").strip()
        except (EOFError, KeyboardInterrupt):
            return ""
    return ask


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """Default action: open an interactive chat."""
    if ctx.invoked_subcommand is None:
        chat()


@app.command()
def chat() -> None:
    """Start an interactive Ghost session."""
    # Fix asyncio conflict between prompt_toolkit and Playwright on Windows
    try:
        import nest_asyncio
        nest_asyncio.apply()
    except ImportError:
        pass

    config.ensure_dirs()
    history_file = config.home / ".chat_history"
    session = PromptSession(history=FileHistory(str(history_file)))

    ghost = Ghost(
        config=config,
        console=console,
        user_asker=_user_asker_factory(session),
    )

    console.print("[bold green]👻 Ghost is awake.[/bold green]  Type your message, /quit to leave.")
    console.print(f"[dim]home={config.home}  model={config.model}  session={ghost.session_id}[/dim]")

    while True:
        try:
            line = session.prompt("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]bye 👻[/dim]")
            break
        if not line:
            continue
        if line.lower() in ("/quit", "/exit", ":q"):
            console.print("[dim]bye 👻[/dim]")
            break
        if line == "/skills":
            _print_skills(ghost)
            continue
        if line == "/stats":
            _print_stats(ghost)
            continue
        if line == "/emotion":
            _print_emotion(ghost)
            continue
        try:
            ghost.run(line)
        except KeyboardInterrupt:
            console.print("[yellow]interrupted[/yellow]")
            continue


@app.command()
def run(message: str = typer.Argument(..., help="Message to send to Ghost.")) -> None:
    """Single-shot: send one message and print the result."""
    ghost = Ghost(config=config, console=console)
    ghost.run(message)
    _print_stats(ghost)


@app.command()
def skills() -> None:
    """List all learned skills."""
    ghost = Ghost(config=config, console=console)
    _print_skills(ghost)


@app.command()
def soul(edit: bool = typer.Option(False, "--edit", "-e", help="Open soul.md in $EDITOR.")) -> None:
    """Show or edit Ghost's soul (personality + values)."""
    config.ensure_dirs()
    if edit:
        import os, subprocess
        editor = os.environ.get("EDITOR") or ("notepad" if sys.platform == "win32" else "vi")
        subprocess.call([editor, str(config.soul_path)])
        return
    if not config.soul_path.exists():
        # touch defaults
        from ghost.memory import MemoryLayers
        MemoryLayers(config)
    console.print(config.soul_path.read_text(encoding="utf-8"))


@app.command()
def memory() -> None:
    """Show persistent memory."""
    config.ensure_dirs()
    if not config.memory_path.exists():
        from ghost.memory import MemoryLayers
        MemoryLayers(config)
    console.print(config.memory_path.read_text(encoding="utf-8"))


@app.command()
def doctor() -> None:
    """Diagnose configuration issues."""
    console.print(f"[bold]Ghost home:[/bold] {config.home}")
    console.print(f"[bold]Model:[/bold] {config.model}")
    if config.anthropic_api_key:
        console.print("[green]✓[/green] ANTHROPIC_API_KEY set")
    else:
        console.print("[red]✗[/red] ANTHROPIC_API_KEY missing — copy .env.example to .env")
    # Test desktop bits
    try:
        from ghost.desktop import Screen
        s = Screen()
        shot = s.primary()
        console.print(f"[green]✓[/green] screen capture OK ({shot.width}x{shot.height})")
    except Exception as e:
        console.print(f"[red]✗[/red] screen capture failed: {e}")
    try:
        import pyautogui
        x, y = pyautogui.position()
        console.print(f"[green]✓[/green] mouse OK (cursor at {x},{y})")
    except Exception as e:
        console.print(f"[red]✗[/red] pyautogui failed: {e}")


# ────────────────────────────────────────────────────────────────────
# helpers
# ────────────────────────────────────────────────────────────────────


def _print_skills(ghost: Ghost) -> None:
    cards = ghost.layers.list_skills()
    if not cards:
        console.print("[dim](no skills yet — every solved task can become one)[/dim]")
        return
    for c in cards:
        total = c.success + c.failure
        rate = f"{int(c.confidence * 100)}%" if total else "new"
        console.print(f"• [bold]{c.name}[/bold] [{rate}] — {c.summary}")


def _print_stats(ghost: Ghost) -> None:
    s = ghost.stats
    console.print(
        f"[dim]turns={s.turns}  tools={s.tool_calls}  "
        f"in={s.input_tokens}  out={s.output_tokens}[/dim]"
    )


def _print_emotion(ghost: Ghost) -> None:
    e = ghost.layers.emotion
    e.decay()
    console.print(f"[bold]emotion:[/bold] {e.describe()}")
    console.print(
        f"  pleasure={e.pleasure:+.2f}  arousal={e.arousal:+.2f}  dominance={e.dominance:+.2f}"
    )


if __name__ == "__main__":
    app()


# ────────────────────────────────────────────────────────────────────
# extended commands: record / cron / daemon / telegram
# ────────────────────────────────────────────────────────────────────


@app.command()
def record(
    intent: str = typer.Argument(..., help="What you're about to demonstrate (e.g. 'send daily report')."),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Override skill slug; default = derived from intent."),
) -> None:
    """Record a human demonstration → distill into a reusable skill.

    Press Ctrl+C when you're done to stop and distill.
    """
    import time as _time
    from datetime import datetime
    from ghost.demo.recorder import DemoRecorder
    from ghost.demo.distill import distill
    from ghost.llm import AnthropicClient

    config.ensure_dirs()
    slug = (name or intent).strip().lower().replace(" ", "-")
    out_dir = config.demos_dir / f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{slug}"

    console.print(f"[bold cyan]🎬 recording demo:[/bold cyan] {intent}")
    console.print(f"[dim]→ {out_dir}[/dim]")
    console.print("[dim]do the task now; press Ctrl+C to stop[/dim]")

    recorder = DemoRecorder(out_dir=out_dir)
    recorder.start()
    try:
        while True:
            _time.sleep(1)
    except KeyboardInterrupt:
        console.print("\n[bold]stopping…[/bold]")

    trace = recorder.stop()
    console.print(f"[green]✓[/green] {trace.summary()}")

    if not config.anthropic_api_key:
        console.print("[yellow]⚠ no ANTHROPIC_API_KEY — saved trace only, skipping distillation[/yellow]")
        return

    console.print("[dim]distilling into a skill…[/dim]")
    from ghost.memory import MemoryLayers
    from ghost.llm.client import GhostLLMClient
    layers = MemoryLayers(config)
    llm = GhostLLMClient()
    skill = distill(trace, llm=llm, layers=layers, user_hint=intent)
    console.print(f"[bold magenta]✶ skill learned:[/bold magenta] {skill.get('name')}")
    console.print(f"[dim]{skill.get('summary')}[/dim]")


@app.command(name="cron")
def cron_cmd(
    action: str = typer.Argument(..., help="list | add | remove"),
    name: Optional[str] = typer.Argument(None),
    expr: Optional[str] = typer.Argument(None, help="5-field cron expression"),
    prompt: Optional[str] = typer.Argument(None, help="prompt to feed Ghost"),
) -> None:
    """Manage scheduled jobs. Persisted to <ghost_home>/cronjobs.json."""
    from ghost.schedule import CronScheduler, CronJob
    config.ensure_dirs()
    sched = CronScheduler.load(config.home / "cronjobs.json", runner=lambda _msg: "")
    if action == "list":
        if not sched.jobs:
            console.print("[dim](no scheduled jobs)[/dim]")
            return
        for j in sched.jobs:
            mark = "✓" if j.enabled else "✗"
            console.print(f"{mark} [bold]{j.name}[/bold]  [cyan]{j.expr}[/cyan]  → {j.prompt[:60]}")
        return
    if action == "add":
        if not (name and expr and prompt):
            console.print("[red]usage:[/red] ghost cron add <name> '<cron expr>' '<prompt>'")
            raise typer.Exit(1)
        sched.add(CronJob(name=name, expr=expr, prompt=prompt))
        console.print(f"[green]✓[/green] added {name}")
        return
    if action == "remove":
        if not name:
            console.print("[red]usage:[/red] ghost cron remove <name>")
            raise typer.Exit(1)
        ok = sched.remove(name)
        console.print(("[green]✓[/green] removed " if ok else "[yellow]not found:[/yellow] ") + name)
        return
    console.print("[red]unknown action[/red]")
    raise typer.Exit(1)


@app.command()
def daemon() -> None:
    """Run Ghost as a background daemon: cron jobs fire automatically."""
    import time as _time
    from ghost.schedule import CronScheduler
    config.ensure_dirs()

    def runner(prompt: str) -> str:
        ghost = Ghost(config=config, console=console)
        return ghost.run(prompt)

    sched = CronScheduler.load(config.home / "cronjobs.json", runner=runner)
    sched.start()
    console.print(f"[bold green]👻 daemon online — {len(sched.jobs)} job(s) loaded[/bold green]")
    console.print("[dim]Ctrl+C to stop[/dim]")
    try:
        while True:
            _time.sleep(60)
    except KeyboardInterrupt:
        console.print("\n[dim]bye[/dim]")
        sched.stop()


@app.command()
def telegram() -> None:
    """Start the Telegram remote channel.

    Set TELEGRAM_BOT_TOKEN and TELEGRAM_ALLOWED_IDS in .env first.
    """
    from ghost.channels.telegram_bot import TelegramBot, TelegramConfig
    cfg = TelegramConfig.from_env()
    if not cfg.token:
        console.print("[red]TELEGRAM_BOT_TOKEN missing in .env[/red]")
        raise typer.Exit(1)
    if not cfg.allowed_ids:
        console.print("[yellow]⚠ TELEGRAM_ALLOWED_IDS empty — anyone can talk to your Ghost![/yellow]")

    def runner(msg: str) -> str:
        ghost = Ghost(config=config, console=console)
        return ghost.run(msg)

    bot = TelegramBot(cfg, runner=runner)
    try:
        bot.run_forever()
    except KeyboardInterrupt:
        console.print("\n[dim]telegram bot stopped[/dim]")



@app.command()
def gateway(
    platform: str = typer.Argument(..., help="Platform: telegram | discord | feishu | weixin | wecom | dingtalk"),
) -> None:
    """Start a messaging platform gateway.

    Connects Ghost to messaging apps so you can control it remotely.

    Supported platforms:
      telegram  — Telegram Bot (works out of the box, just needs BOT_TOKEN)
      discord   — Discord Bot (needs DISCORD_BOT_TOKEN)
      feishu    — 飞书/Lark (needs App ID + Secret)
      weixin    — 个人微信 (via iLink Bot API)
      wecom     — 企业微信 (needs Corp ID + Agent)
      dingtalk  — 钉钉 (needs App Key + Secret)
    """
    from ghost.channels.gateway import GhostGateway
    gw = GhostGateway(platform=platform)
    try:
        gw.run()
    except KeyboardInterrupt:
        console.print(f"\n[dim]{platform} gateway stopped[/dim]")
    except Exception as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)
