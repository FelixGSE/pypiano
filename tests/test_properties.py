"""Property-based tests: rules that must hold for every input, checked against inputs Hypothesis generates."""

import math
from unittest.mock import MagicMock

import numpy as np
import pytest
from hypothesis import example, given
from hypothesis import strategies as st
from mingus.containers import Bar, Note, Track

from pypiano.errors import InvalidKeyIndexError, InvalidNoteError, PlaybackOptionError, UnknownNoteNameError
from pypiano.keyboard import PianoKey, PianoKeyboard
from pypiano.piano import Piano
from pypiano.utils import note_name, notes_in

KEYBOARD = PianoKeyboard()
LOWEST, HIGHEST = int(Note("A-0")), int(Note("C-8"))

LETTERS = "CDEFGAB"
SINGLE_ACCIDENTALS = ("", "#", "b")
ALL_ACCIDENTALS = (*SINGLE_ACCIDENTALS, "##", "bb")


def notes(accidentals: tuple[str, ...]) -> st.SearchStrategy[Note]:
    """Notes with the given accidentals in octaves 0 to 9, partly outside the 88 keys."""
    return st.builds(
        Note,
        st.builds(
            lambda letter, accidental: letter + accidental, st.sampled_from(LETTERS), st.sampled_from(accidentals)
        ),
        st.integers(min_value=0, max_value=9),
    )


def on_keyboard(note: Note) -> bool:
    return LOWEST <= int(note) <= HIGHEST


def make_piano() -> tuple[Piano, MagicMock]:
    # Created per example, because Hypothesis runs each test many times and pytest fixtures run once per test
    sequencer = MagicMock(name="FluidSynthSequencer()")
    sequencer.load_sound_font.return_value = True
    sequencer.fs.get_samples.return_value = np.zeros(8, dtype=np.int16)
    return Piano(sequencer=sequencer), sequencer


def key_at(index: int) -> PianoKey:
    key = KEYBOARD[index]
    assert isinstance(key, PianoKey)
    return key


def index_of(name: str) -> int:
    index = KEYBOARD[name]
    assert isinstance(index, int)
    return index


# Keyboard


@given(notes(SINGLE_ACCIDENTALS))
def test_keyboard_should_know_a_note_name_exactly_when_its_pitch_is_on_the_keyboard(note: Note) -> None:
    # Given a note spelled with at most one accidental, which the keyboard has names for
    name = note_name(note)
    # When / Then
    assert (name in KEYBOARD) == on_keyboard(note)
    if on_keyboard(note):
        key = key_at(index_of(name))
        assert int(key.first_note) == int(key.second_note) == int(note)


@given(st.text(max_size=8))
def test_keyboard_should_find_a_key_or_raise_unknown_note_name_error_when_given_any_text(text: str) -> None:
    # Given any text
    # When / Then it is either exactly a key's name or an UnknownNoteNameError, never a wrong key or another error
    if text in KEYBOARD.distinct_key_names:
        assert text in key_at(index_of(text))
    else:
        assert text not in KEYBOARD
        with pytest.raises(UnknownNoteNameError):
            KEYBOARD[text]


@given(st.integers())
def test_keyboard_should_return_a_key_or_raise_invalid_key_index_error_when_given_any_integer(index: int) -> None:
    # Given any integer
    # When / Then
    if 0 <= index < len(KEYBOARD):
        assert key_at(index).key_index == index
    else:
        with pytest.raises(InvalidKeyIndexError):
            KEYBOARD[index]


# notes_in


beats = st.lists(st.one_of(st.none(), notes(SINGLE_ACCIDENTALS)), max_size=4)


def bar_of(beat_notes: list[Note | None]) -> Bar:
    bar = Bar()
    for note in beat_notes:
        if note is None:
            bar.place_rest(4)
        else:
            bar.place_notes(note, 4)
    return bar


@given(st.lists(beats, max_size=3))
def test_notes_in_should_yield_the_placed_notes_in_order_and_skip_rests_when_given_a_track(
    bars: list[list[Note | None]],
) -> None:
    # Given a track of bars with notes and rests
    track = Track()
    for beat_notes in bars:
        track.add_bar(bar_of(beat_notes))
    # When
    names = [note_name(note) for note in notes_in(track)]
    # Then
    assert names == [note_name(note) for beat_notes in bars for note in beat_notes if note is not None]


