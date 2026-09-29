from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from .config import load_production
from .loader import LoadedEpisode
from .models import Character, DialogueLine, Shot, ValidationIssue
from .pacing import lint_bundle


@dataclass(frozen=True)
class PromptResult:
    shot: Shot
    prompt: str
    prompt_pt: str
    markdown: str
    reference: str
    cost: int | None
    issues: list[ValidationIssue]


def _template_environment(root: Path) -> Environment:
    return Environment(
        loader=FileSystemLoader(root / "templates" / "prompts"),
        undefined=StrictUndefined,
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )


def _character_map(bundle: LoadedEpisode) -> dict[str, Character]:
    return {character.id: character for character in bundle.characters.characters}


def _shot_map(bundle: LoadedEpisode) -> dict[str, Shot]:
    return {shot.id: shot for shot in bundle.shots.shots}


def _reference_for(bundle: LoadedEpisode, shot: Shot, shots: dict[str, Shot]) -> str:
    parent_id = shot.parent or shot.reference_from
    if not parent_id:
        return "none"
    parent = shots.get(parent_id)
    if not parent:
        return "missing"
    return parent.files.image or (
        f"assets/images/{bundle.episode.id.upper()}_{parent_id}_image.jpg"
    )


def _output_for(bundle: LoadedEpisode, shot: Shot) -> str:
    if shot.kind in {"anchor_image", "derived_image"}:
        return shot.files.image or f"assets/images/{bundle.episode.id.upper()}_{shot.id}_image.jpg"
    return shot.files.video or f"assets/videos/{bundle.episode.id.upper()}_{shot.id}_video.mp4"


def _expected_result(bundle: LoadedEpisode, shot: Shot) -> str:
    if shot.expected_result_pt:
        return shot.expected_result_pt
    action = shot.action or shot.action_en or "a ação descrita no plano"
    if shot.kind in {"anchor_image", "derived_image"}:
        return f"Uma imagem {shot.framing} mostrando {action}."
    camera = f" A câmera faz {shot.camera}." if shot.camera else ""
    dialogue = ""
    if shot.dialogue_pt:
        lines = "; ".join(f'{line.speaker}: "{line.text}"' for line in shot.dialogue_pt)
        dialogue = f" Falas: {lines}."
    return f"Um vídeo de {shot.duration_s} segundos mostrando {action}.{camera}{dialogue}"


def _dialogue_context(
    dialogue: list[DialogueLine], characters: dict[str, Character]
) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for line in dialogue:
        character = characters.get(line.speaker)
        result.append(
            {
                "speaker_name": character.name if character else line.speaker,
                "delivery": (
                    line.delivery
                    or (character.default_delivery if character else None)
                    or ""
                ),
                "delivery_pt": (
                    line.delivery_pt
                    or (character.default_delivery_pt if character else None)
                    or ""
                ),
                "text": line.text,
            }
        )
    return result


def _voice_over_context(
    voice_over: list[DialogueLine], characters: dict[str, Character]
) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for line in voice_over:
        character = characters.get(line.speaker)
        result.append(
            {
                "speaker_name": character.name if character else line.speaker,
                "delivery": (
                    line.delivery
                    or (character.default_delivery if character else None)
                    or ""
                ),
                "delivery_pt": (
                    line.delivery_pt
                    or (character.default_delivery_pt if character else None)
                    or ""
                ),
                "text": line.text,
            }
        )
    return result


def _pt_value(value: str, field: str) -> str:
    return value.strip() or f"[falta tradução: campo {field}]"


def _direction_context(shot: Shot) -> dict[str, object]:
    english_timeline = [
        {
            "at_s": beat.at_s,
            "action": beat.action or f"[missing direction: timeline[{index}].action]",
        }
        for index, beat in enumerate(shot.timeline)
    ]
    portuguese_timeline = [
        {
            "at_s": beat.at_s,
            "action_pt": _pt_value(beat.action_pt, f"timeline[{index}].action_pt"),
        }
        for index, beat in enumerate(shot.timeline_pt)
    ]
    return {
        "setup": shot.setup or "[missing direction: setup]",
        "setup_pt": _pt_value(shot.setup_pt, "setup"),
        "start_state": shot.start_state or "[missing direction: start_state]",
        "start_state_pt": _pt_value(shot.start_state_pt, "start_state"),
        "timeline": english_timeline,
        "timeline_pt": portuguese_timeline,
        "end_state": shot.end_state or "[missing direction: end_state]",
        "end_state_pt": _pt_value(shot.end_state_pt, "end_state"),
        "sound": shot.sound or "[missing direction: sound]",
        "sound_pt": _pt_value(shot.sound_pt, "sound"),
        "must_not": shot.must_not or "[missing direction: must_not]",
        "must_not_pt": _pt_value(shot.must_not_pt, "must_not"),
    }


