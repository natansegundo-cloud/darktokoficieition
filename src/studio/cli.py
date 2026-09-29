from __future__ import annotations

from pathlib import Path

import typer
import yaml
from rich.console import Console

from .authoring import check_brief, create_brief, scaffold_episode
from .bible import bible_table, check_bible, has_bible_errors
from .board import next_row, write_board
from .config import load_goals, load_production, set_active_profile, show_first_run_warning
from .credits import build_day_plan, build_episode_plan, plan_summary, plan_table
from .loader import ProjectLoader
from .pacing import lint_bundle, pacing_table
from .pack import PackValidationError, build_pack, write_pack
from .prompts import validate_bundle, write_prompts
from .scaffold import init_project, new_episode, new_series, new_style
from .session import write_session_sheet

app = typer.Typer(help="Offline production studio for vertical AI dramas.", no_args_is_help=True)
series_app = typer.Typer(help="Manage series.", no_args_is_help=True)
style_app = typer.Typer(help="Manage style presets.", no_args_is_help=True)
brief_app = typer.Typer(help="Manage Portuguese authoring briefs.", no_args_is_help=True)
profile_app = typer.Typer(help="Manage production profiles.", no_args_is_help=True)
bible_app = typer.Typer(help="Check series bibles.", no_args_is_help=True)
app.add_typer(series_app, name="series")
app.add_typer(style_app, name="style")
app.add_typer(brief_app, name="brief")
app.add_typer(profile_app, name="profile")
app.add_typer(bible_app, name="bible")


def _root() -> Path:
    return Path.cwd()


@app.callback()
def app_callback() -> None:
    """Show the local terms warning on the first CLI execution."""
    show_first_run_warning(_root())


def _profile_header(production, profile_name: str) -> str:
    profile = production.profile(profile_name)
    bounds = profile.episode_seconds
    return (
        f"Perfil ativo: {profile_name} · {profile.resolution} · "
        f"episódios {bounds.min}-{bounds.max}s"
    )


@app.command()
def init() -> None:
    """Create the base project directories."""
    created = init_project(_root())
    typer.echo(f"Project ready at {_root()}")
    if created:
        typer.echo(f"Created {len(created)} paths")
    show_first_run_warning(_root())
    typer.echo("Studio never logs in to accounts or automates the Flow.")


@series_app.command("new")
def series_new(series_id: str) -> None:
    """Create a series from the templates."""
    try:
        path = new_series(_root(), series_id)
    except FileExistsError as exc:
        raise typer.BadParameter(str(exc)) from exc
    typer.echo(f"Created series: {path}")


@series_app.command("list")
def series_list() -> None:
    """List series and their status."""
    root = _root() / "series"
    if not root.exists():
        typer.echo("No series found.")
        return
    found = False
    for path in sorted(item for item in root.iterdir() if item.is_dir()):
        found = True
        loader = ProjectLoader(_root())
        try:
            series = loader.load_series(path.name)
            typer.echo(f"{series.id}\t{series.status}\t{series.title}")
        except Exception as exc:
            typer.echo(f"{path.name}\tINVALID\t{exc}")
    if not found:
        typer.echo("No series found.")


@style_app.command("new")
def style_new(style_id: str) -> None:
    """Create a style preset from the template."""
    try:
        path = new_style(_root(), style_id)
    except FileExistsError as exc:
        raise typer.BadParameter(str(exc)) from exc
    typer.echo(f"Created style: {path}")


@style_app.command("list")
def style_list() -> None:
    """List style presets."""
    directory = _root() / "styles"
    for path in sorted(directory.glob("*.yaml")):
        if path.name != "_template.yaml":
            typer.echo(path.stem)


episode_app = typer.Typer(help="Manage episodes.", no_args_is_help=True)
app.add_typer(episode_app, name="episode")


@episode_app.command("new")
def episode_new(series_id: str, number: int) -> None:
    """Create an episode from the templates."""
    try:
        path = new_episode(_root(), series_id, number)
    except FileExistsError as exc:
        raise typer.BadParameter(str(exc)) from exc
    typer.echo(f"Created episode: {path}")