# Piano.play


@given(notes(ALL_ACCIDENTALS))
def test_piano_should_play_a_note_exactly_when_its_pitch_is_on_the_keyboard(note: Note) -> None:
    # Given a note in any spelling, double accidentals included
    piano, _ = make_piano()
    # When / Then
    if on_keyboard(note):
        piano.play(note)
    else:
        with pytest.raises(InvalidNoteError):
            piano.play(note)


# Random text, and text from the characters of note names, which forms valid and almost valid notes far more often
note_strings = st.text(max_size=8) | st.text(alphabet="ABCDEFGHcb#- 0123456789", max_size=6)


@given(note_strings)
# The strings mingus rejects with NoteFormatError, ValueError or IndexError, and a name without an octave
@example("H-4")
@example("c-4")
@example(" C-4")
@example("C-4-1")
@example("C-x")
@example("C-")
@example("")
@example("C")
def test_piano_should_play_a_string_or_raise_invalid_note_error_when_given_any_text(text: str) -> None:
    # Given any text
    piano, sequencer = make_piano()
    # When / Then it plays a note, or raises InvalidNoteError, never another error
    try:
        piano.play(text)
    except InvalidNoteError:
        sequencer.play_Note.assert_not_called()
    else:
        sequencer.play_Note.assert_called_once()


@given(st.integers())
def test_piano_should_play_a_key_index_or_raise_invalid_key_index_error_when_given_any_integer(index: int) -> None:
    # Given any integer
    piano, _ = make_piano()
    # When / Then
    if 0 <= index < len(KEYBOARD):
        piano.play(index)
    else:
        with pytest.raises(InvalidKeyIndexError):
            piano.play(index)


@given(st.one_of(st.integers(), st.floats(), st.booleans()))
# Boundaries Hypothesis may or may not try in a given run
@example(0)
@example(127)
@example(-1)
@example(128)
@example(True)  # noqa: FBT003 - bool is an int subclass, the case to check
@example(64.5)
@example(math.nan)
def test_piano_should_accept_velocity_exactly_when_it_is_an_integer_from_0_to_127(velocity: float) -> None:
    # Given any number as velocity
    piano, sequencer = make_piano()
    valid = isinstance(velocity, int) and not isinstance(velocity, bool) and 0 <= velocity <= 127
    note = Note("C-4")
    # When / Then
    if valid:
        piano.play(note, velocity=int(velocity))
        ((played,), _) = sequencer.play_Note.call_args
        assert played.velocity == velocity
        assert note.velocity == 64
    else:
        with pytest.raises(PlaybackOptionError):
            piano.play(note, velocity=velocity)  # ty: ignore[invalid-argument-type] - wrong types are the point


@given(st.floats() | st.integers())
@example(math.nan)
@example(math.inf)
@example(-math.inf)
@example(0)
@example(-60)
@example(1e-9)
def test_piano_should_accept_bpm_exactly_when_it_is_positive_and_finite(bpm: float) -> None:
    # Given any number as tempo
    piano, _ = make_piano()
    # When / Then
    if math.isfinite(bpm) and bpm > 0:
        piano.play(bar_of([Note("C-4")]), bpm=bpm)
    else:
        with pytest.raises(PlaybackOptionError):
            piano.play(bar_of([Note("C-4")]), bpm=bpm)


@given(st.floats(max_value=1e6) | st.integers(max_value=10**6))
@example(math.nan)
@example(math.inf)
@example(-math.inf)
@example(0)
@example(-1)
@example(0.5)
def test_piano_should_accept_record_seconds_exactly_when_positive_and_finite(record_seconds: float) -> None:
    # Given any number as recording length
    piano, _ = make_piano()
    # When / Then
    if math.isfinite(record_seconds) and record_seconds > 0:
        piano.play("C-4", recording_file="out.wav", record_seconds=record_seconds)
    else:
        with pytest.raises(PlaybackOptionError):
            piano.play("C-4", recording_file="out.wav", record_seconds=record_seconds)
