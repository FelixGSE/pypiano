import errno
import math
import os
import re
import wave
from pathlib import Path
from typing import TypeAlias
from unittest.mock import MagicMock, call

import numpy as np
import pytest
from mingus.containers import Bar, Note, NoteContainer, Track
from mingus.containers.mt_exceptions import NoteFormatError

from pypiano import errors
from pypiano import piano as piano_module
from pypiano.keyboard import PianoKey
from pypiano.piano import DEFAULT_SOUND_FONTS, Instrument, Piano

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
    sequencer.fs.sfload.assert_called_once_with(str(DEFAULT_SOUND_FONTS))
    sequencer.fs.sfunload.assert_not_called()
    assert sequencer.sfid == 1
    assert piano._sound_fonts_loaded
    assert piano._sound_fonts_path == DEFAULT_SOUND_FONTS


def test_piano_should_make_the_drum_channel_a_normal_one_when_created(sequencer: MagicMock) -> None:
    # Given the drum channel, which FluidSynth gives a drum bank the bundled piano sound font lacks
    # When
    Piano(sequencer=sequencer)
    # Then channel 9 (MIDI channel 10) is melodic, on bank 0
    sequencer.fs.set_channel_type.assert_called_once_with(9, 0)
    sequencer.fs.bank_select.assert_called_once_with(9, 0)


def test_piano_should_unload_current_sound_fonts_after_loading_new_ones(piano: Piano, sequencer: MagicMock) -> None:
    # Given a piano with the default sound fonts loaded as id 1, and the next sound fonts getting id 2
    sequencer.fs.sfload.return_value = 2
    sequencer.reset_mock()
    # When
    piano.load_sound_fonts(OTHER_SOUND_FONTS)
    # Then the old sound fonts are unloaded only once the new ones are loaded
    assert sequencer.fs.mock_calls[:2] == [call.sfload(str(OTHER_SOUND_FONTS)), call.sfunload(1)]
    assert sequencer.sfid == 2
    assert piano._sound_fonts_loaded
    assert piano._sound_fonts_path == OTHER_SOUND_FONTS


def test_piano_should_keep_sound_fonts_and_instrument_when_new_ones_cannot_be_loaded(
    piano: Piano, sequencer: MagicMock
) -> None:
    # Given a piano playing the Clavi of the default sound fonts, and sound fonts FluidSynth fails to load
    piano.load_instrument("Clavi")
    sequencer.fs.sfload.return_value = -1
    sequencer.reset_mock()
    # When / Then
    with pytest.raises(RuntimeError, match=r"^Could not load sound fonts from /fantasypath/fantasyfile\.sf2$"):
        piano.load_sound_fonts(OTHER_SOUND_FONTS)
    sequencer.fs.sfunload.assert_not_called()
    sequencer.set_instrument.assert_not_called()
    assert sequencer.sfid == 1
    assert piano._sound_fonts_path == DEFAULT_SOUND_FONTS
    assert piano._uses_default_sound_fonts
    assert piano.instrument == "Clavi"


@pytest.mark.parametrize(
    ("before", "new_sound_fonts", "expected"),
    [
        ((DEFAULT_SOUND_FONTS, "Clavi"), DEFAULT_SOUND_FONTS, ("Clavi", 7)),
        ((OTHER_SOUND_FONTS, 5), OTHER_SOUND_FONTS, (5, 5)),
        ((DEFAULT_SOUND_FONTS, "Clavi"), OTHER_SOUND_FONTS, ("Clavi", 7)),
        ((OTHER_SOUND_FONTS, 5), DEFAULT_SOUND_FONTS, ("Acoustic Grand Piano", 0)),
    ],
    ids=[
        "default name kept by default sound fonts",
        "number kept by other sound fonts",
        "instrument kept by other sound fonts as its program",
        "number falls back to Acoustic Grand Piano with default sound fonts",
    ],
)
def test_piano_should_select_an_instrument_of_the_new_sound_fonts_when_loading_them(
    piano: Piano,
    sequencer: MagicMock,
    before: tuple[Path, str | int],
    new_sound_fonts: Path,
    expected: tuple[str | int, int],
) -> None:
    # Given a piano playing an instrument of the default or of other sound fonts
    sound_fonts, instrument = before
    piano.load_sound_fonts(sound_fonts)
    piano.load_instrument(instrument)
    sequencer.set_instrument.reset_mock()
    # When
    piano.load_sound_fonts(new_sound_fonts)
    # Then the channel plays an instrument of the new sound fonts: the same one if they take it, else program 0
    expected_instrument, expected_program = expected
    sequencer.set_instrument.assert_called_once_with(channel=1, instr=expected_program, bank=0)
    assert piano.instrument == expected_instrument


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
    sequencer.fs.program_reset.assert_called_once_with()
    assert piano._audio_driver_is_active