def validate_shot(bundle: LoadedEpisode, shot: Shot) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    characters = _character_map(bundle)
    locations = {location.id: location for location in bundle.locations.locations}
    shots = _shot_map(bundle)

    for character_id in shot.characters:
        if character_id not in characters:
            issues.append(
                ValidationIssue(
                    level="error", message=f"Unknown character: {character_id}", shot_id=shot.id
                )
            )
    if shot.location not in locations:
        issues.append(
            ValidationIssue(
                level="error", message=f"Unknown location: {shot.location}", shot_id=shot.id
            )
        )

    if shot.kind != "anchor_image" and not shot.parent:
        issues.append(
            ValidationIssue(
                level="error", message="parent is required for this shot kind", shot_id=shot.id
            )
        )
    if shot.parent:
        parent = shots.get(shot.parent)
        if not parent:
            issues.append(
                ValidationIssue(
                    level="error", message=f"Unknown parent: {shot.parent}", shot_id=shot.id
                )
            )
        elif shot.kind in {"derived_image", "video_from_image", "video_expression_only"}:
            if parent.status != "approved" or not parent.files.image:
                issues.append(
                    ValidationIssue(
                        level="error",
                        message=f"Parent {shot.parent} has no approved image",
                        shot_id=shot.id,
                    )
                )

    if shot.reference_from:
        reference = shots.get(shot.reference_from)
        if not reference or reference.status != "approved" or not reference.files.image:
            issues.append(
                ValidationIssue(
                    level="error",
                    message=f"Reference {shot.reference_from} has no approved image",
                    shot_id=shot.id,
                )
            )

    present = [characters[item] for item in shot.characters if item in characters]
    for character in present:
        if not character.lock_block.strip() or "\n" in character.lock_block:
            issues.append(
                ValidationIssue(
                    level="error", message=f"Invalid lock_block: {character.id}", shot_id=shot.id
                )
            )
        if (
            character.signature_element
            and character.signature_element.lower() not in character.lock_block.lower()
        ):
            issues.append(
                ValidationIssue(
                    level="warning",
                    message=f"signature_element is absent from lock_block: {character.id}",
                    shot_id=shot.id,
                )
            )

    for line in [*shot.dialogue_pt, *shot.voice_over_pt]:
        if line.speaker not in characters:
            issues.append(
                ValidationIssue(
                    level="error", message=f"Unknown speaker: {line.speaker}", shot_id=shot.id
                )
            )
        for character in characters.values():
            for nickname in character.nicknames:
                if (
                    nickname.name.lower() in line.text.lower()
                    and line.speaker not in nickname.used_by
                ):
                    issues.append(
                        ValidationIssue(
                            level="warning",
                            message=f"Nickname {nickname.name} is not used by {line.speaker}",
                            shot_id=shot.id,
                        )
                    )

    conjunctions = re.findall(r"\b(?:and|then)\b", shot.action.lower())
    if len(conjunctions) > 2:
        issues.append(
            ValidationIssue(
                level="warning",
                message="Action may contain more than one main action",
                shot_id=shot.id,
            )
        )
    if not shot.gaze and "close" in shot.framing.lower() and shot.role in {"hook", "cliffhanger"}:
        issues.append(
            ValidationIssue(
                level="warning", message="Consider filling gaze for this close-up", shot_id=shot.id
            )
        )

    if shot.video_attempts > load_production(bundle.series_dir.parent.parent).video.max_attempts:
        issues.append(
            ValidationIssue(
                level="warning",
                message="video_attempts exceeds max_video_attempts",
                shot_id=shot.id,
            )
        )
    return issues


