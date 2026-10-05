from collections.abc import Callable
from pathlib import Path
from unittest.mock import MagicMock, call

import pytest
from mingus.containers import Bar, Note, NoteContainer, Track

from pypiano import errors
from pypiano import piano as piano_module
from pypiano._utils import notes_in
from pypiano.piano import DEFAULT_SOUND_FONTS, Piano


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
    sequencer.fs.sfload.assert_called_once_with(str(DEFAULT_SOUND_FONTS))


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
        lambda p: p.record("C-4", "out.wav"),
        lambda p: p.load_sound_fonts(DEFAULT_SOUND_FONTS),
        lambda p: p.load_instrument("Clavi"),
    ],
    ids=["play", "record", "load sound fonts", "load instrument"],
)
def test_piano_should_raise_piano_closed_error_when_used_after_close(
    piano: Piano, action: Callable[[Piano], object]
) -> None:
    # Given a closed piano
    piano.close()
    # When / Then
    with pytest.raises(errors.PianoClosedError, match=r"^The piano is closed$") as raised:
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
    with pytest.raises(errors.PlaybackOptionError, match="bpm must be a positive finite number") as raised:
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
def test_piano_should_play_the_container_itself_when_no_velocity_is_given_and_notes_are_on_channel_1(
    piano: Piano, sequencer: MagicMock, container: Note | NoteContainer | Bar | Track, method: str
) -> None:
    # Given a container whose notes are on mingus' default channel 1
    # When
    piano.play(container)
    # Then it is played as it is, not a copy (mingus' containers compare equal to their copies, hence "is")
    ((played, *_), _) = getattr(sequencer, method).call_args
    assert played is container


def bar_of(*notes: Note) -> Bar:
    bar = Bar()
    for note in notes:
        bar.place_notes(note, 4)
    return bar


@pytest.mark.parametrize(
    ("container", "method"),
    [
        (Note("C-4", channel=2), "play_Note"),
        (NoteContainer([Note("C-4"), Note("E-4", channel=9)]), "play_NoteContainer"),
        (bar_of(Note("C-4", channel=0), Note("E-4")), "play_Bar"),
        (Track().add_bar(bar_of(Note("C-4"), Note("E-4", channel=15))), "play_Track"),
    ],
    ids=["note", "note container", "bar", "track"],
)
def test_piano_should_play_a_copy_with_every_note_on_channel_1_when_notes_are_on_other_channels(
    piano: Piano, sequencer: MagicMock, container: Note | NoteContainer | Bar | Track, method: str
) -> None:
    # Given a container with a note on another channel, where no instrument is selected
    original_channels = [note.channel for note in notes_in(container)]
    # When
    piano.play(container)
    # Then a copy plays every note on channel 1, with each note's own velocity, and the caller's notes keep theirs
    ((played, *_), _) = getattr(sequencer, method).call_args
    assert played is not container
    assert [note.channel for note in notes_in(played)] == [1] * len(original_channels)
    assert [note.velocity for note in notes_in(played)] == [64] * len(original_channels)
    assert [note.channel for note in notes_in(container)] == original_channels


@pytest.mark.parametrize("velocity", [-1, 128])
def test_piano_should_raise_playback_option_error_when_velocity_is_out_of_range(
    piano: Piano, sequencer: MagicMock, velocity: int
) -> None:
    # Given a velocity outside 0 to 127
    # When / Then
    with pytest.raises(errors.PlaybackOptionError, match="velocity must be an integer between 0 and 127") as raised:
        piano.play("C-4", velocity=velocity)
    assert isinstance(raised.value, ValueError)
    sequencer.play_Note.assert_not_called()


# Audio output and recording


@pytest.mark.usefixtures("delete_audio_driver", "delete_synth")
def test_piano_should_start_the_configured_audio_driver_when_playing(sequencer: MagicMock) -> None:
    # Given a piano configured with pipewire, which FluidSynth has but mingus' list of FluidSynth 1 drivers lacks
    piano = Piano(audio_driver="pipewire", sequencer=sequencer)
    # When
    piano.play("C-4")
    # Then
    sequencer.start_audio_output.assert_called_once_with("pipewire")


def test_piano_should_record_a_copy_at_the_velocity_when_velocity_is_given(
    piano: Piano, sequencer: MagicMock, tmp_path: Path
) -> None:
    # Given a note with mingus' default velocity
    note = Note("C-4")
    # When
    piano.record(note, tmp_path / "c4.wav", velocity=80)
    # Then
    ((played,), _) = sequencer.play_Note.call_args
    assert played.velocity == 80
    assert note.velocity == 64


def test_piano_should_pass_bpm_when_recording_a_bar(piano: Piano, sequencer: MagicMock, tmp_path: Path) -> None:
    # Given a bar
    bar = make_bar("C-4", "E-4")
    # When
    piano.record(bar, tmp_path / "bar.wav", seconds=1, bpm=90)
    # Then
    sequencer.play_Bar.assert_called_once_with(bar, bpm=90)


