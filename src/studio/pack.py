from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from .bible import check_bible, has_bible_errors
from .config import load_production
from .loader import LoadedEpisode
from .models import Shot, ValidationIssue
from .pacing import VIDEO_KINDS, lint_bundle
from .prompts import PromptResult, render_prompt, validate_bundle

IMAGE_KINDS = {"anchor_image", "derived_image"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm"}


class PackValidationError(ValueError):
    """Raised when an episode cannot produce a safe copy-ready package."""

    def __init__(self, issues: list[ValidationIssue]):
        self.issues = issues
        super().__init__("O episódio tem erros bloqueantes; corrija validate antes do pack.")


@dataclass(frozen=True)
class PackImage:
    number: int
    shot: Shot
    filename: str
    approved: bool
    attachment: str
    prompt: str

    @property
    def status(self) -> str:
        return "✅ aprovada" if self.approved else "⬜ pendente"


@dataclass(frozen=True)
class PackVideo:
    number: int
    shot: Shot
    filename: str
    approved: bool
    attachment: str
    pending_warning: str
    prompt: str

    @property
    def status(self) -> str:
        return "✅ aprovado" if self.approved else "⬜ pendente"


@dataclass(frozen=True)
class PackData:
    series_title: str
    series_id: str
    episode_id: str
    episode_title: str
    profile_name: str
    resolution: str
    estimated_runtime_s: float
    target_seconds: int
    cold_open: object
    scenes: list[dict[str, object]]
    images: list[PackImage]
    videos: list[PackVideo]
    montage_files: list[dict[str, str]]
    cliffhanger: str
    issues: list[ValidationIssue]


def expected_stem(episode_id: str, shot_id: str, media_type: str) -> str:
    suffix = "image" if media_type == "image" else "video"
    return f"{episode_id.upper()}_{shot_id}_{suffix}"


def _asset_directory(bundle: LoadedEpisode, media_type: str) -> Path:
    folder = "images" if media_type == "image" else "videos"
    return bundle.episode_dir / "assets" / folder


def _find_asset(bundle: LoadedEpisode, shot: Shot, media_type: str) -> Path | None:
    directory = _asset_directory(bundle, media_type)
    if not directory.exists():
        return None
    extensions = IMAGE_EXTENSIONS if media_type == "image" else VIDEO_EXTENSIONS
    stem = expected_stem(bundle.episode.id, shot.id, media_type).casefold()
    candidates = [
        path
        for path in directory.iterdir()
        if path.is_file() and path.suffix.casefold() in extensions
        and path.stem.casefold() == stem
    ]
    return sorted(candidates, key=lambda path: path.name.casefold())[0] if candidates else None


def _asset_name(bundle: LoadedEpisode, shot: Shot, media_type: str) -> str:
    found = _find_asset(bundle, shot, media_type)
    if found:
        return found.name
    extension = ".jpg" if media_type == "image" else ".mp4"
    return expected_stem(bundle.episode.id, shot.id, media_type) + extension


def _dependency(shot: Shot) -> str | None:
    return shot.parent or shot.reference_from


def _ordered_images(shots: list[Shot]) -> list[Shot]:
    images = {shot.id: shot for shot in shots if shot.kind in IMAGE_KINDS}
    ordered = sorted(images.values(), key=lambda shot: shot.order)
    result: list[Shot] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(shot: Shot) -> None:
        if shot.id in visited:
            return
        if shot.id in visiting:
            raise ValueError(f"Ciclo de referência de imagem envolvendo {shot.id}.")
        visiting.add(shot.id)
        parent_id = _dependency(shot)
        if parent_id in images:
            visit(images[parent_id])
        visiting.remove(shot.id)
        visited.add(shot.id)
        result.append(shot)

    for shot in ordered:
        visit(shot)
    return result


def _image_reference(
    bundle: LoadedEpisode,
    shot: Shot,
    image_numbers: dict[str, int],
) -> str:
    parent_id = _dependency(shot)
    if not parent_id:
        return "nada"
    parent = next(item for item in bundle.shots.shots if item.id == parent_id)
    filename = _asset_name(bundle, parent, "image")
    number = image_numbers.get(parent_id)
    return f"IMAGEM {number} · {filename}" if number else filename


def _validation_issues(bundle: LoadedEpisode, root: Path) -> list[ValidationIssue]:
    issues = validate_bundle(bundle)
    bible = check_bible(root, bundle.series.id)
    if bible.status == "in_production" and has_bible_errors(bible):
        issues.extend(
            ValidationIssue(level="error", message=f"Bíblia: {issue.message}")
            for issue in bible.issues
            if issue.level == "error"
        )
    filtered: list[ValidationIssue] = []
    parent_error = re.compile(r"^(?:Parent|Reference) (\S+) has no approved image$")
    for issue in issues:
        if issue.level == "error":
            match = parent_error.match(issue.message)
            if match:
                referenced = next(
                    (shot for shot in bundle.shots.shots if shot.id == match.group(1)), None
                )
                if referenced and _find_asset(bundle, referenced, "image"):
                    continue
        filtered.append(issue)
    return filtered


def _character_names(bundle: LoadedEpisode) -> dict[str, str]:
    return {character.id: character.name for character in bundle.characters.characters}


def _time_label(seconds: float) -> str:
    minutes = int(seconds // 60)
    remainder = int(seconds % 60)
    return f"{minutes:02d}:{remainder:02d}"


def _prompt_for(root: Path, bundle: LoadedEpisode, shot: Shot) -> PromptResult:
    return render_prompt(root, bundle, shot, allow_unknown_cost=True)


def build_pack(root: Path, bundle: LoadedEpisode) -> PackData:
    issues = _validation_issues(bundle, root)
    if any(issue.level == "error" for issue in issues):
        raise PackValidationError(issues)

    production = load_production(root)
    profile_name = bundle.profile_name or production.effective_profile_name(
        bundle.series.profile, bundle.episode.profile
    )
    profile = production.profile(profile_name)
    ordered = sorted(bundle.shots.shots, key=lambda shot: shot.order)
    image_shots = _ordered_images(ordered)
    image_numbers = {shot.id: index for index, shot in enumerate(image_shots, start=1)}
    images = [
        PackImage(
            number=index,
            shot=shot,
            filename=_asset_name(bundle, shot, "image"),
            approved=_find_asset(bundle, shot, "image") is not None,
            attachment=_image_reference(bundle, shot, image_numbers),
            prompt=_prompt_for(root, bundle, shot).prompt,
        )
        for index, shot in enumerate(image_shots, start=1)
    ]

    video_shots = [shot for shot in ordered if shot.kind in VIDEO_KINDS]
    videos: list[PackVideo] = []
    for index, shot in enumerate(video_shots, start=1):
        expression_only = shot.kind == "video_expression_only"
        attachment = (
            "nenhuma imagem"
            if expression_only
            else _image_reference(bundle, shot, image_numbers)
        )
        parent_id = _dependency(shot)
        parent = next((item for item in image_shots if item.id == parent_id), None)
        approved = expression_only or bool(parent and _find_asset(bundle, parent, "image"))
        videos.append(
            PackVideo(
                number=index,
                shot=shot,
                filename=_asset_name(bundle, shot, "video"),
                approved=_find_asset(bundle, shot, "video") is not None,
                attachment=attachment,
                pending_warning=(
                    "⚠️ Imagem ainda pendente; gere/aprove a imagem antes do vídeo."
                    if not approved
                    else ""
                ),
                prompt=_prompt_for(root, bundle, shot).prompt,
            )
        )

    pacing = lint_bundle(bundle, production)
    character_names = _character_names(bundle)
    scenes: list[dict[str, object]] = []
    cursor = 0.0
    for shot in video_shots:
        end = cursor + shot.duration_s
        lines = [
            {
                "label": label,
                "text": f"{character_names.get(line.speaker, line.speaker)}: \"{line.text}\"",
            }
            for label, source in (("Fala", shot.dialogue_pt), ("Voz off", shot.voice_over_pt))
            for line in source
        ]
        location = next(
            (
                item.name or item.id
                for item in bundle.locations.locations
                if item.id == shot.location
            ),
            shot.location,
        )
        scenes.append(
            {
                "time_range": f"{_time_label(cursor)}–{_time_label(end)}",
                "location": location,
                "characters": [character_names.get(item, item) for item in shot.characters],
                "what": shot.expected_result_pt or shot.beat_pt or shot.action_pt,
                "dialogue": lines,
            }
        )
        cursor = end

    montage_files = [
        {"filename": video.filename, "status": video.status} for video in videos
    ]
    return PackData(
        series_title=bundle.series.title,
        series_id=bundle.series.id,
        episode_id=bundle.episode.id,
        episode_title=bundle.episode.title,
        profile_name=profile_name,
        resolution=profile.resolution,
        estimated_runtime_s=pacing.estimated_runtime_s,
        target_seconds=bundle.episode.target_seconds,
        cold_open=bundle.episode.cold_open if bundle.episode.cold_open.enabled else None,
        scenes=scenes,
        images=images,
        videos=videos,
        montage_files=montage_files,
        cliffhanger=bundle.episode.cliffhanger,
        issues=issues,
    )


def _environment(root: Path) -> Environment:
    return Environment(
        loader=FileSystemLoader(root / "templates" / "pack"),
        undefined=StrictUndefined,
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )


def write_pack(root: Path, bundle: LoadedEpisode, data: PackData | None = None) -> Path:
    data = data or build_pack(root, bundle)
    episode_dir = bundle.episode_dir
    (episode_dir / "assets" / "images").mkdir(parents=True, exist_ok=True)
    (episode_dir / "assets" / "videos").mkdir(parents=True, exist_ok=True)
    package_dir = episode_dir / "pacote"
    if package_dir.exists():
        shutil.rmtree(package_dir)
    package_dir.mkdir(parents=True, exist_ok=True)
    environment = _environment(root)
    common = {"data": data}
    for filename, template_name in (
        ("1_ROTEIRO.md", "script.md.j2"),
        ("2_IMAGENS.md", "images.md.j2"),
        ("3_VIDEOS.md", "videos.md.j2"),
    ):
        content = environment.get_template(template_name).render(**common)
        (package_dir / filename).write_text(content, encoding="utf-8")
    return package_dir