@pytest.mark.parametrize(("driver", "shown_as"), [(None, "default"), ("pipewire", "pipewire")])
def test_piano_should_warn_and_try_again_when_fluidsynth_cannot_start_the_audio_driver(
    piano: Piano, sequencer: MagicMock, caplog: pytest.LogCaptureFixture, driver: str | None, shown_as: str
) -> None:
    # Given FluidSynth fails to create the audio driver, e.g. without a sound device, which leaves no driver handle
    piano._current_audio_driver = driver  # ty: ignore[invalid-assignment] - any configured driver
    sequencer.fs.audio_driver = None
    # When
    piano._start_audio_output()
    piano._start_audio_output()
    # Then each start tries again and warns, and the output never counts as active
    assert sequencer.start_audio_output.call_args_list == [call(driver), call(driver)]
    sequencer.fs.program_reset.assert_not_called()
    assert not piano._audio_driver_is_active
    assert [(record.levelname, record.getMessage()) for record in caplog.records] == [
        (
            "WARNING",
            f"FluidSynth could not start the {shown_as} audio driver, so nothing is heard. The next play tries again",
        )
    ] * 2


def test_piano_should_raise_value_error_listing_fluidsynths_drivers_when_audio_driver_is_unknown(
    piano: Piano, sequencer: MagicMock
) -> None:
    # Given a piano configured with an audio driver this FluidSynth doesn't have
    piano._current_audio_driver = "SomeFantasyDriverName"  # ty: ignore[invalid-assignment] - unknown on purpose
    # When / Then
    with pytest.raises(
        ValueError,
        match=re.escape(
            "FluidSynth has no audio driver 'SomeFantasyDriverName'. This FluidSynth has: alsa, file, pipewire"
        ),
    ):
        piano._start_audio_output()
    sequencer.start_audio_output.assert_not_called()


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
    assert piano.instrument is Instrument.ACOUSTIC_GRAND_PIANO
    assert piano.instrument == "Acoustic Grand Piano"


def test_piano_should_raise_attribute_error_when_the_instrument_is_assigned(piano: Piano, sequencer: MagicMock) -> None:
    # Given a piano playing the Acoustic Grand Piano
    # When / Then the instrument can only change through load_instrument, which also selects it in FluidSynth
    with pytest.raises(AttributeError):
        piano.instrument = Instrument.CLAVI  # ty: ignore[invalid-assignment] - read-only on purpose
    assert piano.instrument is Instrument.ACOUSTIC_GRAND_PIANO
    sequencer.set_instrument.assert_called_once_with(channel=1, instr=0, bank=0)


@pytest.mark.parametrize(
    ("instrument", "program"),
    [
        (Instrument.ACOUSTIC_GRAND_PIANO, 0),
        (Instrument.BRIGHT_ACOUSTIC_PIANO, 1),
        (Instrument.ELECTRIC_GRAND_PIANO, 2),
        (Instrument.HONKY_TONK_PIANO, 3),
        (Instrument.ELECTRIC_PIANO_1, 4),
        (Instrument.ELECTRIC_PIANO_2, 5),
        (Instrument.HARPSICHORD, 6),
        (Instrument.CLAVI, 7),
    ],
)
def test_instrument_should_have_its_general_midi_program_number(instrument: Instrument, program: int) -> None:
    # Given a General MIDI piano
    # When / Then
    assert instrument.program == program


@pytest.mark.parametrize("instrument", [Instrument.HONKY_TONK_PIANO, "Honky-tonk Piano"], ids=["enum", "name"])
def test_piano_should_set_instrument_when_given_an_instrument_or_its_name(
    piano: Piano, sequencer: MagicMock, instrument: Instrument | str
) -> None:
    # Given a piano with the default sound fonts
    # When
    piano.load_instrument(instrument)
    # Then
    sequencer.set_instrument.assert_called_with(channel=1, instr=3, bank=0)
    assert piano.instrument is Instrument.HONKY_TONK_PIANO


