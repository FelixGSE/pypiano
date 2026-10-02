import hashlib
import importlib.util
import io
import logging
import sys
import tarfile
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "get_default_sf_file.py"
SOUND_FONT = b"fake sound font"
LICENSE = "fake license\n\n"


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("get_default_sf_file", SCRIPT)
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


@pytest.fixture
def script(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[ModuleType]:
    """The script with its paths in tmp_path and a fake archive in place of the Debian download."""
    module = load_script()
    archive = make_archive(
        tmp_path / "source.tar.gz",
        {module.SOUND_FONT_MEMBER: SOUND_FONT, module.LICENSE_MEMBER: LICENSE.encode()},
    )
    monkeypatch.setattr(module, "SOUND_FONT_PATH", tmp_path / "pypiano" / "sound_fonts" / "FluidR3_GM.sf2")
    monkeypatch.setattr(module, "LICENSE_PATH", tmp_path / "licenses" / "LICENSE-FluidR3_GM_sf2.txt")
    monkeypatch.setattr(module, "ARCHIVE_SHA256", sha256(archive))
    monkeypatch.setattr(module, "SOUND_FONT_SHA256", sha256(SOUND_FONT))
    monkeypatch.setattr(module, "download", MagicMock(side_effect=lambda _url, target: target.write_bytes(archive)))
    sys.modules["get_default_sf_file"] = module
    yield module
    del sys.modules["get_default_sf_file"]


# Existing files are never overwritten


def test_main_should_keep_sound_font_without_downloading_when_it_is_already_in_place(script: ModuleType) -> None:
    # Given the correct sound font is in place
    script.SOUND_FONT_PATH.parent.mkdir(parents=True)
    script.SOUND_FONT_PATH.write_bytes(SOUND_FONT)
    # When
    exit_code = script.main([])
    # Then
    assert exit_code == 0
    script.download.assert_not_called()
    assert script.SOUND_FONT_PATH.read_bytes() == SOUND_FONT


def test_main_should_refuse_and_leave_file_untouched_when_another_file_is_in_place(
    script: ModuleType, caplog: pytest.LogCaptureFixture
) -> None:
    # Given a Git LFS pointer instead of the sound font
    pointer = b"version https://git-lfs.github.com/spec/v1\noid sha256:74594e8f\nsize 148398306\n"
    script.SOUND_FONT_PATH.parent.mkdir(parents=True)
    script.SOUND_FONT_PATH.write_bytes(pointer)
    # When
    with caplog.at_level(logging.ERROR):
        exit_code = script.main([])
    # Then
    assert exit_code == 1
    script.download.assert_not_called()
    assert script.SOUND_FONT_PATH.read_bytes() == pointer
    assert "Not overwriting it" in caplog.text


def test_install_should_not_overwrite_sound_font_when_it_appears_during_the_download(script: ModuleType) -> None:
    # Given another file shows up at the target while downloading
    download_archive = script.download.side_effect

    def download_then_create_target(url: str, target: Path) -> None:
        download_archive(url, target)
        script.SOUND_FONT_PATH.parent.mkdir(parents=True)
        script.SOUND_FONT_PATH.write_bytes(b"someone else's file")

    script.download.side_effect = download_then_create_target
    # When / Then
    with pytest.raises(script.ExistingFileError, match="not overwriting"):
        script.install_sound_font(script.SOUND_FONT_PATH, script.LICENSE_PATH)
    assert script.SOUND_FONT_PATH.read_bytes() == b"someone else's file"
    assert not script.SOUND_FONT_PATH.with_name("FluidR3_GM.sf2.part").exists()


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


# Installing a missing sound font


def test_main_should_install_sound_font_and_license_when_both_are_missing(script: ModuleType) -> None:
    # Given neither file exists
    # When
    exit_code = script.main([])
    # Then
    assert exit_code == 0
    assert script.SOUND_FONT_PATH.read_bytes() == SOUND_FONT
    # The repository keeps the license with a single trailing newline
    assert script.LICENSE_PATH.read_text() == "fake license\n"
    assert not script.SOUND_FONT_PATH.with_name("FluidR3_GM.sf2.part").exists()


def test_install_should_raise_and_install_nothing_when_archive_checksum_differs(
    monkeypatch: pytest.MonkeyPatch, script: ModuleType
) -> None:
    # Given an archive with an unexpected checksum
    monkeypatch.setattr(script, "ARCHIVE_SHA256", sha256(b"something else"))
    # When / Then
    with pytest.raises(script.ChecksumError, match=r"fluid-soundfont\.orig\.tar\.gz has sha256"):
        script.install_sound_font(script.SOUND_FONT_PATH, script.LICENSE_PATH)
    assert not script.SOUND_FONT_PATH.exists()
    assert not script.LICENSE_PATH.exists()


def test_install_should_raise_and_leave_no_partial_file_when_sound_font_checksum_differs(
    monkeypatch: pytest.MonkeyPatch, script: ModuleType
) -> None:
    # Given a sound font with an unexpected checksum in the archive
    monkeypatch.setattr(script, "SOUND_FONT_SHA256", sha256(b"something else"))
    # When / Then
    with pytest.raises(script.ChecksumError, match=r"FluidR3_GM\.sf2\.part has sha256"):
        script.install_sound_font(script.SOUND_FONT_PATH, script.LICENSE_PATH)
    assert not script.SOUND_FONT_PATH.exists()
    assert not script.SOUND_FONT_PATH.with_name("FluidR3_GM.sf2.part").exists()


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
