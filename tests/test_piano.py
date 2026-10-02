from pathlib import Path
from typing import TypeAlias
from unittest.mock import MagicMock

import pytest
from mingus.containers import Bar, Note, NoteContainer, Track

from pypiano import piano as piano_module
from pypiano.keyboard import PianoKey
from pypiano.piano import DEFAULT_SOUND_FONTS, Piano

OTHER_SOUND_FONTS = Path("/fantasypath/fantasyfile.sf2")

MusicContainer: TypeAlias = str | Note | NoteContainer | Bar | Track


def make_bar(*notes: str) -> Bar:
    bar = Bar()
    for note in notes:
        bar.place_notes(note, 4)
    return bar


# Sound fonts


def test_piano_should_load_default_sound_fonts_when_created(piano: Piano, sequencer: MagicMock) -> None:
    # Given a piano created without arguments
    # When / Then
    sequencer.load_sound_font.assert_called_once_with(str(DEFAULT_SOUND_FONTS))
    assert piano._sound_fonts_loaded
    assert piano._sound_fonts_path == DEFAULT_SOUND_FONTS


def test_piano_should_unload_current_sound_fonts_when_loading_new_ones(piano: Piano, sequencer: MagicMock) -> None:
    # Given a piano with the default sound fonts loaded
    # When
    piano.load_sound_fonts(OTHER_SOUND_FONTS)
    # Then
    sequencer.fs.sfunload.assert_called_once_with(sequencer.sfid)
    sequencer.load_sound_font.assert_called_with(str(OTHER_SOUND_FONTS))
    assert piano._sound_fonts_loaded
    assert piano._sound_fonts_path == OTHER_SOUND_FONTS


def test_piano_should_raise_runtime_error_when_sound_fonts_cannot_be_loaded(piano: Piano, sequencer: MagicMock) -> None:
    # Given fluidsynth fails to load the sound fonts
    sequencer.load_sound_font.return_value = False
    # When / Then
    with pytest.raises(RuntimeError, match="Could not load sound fonts"):
        piano.load_sound_fonts(OTHER_SOUND_FONTS)


def test_piano_should_forget_sound_fonts_when_unloaded(piano: Piano, sequencer: MagicMock) -> None:
    # Given a piano with the default sound fonts loaded
    # When
    piano._unload_sound_fonts()
    # Then
    sequencer.fs.sfunload.assert_called_once()
    assert not piano._sound_fonts_loaded
    assert piano._sound_fonts_path is None


def test_piano_should_do_nothing_when_unloading_without_loaded_sound_fonts(piano: Piano, sequencer: MagicMock) -> None:
    # Given a piano whose sound fonts are already unloaded
    piano._unload_sound_fonts()
    sequencer.fs.sfunload.reset_mock()
    # When
    piano._unload_sound_fonts()
    # Then
    sequencer.fs.sfunload.assert_not_called()


# Audio output


def test_piano_should_start_audio_output_once_when_started_repeatedly(piano: Piano, sequencer: MagicMock) -> None:
    # Given a piano without active audio output
    assert not piano._audio_driver_is_active
    # When
    piano._start_audio_output()
    piano._start_audio_output()
    # Then
    sequencer.start_audio_output.assert_called_once_with(None)
    assert piano._audio_driver_is_active


def test_piano_should_raise_value_error_when_audio_driver_is_unknown(piano: Piano) -> None:
    # Given a piano configured with an unknown audio driver
    piano._current_audio_driver = "SomeFantasyDriverName"
    # When / Then
    with pytest.raises(ValueError, match="is not a valid audio driver"):
        piano._start_audio_output()


def test_piano_should_delete_audio_driver_when_stopping_active_output(
    piano: Piano, delete_audio_driver: MagicMock
) -> None:
    # Given a piano with active audio output
    piano._start_audio_output()
    # When
    piano._stop_audio_output()
    # Then
    delete_audio_driver.assert_called_once()
    assert not piano._audio_driver_is_active


def test_piano_should_not_delete_audio_driver_when_output_is_already_inactive(
    piano: Piano, delete_audio_driver: MagicMock
) -> None:
    # Given a piano without active audio output
    # When
    piano._stop_audio_output()
    # Then
    delete_audio_driver.assert_not_called()
    assert not piano._audio_driver_is_active


# Instruments


def test_piano_should_set_default_instrument_when_created(piano: Piano, sequencer: MagicMock) -> None:
    # Given a piano created without arguments
    # When / Then
    sequencer.set_instrument.assert_called_once_with(channel=1, instr=0, bank=0)
    assert piano.instrument == "Acoustic Grand Piano"


def test_piano_should_set_instrument_when_name_is_known(piano: Piano, sequencer: MagicMock) -> None:
    # Given a piano with the default sound fonts
    # When
    piano.load_instrument("Honky-tonk Piano")
    # Then
    sequencer.set_instrument.assert_called_with(channel=1, instr=3, bank=0)
    assert piano.instrument == "Honky-tonk Piano"


def test_piano_should_raise_value_error_when_instrument_name_is_unknown(piano: Piano) -> None:
    # Given a piano with the default sound fonts
    # When / Then
    with pytest.raises(ValueError, match="Unknown instrument parameter"):
        piano.load_instrument("FantasyInstrument")


def test_piano_should_raise_type_error_when_default_sound_fonts_get_instrument_number(piano: Piano) -> None:
    # Given a piano with the default sound fonts
    # When / Then
    with pytest.raises(TypeError, match="must pass a string"):
        piano.load_instrument(1)


