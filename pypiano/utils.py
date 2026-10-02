"""Helpers to convert mingus music containers to note strings."""

from mingus.containers import (
    Bar,
    Note,
    NoteContainer,
    Track,
)


def note_to_string(note: Note) -> str:
    """Convert a mingus.containers.Note to a note string."""
    return f"{note.name}-{note.octave}"


def note_container_to_note_string_list(
    note_container: NoteContainer,
) -> list[str]:
    """Convert a mingus.containers.NoteContainer to a list of note strings."""
    return [note_to_string(note) for note in note_container.notes]


def bar_to_note_string_list(
    bar: Bar,
) -> list[str]:
    """Convert a mingus.containers.Bar to a list of note strings."""
    return [note_to_string(note) for note_list in bar.bar for note in note_list[-1]]


def track_to_note_string_list(
    track: Track,
) -> list[str]:
    """Convert a mingus.containers.Track to a list of note strings."""
    return [note_to_string(note) for element in track.get_notes() for note in element[-1]]
