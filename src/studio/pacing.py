from __future__ import annotations

import re
from dataclasses import dataclass

from rich.table import Table

from .loader import LoadedEpisode
from .models import Character, ProductionConfig, Shot, ValidationIssue

VIDEO_KINDS = {"video_from_image", "video_expression_only"}
WORD_RE = re.compile(r"\b[\w]+(?:['’\-][\w]+)*\b", re.UNICODE)


@dataclass(frozen=True)
class PacingRow:
    shot_id: str
    kind: str
    words: int
    speech_seconds: float
    fill_percent: float
    empty_seconds: float


@dataclass(frozen=True)
class PacingReport:
    rows: list[PacingRow]
    issues: list[ValidationIssue]
    estimated_runtime_s: float = 0.0
    target_seconds: float = 0.0
    profile_name: str = ""
    profile_resolution: str = ""


def count_words(text: str) -> int:
    return len(WORD_RE.findall(text))


def shot_words(shot: Shot) -> int:
    lines = [*shot.dialogue_pt, *shot.voice_over_pt]
    return sum(count_words(line.text) for line in lines)


def _issue(level: str, message: str, shot_id: str | None = None) -> ValidationIssue:
    return ValidationIssue(level=level, message=message, shot_id=shot_id)


def _forbidden_delivery_issue(
    delivery: str | None,
    field: str,
    markers: list[str],
    shot_id: str | None = None,
) -> ValidationIssue | None:
    if not delivery:
        return None
    for marker in markers:
        if marker and marker.casefold() in delivery.casefold():
            return _issue(
                "error",
                f"{field} contém marcador de tom duplo proibido: {marker!r}",
                shot_id,
            )
    return None