@brief_app.command("new")
def brief_new(series_id: str) -> None:
    """Create a Portuguese authoring brief for a series."""
    try:
        path = create_brief(_root(), series_id)
    except (FileExistsError, FileNotFoundError) as exc:
        raise typer.BadParameter(str(exc)) from exc
    typer.echo(f"Created brief: {path}")


@brief_app.command("check")
def brief_check(series_id: str) -> None:
    """Report empty sections in a Portuguese authoring brief."""
    try:
        missing = check_brief(_root(), series_id)
    except FileNotFoundError as exc:
        typer.echo(f"ERROR: {exc}")
        raise typer.Exit(code=1) from exc
    if missing:
        for section in missing:
            typer.echo(f"WARNING: empty brief section: {section}")
        raise typer.Exit(code=1)
    typer.echo(f"OK: brief {series_id}")


def _print_bible_result(report, *, integration: bool = False) -> bool:
    blocked = False
    for issue in report.issues:
        if issue.level == "error" and integration and report.status != "in_production":
            prefix = "WARNING"
        else:
            prefix = issue.level.upper()
        typer.echo(f"{prefix}: Bíblia: {issue.message}")
        if issue.level == "error" and report.status == "in_production":
            blocked = True
    return blocked


@bible_app.command("check")
def bible_check(series_id: str) -> None:
    """Check required sections, placeholders, and episode cliffhangers."""
    try:
        report = check_bible(_root(), series_id)
    except Exception as exc:
        typer.echo(f"ERROR: Bíblia: {exc}")
        raise typer.Exit(code=1) from exc
    _print_bible_result(report)
    Console().print(bible_table(report))
    if has_bible_errors(report):
        raise typer.Exit(code=1)
    typer.echo(f"OK: bible {series_id}")


@app.command("scaffold")
def scaffold(series_id: str, episode_id: str) -> None:
    """Create an episode scaffold with the complete bilingual shot schema."""
    try:
        path = scaffold_episode(_root(), series_id, episode_id)
    except (FileExistsError, FileNotFoundError, ValueError) as exc:
        raise typer.BadParameter(str(exc)) from exc
    typer.echo(f"Created authoring scaffold: {path}")
    report = check_bible(_root(), series_id)
    if _print_bible_result(report, integration=True):
        raise typer.Exit(code=1)


@app.command()
def validate(
    series_id: str,
    episode_id: str | None = typer.Argument(None),
) -> None:
    """Validate a series or one episode."""
    loader = ProjectLoader(_root())
    production = load_production(_root())
    if not episode_id:
        try:
            series = loader.load_series(series_id)
            loader.load_characters(series_id)
            loader.load_locations(series_id)
            loader.load_style(series)
        except Exception as exc:
            typer.echo(f"ERROR: {exc}")
            raise typer.Exit(code=1) from exc
        bible_report = check_bible(_root(), series_id)
        try:
            profile_name = production.effective_profile_name(series.profile)
            typer.echo(_profile_header(production, profile_name))
        except ValueError as exc:
            typer.echo(f"ERROR: {exc}")
            raise typer.Exit(code=1) from exc
        if warning := production.costs_warning():
            typer.echo(f"WARNING: {warning}")
        bible_blocked = _print_bible_result(bible_report, integration=True)
        if bible_report.issues:
            Console().print(bible_table(bible_report))
        if bible_blocked:
            raise typer.Exit(code=1)
        typer.echo(f"OK: {series_id}")
        return
    try:
        bundle = loader.load_episode_bundle(series_id, episode_id)
        issues = validate_bundle(bundle)
        report = lint_bundle(bundle, production)
        bible_report = check_bible(_root(), series_id)
    except Exception as exc:
        typer.echo(f"ERROR: {exc}")
        raise typer.Exit(code=1) from exc
    typer.echo(_profile_header(production, report.profile_name))
    if warning := production.costs_warning():
        typer.echo(f"WARNING: {warning}")
    bible_blocked = _print_bible_result(bible_report, integration=True)
    if bible_report.issues:
        Console().print(bible_table(bible_report))
    for issue in issues:
        prefix = issue.level.upper()
        suffix = f" [{issue.shot_id}]" if issue.shot_id else ""
        typer.echo(f"{prefix}{suffix}: {issue.message}")
    Console().print(pacing_table(report))
    if bible_blocked or any(issue.level == "error" for issue in issues):
        raise typer.Exit(code=1)
    typer.echo(f"OK: {series_id}/{episode_id}")


