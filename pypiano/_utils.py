"""Helpers to read the notes of mingus music containers."""

from collections.abc import Iterable, Iterator
from functools import singledispatch

from mingus.containers import Bar, Note, NoteContainer, Track

from pypiano.errors import UnsupportedContainerError


def note_name(note: Note) -> str:
    """Return the note string of a mingus.containers.Note, for example C-4 or Db-5."""
    return f"{note.name}-{note.octave}"


@singledispatch
def notes_in(container: object) -> Iterator[Note]:
    """Yield every note of a mingus music container: a Note, NoteContainer, Bar or Track.

    Raises:
        UnsupportedContainerError: If the container is none of these types

    """
    msg = f"Unsupported music container type: {type(container)}"
    raise UnsupportedContainerError(msg)


@notes_in.register
def _notes_of_note(note: Note) -> Iterator[Note]:
    yield note


@notes_in.register
def _notes_of_note_container(note_container: NoteContainer) -> Iterator[Note]:
    yield from note_container.notes


def _notes_of_beats(beats: Iterable[tuple[float, float, NoteContainer | None]]) -> Iterator[Note]:
    # Each beat is (beat, duration, notes); mingus stores a rest as None instead of notes
    for _beat, _duration, notes in beats:
        if notes is not None:
            yield from notes


@notes_in.register
def _notes_of_bar(bar: Bar) -> Iterator[Note]:
    yield from _notes_of_beats(bar.bar)


@notes_in.register
def _notes_of_track(track: Track) -> Iterator[Note]:
    yield from _notes_of_beats(track.get_notes())
