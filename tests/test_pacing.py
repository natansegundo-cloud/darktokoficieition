import shutil
from dataclasses import replace
from pathlib import Path

import yaml

from studio.config import load_production
from studio.loader import ProjectLoader
from studio.models import (
    CharactersFile,
    DialogueLine,
    ProductionConfig,
    SafetyConfig,
    Shot,
    ShotsFile,
)
from studio.pacing import lint_bundle, shot_words

ROOT = Path(__file__).parents[1]


def _bundle_with(*shots: Shot):
    bundle = ProjectLoader(ROOT).load_episode_bundle("revenge_republic", "ep01")
    return replace(bundle, shots=ShotsFile(shots=list(shots)))


def _video(shot_id: str = "P99", **updates: object) -> Shot:
    values: dict[str, object] = {
        "id": shot_id,
        "order": 0,
        "kind": "video_from_image",
        "location": "kitchen",
        "framing": "medium shot",
        "framing_pt": "plano médio",
        "action": "a visible action",
        "action_pt": "uma ação visível",
        "duration_s": 8,
        "beat_pt": "uma mudança concreta",
    }
    values.update(updates)
    return Shot.model_validate(values)


def _messages(report, level: str | None = None, shot_id: str | None = None) -> list[str]:
    return [
        issue.message
        for issue in report.issues
        if (level is None or issue.level == level) and (shot_id is None or issue.shot_id == shot_id)
    ]


def test_video_without_speech_is_an_error() -> None:
    report = lint_bundle(_bundle_with(_video()), load_production(ROOT))
    assert any("needs dialogue_pt" in message for message in _messages(report, "error"))


def test_speech_longer_than_duration_is_an_error() -> None:
    line = DialogueLine(speaker="duda", text="uma " * 25)
    report = lint_bundle(_bundle_with(_video(dialogue_pt=[line])), load_production(ROOT))
    assert any("exceeds duration" in message for message in _messages(report, "error"))


def test_underfilled_speech_reports_empty_seconds() -> None:
    line = DialogueLine(speaker="duda", text="Uma revelação curta")
    report = lint_bundle(_bundle_with(_video(dialogue_pt=[line])), load_production(ROOT))
    assert any("faltam" in message for message in _messages(report, "error"))
    compatibility = lint_bundle(_bundle_with(_video(dialogue_pt=[line])), ProductionConfig())
    assert any("faltam" in message for message in _messages(compatibility, "warning"))


def test_excess_silence_uses_configured_severity() -> None:
    line = DialogueLine(speaker="duda", text="Uma fala curta")
    report = lint_bundle(_bundle_with(_video(dialogue_pt=[line])), load_production(ROOT))
    assert any("Silêncio estimado" in message for message in _messages(report, "error"))
    compatibility = lint_bundle(_bundle_with(_video(dialogue_pt=[line])), ProductionConfig())
    assert any("Silêncio estimado" in message for message in _messages(compatibility, "warning"))


def test_long_line_and_line_count_are_warnings() -> None:
    lines = [DialogueLine(speaker="duda", text="uma " * 16) for _ in range(3)]
    report = lint_bundle(_bundle_with(_video(dialogue_pt=lines)), load_production(ROOT))
    warnings = _messages(report, "warning")
    assert any("spoken lines exceed" in message for message in warnings)
    assert sum("maximum is 15" in message for message in warnings) == 3


def test_voice_over_counts_as_speech() -> None:
    shot = _video(
        dialogue_pt=[],
        voice_over_pt=[DialogueLine(speaker="duda", text="A prova está comigo")],
    )
    report = lint_bundle(_bundle_with(shot), load_production(ROOT))
    assert shot_words(shot) == 4
    assert not any("needs dialogue_pt" in message for message in _messages(report, "error"))


def test_intentional_silence_is_allowed_but_episode_limit_warns() -> None:
    shots = [
        _video("P01", intentional_silence=True, beat_pt="primeiro golpe"),
        _video("P02", order=1, duration_s=9, intentional_silence=True, beat_pt="segundo golpe"),
    ]
    report = lint_bundle(_bundle_with(*shots), load_production(ROOT))
    assert not _messages(report, "error")
    assert any("intentional silences" in message for message in _messages(report, "warning"))


def test_empty_and_repeated_beats_are_warnings() -> None:
    shots = [
        _video("P01", beat_pt=""),
        _video(
            "P02",
            order=1,
            beat_pt="mesmo golpe",
            dialogue_pt=[DialogueLine(speaker="duda", text="Vai")],
        ),
        _video(
            "P03",
            order=2,
            beat_pt="mesmo golpe",
            dialogue_pt=[DialogueLine(speaker="duda", text="Agora")],
        ),
    ]
    report = lint_bundle(_bundle_with(*shots), load_production(ROOT))
    warnings = _messages(report, "warning")
    assert "beat_pt is empty" in warnings
    assert "Consecutive shots repeat the same beat_pt" in warnings


