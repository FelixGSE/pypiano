from importlib.metadata import version

import pytest

import pypiano


def test_package_should_expose_installed_version_when_imported() -> None:
    # Given the installed distribution
    # When
    package_version = pypiano.__version__
    # Then
    assert package_version == version("pypiano")


def test_package_should_export_exactly_the_public_api_when_imported() -> None:
    # Given the names PyPiano documents as its public API; a change here is a change of the API
    public_api = {
        "AudioDriver",
        "AudioDriverError",
        "DEFAULT_SOUND_FONTS",
        "Instrument",
        "InstrumentError",
        "InstrumentTypeError",
        "InvalidKeyIndexError",
        "InvalidNoteError",
        "KeyColor",
        "NoteIdentity",
        "Piano",
        "PianoClosedError",
        "PianoKey",
        "PianoKeyboard",
        "PlaybackOptionError",
        "PyPianoError",
        "SoundFontError",
        "UnknownNoteNameError",
        "UnparsableNoteError",
        "UnsupportedContainerError",
        "__version__",
    }
    # When / Then every name is listed once
    assert sorted(pypiano.__all__) == sorted(public_api)


@pytest.mark.parametrize("name", pypiano.__all__)
def test_package_should_provide_every_exported_name_when_imported(name: str) -> None:
    # Given a name listed in __all__
    # When / Then
    assert hasattr(pypiano, name)


def test_package_should_ship_py_typed_marker_when_installed() -> None:
    # Given the installed package
    # When / Then
    assert (pypiano.DEFAULT_SOUND_FONTS.parents[1] / "py.typed").is_file()
