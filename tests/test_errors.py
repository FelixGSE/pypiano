from collections.abc import Callable
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from mingus.containers import Note

from pypiano import errors
from pypiano.keyboard import PianoKeyboard
from pypiano.piano import Piano

OTHER_SOUND_FONTS = Path("/fantasypath/fantasyfile.sf2")


def load_other_sound_fonts_then(action: Callable[[Piano], object]) -> Callable[[Piano], object]:
    def run(piano: Piano) -> object:
        piano.load_sound_fonts(OTHER_SOUND_FONTS)
        return action(piano)

    return run


def unknown_audio_driver(piano: Piano) -> None:
    piano._current_audio_driver = "SomeFantasyDriverName"
    piano._start_audio_output()


@pytest.mark.parametrize(
    ("action", "error", "builtins"),
    [
        (lambda p: p.play(Note("G-0")), errors.InvalidNoteError, (ValueError,)),
        (lambda p: p.play(88), errors.InvalidKeyIndexError, (ValueError, IndexError)),
        (lambda p: p.play(3.5), errors.UnsupportedContainerError, (TypeError,)),
        (lambda p: p.load_instrument("FantasyInstrument"), errors.InstrumentError, (ValueError,)),
        (lambda p: p.load_instrument(1), errors.InstrumentTypeError, (TypeError,)),
        (load_other_sound_fonts_then(lambda p: p.load_instrument("Clavi")), errors.InstrumentTypeError, (TypeError,)),
        (unknown_audio_driver, errors.AudioDriverError, (ValueError,)),
    ],
    ids=[
        "note outside the keyboard",
        "key index outside 0-87",
        "unsupported container",
        "unknown instrument name",
        "instrument number with default sound font",
        "instrument name with other sound font",
        "unknown audio driver",
    ],
)
def test_piano_should_raise_pypiano_error_that_is_also_the_old_builtin_when_input_is_invalid(
    piano: Piano, action: Callable[[Piano], object], error: type[Exception], builtins: tuple[type[Exception], ...]
) -> None:
    # Given a piano
    # When / Then
    with pytest.raises(error) as raised:
        action(piano)
    assert isinstance(raised.value, errors.PyPianoError)
    for builtin in builtins:
        assert isinstance(raised.value, builtin)


def test_piano_should_raise_sound_font_error_that_is_also_a_runtime_error_when_sound_fonts_fail_to_load(
    piano: Piano, sequencer: MagicMock
) -> None:
    # Given fluidsynth fails to load the sound fonts
    sequencer.load_sound_font.return_value = False
    # When / Then
    with pytest.raises(errors.SoundFontError) as raised:
        piano.load_sound_fonts(OTHER_SOUND_FONTS)
    assert isinstance(raised.value, errors.PyPianoError)
    assert isinstance(raised.value, RuntimeError)


@pytest.mark.parametrize(
    ("key", "error", "builtins"),
    [
        (88, errors.InvalidKeyIndexError, (IndexError, ValueError)),
        (-1, errors.InvalidKeyIndexError, (IndexError, ValueError)),
        ("X-9", errors.UnknownNoteNameError, (IndexError, ValueError)),
    ],
)
def test_keyboard_should_raise_pypiano_error_that_is_also_an_index_error_when_key_does_not_exist(
    key: int | str, error: type[Exception], builtins: tuple[type[Exception], ...]
) -> None:
    # Given a keyboard
    keyboard = PianoKeyboard()
    # When / Then
    with pytest.raises(error) as raised:
        keyboard[key]
    assert isinstance(raised.value, errors.PyPianoError)
    for builtin in builtins:
        assert isinstance(raised.value, builtin)


def test_errors_should_share_invalid_note_error_when_note_is_unknown_to_keyboard() -> None:
    # Given the error for unknown note names
    # When / Then
    assert issubclass(errors.UnknownNoteNameError, errors.InvalidNoteError)