@app.command()
def lint(series_id: str, episode_id: str) -> None:
    """Check spoken pacing, intentional silence, beats, and Portuguese mirrors."""
    loader = ProjectLoader(_root())
    production = load_production(_root())
    try:
        bundle = loader.load_episode_bundle(series_id, episode_id)
        report = lint_bundle(bundle, production)
    except Exception as exc:
        typer.echo(f"ERROR: {exc}")
        raise typer.Exit(code=1) from exc
    typer.echo(_profile_header(production, report.profile_name))
    for issue in report.issues:
        prefix = issue.level.upper()
        suffix = f" [{issue.shot_id}]" if issue.shot_id else ""
        typer.echo(f"{prefix}{suffix}: {issue.message}")
    Console().print(pacing_table(report))
    if any(issue.level == "error" for issue in report.issues):
        raise typer.Exit(code=1)
    typer.echo(f"OK: pacing {series_id}/{episode_id}")


@app.command()
def prompts(
    series_id: str,
    episode_id: str,
    shot: str | None = typer.Option(None, "--shot"),
    phase: str | None = typer.Option(None, "--phase"),
) -> None:
    """Generate copy-ready prompts for pending shots."""
    if phase not in {None, "images", "videos"}:
        raise typer.BadParameter("phase must be images or videos")
    loader = ProjectLoader(_root())
    try:
        bundle = loader.load_episode_bundle(series_id, episode_id)
        results = write_prompts(_root(), bundle, shot_filter=shot, phase=phase)
    except Exception as exc:
        typer.echo(f"ERROR: {exc}")
        raise typer.Exit(code=1) from exc
    if not results:
        typer.echo("No prompts generated.")
        return
    printed: set[Path] = set()
    shot_ids = {item.id for item in bundle.shots.shots}
    for result in results:
        scene_id = (
            result.shot.id[:-1]
            if result.shot.id.endswith("i") and result.shot.id[:-1] in shot_ids
            else result.shot.id
        )
        target = bundle.episode_dir / "prompts" / f"{scene_id}.md"
        if target not in printed:
            typer.echo(f"Generated {target}")
            printed.add(target)
        for issue in result.issues:
            if issue.level in {"warning", "error"}:
                typer.echo(f"{issue.level.upper()} [{result.shot.id}]: {issue.message}")


@app.command("plan")
def plan(series_id: str, episode_id: str) -> None:
    """Plan pending video credits and account allocation."""
    show_first_run_warning(_root())
    loader = ProjectLoader(_root())
    try:
        bundle = loader.load_episode_bundle(series_id, episode_id)
        production = load_production(_root())
        report = build_episode_plan(_root(), bundle)
    except Exception as exc:
        typer.echo(f"ERROR: {exc}")
        raise typer.Exit(code=1) from exc
    typer.echo(_profile_header(production, bundle.profile_name))
    if warning := production.costs_warning():
        typer.echo(f"WARNING: {warning}")
    Console().print(plan_table(report))
    for line in plan_summary(report):
        typer.echo(line)
    if report.worst_days > 1:
        typer.echo(
            "WARNING: a capacidade diária não comporta o pior caso; sugere-se dividir em dias."
        )


