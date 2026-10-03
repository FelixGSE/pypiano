from collections.abc import Callable
from unittest.mock import MagicMock, call

import pytest
from mingus.containers import Bar, Note, NoteContainer, Track

from pypiano import errors
from pypiano import piano as piano_module
from pypiano.piano import DEFAULT_SOUND_FONTS, Piano
from pypiano.utils import notes_in


def make_bar(*notes: str) -> Bar:
    bar = Bar()
    for note in notes:
        bar.place_notes(note, 4)
    return bar


# Sequencer


def test_piano_should_create_a_fluidsynth_sequencer_when_none_is_given(
    monkeypatch: pytest.MonkeyPatch, sequencer: MagicMock
) -> None:
    # Given FluidSynthSequencer is replaced
    sequencer_class = MagicMock(return_value=sequencer)
    monkeypatch.setattr(piano_module, "FluidSynthSequencer", sequencer_class)
    # When
    Piano()
    # Then
    sequencer_class.assert_called_once_with()
    sequencer.load_sound_font.assert_called_once_with(str(DEFAULT_SOUND_FONTS))


def test_piano_should_use_the_given_sequencer_when_one_is_passed(piano: Piano, sequencer: MagicMock) -> None:
    # Given a piano created with a sequencer
    # When
    piano.play("C-4")
    # Then
    sequencer.play_Note.assert_called_once()


# Closing


def test_close_should_stop_audio_unload_sound_fonts_and_free_the_synth_when_called(
    piano: Piano, sequencer: MagicMock, delete_audio_driver: MagicMock, delete_synth: MagicMock
) -> None:
    # Given a piano with active audio output
    piano._start_audio_output()
    audio_driver, synth, settings = sequencer.fs.audio_driver, sequencer.fs.synth, sequencer.fs.settings
    # When
    piano.close()
    # Then
    delete_audio_driver.assert_called_once_with(audio_driver)
    sequencer.fs.sfunload.assert_called_once_with(sequencer.sfid)
    assert delete_synth.mock_calls == [call.delete_fluid_synth(synth), call.delete_fluid_settings(settings)]
    # mingus frees these again on garbage collection; NULL handles make that a no-op
    assert (sequencer.fs.audio_driver, sequencer.fs.synth, sequencer.fs.settings) == (None, None, None)


def test_close_should_do_nothing_when_called_again(
    piano: Piano, delete_audio_driver: MagicMock, delete_synth: MagicMock
) -> None:
    # Given a closed piano with audio output started before
    piano._start_audio_output()
    piano.close()
    # When
    piano.close()
    # Then
    delete_audio_driver.assert_called_once()
    delete_synth.delete_fluid_synth.assert_called_once()


def test_piano_should_close_when_leaving_a_with_block(piano: Piano, delete_synth: MagicMock) -> None:
    # Given a piano used as a context manager
    # When
    with piano as entered:
        entered.play("C-4")
    # Then
    assert entered is piano
    delete_synth.delete_fluid_synth.assert_called_once()
    with pytest.raises(errors.PianoClosedError):
        piano.play("C-4")


@pytest.mark.parametrize(
    "action",
    [
        lambda p: p.play("C-4"),
        lambda p: p.load_sound_fonts(DEFAULT_SOUND_FONTS),
        lambda p: p.load_instrument("Clavi"),
    ],
    ids=["play", "load sound fonts", "load instrument"],
)
def test_piano_should_raise_piano_closed_error_when_used_after_close(
    piano: Piano, action: Callable[[Piano], object]
) -> None:
    # Given a closed piano
    piano.close()
    # When / Then
    with pytest.raises(errors.PianoClosedError, match="closed") as raised:
        action(piano)
    assert isinstance(raised.value, RuntimeError)


# bpm


@pytest.mark.parametrize(
    ("container", "method"),
    [(make_bar("C-4", "E-4"), "play_Bar"), (Track().add_bar(make_bar("C-4")), "play_Track")],
    ids=["bar", "track"],
)
def test_piano_should_pass_bpm_when_playing_bars_and_tracks(
    piano: Piano, sequencer: MagicMock, container: Bar | Track, method: str
) -> None:
    # Given a bar or track
    # When
    piano.play(container, bpm=90)
    # Then
    getattr(sequencer, method).assert_called_once_with(container, bpm=90)


@pytest.mark.parametrize(
    ("container", "method"),
    [(Note("C-4"), "play_Note"), (NoteContainer(["C-4", "E-4"]), "play_NoteContainer")],
    ids=["note", "note container"],
)
def test_piano_should_not_pass_bpm_when_playing_notes(
    piano: Piano, sequencer: MagicMock, container: Note | NoteContainer, method: str
) -> None:
    # Given a note or note container
    # When
    piano.play(container, bpm=90)
    # Then
    getattr(sequencer, method).assert_called_once_with(container)


@pytest.mark.parametrize("bpm", [0, -60])
def test_piano_should_raise_playback_option_error_when_bpm_is_not_positive(piano: Piano, bpm: float) -> None:
    # Given a non-positive tempo
    # When / Then
    with pytest.raises(errors.PlaybackOptionError, match="bpm must be positive") as raised:
        piano.play("C-4", bpm=bpm)
    assert isinstance(raised.value, ValueError)


# velocity


@pytest.mark.parametrize(
    ("container", "method"),
    [
        (Note("C-4"), "play_Note"),
        (NoteContainer(["C-4", "E-4"]), "play_NoteContainer"),
        (make_bar("C-4", "E-4"), "play_Bar"),
        (Track().add_bar(make_bar("C-4", "E-4")), "play_Track"),
    ],
    ids=["note", "note container", "bar", "track"],
)
def test_piano_should_play_a_copy_with_every_note_at_the_velocity_when_velocity_is_given(
    piano: Piano, sequencer: MagicMock, container: Note | NoteContainer | Bar | Track, method: str
) -> None:
    # Given a container whose notes have mingus' default velocity
    original_velocities = [note.velocity for note in notes_in(container)]
    # When
    piano.play(container, velocity=80)
    # Then
    ((played, *_), _) = getattr(sequencer, method).call_args
    assert played is not container
    assert [note.velocity for note in notes_in(played)] == [80] * len(original_velocities)
    assert [note.velocity for note in notes_in(container)] == original_velocities


def test_piano_should_play_the_container_itself_when_no_velocity_is_given(piano: Piano, sequencer: MagicMock) -> None:
    # Given a note
    note = Note("C-4")
    # When
    piano.play(note)
    # Then
    sequencer.play_Note.assert_called_once_with(note)


@pytest.mark.parametrize("velocity", [-1, 128])
def test_piano_should_raise_playback_option_error_when_velocity_is_out_of_range(
    piano: Piano, sequencer: MagicMock, velocity: int
) -> None:
    # Given a velocity outside 0 to 127
    # When / Then
    with pytest.raises(errors.PlaybackOptionError, match="velocity must be between 0 and 127") as raised:
        piano.play("C-4", velocity=velocity)
    assert isinstance(raised.value, ValueError)
    sequencer.play_Note.assert_not_called()
