import pytest
from mingus.containers import Bar, Note, NoteContainer, Track

from pypiano._utils import note_name, notes_in
from pypiano.errors import UnsupportedContainerError


def bar_with_rest() -> Bar:
    bar = Bar()
    bar.place_notes("C-4", 4)
    bar.place_rest(4)
    bar.place_notes(["E-4", "G-4"], 4)
    return bar


@pytest.mark.parametrize(
    ("container", "expected"),
    [
        (Note("C-4"), ["C-4"]),
        (NoteContainer(["C-4", "E-4", "G-4"]), ["C-4", "E-4", "G-4"]),
        (bar_with_rest(), ["C-4", "E-4", "G-4"]),
        (Track().add_bar(bar_with_rest()), ["C-4", "E-4", "G-4"]),
    ],
    ids=["note", "note container", "bar with a rest", "track with a rest"],
)
def test_notes_in_should_yield_every_note_and_skip_rests_when_given_a_container(
    container: Note | NoteContainer | Bar | Track, expected: list[str]
) -> None:
    # Given a music container
    # When
    names = [note_name(note) for note in notes_in(container)]
    # Then
    assert names == expected


def test_notes_in_should_raise_unsupported_container_error_when_given_another_type() -> None:
    # Given an object that is not a mingus container
    # When / Then
    with pytest.raises(UnsupportedContainerError, match="Unsupported music container type"):
        list(notes_in(3.5))


def test_note_name_should_combine_name_and_octave_when_given_a_note() -> None:
    # Given a note
    # When
    name = note_name(Note("Db", 5))
    # Then
    assert name == "Db-5"