def test_missing_portuguese_mirror_is_a_warning() -> None:
    shot = _video(framing_pt="")
    report = lint_bundle(_bundle_with(shot), load_production(ROOT))
    assert any("framing_pt" in message for message in _messages(report, "warning"))


def test_missing_direction_mirror_is_a_warning() -> None:
    shot = _video(setup="A room", setup_pt="")
    report = lint_bundle(_bundle_with(shot), load_production(ROOT))
    assert any("setup_pt" in message for message in _messages(report, "warning"))


def test_delivery_mirror_warning_and_forbidden_marker_error() -> None:
    incomplete = DialogueLine(speaker="duda", text="Vai", delivery="low, controlled")
    report = lint_bundle(_bundle_with(_video(dialogue_pt=[incomplete])), ProductionConfig())
    assert any("delivery_pt" in message for message in _messages(report, "warning"))

    reverse = DialogueLine(speaker="duda", text="Vai", delivery_pt="baixa")
    report = lint_bundle(_bundle_with(_video(dialogue_pt=[reverse])), ProductionConfig())
    assert any("delivery e delivery_pt" in message for message in _messages(report, "warning"))

    contradictory = DialogueLine(
        speaker="duda",
        text="Vai",
        delivery="soft or cold",
        delivery_pt="suave ou fria",
    )
    report = lint_bundle(_bundle_with(_video(dialogue_pt=[contradictory])), load_production(ROOT))
    assert any("tom duplo" in message for message in _messages(report, "error"))


def test_delivery_forbidden_markers_are_configurable() -> None:
    line = DialogueLine(
        speaker="duda",
        text="Vai",
        delivery="soft / cold",
        delivery_pt="suave / fria",
    )
    production = ProductionConfig(
        pacing={
            "delivery_forbidden_markers": [" / "],
            "enforcement": {"low_fill": "warning", "excess_silence": "warning"},
        }
    )
    report = lint_bundle(_bundle_with(_video(dialogue_pt=[line])), production)
    assert any("tom duplo" in message for message in _messages(report, "error"))


def test_voice_profile_missing_mirror_and_duplicate_are_warnings() -> None:
    bundle = _bundle_with(
        _video(
            dialogue_pt=[
                DialogueLine(speaker="duda", text="Vai"),
                DialogueLine(speaker="manu", text="Agora"),
            ]
        )
    )
    updated = [
        item.model_copy(update={"voice_profile": "same voice"})
        if item.id == "duda"
        else item
        for item in bundle.characters.characters
    ]
    updated = [
        item.model_copy(update={"voice_profile": "same voice", "voice_profile_pt": None})
        if item.id == "manu"
        else item
        for item in updated
    ]
    report = lint_bundle(
        replace(bundle, characters=CharactersFile(characters=updated)), ProductionConfig()
    )
    warnings = _messages(report, "warning")
    assert any("voice_profile_pt" in message for message in warnings)
    assert any("duplicados" in message for message in warnings)


def test_runtime_is_reported_and_warns_outside_ten_percent() -> None:
    bundle = _bundle_with(_video(duration_s=8), _video("P100", order=1, duration_s=8))
    bundle = replace(
        bundle,
        episode=bundle.episode.model_copy(
            update={
                "target_seconds": 30,
                "cold_open": bundle.episode.cold_open.model_copy(update={"enabled": False}),
            }
        ),
    )
    report = lint_bundle(bundle, ProductionConfig())
    assert report.estimated_runtime_s == 16
    assert any("Runtime estimado" in message for message in _messages(report, "warning"))
    on_target = replace(
        bundle,
        episode=bundle.episode.model_copy(update={"target_seconds": 16}),
    )
    on_target_report = lint_bundle(on_target, ProductionConfig())
    assert not any(
        "Runtime estimado" in message for message in _messages(on_target_report, "warning")
    )


def test_hook_and_cliffhanger_rules_have_passing_and_failing_cases() -> None:
    passing = _video(
        role="hook",
        dialogue_pt=[
            DialogueLine(speaker="duda", text="Agora", delivery="low", delivery_pt="baixa")
        ],
        timeline=[{"at_s": "0-2s", "action": "She speaks", "action_pt": "Ela fala"}],
        timeline_pt=[{"at_s": "0-2s", "action_pt": "Ela fala"}],
    )
    report = lint_bundle(_bundle_with(passing), ProductionConfig())
    assert not any("gancho" in message.lower() for message in _messages(report, "warning"))

    failing = _video(
        role="body",
        dialogue_pt=[DialogueLine(speaker="duda", text="Agora")],
        timeline=[{"at_s": "2-4s", "action": "She speaks", "action_pt": "Ela fala"}],
        timeline_pt=[{"at_s": "2-4s", "action_pt": "Ela fala"}],
    )
    failed_bundle = _bundle_with(failing)
    failed_bundle = replace(
        failed_bundle,
        episode=failed_bundle.episode.model_copy(update={"cliffhanger": ""}),
    )
    report = lint_bundle(failed_bundle, ProductionConfig())
    assert any("role: hook" in message for message in _messages(report, "warning"))
    assert any("antes de 2 segundos" in message for message in _messages(report, "warning"))
    assert any("cliffhanger" in message for message in _messages(report, "error"))