def validate_bundle(bundle: LoadedEpisode) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if bundle.style.id != bundle.series.style:
        issues.append(
            ValidationIssue(level="error", message="Style id does not match series.style")
        )
    if bundle.episode.cold_open.enabled and not bundle.episode.cold_open.source_shot:
        issues.append(ValidationIssue(level="error", message="Enabled cold open needs source_shot"))
    for shot in bundle.shots.shots:
        issues.extend(validate_shot(bundle, shot))
    root = bundle.series_dir.parent.parent
    issues.extend(lint_bundle(bundle, load_production(root)).issues)
    return issues


def render_prompt(
    root: Path,
    bundle: LoadedEpisode,
    shot: Shot,
    *,
    allow_unknown_cost: bool = False,
) -> PromptResult:
    issues = validate_shot(bundle, shot)
    characters = _character_map(bundle)
    locations = {location.id: location for location in bundle.locations.locations}
    shots = _shot_map(bundle)
    location = locations.get(shot.location)
    if location is None:
        raise ValueError(f"Unknown location: {shot.location}")
    reference = _reference_for(bundle, shot, shots)
    production = load_production(root)
    profile_name = bundle.profile_name or production.effective_profile_name(
        bundle.series.profile, bundle.episode.profile
    )
    profile = production.profile(profile_name)
    try:
        cost = production.shot_credits(shot, resolution=profile.resolution)
    except ValueError:
        if not allow_unknown_cost:
            raise
        cost = None
    environment = _template_environment(root)
    selected = [characters[item] for item in shot.characters if item in characters]
    light = shot.light or location.default_light
    context = {
        "framing": shot.framing,
        "action": shot.action,
        "action_en": shot.action_en or shot.action,
        "expression": shot.expression,
        "camera": shot.camera or bundle.style.camera_defaults,
        "gaze": shot.gaze,
        "light": light,
        "mood": shot.mood,
        "duration_s": shot.duration_s,
        "location": location,
        "characters": selected,
        "style": bundle.style,
        "dialogue": _dialogue_context(shot.dialogue_pt, characters),
        "voice_over": _voice_over_context(shot.voice_over_pt, characters),
        "reference_names": (
            ", ".join(character.name for character in selected) if shot.reference_from else ""
        ),
        "completely_different_room": False,
        "old_location": "",
        "framing_pt": _pt_value(shot.framing_pt, "framing"),
        "action_pt": _pt_value(shot.action_pt, "action"),
        "camera_pt": (
            _pt_value(shot.camera_pt, "camera")
            if shot.camera
            else _pt_value(bundle.style.camera_defaults_pt, "camera_defaults")
        ),
        "gaze_pt": _pt_value(shot.gaze_pt, "gaze") if shot.gaze else "",
        "mood_pt": _pt_value(shot.mood_pt, "mood") if shot.mood else "",
        "expression_pt": (
            _pt_value(shot.expression_pt, "expression") if shot.expression else ""
        ),
        "light_pt": (
            _pt_value(shot.light_pt, "light")
            if shot.light
            else _pt_value(location.default_light_pt, "default_light")
        ),
        "characters_pt": [
            {
                "name": character.name,
                "lock_block_pt": _pt_value(character.lock_block_pt, "lock_block"),
            }
            for character in selected
        ],
        "location_pt": {
            "description": _pt_value(location.description_pt, "description"),
            "default_light": _pt_value(location.default_light_pt, "default_light"),
        },
        "style_pt": {
            "style_block": _pt_value(bundle.style.style_block_pt, "style_block"),
            "negative_hints": _pt_value(bundle.style.negative_hints_pt, "negative_hints"),
            "camera_defaults": _pt_value(bundle.style.camera_defaults_pt, "camera_defaults"),
            "video_motion_defaults": _pt_value(
                bundle.style.video_motion_defaults_pt, "video_motion_defaults"
            ),
            "character_rules": _pt_value(bundle.style.character_rules_pt, "character_rules"),
        },
    }
    context.update(_direction_context(shot))
    if shot.kind == "anchor_image":
        template = environment.get_template("image_anchor.j2")
    elif shot.kind == "derived_image":
        template = environment.get_template("image_derivative.j2")
    elif shot.kind == "video_expression_only" or shot.intentional_silence:
        template = environment.get_template("video_expression_only.j2")
    else:
        template = environment.get_template("video_from_image.j2")
    prompt = " ".join(template.render(**context).split())
    if shot.kind == "anchor_image":
        pt_template_name = "image_anchor_pt.j2"
    elif shot.kind == "derived_image":
        pt_template_name = "image_derivative_pt.j2"
    elif shot.kind == "video_expression_only" or shot.intentional_silence:
        pt_template_name = "video_expression_only_pt.j2"
    else:
        pt_template_name = "video_from_image_pt.j2"
    prompt_pt = " ".join(environment.get_template(pt_template_name).render(**context).split())
    if len(prompt) > 1200:
        issues.append(
            ValidationIssue(
                level="warning", message="Prompt is longer than 1,200 characters", shot_id=shot.id
            )
        )
    output = _output_for(bundle, shot)
    expected_result = _expected_result(bundle, shot)
    parent_id = shot.parent or shot.reference_from
    if shot.kind in {"anchor_image", "derived_image"}:
        title = "## IMAGEM:"
        action = f"Criar a imagem nova do plano {shot.id}"
        reference_text = (
            f"Anexar a imagem de referência do plano {parent_id}: {reference}"
            if parent_id
            else "Anexar: nenhuma imagem; esta é uma imagem âncora nova"
        )
    else:
        title = "## VIDEO:"
        action = f"Criar o vídeo do plano {shot.id} usando a imagem aprovada {parent_id}"
        reference_text = f"Anexar a imagem aprovada do plano {parent_id}: {reference}"
    blocked = ""
    if any(issue.level == "error" for issue in issues):
        blocked = "Status: BLOQUEADO — resolva a etapa anterior antes de executar esta etapa.\n\n"
    header = (
        f"{title}\n"
        f"Ação: {action}.\n"
        f"{reference_text}.\n"
        f"Resultado esperado: {expected_result}\n"
        f"Salvar o resultado em: `{output}`.\n"
        f"Conta sugerida: {shot.account or 'não atribuída'} · Custo: {cost} créditos.\n\n"
        f"{blocked}"
        f"### Prompt para copiar no Google Flow\n\n"
        f"```text\n{prompt}\n```\n\n"
        "### Leitura em português (NÃO copiar para o Flow)\n\n"
        f"> {prompt_pt}\n"
    )
    return PromptResult(
        shot=shot,
        prompt=prompt,
        prompt_pt=prompt_pt,
        markdown=header,
        reference=reference,
        cost=cost,
        issues=issues,
    )