@pytest.mark.parametrize("instrument", [Instrument.ELECTRIC_PIANO_2, "Electric Piano 2"], ids=["enum", "name"])
def test_piano_should_set_the_program_number_when_other_sound_fonts_get_an_instrument_or_its_name(
    piano: Piano, sequencer: MagicMock, instrument: Instrument | str
) -> None:
    # Given a piano with other sound fonts, which take General MIDI program numbers
    piano.load_sound_fonts(OTHER_SOUND_FONTS)
    # When
    piano.load_instrument(instrument)
    # Then
    sequencer.set_instrument.assert_called_with(channel=1, instr=5, bank=0)
    assert piano.instrument is Instrument.ELECTRIC_PIANO_2


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
    with pytest.raises(
        ValueError,
        match=r"^Unknown instrument 'FantasyInstrument'\. Instrument must be one of: Acoustic Grand Piano, "
        r"Bright Acoustic Piano, Electric Grand Piano, Honky-tonk Piano, Electric Piano 1, Electric Piano 2, "
        r"Harpsichord, Clavi$",
    ):
        piano.load_instrument("FantasyInstrument")


def test_piano_should_raise_type_error_when_default_sound_fonts_get_instrument_number(piano: Piano) -> None:
    # Given a piano with the default sound fonts
    # When / Then
    with pytest.raises(
        TypeError, match=r"^The default sound fonts take an Instrument or its name, not a program number$"
    ):
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