def test_season_finale_may_omit_cliffhanger() -> None:
    bundle = _bundle_with(
        _video(role="hook", dialogue_pt=[DialogueLine(speaker="duda", text="Agora")])
    )
    bundle = replace(
        bundle,
        episode=bundle.episode.model_copy(update={"cliffhanger": "", "season_finale": True}),
    )
    report = lint_bundle(bundle, ProductionConfig())
    assert not any("cliffhanger" in message for message in _messages(report))


def test_profile_duration_and_resolution_rules() -> None:
    short_bundle = _bundle_with(_video(resolution="1080p"))
    report = lint_bundle(short_bundle, load_production(ROOT))
    assert any("fora da faixa do perfil" in message for message in _messages(report, "error"))
    assert any("Resolução do plano" in message for message in _messages(report, "warning"))

    passing_bundle = _bundle_with(
        _video("P01", duration_s=8),
        _video("P02", order=1, duration_s=9, beat_pt="outro beat"),
    )
    passing = lint_bundle(passing_bundle, load_production(ROOT))
    assert not any("fora da faixa do perfil" in message for message in _messages(passing))

    warning_config = load_production(ROOT)
    warning_pacing = warning_config.pacing.model_copy(
        update={
            "enforcement": warning_config.pacing.enforcement.model_copy(
                update={"profile_duration": "warning"}
            )
        }
    )
    warning_config = warning_config.model_copy(update={"pacing": warning_pacing})
    warning_report = lint_bundle(short_bundle, warning_config)
    assert any(
        "fora da faixa do perfil" in message
        for message in _messages(warning_report, "warning")
    )


def test_style_requiring_silhouette_warns_for_missing_hooks() -> None:
    bundle = _bundle_with(_video())
    style = bundle.style.model_copy(
        update={
            "character_rules": "Each character needs a silhouette hook.",
            "character_rules_pt": "Cada personagem precisa de uma silhueta.",
        }
    )
    report = lint_bundle(replace(bundle, style=style), ProductionConfig())
    assert any("não tem silhouette_hook" in message for message in _messages(report, "warning"))


def test_silhouette_hook_must_appear_in_lock_block() -> None:
    bundle = _bundle_with(_video(characters=["manu"]))
    character = bundle.characters.characters[0].model_copy(
        update={"silhouette_hook": "triangular nose"}
    )
    report = lint_bundle(
        replace(bundle, characters=CharactersFile(characters=[character])), ProductionConfig()
    )
    assert any(
        "silhouette_hook" in message and "lock_block" in message
        for message in _messages(report, "warning")
    )


def test_same_silhouette_or_hair_color_in_one_shot_warns() -> None:
    bundle = _bundle_with(_video(characters=["manu", "duda"]))
    first, second = bundle.characters.characters[:2]
    first = first.model_copy(update={"silhouette_hook": "square jaw", "hair_color": "violet"})
    second = second.model_copy(
        update={"silhouette_hook": "square jaw", "hair_color": "VIOLET"}
    )
    report = lint_bundle(
        replace(bundle, characters=CharactersFile(characters=[first, second])), ProductionConfig()
    )
    warnings = _messages(report, "warning")
    assert any("mesmo silhouette_hook" in message for message in warnings)
    assert any("mesma hair_color" in message for message in warnings)


def test_blocked_terms_are_errors_in_lock_style_and_action() -> None:
    bundle = _bundle_with(_video(action="forbidden action"))
    character = bundle.characters.characters[0].model_copy(
        update={"lock_block": "Manu, forbidden character"}
    )
    style = bundle.style.model_copy(update={"style_block": "forbidden style"})
    production = ProductionConfig(safety=SafetyConfig(blocked_terms=["forbidden"]))
    report = lint_bundle(
        replace(
            bundle,
            characters=CharactersFile(characters=[character]),
            style=style,
        ),
        production,
    )
    errors = _messages(report, "error")
    assert sum("Termo bloqueado 'forbidden'" in message for message in errors) == 3


def test_fixture_copy_fails_when_speech_is_removed(tmp_path: Path) -> None:
    for directory in ("config", "series", "styles"):
        shutil.copytree(ROOT / directory, tmp_path / directory)
    shots_path = tmp_path / "series" / "revenge_republic" / "episodes" / "ep01" / "shots.yaml"
    data = yaml.safe_load(shots_path.read_text(encoding="utf-8"))
    shot = next(item for item in data["shots"] if item["id"] == "P04")
    shot["dialogue_pt"] = []
    shot["voice_over_pt"] = []
    shot["intentional_silence"] = False
    shots_path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )

    bundle = ProjectLoader(tmp_path).load_episode_bundle("revenge_republic", "ep01")
    report = lint_bundle(bundle, load_production(tmp_path))
    assert any(issue.level == "error" and issue.shot_id == "P04" for issue in report.issues)