def _scene_key(shot_id: str, shots: dict[str, Shot]) -> str:
    if shot_id.endswith("i") and shot_id[:-1] in shots:
        return shot_id[:-1]
    return shot_id


def _scene_document_path(bundle: LoadedEpisode, scene_id: str) -> Path:
    return bundle.episode_dir / "prompts" / f"{scene_id}.md"


def write_prompts(
    root: Path,
    bundle: LoadedEpisode,
    shot_filter: str | None = None,
    phase: str | None = None,
) -> list[PromptResult]:
    shots = {shot.id: shot for shot in bundle.shots.shots}
    grouped: dict[str, list[Shot]] = {}
    for shot in sorted(bundle.shots.shots, key=lambda item: item.order):
        grouped.setdefault(_scene_key(shot.id, shots), []).append(shot)

    results: list[PromptResult] = []
    for scene_id, scene_shots in grouped.items():
        if shot_filter and shot_filter not in {shot.id for shot in scene_shots}:
            continue
        if phase == "images" and not any(
            shot.kind in {"anchor_image", "derived_image"} for shot in scene_shots
        ):
            continue
        if phase == "videos" and not any(
            shot.kind in {"video_from_image", "video_expression_only"} for shot in scene_shots
        ):
            continue
        scene_results = [render_prompt(root, bundle, shot) for shot in scene_shots]
        document = (
            f"# {bundle.episode.id.upper()} · {scene_id} — CENA COMPLETA\n\n"
            "Ordem de trabalho: gerar/aprovar a imagem primeiro; depois anexá-la para gerar "
            "o vídeo.\n\n"
        )
        document += "\n".join(result.markdown for result in scene_results)
        target = _scene_document_path(bundle, scene_id)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(document, encoding="utf-8")
        results.extend(scene_results)
    return results