def test_piano_should_raise_type_error_when_other_sound_fonts_get_an_unknown_instrument_name(
    piano: Piano, sequencer: MagicMock
) -> None:
    # Given a piano with other sound fonts and its instrument
    piano.load_sound_fonts(OTHER_SOUND_FONTS)
    instrument = piano.instrument
    sequencer.set_instrument.reset_mock()
    # When / Then
    with pytest.raises(
        TypeError,
        match=r"^Unknown instrument 'FantasyInstrument'\. Other sound fonts take a program number or an Instrument$",
    ):
        piano.load_instrument("FantasyInstrument")
    assert piano.instrument is instrument
    sequencer.set_instrument.assert_not_called()


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
def test_piano_should_play_container_via_audio_when_played(
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


def test_piano_should_play_octave_4_when_note_string_has_no_octave(piano: Piano, sequencer: MagicMock) -> None:
    # Given a note name without an octave, which mingus puts in octave 4
    # When
    piano.play("C")
    # Then
    (played,), _ = sequencer.play_Note.call_args
    assert (played.name, played.octave) == ("C", 4)


@pytest.mark.parametrize(
    ("note_string", "mingus_error"),
    [
        ("H-4", NoteFormatError),
        ("c-4", NoteFormatError),
        (" C-4", NoteFormatError),
        ("C-4-1", NoteFormatError),
        ("C-x", ValueError),
        ("C-", ValueError),
        ("", IndexError),
    ],
    ids=["unknown letter", "lowercase", "leading space", "two dashes", "octave not a number", "no octave", "empty"],
)
def test_piano_should_raise_unparsable_note_error_when_note_string_is_not_a_note(
    piano: Piano, sequencer: MagicMock, note_string: str, mingus_error: type[Exception]
) -> None:
    # Given a string mingus cannot parse into a note, which it rejects with one of three errors
    # When / Then
    with pytest.raises(
        errors.UnparsableNoteError,
        match=re.escape(f"Not a note name with an optional octave, such as 'C#-4' or 'Bb-2': {note_string!r}"),
    ) as raised:
        piano.play(note_string)
    # It is an InvalidNoteError, and still mingus' NoteFormatError, which play() let through before
    assert isinstance(raised.value, errors.InvalidNoteError)
    assert isinstance(raised.value, NoteFormatError)
    assert isinstance(raised.value.__cause__, mingus_error)
    sequencer.play_Note.assert_not_called()


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


# The sample value of the music the fake FluidSynth below renders
MUSIC = 7


def frames(value: int, count: int) -> bytes:
    """count stereo frames of 16-bit samples, all of value."""
    return np.full(2 * count, value, dtype=np.int16).tobytes()


def render_like_fluidsynth(sequencer: MagicMock, chunks: list[int] | None = None) -> None:
    """Make the mocked sequencer render like FluidSynth while recording.

    get_samples renders MUSIC, except 10 ms chunks (441 frames), which take their values from chunks in order, starting
    with the one rendered before the recording, and are silent once chunks runs out. sleep renders its time into the
    sequencer's wav, as mingus' sleep does while recording.
    """
    values = iter(chunks or [])

    def get_samples(count: int) -> np.ndarray:
        return np.full(2 * count, next(values, 0) if count == 441 else MUSIC, dtype=np.int16)

    def sleep(seconds: float) -> None:
        sequencer.wav.writeframes(np.asarray(sequencer.fs.get_samples(int(seconds * 44100))).tobytes())

    sequencer.fs.get_samples.side_effect = get_samples
    sequencer.sleep.side_effect = sleep


def read_wav(path: Path) -> tuple[tuple[int, int, int], bytes]:
    """Return a wav file's channels, sample width and frame rate, and its frames."""
    with wave.open(str(path)) as wav:
        return (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()), wav.readframes(wav.getnframes())


def test_piano_should_record_the_music_and_its_fade_between_silences_when_no_length_is_given(
    piano: Piano, sequencer: MagicMock, tmp_path: Path
) -> None:
    # Given a piano with active audio output, and FluidSynth falling silent right after the music
    piano._start_audio_output()
    render_like_fluidsynth(sequencer)
    path = tmp_path / "c4.wav"
    # When
    piano.record("C-4", path)
    # Then the file holds the second the note sounds and the 10 ms in which it fell silent, as 16-bit stereo
    assert read_wav(path) == ((2, 2, 44100), frames(MUSIC, 44100) + frames(0, 441))
    # All sound stops (and fades) before the recording starts and after it ends, so no note carries over
    (played,), _ = sequencer.play_Note.call_args
    steps = {"fs.cc", "fs.get_samples", "play_Note", "sleep", "stop_Note"}
    assert [step for step in sequencer.mock_calls if step[0] in steps] == [
        call.fs.cc(1, 120, 0),
        call.fs.get_samples(441),
        call.play_Note(played),
        call.sleep(1.0),
        call.fs.get_samples(44100),
        call.stop_Note(played),
        call.fs.cc(1, 123, 0),
        call.fs.get_samples(441),
        call.fs.cc(1, 120, 0),
        call.fs.get_samples(441),
    ]
    assert not piano._audio_driver_is_active
    # The wav attribute is removed, so mingus' sleep waits in real time again
    assert not hasattr(sequencer, "wav")
    assert list(tmp_path.iterdir()) == [path]


def test_piano_should_record_the_fade_up_to_the_first_silent_chunk_when_no_length_is_given(
    piano: Piano, sequencer: MagicMock, tmp_path: Path
) -> None:
    # Given FluidSynth fades out over three 10 ms chunks after the music, down to the dither's 1
    render_like_fluidsynth(sequencer, [0, 900, 30, 1])
    path = tmp_path / "c4.wav"
    # When
    piano.record("C-4", path, duration=0.5)
    # Then the fade is recorded up to and including the first silent chunk
    assert read_wav(path)[1] == frames(MUSIC, 22050) + frames(900, 441) + frames(30, 441) + frames(1, 441)


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        (1, ([], 44100)),
        (0.5, ([], 22050)),
        (1.15, ([call(6615)], 50715)),
        (2.5, ([call(44100), call(22050)], 110250)),
    ],
    ids=["as long as the music", "shorter: cut", "rounded to a frame", "longer: filled a second at a time"],
)
def test_piano_should_record_exactly_the_given_length_when_seconds_is_given(
    piano: Piano, sequencer: MagicMock, tmp_path: Path, seconds: float, expected: tuple[list[object], int]
) -> None:
    # Given a note that sounds for one second
    render_like_fluidsynth(sequencer)
    path = tmp_path / "c4.wav"
    fill, length = expected
    # When
    piano.record("C-4", path, seconds=seconds)
    # Then the file has round(seconds * 44100) frames, and only what was missing was rendered
    assert read_wav(path)[1] == frames(MUSIC, length)
    assert sequencer.fs.get_samples.call_args_list == [call(441), call(44100), *fill, call(441)]


