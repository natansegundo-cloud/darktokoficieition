from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StudioModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


class Nickname(StudioModel):
    name: str
    used_by: list[str] = Field(default_factory=list)


class Character(StudioModel):
    id: str
    name: str
    full_name: str | None = None
    nicknames: list[Nickname] = Field(default_factory=list)
    role: Literal["protagonist", "villain", "ally", "love_interest", "support"] = "support"
    age: int | None = None
    lock_version: int = 1
    lock_block: str
    lock_block_pt: str = ""
    signature_element: str | None = None
    hair_color: str | None = None
    silhouette_hook: str | None = None
    silhouette_hook_pt: str | None = None
    palette: str | list[str] | None = None
    voice_notes: str = ""
    default_delivery: str | None = None
    default_delivery_pt: str | None = None
    voice_profile: str | None = None
    voice_profile_pt: str | None = None
    bio_pt: str = ""
    arc_pt: str = ""
    approved_reference: str | None = None


class CharactersFile(StudioModel):
    characters: list[Character] = Field(default_factory=list)


class Location(StudioModel):
    id: str
    name: str = ""
    description_en: str
    description_pt: str = ""
    default_light: str = "natural light"
    default_light_pt: str = ""


class LocationsFile(StudioModel):
    locations: list[Location] = Field(default_factory=list)


class StylePreset(StudioModel):
    id: str
    name: str
    style_block: str
    style_block_pt: str = ""
    negative_hints: str = ""
    negative_hints_pt: str = ""
    camera_defaults: str = ""
    camera_defaults_pt: str = ""
    video_motion_defaults: str = "subtle natural motion"
    video_motion_defaults_pt: str = ""
    notes: str = ""
    character_rules: str = ""
    character_rules_pt: str = ""
    audio_style: str = (
        "clean dialogue in Brazilian Portuguese, natural room tone, no background music, "
        "no laugh track, no on-screen text"
    )
    audio_style_pt: str = (
        "áudio limpo em português do Brasil, som natural do ambiente, sem música de fundo, "
        "sem risadas de fundo, sem texto na tela"
    )


class Series(StudioModel):
    id: str
    title: str
    genre: str = ""
    audience: str = ""
    language: str = "pt-BR"
    aspect_ratio: str = "9:16"
    style: str
    episodes_planned: int = 1
    episode_target_seconds: list[int] = Field(default_factory=lambda: [30, 90])
    logline: str = ""
    synopsis: str = ""
    season_hook: str = ""
    status: Literal["idea", "planning", "in_production", "paused", "released"] = "planning"
    profile: str | None = None
    notes: str = ""


class ColdOpen(StudioModel):
    enabled: bool = False
    source_shot: str | None = None
    trim_start_s: float = 0.0
    trim_end_s: float = 3.5
    transition: str = "white flash + impact sound"
    title_card_pt: str = "Horas antes..."


class Episode(StudioModel):
    id: str
    title: str
    number: int
    target_seconds: int = 60
    cold_open: ColdOpen = Field(default_factory=ColdOpen)
    cliffhanger: str = ""
    season_finale: bool = False
    profile: str | None = None
    key_prop: str = ""
    status: Literal[
        "planning", "scripted", "prompts_ready", "generating", "editing", "ready", "posted"
    ] = "planning"
    metrics: dict[str, object] = Field(default_factory=dict)
    notes: str = ""


class DialogueLine(StudioModel):
    speaker: str
    text: str
    delivery: str | None = None
    delivery_pt: str | None = None


class DirectionBeat(StudioModel):
    at_s: str
    action: str = ""
    action_pt: str = ""


class ShotFiles(StudioModel):
    image: str | None = None
    video: str | None = None


class Shot(StudioModel):
    id: str
    order: int
    kind: Literal["anchor_image", "derived_image", "video_from_image", "video_expression_only"]
    role: Literal["hook", "body", "cliffhanger"] = "body"
    location: str
    characters: list[str] = Field(default_factory=list)
    framing: str = "medium shot"
    framing_pt: str = ""
    action: str = ""
    action_en: str = ""
    action_pt: str = ""
    expected_result_pt: str = ""
    camera: str = ""
    camera_pt: str = ""
    gaze: str = ""
    gaze_pt: str = ""
    mood: str = ""
    mood_pt: str = ""
    expression: str = ""
    expression_pt: str = ""
    parent: str | None = None
    reference_from: str | None = None
    light: str | None = None
    light_pt: str = ""
    resolution: str | None = None
    dialogue_pt: list[DialogueLine] = Field(default_factory=list)
    voice_over_pt: list[DialogueLine] = Field(default_factory=list)
    intentional_silence: bool = False
    beat_pt: str = ""
    setup: str = ""
    setup_pt: str = ""
    start_state: str = ""
    start_state_pt: str = ""
    timeline: list[DirectionBeat] = Field(default_factory=list)
    timeline_pt: list[DirectionBeat] = Field(default_factory=list)
    end_state: str = ""
    end_state_pt: str = ""
    sound: str = ""
    sound_pt: str = ""
    must_not: str = ""
    must_not_pt: str = ""
    voice_mode: Literal["native"] = "native"
    duration_s: int = 8
    account: str | None = None
    status: Literal["todo", "prompt_ready", "generated", "approved", "rejected", "edited"] = "todo"
    video_attempts: int = 0
    files: ShotFiles = Field(default_factory=ShotFiles)
    notes: str = ""