def _delivery_issues_for_lines(shot: Shot, markers: list[str]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for line in [*shot.dialogue_pt, *shot.voice_over_pt]:
        has_delivery = bool(line.delivery and line.delivery.strip())
        has_delivery_pt = bool(line.delivery_pt and line.delivery_pt.strip())
        if has_delivery != has_delivery_pt:
            issues.append(
                _issue(
                    "warning",
                    f"Fala de {line.speaker} precisa de delivery e delivery_pt juntos",
                    shot.id,
                )
            )
        forbidden = _forbidden_delivery_issue(
            line.delivery, f"delivery de {line.speaker}", markers, shot.id
        )
        if forbidden:
            issues.append(forbidden)
    return issues


def _character_delivery_issues(
    characters: dict[str, Character], markers: list[str]
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for character in characters.values():
        default_delivery = character.default_delivery
        default_delivery_pt = character.default_delivery_pt
        if bool(default_delivery and default_delivery.strip()) != bool(
            default_delivery_pt and default_delivery_pt.strip()
        ):
            issues.append(
                _issue(
                    "warning",
                    f"Personagem {character.id} precisa de default_delivery e "
                    "default_delivery_pt juntos",
                )
            )
        forbidden = _forbidden_delivery_issue(
            default_delivery,
            f"default_delivery de {character.id}",
            markers,
        )
        if forbidden:
            issues.append(forbidden)
    return issues


def _character_style_issues(bundle: LoadedEpisode) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    requires_silhouette = re.search(
        r"\b(?:silhouette|silhueta)\b", bundle.style.character_rules, re.IGNORECASE
    )
    for character in bundle.characters.characters:
        if requires_silhouette and not character.silhouette_hook:
            issues.append(
                _issue(
                    "warning",
                    f"Personagem {character.id} não tem silhouette_hook apesar das "
                    "regras do estilo",
                )
            )
        if character.silhouette_hook and (
            character.silhouette_hook.casefold() not in character.lock_block.casefold()
        ):
            issues.append(
                _issue(
                    "warning",
                    f"silhouette_hook não aparece no lock_block de {character.id}",
                )
            )
    return issues


def _character_visual_issues(bundle: LoadedEpisode, shot: Shot) -> list[ValidationIssue]:
    present = [
        character
        for character_id in shot.characters
        for character in bundle.characters.characters
        if character.id == character_id
    ]
    issues: list[ValidationIssue] = []
    hooks = [
        character.silhouette_hook.casefold()
        for character in present
        if character.silhouette_hook
    ]
    if len(hooks) != len(set(hooks)):
        issues.append(
            _issue(
                "warning",
                "Dois personagens no plano têm o mesmo silhouette_hook",
                shot.id,
            )
        )
    hair_colors = [character.hair_color.casefold() for character in present if character.hair_color]
    if len(hair_colors) != len(set(hair_colors)):
        issues.append(
            _issue("warning", "Dois personagens no plano têm a mesma hair_color", shot.id)
        )
    return issues


def _voice_issues(bundle: LoadedEpisode, shot: Shot) -> list[ValidationIssue]:
    characters = {character.id: character for character in bundle.characters.characters}
    speaking_ids = {line.speaker for line in [*shot.dialogue_pt, *shot.voice_over_pt]}
    issues: list[ValidationIssue] = []
    profiles: dict[str, str] = {}
    for character_id in speaking_ids:
        character = characters.get(character_id)
        if not character:
            continue
        if not character.voice_profile:
            issues.append(
                _issue(
                    "warning",
                    f"Personagem falante {character.id} não tem voice_profile",
                    shot.id,
                )
            )
        if character.voice_profile and not character.voice_profile_pt:
            issues.append(
                _issue(
                    "warning",
                    f"Missing Portuguese mirror: voice_profile_pt de {character.id}",
                    shot.id,
                )
            )
        if character.voice_profile_pt and not character.voice_profile:
            issues.append(
                _issue(
                    "warning",
                    f"Missing English mirror: voice_profile de {character.id}",
                    shot.id,
                )
            )
        if character.voice_profile:
            folded = character.voice_profile.casefold().strip()
            if folded in profiles:
                issues.append(
                    _issue(
                        "warning",
                        f"Perfis de voz duplicados no plano: {profiles[folded]} e {character_id}",
                        shot.id,
                    )
                )
            else:
                profiles[folded] = character_id
    return issues


def _safety_issues(bundle: LoadedEpisode, blocked_terms: list[str]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    def scan(text: str, location: str, shot_id: str | None = None) -> None:
        folded = text.casefold()
        for term in blocked_terms:
            if term and term.casefold() in folded:
                issues.append(
                    _issue(
                        "error",
                        f"Termo bloqueado '{term}' encontrado em {location}; revise o conteúdo.",
                        shot_id,
                    )
                )

    for character in bundle.characters.characters:
        scan(character.lock_block, f"lock_block de {character.id}")
    scan(bundle.style.style_block, "style_block do estilo")
    for shot in bundle.shots.shots:
        scan(shot.action, "action", shot.id)
        if shot.action_en and shot.action_en != shot.action:
            scan(shot.action_en, "action_en", shot.id)
    return issues


def _missing_pt_issues(bundle: LoadedEpisode, shot: Shot) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    def check(english: str, portuguese: str, field: str) -> None:
        if not english or portuguese.strip():
            return
        issues.append(_issue("warning", f"Missing Portuguese mirror: {field}_pt", shot.id))

    check(shot.framing, shot.framing_pt, "framing")
    if shot.action or shot.action_en:
        check(shot.action or shot.action_en, shot.action_pt, "action")
    if shot.camera:
        check(shot.camera, shot.camera_pt, "camera")
    if shot.gaze:
        check(shot.gaze, shot.gaze_pt, "gaze")
    if shot.mood:
        check(shot.mood, shot.mood_pt, "mood")
    if shot.expression:
        check(shot.expression, shot.expression_pt, "expression")
    if shot.light:
        check(shot.light, shot.light_pt, "light")

    location = next((item for item in bundle.locations.locations if item.id == shot.location), None)
    if location:
        if location.description_en:
            check(location.description_en, location.description_pt, "description")
        if location.default_light:
            check(location.default_light, location.default_light_pt, "default_light")
    characters = {item.id: item for item in bundle.characters.characters}
    for character_id in shot.characters:
        character = characters.get(character_id)
        if character and character.lock_block:
            check(character.lock_block, character.lock_block_pt, "lock_block")

    style = bundle.style
    for english, portuguese, field in (
        (style.style_block, style.style_block_pt, "style_block"),
        (style.negative_hints, style.negative_hints_pt, "negative_hints"),
        (style.camera_defaults, style.camera_defaults_pt, "camera_defaults"),
        (style.video_motion_defaults, style.video_motion_defaults_pt, "video_motion_defaults"),
        (style.character_rules, style.character_rules_pt, "character_rules"),
        (style.audio_style, style.audio_style_pt, "audio_style"),
    ):
        check(english, portuguese, field)
    return issues


def _direction_issues(shot: Shot) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for english, portuguese, field in (
        (shot.setup, shot.setup_pt, "setup"),
        (shot.start_state, shot.start_state_pt, "start_state"),
        (shot.end_state, shot.end_state_pt, "end_state"),
        (shot.sound, shot.sound_pt, "sound"),
        (shot.must_not, shot.must_not_pt, "must_not"),
    ):
        if english and not portuguese:
            issues.append(_issue("warning", f"Missing Portuguese mirror: {field}_pt", shot.id))
        if portuguese and not english:
            issues.append(_issue("warning", f"Missing English direction field: {field}", shot.id))

    if shot.timeline and not shot.timeline_pt:
        issues.append(_issue("warning", "Missing Portuguese mirror: timeline_pt", shot.id))
    if shot.timeline_pt and not shot.timeline:
        issues.append(_issue("warning", "Missing English direction field: timeline", shot.id))
    if len(shot.timeline) != len(shot.timeline_pt) and shot.timeline and shot.timeline_pt:
        issues.append(_issue("warning", "timeline and timeline_pt have different lengths", shot.id))
    for index, beat in enumerate(shot.timeline):
        if beat.action and not beat.action_pt:
            issues.append(
                _issue(
                    "warning",
                    f"Missing Portuguese mirror: timeline[{index}].action_pt",
                    shot.id,
                )
            )
    return issues


def _timeline_start(at_s: str) -> float | None:
    match = re.match(r"\s*(\d+(?:[.,]\d+)?)", at_s)
    if not match:
        return None
    return float(match.group(1).replace(",", "."))


def _hook_issues(
    bundle: LoadedEpisode, ordered: list[Shot], severity: str
) -> list[ValidationIssue]:
    videos = [shot for shot in ordered if shot.kind in VIDEO_KINDS]
    if not videos:
        return [_issue(severity, "Episódio precisa de um clipe de gancho")]

    candidate = videos[0]
    if bundle.episode.cold_open.enabled and bundle.episode.cold_open.source_shot:
        source = next(
            (shot for shot in ordered if shot.id == bundle.episode.cold_open.source_shot),
            None,
        )
        if source and source.kind in VIDEO_KINDS:
            candidate = source

    issues: list[ValidationIssue] = []
    if candidate.role != "hook":
        issues.append(
            _issue(
                severity,
                f"Primeiro clipe {candidate.id} precisa ter role: hook",
                candidate.id,
            )
        )
    lines = [*candidate.dialogue_pt, *candidate.voice_over_pt]
    if not lines:
        issues.append(
            _issue(
                severity,
                f"Gancho {candidate.id} precisa começar com fala ou voice-over",
                candidate.id,
            )
        )
    first_timeline = candidate.timeline[0] if candidate.timeline else None
    start_s = _timeline_start(first_timeline.at_s) if first_timeline else None
    if start_s is None or start_s >= 2:
        issues.append(
            _issue(
                severity,
                f"A fala do gancho {candidate.id} precisa começar antes de 2 segundos",
                candidate.id,
            )
        )
    return issues


def lint_bundle(bundle: LoadedEpisode, production: ProductionConfig) -> PacingReport:
    config = production.pacing
    rows: list[PacingRow] = []
    issues: list[ValidationIssue] = []
    ordered = sorted(bundle.shots.shots, key=lambda item: item.order)
    previous_beat = ""
    intentional_count = 0
    characters = {item.id: item for item in bundle.characters.characters}
    issues.extend(_character_delivery_issues(characters, config.delivery_forbidden_markers))
    issues.extend(_character_style_issues(bundle))
    issues.extend(_safety_issues(bundle, production.safety.blocked_terms))
    profile_name = bundle.episode.profile or bundle.series.profile or production.active_profile
    profile = production.profiles.get(profile_name)
    if production.profiles and profile is None:
        issues.append(
            _issue(
                "error",
                f"Perfil '{profile_name}' não está configurado em config/production.yaml",
            )
        )

    for shot in ordered:
        issues.extend(_character_visual_issues(bundle, shot))
        words = shot_words(shot)
        is_video = shot.kind in VIDEO_KINDS
        duration = float(shot.duration_s) if is_video else 0.0
        speech_seconds = words / config.words_per_second if config.words_per_second else 0.0
        empty_seconds = max(duration - speech_seconds, 0.0)
        fill_percent = (speech_seconds / duration * 100) if duration else 0.0
        rows.append(
            PacingRow(
                shot_id=shot.id,
                kind=shot.kind,
                words=words,
                speech_seconds=speech_seconds,
                fill_percent=fill_percent,
                empty_seconds=empty_seconds,
            )
        )

        if not shot.beat_pt.strip():
            issues.append(_issue("warning", "beat_pt is empty", shot.id))
        elif previous_beat and shot.beat_pt.strip() == previous_beat:
            issues.append(_issue("warning", "Consecutive shots repeat the same beat_pt", shot.id))
        previous_beat = shot.beat_pt.strip()

        issues.extend(_missing_pt_issues(bundle, shot))
        issues.extend(_voice_issues(bundle, shot))
        if not is_video:
            continue

        issues.extend(_direction_issues(shot))
        lines = [*shot.dialogue_pt, *shot.voice_over_pt]
        issues.extend(_delivery_issues_for_lines(shot, config.delivery_forbidden_markers))
        if profile and shot.resolution and shot.resolution != profile.resolution:
            issues.append(
                _issue(
                    "warning",
                    f"Resolução do plano ({shot.resolution}) difere do perfil "
                    f"{profile_name} ({profile.resolution})",
                    shot.id,
                )
            )
        if not lines and not shot.intentional_silence:
            issues.append(
                _issue(
                    "error",
                    "Video shot needs dialogue_pt, voice_over_pt, or intentional_silence",
                    shot.id,
                )
            )
        if speech_seconds > duration:
            issues.append(
                _issue(
                    "error",
                    f"Estimated speech ({speech_seconds:.1f}s) exceeds duration ({duration:.1f}s)",
                    shot.id,
                )
            )
        if not shot.intentional_silence and speech_seconds < config.min_speech_fill * duration:
            issues.append(
                _issue(
                    config.enforcement.low_fill,
                    f"Fala estimada preenche {speech_seconds:.1f}s; faltam "
                    f"{empty_seconds:.1f}s para preencher o clipe",
                    shot.id,
                )
            )
        if empty_seconds > config.max_silence_s and not shot.intentional_silence:
            issues.append(
                _issue(
                    config.enforcement.excess_silence,
                    f"Silêncio estimado de {empty_seconds:.1f}s excede o máximo "
                    f"configurado de {config.max_silence_s:.1f}s; faltam "
                    f"{empty_seconds:.1f}s para preencher o clipe",
                    shot.id,
                )
            )
        if len(lines) > config.max_dialogue_lines:
            issues.append(
                _issue(
                    "warning",
                    f"{len(lines)} spoken lines exceed max_dialogue_lines "
                    f"({config.max_dialogue_lines})",
                    shot.id,
                )
            )
        for line in lines:
            words_in_line = count_words(line.text)
            if words_in_line > config.max_words_per_line:
                issues.append(
                    _issue(
                        "warning",
                        f"Line by {line.speaker} has {words_in_line} words; maximum is "
                        f"{config.max_words_per_line}",
                        shot.id,
                    )
                )
        if shot.intentional_silence:
            intentional_count += 1

    if intentional_count > config.max_intentional_silences_per_episode:
        issues.append(
            _issue(
                "warning",
                f"Episode has {intentional_count} intentional silences; maximum is "
                f"{config.max_intentional_silences_per_episode}",
            )
        )

    if not bundle.episode.season_finale and not bundle.episode.cliffhanger.strip():
        issues.append(_issue("error", "Episódio precisa ter cliffhanger preenchido"))
    issues.extend(_hook_issues(bundle, ordered, config.enforcement.missing_hook))

    estimated_runtime_s = sum(
        float(shot.duration_s)
        for shot in ordered
        if shot.kind in VIDEO_KINDS and shot.status != "rejected"
    )
    if bundle.episode.cold_open.enabled:
        estimated_runtime_s += max(
            bundle.episode.cold_open.trim_end_s - bundle.episode.cold_open.trim_start_s,
            0.0,
        )
    target_seconds = float(bundle.episode.target_seconds)
    if target_seconds and abs(estimated_runtime_s - target_seconds) / target_seconds > 0.10:
        difference = abs(estimated_runtime_s - target_seconds) / target_seconds * 100
        issues.append(
            _issue(
                "warning",
                f"Runtime estimado de {estimated_runtime_s:.1f}s difere "
                f"{difference:.1f}% da meta de {target_seconds:.1f}s",
            )
        )
    if profile:
        minimum = profile.episode_seconds.min
        maximum = profile.episode_seconds.max
        if not minimum <= estimated_runtime_s <= maximum:
            issues.append(
                _issue(
                    config.enforcement.profile_duration,
                    f"Runtime estimado de {estimated_runtime_s:.1f}s fora da faixa do perfil "
                    f"{profile_name}: {minimum}-{maximum}s",
                )
            )
    return PacingReport(
        rows=rows,
        issues=issues,
        estimated_runtime_s=estimated_runtime_s,
        target_seconds=target_seconds,
        profile_name=profile_name,
        profile_resolution=profile.resolution if profile else "",
    )


def pacing_table(report: PacingReport) -> Table:
    table = Table(
        title=(
            f"Pacing lint · Perfil: {report.profile_name or 'não configurado'} "
            f"({report.profile_resolution or 'resolução desconhecida'}) · "
            f"Runtime estimado: {report.estimated_runtime_s:.1f}s "
            f"/ meta: {report.target_seconds:.1f}s"
        )
    )
    table.add_column("Plano")
    table.add_column("Tipo")
    table.add_column("Palavras", justify="right")
    table.add_column("Fala (s)", justify="right")
    table.add_column("Preenchimento", justify="right")
    table.add_column("Vazio (s)", justify="right")
    for row in report.rows:
        table.add_row(
            row.shot_id,
            row.kind,
            str(row.words),
            f"{row.speech_seconds:.1f}",
            f"{row.fill_percent:.0f}%",
            f"{row.empty_seconds:.1f}",
        )
    table.add_row(
        "TOTAL",
        "runtime",
        "",
        "",
        "",
        f"{report.estimated_runtime_s:.1f}s / meta {report.target_seconds:.1f}s",
    )
    return table