@pytest.mark.parametrize("path_type", [str, Path], ids=["str", "pathlib.Path"])
def test_piano_should_write_the_recording_when_the_path_is_a_str_or_a_path(
    piano: Piano, tmp_path: Path, path_type: type
) -> None:
    # Given a path to record to, as a str or a pathlib.Path
    path = tmp_path / "c4.wav"
    # When
    piano.record("C-4", path_type(path), seconds=0.5)
    # Then
    assert read_wav(path)[0] == (2, 2, 44100)


def test_piano_should_keep_the_file_and_leave_nothing_behind_when_recording_fails(
    piano: Piano, sequencer: MagicMock, tmp_path: Path
) -> None:
    # Given an existing file, and mingus raising while it plays
    path = tmp_path / "c4.wav"
    path.write_bytes(b"an earlier recording")
    sequencer.play_Bar.side_effect = ZeroDivisionError
    # When / Then
    with pytest.raises(ZeroDivisionError):
        piano.record(make_bar("C-4"), path)
    assert path.read_bytes() == b"an earlier recording"
    assert list(tmp_path.iterdir()) == [path]
    assert not hasattr(sequencer, "wav")
    # The notes are released after the failed play, and the sound stops after the failed recording too
    assert sequencer.fs.cc.call_args_list == [call(1, 120, 0), call(1, 123, 0), call(1, 120, 0)]


def test_piano_should_raise_type_error_before_rendering_when_the_path_is_not_a_path(
    piano: Piano, sequencer: MagicMock
) -> None:
    # Given no path
    # When / Then it fails before anything is played or rendered
    with pytest.raises(TypeError):
        piano.record("C-4", None)  # ty: ignore[invalid-argument-type] - None is the point
    sequencer.play_Note.assert_not_called()
    sequencer.fs.get_samples.assert_not_called()


@pytest.mark.parametrize(
    "case",
    [
        ("missing/c4.wav", FileNotFoundError, errno.ENOENT, "missing"),
        (".", IsADirectoryError, errno.EISDIR, "."),
    ],
    ids=["missing directory", "a directory"],
)
def test_piano_should_check_the_path_before_rendering_when_recording(
    piano: Piano,
    sequencer: MagicMock,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case: tuple[str, type[OSError], int, str],
) -> None:
    # Given a path that cannot be written, relative to an empty directory
    path, error, code, filename = case
    monkeypatch.chdir(tmp_path)
    # When / Then it fails like opening the file would, before anything is played or rendered, and writes nothing
    with pytest.raises(error) as raised:
        piano.record("C-4", path)
    assert (raised.value.errno, raised.value.strerror, raised.value.filename) == (code, os.strerror(code), filename)
    sequencer.play_Note.assert_not_called()
    sequencer.fs.get_samples.assert_not_called()
    assert list(tmp_path.iterdir()) == []


def test_wav_buffer_should_keep_exactly_its_length_when_more_frames_are_written() -> None:
    # Given a buffer of three frames
    buffer = piano_module._WavBuffer(3)
    # When two writes of two frames each are written, the second one beyond its length
    buffer.writeframes(frames(1, 2))
    buffer.writeframes(frames(2, 2))
    # Then the second write is cut at the length, and nothing is missing
    assert buffer.frames == frames(1, 2) + frames(2, 1)
    assert buffer.missing_frames == 0


@pytest.mark.parametrize("bpm", [0, -60, math.nan, math.inf])
@pytest.mark.parametrize("in_track", [False, True], ids=["bar", "track"])
def test_piano_should_raise_playback_option_error_when_a_bpm_set_in_a_bar_is_invalid(
    piano: Piano, sequencer: MagicMock, bpm: float, *, in_track: bool
) -> None:
    # Given a bar whose second NoteContainer changes the tempo to an invalid one, which mingus would fail on
    bar = make_bar("C-4", "E-4")
    bar.bar[1][2].bpm = bpm
    container = Track().add_bar(bar) if in_track else bar
    # When / Then
    with pytest.raises(
        errors.PlaybackOptionError,
        match=rf"^bpm of a NoteContainer in a Bar must be a positive finite number\. Got {re.escape(str(bpm))}$",
    ):
        piano.play(container)
    sequencer.play_Bar.assert_not_called()
    sequencer.play_Track.assert_not_called()