class ShotsFile(StudioModel):
    shots: list[Shot] = Field(default_factory=list)


class VideoConfig(StudioModel):
    default_duration_s: int = 8
    costs_verified_on: date | None = None
    costs_max_age_days: int = 30
    costs: dict[str, dict[int, int | None]] = Field(default_factory=dict)
    max_attempts: int = 2


class EpisodeSeconds(StudioModel):
    min: int
    max: int


class ProductionProfile(StudioModel):
    purpose_pt: str
    resolution: str
    episode_seconds: EpisodeSeconds
    cold_open: bool = True


class ImageConfig(StudioModel):
    credits: int = 0


class SafetyConfig(StudioModel):
    blocked_terms: list[str] = Field(default_factory=list)


class AccountsConfig(StudioModel):
    count: int = 5
    daily_credits_per_account: int = 50
    reserve_videos_per_account: int = 1


class WorkflowConfig(StudioModel):
    mode: Literal["images_first", "sequential"] = "images_first"


class PacingEnforcement(StudioModel):
    low_fill: Literal["error", "warning"] = "warning"
    excess_silence: Literal["error", "warning"] = "warning"
    missing_hook: Literal["error", "warning"] = "warning"
    profile_duration: Literal["error", "warning"] = "error"


class PacingConfig(StudioModel):
    words_per_second: float = 2.5
    min_speech_fill: float = 0.6
    max_silence_s: float = 1.5
    max_dialogue_lines: int = 2
    max_words_per_line: int = 15
    max_intentional_silences_per_episode: int = 1
    delivery_forbidden_markers: list[str] = Field(
        default_factory=lambda: [" or ", ";", " when "]
    )
    enforcement: PacingEnforcement = Field(default_factory=PacingEnforcement)


class BibleConfig(StudioModel):
    min_section_chars: int = 80
    placeholder_markers: list[str] = Field(
        default_factory=lambda: ["TODO", "Describe", "Descreva", "XXX"]
    )


class ProductionConfig(StudioModel):
    active_profile: str = "growth"
    profiles: dict[str, ProductionProfile] = Field(default_factory=dict)
    tool: str = "google_flow"
    aspect_ratio: str = "9:16"
    video: VideoConfig = Field(default_factory=VideoConfig)
    image: ImageConfig = Field(default_factory=ImageConfig)
    safety: SafetyConfig = Field(default_factory=SafetyConfig)
    accounts: AccountsConfig = Field(default_factory=AccountsConfig)
    workflow: WorkflowConfig = Field(default_factory=WorkflowConfig)
    pacing: PacingConfig = Field(default_factory=PacingConfig)
    bible: BibleConfig = Field(default_factory=BibleConfig)

    def effective_profile_name(
        self,
        series_profile: str | None = None,
        episode_profile: str | None = None,
    ) -> str:
        name = episode_profile or series_profile or self.active_profile
        if name not in self.profiles:
            raise ValueError(
                f"Perfil '{name}' não está configurado em config/production.yaml"
            )
        return name

    def profile(self, name: str | None = None) -> ProductionProfile:
        profile_name = name or self.active_profile
        try:
            return self.profiles[profile_name]
        except KeyError as exc:
            raise ValueError(
                f"Perfil '{profile_name}' não está configurado em config/production.yaml"
            ) from exc

    def video_credits(self, duration_s: int, resolution: str | None = None) -> int:
        selected_resolution = resolution or self.profile().resolution
        resolution_costs = self.video.costs.get(selected_resolution)
        if resolution_costs is None or duration_s not in resolution_costs:
            raise ValueError(
                f"Preencha o custo de {selected_resolution} em config/production.yaml"
            )
        cost = resolution_costs[duration_s]
        if cost is None:
            raise ValueError(
                f"Preencha o custo de {selected_resolution} em config/production.yaml"
            )
        return cost

    def shot_credits(self, shot: Shot, resolution: str | None = None) -> int:
        if shot.kind in {"anchor_image", "derived_image"}:
            return self.image.credits
        return self.video_credits(shot.duration_s, resolution=resolution)

    def costs_warning(self) -> str | None:
        if self.video.costs_verified_on is None:
            return "Conferir custos na interface do Flow: eles mudam"
        age = (date.today() - self.video.costs_verified_on).days
        if age > self.video.costs_max_age_days:
            return "Conferir custos na interface do Flow: eles mudam"
        return None


class Account(StudioModel):
    id: str


class AccountsFile(StudioModel):
    accounts: list[Account] = Field(default_factory=list)


class ValidationIssue(StudioModel):
    level: Literal["error", "warning"]
    message: str
    shot_id: str | None = None
