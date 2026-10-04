import hashlib
import importlib.util
import io
import logging
import subprocess
import sys
import tarfile
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_sound_font.py"
FULL_SOUND_FONT = b"fake full sound font"
PIANOS = b"fake piano subset"
LICENSE = "fake license\n\n"


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("build_sound_font", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def make_archive(path: Path, members: dict[str, bytes]) -> bytes:
    with tarfile.open(path, "w:gz") as tar:
        for name, data in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return path.read_bytes()


def fake_sf2_cutter(output: bytes = PIANOS, returncode: int = 0) -> MagicMock:
    """A subprocess.run that writes output to sf2-cutter's -o path, the way the real tool writes the subset."""

    def run(args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        assert args[1] == "extract"
        if returncode == 0:
            Path(args[args.index("-o") + 1]).write_bytes(output)
        return subprocess.CompletedProcess(args, returncode, stdout="out\n", stderr="warnings\n")

    return MagicMock(side_effect=run)


@pytest.fixture
def script(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[ModuleType]:
    """The script with its paths in tmp_path, a fake archive instead of the Debian download and a fake sf2-cutter."""
    module = load_script()
    archive = make_archive(
        tmp_path / "source.tar.gz",
        {module.SOUND_FONT_MEMBER: FULL_SOUND_FONT, module.LICENSE_MEMBER: LICENSE.encode()},
    )
    monkeypatch.setattr(module, "SOUND_FONT_PATH", tmp_path / "pypiano" / "sound_fonts" / "pianos.sf2")
    monkeypatch.setattr(module, "LICENSE_PATH", tmp_path / "licenses" / "LICENSE-FluidR3_GM_sf2.txt")
    monkeypatch.setattr(module, "ARCHIVE_CACHE", tmp_path / "cache")
    monkeypatch.setattr(module, "ARCHIVE_SHA256", sha256(archive))
    monkeypatch.setattr(module, "FULL_SOUND_FONT_SHA256", sha256(FULL_SOUND_FONT))
    monkeypatch.setattr(module, "PIANOS_SHA256", sha256(PIANOS))
    monkeypatch.setattr(module, "download", MagicMock(side_effect=lambda _url, target: target.write_bytes(archive)))
    monkeypatch.setattr(module.shutil, "which", lambda name: f"/usr/local/bin/{name}")
    monkeypatch.setattr(module.subprocess, "run", fake_sf2_cutter())
    sys.modules["build_sound_font"] = module
    yield module
    del sys.modules["build_sound_font"]


# Existing files are never overwritten


def test_main_should_keep_sound_font_without_building_when_it_is_already_in_place(script: ModuleType) -> None:
    # Given the correct sound font is in place
    script.SOUND_FONT_PATH.parent.mkdir(parents=True)
    script.SOUND_FONT_PATH.write_bytes(PIANOS)
    # When
    exit_code = script.main([])
    # Then
    assert exit_code == 0
    script.download.assert_not_called()
    script.subprocess.run.assert_not_called()


def test_main_should_refuse_and_leave_file_untouched_when_another_file_is_in_place(
    script: ModuleType, caplog: pytest.LogCaptureFixture
) -> None:
    # Given another file at the sound font's path
    script.SOUND_FONT_PATH.parent.mkdir(parents=True)
    script.SOUND_FONT_PATH.write_bytes(b"something else")
    # When
    with caplog.at_level(logging.ERROR):
        exit_code = script.main([])
    # Then
    assert exit_code == 1
    script.download.assert_not_called()
    assert script.SOUND_FONT_PATH.read_bytes() == b"something else"
    assert "Not overwriting it" in caplog.text


def test_install_should_not_overwrite_sound_font_when_it_appears_during_the_build(script: ModuleType) -> None:
    # Given another file shows up at the target while building
    cutter = script.subprocess.run.side_effect

    def cut_then_create_target(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        result = cutter(args, **kwargs)
        script.SOUND_FONT_PATH.write_bytes(b"someone else's file")
        return result

    script.subprocess.run.side_effect = cut_then_create_target
    # When / Then
    with pytest.raises(script.ExistingFileError, match="not overwriting"):
        script.install_sound_font(script.SOUND_FONT_PATH, script.LICENSE_PATH)
    assert script.SOUND_FONT_PATH.read_bytes() == b"someone else's file"
    assert not script.SOUND_FONT_PATH.with_name("pianos.sf2.part").exists()


def test_install_should_keep_existing_license_when_it_differs(
    script: ModuleType, caplog: pytest.LogCaptureFixture
) -> None:
    # Given a license file with other content
    script.LICENSE_PATH.parent.mkdir(parents=True)
    script.LICENSE_PATH.write_text("my license\n")
    # When
    with caplog.at_level(logging.WARNING):
        script.install_sound_font(script.SOUND_FONT_PATH, script.LICENSE_PATH)
    # Then
    assert script.LICENSE_PATH.read_text() == "my license\n"
    assert "Leaving" in caplog.text


def test_install_should_keep_existing_license_silently_when_it_matches(
    script: ModuleType, caplog: pytest.LogCaptureFixture
) -> None:
    # Given the license is already in place
    script.LICENSE_PATH.parent.mkdir(parents=True)
    script.LICENSE_PATH.write_text("fake license\n")
    # When
    with caplog.at_level(logging.WARNING):
        script.install_sound_font(script.SOUND_FONT_PATH, script.LICENSE_PATH)
    # Then
    assert script.LICENSE_PATH.read_text() == "fake license\n"
    assert caplog.text == ""


# Building


def test_main_should_build_sound_font_and_license_when_both_are_missing(script: ModuleType) -> None:
    # Given neither file exists
    # When
    exit_code = script.main([])
    # Then
    assert exit_code == 0
    assert script.SOUND_FONT_PATH.read_bytes() == PIANOS
    # The repository keeps the license with a single trailing newline
    assert script.LICENSE_PATH.read_text() == "fake license\n"
    assert not script.SOUND_FONT_PATH.with_name("pianos.sf2.part").exists()


def test_build_should_run_sf2_cutter_with_the_recipe_and_bank_name_when_cutting(script: ModuleType) -> None:
    # Given a missing sound font
    # When
    script.main([])
    # Then
    ((args,), _) = script.subprocess.run.call_args
    assert args[0] == "/usr/local/bin/sf2-cutter"
    assert args[1:5] == ["extract", args[2], "--config", str(script.RECIPE_PATH)]
    assert args[2].endswith("FluidR3_GM.sf2")
    assert args[5:7] == ["--name", "Fluid R3 GM pianos"]


def test_build_should_reuse_a_verified_cached_archive_when_building_again(script: ModuleType) -> None:
    # Given a first build filled the cache
    script.main([])
    script.SOUND_FONT_PATH.unlink()
    # When
    script.main([])
    # Then
    script.download.assert_called_once()


def test_build_should_download_again_when_the_cached_archive_is_corrupt(script: ModuleType) -> None:
    # Given a corrupt archive in the cache
    script.ARCHIVE_CACHE.mkdir(parents=True)
    (script.ARCHIVE_CACHE / "fluid-soundfont_3.1.orig.tar.gz").write_bytes(b"corrupt")
    # When
    script.main([])
    # Then
    script.download.assert_called_once()
    assert script.SOUND_FONT_PATH.read_bytes() == PIANOS


@pytest.mark.parametrize(
    ("checksum", "file_name"),
    [
        ("ARCHIVE_SHA256", r"fluid-soundfont_3\.1\.orig\.tar\.gz\.part"),
        ("FULL_SOUND_FONT_SHA256", r"FluidR3_GM\.sf2"),
        ("PIANOS_SHA256", r"pianos\.sf2\.part"),
    ],
    ids=["archive", "full sound font", "piano subset"],
)
def test_build_should_raise_and_install_nothing_when_a_checksum_differs(
    monkeypatch: pytest.MonkeyPatch, script: ModuleType, checksum: str, file_name: str
) -> None:
    # Given a file with an unexpected checksum
    monkeypatch.setattr(script, checksum, sha256(b"something else"))
    # When / Then
    with pytest.raises(script.ChecksumError, match=rf"^{file_name} has sha256"):
        script.install_sound_font(script.SOUND_FONT_PATH, script.LICENSE_PATH)
    assert not script.SOUND_FONT_PATH.exists()
    assert not script.SOUND_FONT_PATH.with_name("pianos.sf2.part").exists()
    assert not script.LICENSE_PATH.exists()
    assert not (script.ARCHIVE_CACHE / "fluid-soundfont_3.1.orig.tar.gz.part").exists()


def test_build_should_raise_with_sf2_cutter_output_when_sf2_cutter_fails(script: ModuleType) -> None:
    # Given sf2-cutter fails
    script.subprocess.run = fake_sf2_cutter(returncode=1)
    # When / Then
    with pytest.raises(RuntimeError, match=r"^sf2-cutter failed with exit code 1:\nout\nwarnings\n$"):
        script.install_sound_font(script.SOUND_FONT_PATH, script.LICENSE_PATH)
    assert not script.SOUND_FONT_PATH.exists()


def test_build_should_raise_with_install_hint_when_sf2_cutter_is_missing(
    monkeypatch: pytest.MonkeyPatch, script: ModuleType
) -> None:
    # Given sf2-cutter is not installed
    monkeypatch.setattr(script.shutil, "which", lambda _name: None)
    # When / Then
    with pytest.raises(FileNotFoundError, match="devcontainer"):
        script.install_sound_font(script.SOUND_FONT_PATH, script.LICENSE_PATH)


# Reproducibility check


def test_check_should_pass_when_the_bundled_file_is_byte_identical_to_the_rebuild(
    script: ModuleType, caplog: pytest.LogCaptureFixture
) -> None:
    # Given the bundled file is what the build produces
    script.SOUND_FONT_PATH.parent.mkdir(parents=True)
    script.SOUND_FONT_PATH.write_bytes(PIANOS)
    # When
    with caplog.at_level(logging.INFO):
        exit_code = script.main(["--check"])
    # Then
    assert exit_code == 0
    assert "byte-identical" in caplog.text
    assert script.SOUND_FONT_PATH.read_bytes() == PIANOS


@pytest.mark.parametrize("bundled", [b"tampered sound font", None], ids=["different file", "missing file"])
def test_check_should_fail_without_changing_anything_when_the_bundled_file_differs(
    script: ModuleType, caplog: pytest.LogCaptureFixture, bundled: bytes | None
) -> None:
    # Given a bundled file that is not what the build produces
    script.SOUND_FONT_PATH.parent.mkdir(parents=True)
    if bundled is not None:
        script.SOUND_FONT_PATH.write_bytes(bundled)
    # When
    with caplog.at_level(logging.ERROR):
        exit_code = script.main(["--check"])
    # Then
    assert exit_code == 1
    assert "is not the file the build produces" in caplog.text
    assert (script.SOUND_FONT_PATH.read_bytes() if bundled is not None else None) == bundled
    assert not script.LICENSE_PATH.exists()


# Helpers


def test_extract_should_raise_value_error_when_member_is_not_a_regular_file(tmp_path: Path) -> None:
    # Given an archive whose member is a directory
    script = load_script()
    archive = tmp_path / "a.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        info = tarfile.TarInfo("fluid-soundfont-3.1/FluidR3_GM.sf2")
        info.type = tarfile.DIRTYPE
        tar.addfile(info)
    # When / Then
    with pytest.raises(ValueError, match="not a regular file"):
        script.extract(archive, "fluid-soundfont-3.1/FluidR3_GM.sf2", tmp_path / "out")


def test_download_should_write_streamed_chunks_when_request_succeeds(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Given a server that streams two chunks
    script = load_script()
    response = MagicMock()
    response.__enter__.return_value = response
    response.headers = {"content-length": "6"}
    response.iter_content.return_value = [b"abc", b"def"]
    get = MagicMock(return_value=response)
    monkeypatch.setattr(script.requests, "get", get)
    target = tmp_path / "archive.tar.gz"
    # When
    script.download("https://example.org/archive.tar.gz", target)
    # Then
    assert target.read_bytes() == b"abcdef"
    response.raise_for_status.assert_called_once()
    get.assert_called_once_with(
        "https://example.org/archive.tar.gz", stream=True, timeout=script.REQUEST_TIMEOUT_SECONDS
    )