def test_piano_should_set_instrument_number_when_other_sound_fonts_are_loaded(
    piano: Piano, sequencer: MagicMock
) -> None:
    # Given a piano with other sound fonts
    piano.load_sound_fonts(OTHER_SOUND_FONTS)
    # When
    piano.load_instrument(5)
    # Then
    sequencer.set_instrument.assert_called_with(channel=1, instr=5, bank=0)
    assert piano.instrument == 5


def test_piano_should_raise_type_error_when_other_sound_fonts_get_instrument_name(piano: Piano) -> None:
    # Given a piano with other sound fonts
    piano.load_sound_fonts(OTHER_SOUND_FONTS)
    # When / Then
    with pytest.raises(TypeError, match="must pass an integer"):
        piano.load_instrument("Bright Acoustic Piano")


# Playing and recording


@pytest.mark.parametrize(
    ("music_container", "play_method"),
    [
        ("C-4", "play_Note"),
        (Note("C-4"), "play_Note"),
        (NoteContainer(["C-4", "E-4", "G-4"]), "play_NoteContainer"),
        (make_bar("C-4", "E-4", "G-4", "C-5"), "play_Bar"),
        (Track().add_bar(make_bar("C-4", "E-4", "G-4", "C-5")), "play_Track"),
    ],
    ids=["note string", "note", "note container", "bar", "track"],
)
def test_piano_should_play_container_via_audio_when_no_recording_file_is_given(
    piano: Piano, sequencer: MagicMock, music_container: MusicContainer, play_method: str
) -> None:
    # Given a piano and a valid music container
    # When
    piano.play(music_container)
    # Then
    assert piano._audio_driver_is_active
    getattr(sequencer, play_method).assert_called_once()


@pytest.mark.parametrize(
    ("music_container", "expected_note"),
    [(39, "C-4"), (0, "A-0"), (87, "C-8"), (PianoKey("C", "B#", 4, "white", second_octave=3), "C-4")],
    ids=["key index C-4", "first key index", "last key index", "piano key"],
)
def test_piano_should_play_first_identity_when_given_key_index_or_piano_key(
    piano: Piano, sequencer: MagicMock, music_container: int | PianoKey, expected_note: str
) -> None:
    # Given a piano
    # When
    piano.play(music_container)
    # Then
    (played,), _ = sequencer.play_Note.call_args
    assert f"{played.name}-{played.octave}" == expected_note


@pytest.mark.parametrize("key_index", [-1, 88])
def test_piano_should_raise_value_error_when_key_index_is_out_of_range(
    piano: Piano, sequencer: MagicMock, key_index: int
) -> None:
    # Given a piano
    # When / Then
    with pytest.raises(ValueError, match="Key index must be between 0 and 87"):
        piano.play(key_index)
    sequencer.play_Note.assert_not_called()


def test_piano_should_raise_value_error_when_piano_key_is_not_on_the_keyboard(
    piano: Piano, sequencer: MagicMock
) -> None:
    # Given a key above C-8
    key = PianoKey("D", "D", 8, "white")
    # When / Then
    with pytest.raises(ValueError, match="not on a piano with 88 keys"):
        piano.play(key)
    sequencer.play_Note.assert_not_called()


def test_piano_should_write_wav_file_when_recording_file_is_given(piano: Piano, sequencer: MagicMock) -> None:
    # Given a piano with active audio output
    piano._start_audio_output()
    wav = sequencer.wav
    # When
    piano.play("C-4", recording_file="test.wav", record_seconds=2)
    # Then
    assert not piano._audio_driver_is_active
    sequencer.start_recording.assert_called_once_with("test.wav")
    sequencer.fs.get_samples.assert_called_once_with(2 * piano_module.WAV_SAMPLE_FREQUENCY)
    wav.writeframes.assert_called_once()
    wav.close.assert_called_once()
    # The wav attribute is removed so mingus' sleep does not write to a closed file
    assert not hasattr(sequencer, "wav")


@pytest.mark.parametrize(
    "music_container",
    [
        Note("G-0"),
        Note("D-8"),
        NoteContainer([Note("G-0"), Note("C-4")]),
        make_bar("C-4", "D-8"),
        Track().add_bar(make_bar("G-0")),
    ],
    ids=["note below A-0", "note above C-8", "note container", "bar", "track"],
)
def test_piano_should_raise_value_error_when_container_has_notes_outside_the_keyboard(
    piano: Piano, sequencer: MagicMock, music_container: MusicContainer
) -> None:
    # Given a music container with a note that is not on an 88 key piano
    # When / Then
    with pytest.raises(ValueError, match="not on a piano with 88 keys"):
        piano.play(music_container)
    sequencer.play_Note.assert_not_called()


def test_piano_should_raise_type_error_when_container_type_is_unsupported(piano: Piano) -> None:
    # Given an object that is not a music container
    # When / Then
    with pytest.raises(TypeError, match="Unsupported music container type"):
        piano._lint_music_container(3.5)  # ty: ignore[invalid-argument-type] - the wrong type is the point


def test_piano_should_sleep_when_paused(monkeypatch: pytest.MonkeyPatch) -> None:
    # Given time.sleep is replaced
    sleep = MagicMock()
    monkeypatch.setattr(piano_module.time, "sleep", sleep)
    # When
    Piano.pause(2)
    # Then
    sleep.assert_called_once_with(2)
