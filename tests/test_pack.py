import shutil
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from studio.cli import app
from studio.loader import ProjectLoader
from studio.pack import PackValidationError, build_pack, expected_stem, write_pack

ROOT = Path(__file__).parents[1]
RUNNER = CliRunner()


def _copy_project(tmp_path: Path) -> Path:
    for directory in ("config", "styles", "templates"):
        shutil.copytree(ROOT / directory, tmp_path / directory)
    shutil.copytree(
        ROOT / "series" / "revenge_republic",
        tmp_path / "series" / "revenge_republic",
    )
    return tmp_path


def _make_images(root: Path, *, extension: str = ".jpg") -> Path:
    directory = root / "series" / "revenge_republic" / "episodes" / "ep01" / "assets" / "images"
    directory.mkdir(parents=True, exist_ok=True)
    for shot_id in ("P01i", "P02i", "P03i", "P04i", "P05i", "P06i"):
        name = expected_stem("ep01", shot_id, "image") + extension
        (directory / name).write_bytes(b"approved image")
    return directory


def _bundle(root: Path):
    return ProjectLoader(root).load_episode_bundle("revenge_republic", "ep01")


def test_pack_creates_four_documents_and_asset_folders(tmp_path: Path) -> None:
    root = _copy_project(tmp_path)
    _make_images(root)

    package = write_pack(root, _bundle(root))

    assert sorted(path.name for path in package.iterdir()) == [
        "0_PERSONAGENS.md",
        "1_ROTEIRO.md",
        "2_IMAGENS.md",
        "3_VIDEOS.md",
    ]
    assert (package.parent / "assets" / "images").exists()
    assert (package.parent / "assets" / "videos").exists()
    assert (root / "series" / "revenge_republic" / "assets" / "characters").exists()
    script = (package / "1_ROTEIRO.md").read_text(encoding="utf-8")
    assert "00:00–00:08" in script
    assert "Duda revela ao telefone" in script


def test_pack_command_reports_generated_path(tmp_path: Path, monkeypatch) -> None:
    root = _copy_project(tmp_path)
    _make_images(root)
    monkeypatch.chdir(root)

    result = RUNNER.invoke(app, ["pack", "revenge_republic", "ep01"])

    assert result.exit_code == 0
    assert "Pacote gerado em" in result.stdout


def test_pack_orders_parent_before_derived_and_marks_files_by_extension(tmp_path: Path) -> None:
    root = _copy_project(tmp_path)
    image_dir = _make_images(root)
    (image_dir / (expected_stem("ep01", "P04i", "image") + ".jpg")).unlink()
    (image_dir / (expected_stem("ep01", "P04i", "image") + ".png")).write_bytes(b"png")

    data = build_pack(root, _bundle(root))
    image_ids = [item.shot.id for item in data.images]

    assert image_ids.index("P03i") < image_ids.index("P04i")
    assert data.images[image_ids.index("P04i")].filename.endswith(".png")
    assert data.images[image_ids.index("P04i")].approved is True
    assert "IMAGEM 3" in data.images[image_ids.index("P04i")].attachment