@pytest.mark.parametrize("name", ["bpm", "seconds", "duration"])
def test_piano_should_name_the_option_when_a_playback_option_is_invalid(piano: Piano, name: str) -> None:
    # Given an invalid value for one option
    # When / Then
    with pytest.raises(errors.PlaybackOptionError, match=f"^{name} must be a positive finite number. Got 0$"):
        piano.record("C-4", "out.wav", **{name: 0})


@pytest.mark.parametrize(
    "case",
    [
        (method, name, value)
        for method, name in [("play", "bpm"), ("play", "duration"), ("record", "bpm"), ("record", "duration")]
        for value in (None, True, "1")
    ]
    # seconds may be None: that records until the fade has ended
    + [("record", "seconds", True), ("record", "seconds", "1")],
)
def test_piano_should_raise_playback_option_error_before_playing_when_an_option_is_not_a_number(
    piano: Piano, sequencer: MagicMock, tmp_path: Path, case: tuple[str, str, object]
) -> None:
    # Given an option that is not a number
    method, name, value = case
    args = ("C-4", tmp_path / "out.wav") if method == "record" else ("C-4",)
    # When / Then it fails before anything is played
    with pytest.raises(errors.PlaybackOptionError, match=f"^{name} must be a positive finite number"):
        getattr(piano, method)(*args, **{name: value})
    sequencer.play_Note.assert_not_called()


# duration


def test_piano_should_play_a_note_for_its_duration_and_release_the_note_it_played_when_played(
    piano: Piano, sequencer: MagicMock
) -> None:
    # Given a note on another channel, which plays as a copy on channel 1
    note = Note("C-4", channel=2)
    # When
    piano.play(note, velocity=80)
    # Then the copy sounds for a second, and that copy is stopped: mingus stops a note on the channel stored on it
    played = sequencer.play_Note.call_args.args[0]
    stopped = sequencer.stop_Note.call_args.args[0]
    steps = {"start_audio_output", "play_Note", "sleep", "stop_Note", "fs.cc"}
    assert [step for step in sequencer.mock_calls if step[0] in steps] == [
        call.start_audio_output(None),
        call.play_Note(played),
        call.sleep(1.0),
        call.stop_Note(stopped),
        call.fs.cc(1, 123, 0),
    ]
    assert stopped is played
    assert (played.channel, played.velocity) == (1, 80)


@pytest.mark.parametrize(
    ("container", "play", "stop"),
    [("C-4", "play_Note", "stop_Note"), (NoteContainer(["C-4", "E-4"]), "play_NoteContainer", "stop_NoteContainer")],
    ids=["note", "note container"],
)
def test_piano_should_sound_for_the_given_duration_when_playing_notes(
    piano: Piano, sequencer: MagicMock, container: str | NoteContainer, play: str, stop: str
) -> None:
    # Given a note or note container
    # When
    piano.play(container, duration=0.25)
    # Then
    sequencer.sleep.assert_called_once_with(0.25)
    getattr(sequencer, stop).assert_called_once_with(getattr(sequencer, play).call_args.args[0])


@pytest.mark.parametrize(
    ("container", "method"),
    [(make_bar("C-4", "E-4"), "play_Bar"), (Track().add_bar(make_bar("C-4")), "play_Track")],
    ids=["bar", "track"],
)
def test_piano_should_leave_the_timing_to_bars_and_tracks_when_playing_them(
    piano: Piano, sequencer: MagicMock, container: Bar | Track, method: str
) -> None:
    # Given a bar or track, whose notes have their own values
    # When
    piano.play(container, duration=0.25)
    # Then mingus times and stops the notes; PyPiano only releases what may still be held
    getattr(sequencer, method).assert_called_once_with(container, bpm=120)
    sequencer.sleep.assert_not_called()
    sequencer.stop_Note.assert_not_called()
    sequencer.stop_NoteContainer.assert_not_called()
    sequencer.fs.cc.assert_called_once_with(1, 123, 0)


def test_piano_should_take_the_duration_when_audio_output_cannot_start(piano: Piano, sequencer: MagicMock) -> None:
    # Given FluidSynth cannot start an audio driver, e.g. without a sound device
    sequencer.fs.audio_driver = None
    # When
    piano.play("C-4")
    # Then play takes as long as with a sound device
    sequencer.sleep.assert_called_once_with(1.0)


def test_piano_should_release_all_notes_when_interrupted_while_a_note_sounds(
    piano: Piano, sequencer: MagicMock
) -> None:
    # Given Ctrl+C while the note sounds
    sequencer.sleep.side_effect = KeyboardInterrupt
    # When / Then
    with pytest.raises(KeyboardInterrupt):
        piano.play("C-4")
    sequencer.stop_Note.assert_not_called()
    sequencer.fs.cc.assert_called_once_with(1, 123, 0)
