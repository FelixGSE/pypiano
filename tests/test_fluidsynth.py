import os
from ctypes.macholib.dyld import dyld_find
from pathlib import Path

import pytest

from pypiano import _fluidsynth

FALLBACK = _fluidsynth.FALLBACK_LIBRARY_PATH


def make_homebrew_prefix(prefix: Path) -> Path:
    library_dir = prefix / "lib"
    library_dir.mkdir(parents=True)
    (library_dir / _fluidsynth.MACOS_LIBRARY_NAME).touch()
    return library_dir


@pytest.fixture
def no_homebrew(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Point the Homebrew lookup at empty directories."""
    monkeypatch.delenv("HOMEBREW_PREFIX", raising=False)
    monkeypatch.setattr(_fluidsynth, "HOMEBREW_PREFIXES", (str(tmp_path / "opt"), str(tmp_path / "usr")))


@pytest.fixture
def imports(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str | None]]:
    """Record each import of mingus' fluidsynth module together with the fallback search path at that moment."""
    calls: list[tuple[str, str | None]] = []
    monkeypatch.setattr(_fluidsynth, "import_module", lambda name: calls.append((name, os.environ.get(FALLBACK))))
    return calls


# Finding Homebrew's lib directory


@pytest.mark.usefixtures("no_homebrew")
def test_homebrew_library_dir_should_prefer_homebrew_prefix_when_it_is_set(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Given HOMEBREW_PREFIX points to a prefix with libfluidsynth
    library_dir = make_homebrew_prefix(tmp_path / "custom")
    make_homebrew_prefix(tmp_path / "opt")
    monkeypatch.setenv("HOMEBREW_PREFIX", str(tmp_path / "custom"))
    # When
    found = _fluidsynth.homebrew_library_dir()
    # Then
    assert found == library_dir


@pytest.mark.usefixtures("no_homebrew")
def test_homebrew_library_dir_should_check_default_prefixes_in_order_when_homebrew_prefix_is_unset(
    tmp_path: Path,
) -> None:
    # Given libfluidsynth only in the second default prefix (/usr/local on Intel Macs)
    library_dir = make_homebrew_prefix(tmp_path / "usr")
    # When
    found = _fluidsynth.homebrew_library_dir()
    # Then
    assert found == library_dir


@pytest.mark.usefixtures("no_homebrew")
def test_homebrew_library_dir_should_return_none_when_no_prefix_has_libfluidsynth() -> None:
    # Given no Homebrew prefix with libfluidsynth
    # When
    found = _fluidsynth.homebrew_library_dir()
    # Then
    assert found is None


# Prepending to the fallback search path


def test_fallback_path_should_keep_dyld_defaults_and_restore_unset_when_it_was_unset(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Given DYLD_FALLBACK_LIBRARY_PATH is unset
    monkeypatch.delenv(FALLBACK, raising=False)
    # When
    with _fluidsynth.prepended_fallback_library_path(tmp_path):
        during = os.environ[FALLBACK]
    # Then
    assert during.split(os.pathsep) == [str(tmp_path), *_fluidsynth.DYLD_DEFAULT_FALLBACK]
    assert FALLBACK not in os.environ


def test_fallback_path_should_keep_and_restore_existing_value_when_it_was_set(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Given DYLD_FALLBACK_LIBRARY_PATH is already set
    monkeypatch.setenv(FALLBACK, "/some/lib")
    # When
    with _fluidsynth.prepended_fallback_library_path(tmp_path):
        during = os.environ[FALLBACK]
    # Then
    assert during == os.pathsep.join([str(tmp_path), "/some/lib"])
    assert os.environ[FALLBACK] == "/some/lib"


def test_fallback_path_should_restore_environment_when_the_block_raises(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Given DYLD_FALLBACK_LIBRARY_PATH is unset
    monkeypatch.delenv(FALLBACK, raising=False)
    # When
    with pytest.raises(ImportError), _fluidsynth.prepended_fallback_library_path(tmp_path):
        raise ImportError
    # Then
    assert FALLBACK not in os.environ


def test_fallback_path_should_let_dyld_find_libfluidsynth_when_prepended(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Given libfluidsynth in a directory dyld does not search by default
    library_dir = make_homebrew_prefix(tmp_path / "opt")
    monkeypatch.delenv(FALLBACK, raising=False)
    # When the search ctypes.util.find_library uses on macOS runs inside and outside the block
    with _fluidsynth.prepended_fallback_library_path(library_dir):
        found = dyld_find(_fluidsynth.MACOS_LIBRARY_NAME)
    # Then
    assert found == str(library_dir / _fluidsynth.MACOS_LIBRARY_NAME)
    with pytest.raises(ValueError, match="could not be found"):
        dyld_find(_fluidsynth.MACOS_LIBRARY_NAME)


# Loading mingus' fluidsynth module


def test_load_should_import_with_homebrew_lib_dir_when_macos_cannot_find_libfluidsynth(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, imports: list[tuple[str, str | None]]
) -> None:
    # Given macOS where find_library misses Homebrew's libfluidsynth
    library_dir = make_homebrew_prefix(tmp_path / "opt")
    monkeypatch.setattr(_fluidsynth.sys, "platform", "darwin")
    monkeypatch.setattr(_fluidsynth, "find_library", lambda _name: None)
    monkeypatch.setattr(_fluidsynth, "homebrew_library_dir", lambda: library_dir)
    monkeypatch.delenv(FALLBACK, raising=False)
    # When
    _fluidsynth.load_mingus_fluidsynth()
    # Then
    ((module, fallback_during_import),) = imports
    assert module == _fluidsynth.MINGUS_FLUIDSYNTH_MODULE
    assert fallback_during_import is not None
    assert fallback_during_import.split(os.pathsep)[0] == str(library_dir)
    assert FALLBACK not in os.environ


@pytest.mark.parametrize(
    ("platform", "found_library"),
    [("darwin", "/usr/local/lib/libfluidsynth.dylib"), ("linux", None), ("linux", "libfluidsynth.so.3")],
    ids=["macos with library on default path", "linux without library", "linux with library"],
)
def test_load_should_import_without_changing_search_path_when_no_homebrew_lookup_is_needed(
    monkeypatch: pytest.MonkeyPatch, imports: list[tuple[str, str | None]], platform: str, found_library: str | None
) -> None:
    # Given a platform where mingus' own lookup applies
    monkeypatch.setattr(_fluidsynth.sys, "platform", platform)
    monkeypatch.setattr(_fluidsynth, "find_library", lambda _name: found_library)
    monkeypatch.delenv(FALLBACK, raising=False)
    # When
    _fluidsynth.load_mingus_fluidsynth()
    # Then
    assert imports == [(_fluidsynth.MINGUS_FLUIDSYNTH_MODULE, None)]


@pytest.mark.parametrize(
    ("platform", "hint"),
    [("darwin", "brew install fluid-synth"), ("linux", "apt install libfluidsynth3"), ("win32", "fluidsynth.org")],
)
@pytest.mark.usefixtures("no_homebrew")
def test_load_should_raise_import_error_with_install_hint_when_libfluidsynth_is_missing(
    monkeypatch: pytest.MonkeyPatch, platform: str, hint: str
) -> None:
    # Given mingus cannot find libfluidsynth
    def missing_library(_name: str) -> None:
        msg = "Couldn't find the FluidSynth library."
        raise ImportError(msg)

    monkeypatch.setattr(_fluidsynth.sys, "platform", platform)
    monkeypatch.setattr(_fluidsynth, "find_library", lambda _name: None)
    monkeypatch.setattr(_fluidsynth, "import_module", missing_library)
    # When / Then
    with pytest.raises(ImportError, match=f"could not be found.*{hint}") as error:
        _fluidsynth.load_mingus_fluidsynth()
    assert isinstance(error.value.__cause__, ImportError)