def test_status_is_ignored_but_downloads_are_not_approval(tmp_path: Path) -> None:
    root = _copy_project(tmp_path)
    image_dir = _make_images(root)
    shots_path = root / "series" / "revenge_republic" / "episodes" / "ep01" / "shots.yaml"
    shots = yaml.safe_load(shots_path.read_text(encoding="utf-8"))
    for shot in shots["shots"]:
        if shot["kind"] in {"anchor_image", "derived_image"}:
            shot["status"] = "rejected"
    shots_path.write_text(
        yaml.safe_dump(shots, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )

    data = build_pack(root, _bundle(root))
    assert all(item.approved for item in data.images)

    outside = root / "Downloads"
    outside.mkdir()
    (outside / (expected_stem("ep01", "P06i", "image") + ".jpg")).write_bytes(b"outside")
    (image_dir / (expected_stem("ep01", "P06i", "image") + ".jpg")).unlink()
    with pytest.raises(PackValidationError):
        build_pack(root, _bundle(root))


def test_pack_rerun_replaces_only_package(tmp_path: Path) -> None:
    root = _copy_project(tmp_path)
    image_dir = _make_images(root)
    package = write_pack(root, _bundle(root))
    (package / "obsolete.md").write_text("old", encoding="utf-8")
    asset = image_dir / (expected_stem("ep01", "P01i", "image") + ".jpg")
    before = asset.read_bytes()

    write_pack(root, _bundle(root))

    assert not (package / "obsolete.md").exists()
    assert asset.read_bytes() == before


def test_expression_only_video_has_no_attachment(tmp_path: Path) -> None:
    root = _copy_project(tmp_path)
    _make_images(root)
    shots_path = root / "series" / "revenge_republic" / "episodes" / "ep01" / "shots.yaml"
    shots = yaml.safe_load(shots_path.read_text(encoding="utf-8"))
    next(shot for shot in shots["shots"] if shot["id"] == "P06")["kind"] = "video_expression_only"
    shots_path.write_text(
        yaml.safe_dump(shots, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )

    package = write_pack(root, _bundle(root))
    content = (package / "3_VIDEOS.md").read_text(encoding="utf-8")

    assert "Anexar: nenhuma imagem" in content


def test_pending_image_is_marked_without_using_yaml_status(tmp_path: Path) -> None:
    root = _copy_project(tmp_path)
    image_dir = _make_images(root)
    pending = image_dir / (expected_stem("ep01", "P06i", "image") + ".jpg")
    pending.unlink()
    shots_path = root / "series" / "revenge_republic" / "episodes" / "ep01" / "shots.yaml"
    shots = yaml.safe_load(shots_path.read_text(encoding="utf-8"))
    image = next(shot for shot in shots["shots"] if shot["id"] == "P06i")
    image["status"] = "approved"
    image["files"] = {"image": "assets/images/EP01_P06i_image.jpg"}
    shots_path.write_text(
        yaml.safe_dump(shots, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )

    data = build_pack(root, _bundle(root))

    video = next(item for item in data.videos if item.shot.id == "P06")
    assert "Imagem ainda pendente" in video.pending_warning


def test_pack_allows_unknown_video_cost(tmp_path: Path) -> None:
    root = _copy_project(tmp_path)
    _make_images(root)
    production_path = root / "config" / "production.yaml"
    production = yaml.safe_load(production_path.read_text(encoding="utf-8"))
    production["video"]["costs"]["360p"][6] = None
    production_path.write_text(
        yaml.safe_dump(production, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )

    package = write_pack(root, _bundle(root))

    assert (package / "3_VIDEOS.md").exists()


def test_production_bible_error_blocks_pack(tmp_path: Path) -> None:
    root = _copy_project(tmp_path)
    _make_images(root)
    series_path = root / "series" / "revenge_republic" / "series.yaml"
    series = yaml.safe_load(series_path.read_text(encoding="utf-8"))
    series["status"] = "in_production"
    series_path.write_text(
        yaml.safe_dump(series, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    (series_path.parent / "bible.md").write_text("# incompleta", encoding="utf-8")

    with pytest.raises(PackValidationError, match="erros bloqueantes"):
        build_pack(root, _bundle(root))


def test_validation_error_blocks_pack(tmp_path: Path) -> None:
    root = _copy_project(tmp_path)
    _make_images(root)
    shots_path = root / "series" / "revenge_republic" / "episodes" / "ep01" / "shots.yaml"
    shots = yaml.safe_load(shots_path.read_text(encoding="utf-8"))
    next(shot for shot in shots["shots"] if shot["id"] == "P06")["location"] = "missing_location"
    shots_path.write_text(
        yaml.safe_dump(shots, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )

    with pytest.raises(PackValidationError, match="erros bloqueantes"):
        write_pack(root, _bundle(root))
    assert not (root / "series" / "revenge_republic" / "episodes" / "ep01" / "pacote").exists()