@pytest.mark.parametrize("bpm", [0.5, 90])
def test_piano_should_play_a_bar_when_a_note_container_in_it_sets_a_valid_bpm(
    piano: Piano, sequencer: MagicMock, bpm: float
) -> None:
    # Given a bar whose second NoteContainer changes the tempo, also to a slow one below 1 bpm
    bar = make_bar("C-4", "E-4")
    bar.bar[1][2].bpm = bpm
    # When
    piano.play(bar)
    # Then
    sequencer.play_Bar.assert_called_once_with(bar, bpm=120)


def test_piano_should_render_until_silent_when_stopping_sounds(piano: Piano, sequencer: MagicMock) -> None:
    # Given FluidSynth fades out: the stopped voices first (down to the int16 minimum), then the reverb tail, down to
    # the dither's -1 to 1
    chunks = [[0, -32768], [1105, -1105], [-88, 88], [2, -2], [1, -1], [0, 0]]
    sequencer.fs.get_samples.side_effect = [np.array(chunk, dtype=np.int16) for chunk in chunks]
    # When
    piano._stop_sounds()
    # Then every voice is stopped at once (All Sound Off), and FluidSynth renders 10 ms at a time until it is silent
    sequencer.fs.cc.assert_called_once_with(1, 120, 0)
    assert sequencer.fs.get_samples.call_args_list == [call(441)] * 5


def test_piano_should_stop_rendering_after_five_seconds_when_never_silent(piano: Piano, sequencer: MagicMock) -> None:
    # Given FluidSynth never falls silent
    sequencer.fs.get_samples.return_value = np.array([1000, -1000], dtype=np.int16)
    # When
    piano._stop_sounds()
    # Then it renders 5 seconds in chunks of 10 ms, and no more
    assert sequencer.fs.get_samples.call_args_list == [call(441)] * 500


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
    with pytest.raises(TypeError, match=r"^Unsupported music container type: <class 'float'>$"):
        piano.play(3.5)  # ty: ignore[invalid-argument-type] - the wrong type is the point


def test_piano_should_sleep_when_paused(monkeypatch: pytest.MonkeyPatch) -> None:
    # Given time.sleep is replaced
    sleep = MagicMock()
    monkeypatch.setattr(piano_module.time, "sleep", sleep)
    # When
    Piano.pause(2)
    # Then
    sleep.assert_called_once_with(2)


def test_piano_should_play_bar_with_a_rest_when_given_one(piano: Piano, sequencer: MagicMock) -> None:
    # Given a bar with a rest, which mingus stores as None
    bar = make_bar("C-4")
    bar.place_rest(4)
    # When
    piano.play(bar)
    # Then
    sequencer.play_Bar.assert_called_once_with(bar, bpm=120)


def test_piano_should_dispatch_to_base_type_method_when_given_a_container_subclass(
    piano: Piano, sequencer: MagicMock
) -> None:
    # Given a subclass of Bar
    class MyBar(Bar):
        pass

    bar = MyBar()
    bar.place_notes("C-4", 4)
    # When
    piano.play(bar)
    # Then
    sequencer.play_Bar.assert_called_once_with(bar, bpm=120)


def test_piano_should_parse_note_string_once_when_playing_it(
    piano: Piano, sequencer: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given Note construction is counted
    note_class = MagicMock(wraps=Note)
    monkeypatch.setattr(piano_module, "Note", note_class)
    # When
    piano.play("C-4")
    # Then
    note_class.assert_called_once_with("C-4")
    sequencer.play_Note.assert_called_once()


def test_piano_should_accept_instrument_names_when_default_sound_fonts_are_loaded_through_another_path(
    piano: Piano, sequencer: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given the default sound font file, loaded through a relative path
    monkeypatch.chdir(DEFAULT_SOUND_FONTS.parent)
    piano.load_sound_fonts(Path(DEFAULT_SOUND_FONTS.name))
    # When
    piano.load_instrument("Honky-tonk Piano")
    # Then
    sequencer.set_instrument.assert_called_with(channel=1, instr=3, bank=0)


def test_piano_should_forget_default_sound_fonts_when_they_are_unloaded(piano: Piano) -> None:
    # Given a piano with the default sound fonts
    # When
    piano._unload_sound_fonts()
    # Then
    assert not piano._uses_default_sound_fonts