@app.command("plan-day")
def plan_day(episodes: int | None = typer.Option(None, "--episodes", min=1)) -> None:
    """Estimate episodes and videos per day for the active profile."""
    show_first_run_warning(_root())
    try:
        production = load_production(_root())
        report = build_day_plan(_root(), requested_episodes=episodes)
    except Exception as exc:
        typer.echo(f"ERROR: {exc}")
        raise typer.Exit(code=1) from exc
    typer.echo(_profile_header(production, report.profile_name))
    if warning := production.costs_warning():
        typer.echo(f"WARNING: {warning}")
    typer.echo(
        f"Tamanho médio do episódio: {report.average_episode_seconds:.1f}s; "
        f"clipe médio real: {report.average_clip_seconds:.1f}s; "
        f"{report.videos_per_episode} vídeos/episódio."
    )
    typer.echo(
        f"Esperado: {report.expected_episodes_per_day} episódios/dia; "
        f"{report.expected_videos_per_day} vídeos/dia; "
        f"{report.expected_episode_credits} créditos/episódio."
    )
    typer.echo(
        f"Pior caso: {report.worst_episodes_per_day} episódios/dia; "
        f"{report.worst_videos_per_day} vídeos/dia; "
        f"{report.worst_episode_credits} créditos/episódio."
    )
    if episodes is not None:
        typer.echo(
            f"{episodes} episódios solicitados cabem no dia? "
            f"esperado: {'sim' if report.requested_expected_fits else 'não'}; "
            f"pior caso: {'sim' if report.requested_worst_fits else 'não'}."
        )


@app.command("session")
def session(
    series_id: str,
    episode_id: str,
    account: str | None = typer.Option(None, "--account"),
) -> None:
    """Generate an offline production session sheet."""
    show_first_run_warning(_root())
    loader = ProjectLoader(_root())
    try:
        bundle = loader.load_episode_bundle(series_id, episode_id)
        target = write_session_sheet(_root(), bundle, account=account)
        production = load_production(_root())
    except Exception as exc:
        typer.echo(f"ERROR: {exc}")
        raise typer.Exit(code=1) from exc
    if warning := production.costs_warning():
        typer.echo(f"WARNING: {warning}")
    typer.echo(f"Session sheet written to {target}")


@app.command("pack")
def pack(series_id: str, episode_id: str) -> None:
    """Generate the three simple copy-ready production documents."""
    loader = ProjectLoader(_root())
    try:
        bundle = loader.load_episode_bundle(series_id, episode_id)
        data = build_pack(_root(), bundle)
        target = write_pack(_root(), bundle, data=data)
    except PackValidationError as exc:
        for issue in exc.issues:
            prefix = issue.level.upper()
            suffix = f" [{issue.shot_id}]" if issue.shot_id else ""
            typer.echo(f"{prefix}{suffix}: {issue.message}")
        typer.echo("ERROR: pacote não gerado; corrija os erros de validate e tente novamente.")
        raise typer.Exit(code=1) from exc
    except Exception as exc:
        typer.echo(f"ERROR: pack: {exc}")
        raise typer.Exit(code=1) from exc
    for issue in data.issues:
        if issue.level == "warning":
            suffix = f" [{issue.shot_id}]" if issue.shot_id else ""
            typer.echo(f"WARNING{suffix}: {issue.message}")
    typer.echo(f"Pacote gerado em {target}")


@app.command()
def board(series_id: str, episode_id: str) -> None:
    """Write and display the visual production board for an episode."""
    loader = ProjectLoader(_root())
    try:
        bundle = loader.load_episode_bundle(series_id, episode_id)
        target = write_board(bundle)
    except Exception as exc:
        typer.echo(f"ERROR: {exc}")
        raise typer.Exit(code=1) from exc
    typer.echo(f"Board written to {target}")
    typer.echo(target.read_text(encoding="utf-8"))


@app.command()
def next(series_id: str, episode_id: str) -> None:
    """Show the next safe production action and its prompt."""
    show_first_run_warning(_root())
    loader = ProjectLoader(_root())
    try:
        bundle = loader.load_episode_bundle(series_id, episode_id)
        row = next_row(bundle)
    except Exception as exc:
        typer.echo(f"ERROR: {exc}")
        raise typer.Exit(code=1) from exc
    production = load_production(_root())
    typer.echo(_profile_header(production, bundle.profile_name))
    if row is None:
        typer.echo("Episódio concluído: todos os planos estão aprovados.")
        return
    typer.echo(f"Próxima ação: {row.next_action}")
    typer.echo(f"Plano: {row.shot_id} · Etapa: {row.stage} · Prompt: {row.prompt_file}")
    if row.stage == "VIDEO":
        try:
            budget = build_episode_plan(_root(), bundle)
        except Exception as exc:
            typer.echo(f"ERROR: orçamento: {exc}")
            raise typer.Exit(code=1) from exc
        assignment = budget.assignment_for(row.shot_id)
        if assignment is None:
            typer.echo("WARNING: não há capacidade reservada para este vídeo.")
            return
        typer.echo(
            f"Orçamento reservado: {assignment.account_id}, dia {assignment.day} "
            "(pior caso)."
        )
    can_generate = (row.stage == "IMAGE" and "Gerar imagem" in row.next_action) or (
        row.stage == "VIDEO" and "gerar vídeo" in row.next_action
    )
    if not can_generate:
        return
    shot_ids = {item.id for item in bundle.shots.shots}
    scene_id = (
        row.shot_id[:-1]
        if row.shot_id.endswith("i") and row.shot_id[:-1] in shot_ids
        else row.shot_id
    )
    write_prompts(_root(), bundle, shot_filter=row.shot_id)
    prompt_path = bundle.episode_dir / "prompts" / f"{scene_id}.md"
    typer.echo("")
    typer.echo(prompt_path.read_text(encoding="utf-8"))


@app.command()
def credits() -> None:
    """Show configured media costs."""
    config = load_production(_root())
    typer.echo(f"Image: {config.image.credits} credits")
    for resolution, costs in sorted(config.video.costs.items()):
        for duration, cost in sorted(costs.items()):
            label = "desconhecido" if cost is None else f"{cost} créditos"
            typer.echo(f"Video {duration}s ({resolution}): {label}")


@profile_app.command("show")
def profile_show() -> None:
    """Show the active production profile and known costs."""
    config = load_production(_root())
    try:
        profile_name = config.effective_profile_name()
        profile = config.profile(profile_name)
    except ValueError as exc:
        typer.echo(f"ERROR: {exc}")
        raise typer.Exit(code=1) from exc
    typer.echo(_profile_header(config, profile_name))
    typer.echo(f"Objetivo: {profile.purpose_pt}")
    typer.echo(f"Cold open: {'sim' if profile.cold_open else 'não'}")
    typer.echo("Custos conhecidos:")
    for resolution, costs in sorted(config.video.costs.items()):
        values = ", ".join(
            f"{duration}s={cost if cost is not None else 'desconhecido'}"
            for duration, cost in sorted(costs.items())
        )
        typer.echo(f"  {resolution}: {values}")
    verified = (
        config.video.costs_verified_on.isoformat()
        if config.video.costs_verified_on
        else "nunca"
    )
    typer.echo(f"Custos conferidos em: {verified}")
    if warning := config.costs_warning():
        typer.echo(f"WARNING: {warning}")


@profile_app.command("set")
def profile_set(profile_name: str) -> None:
    """Set the active production profile."""
    config = load_production(_root())
    try:
        config.profile(profile_name)
        path = set_active_profile(_root(), profile_name)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    typer.echo(f"Perfil ativo definido: {profile_name} ({path})")
    if profile_name == "monetize":
        goals = load_goals(_root())
        typer.echo("Requisitos de qualificação:")
        if goals is None:
            typer.echo("  config/goals.yaml ainda não existe.")
        else:
            typer.echo(yaml.safe_dump(goals, allow_unicode=True, sort_keys=False).rstrip())


if __name__ == "__main__":
    app()
