"""Model of an 88 key piano keyboard."""

from collections.abc import Iterator
from dataclasses import dataclass
from enum import StrEnum

from mingus.containers import Note

from pypiano.errors import InvalidKeyIndexError, UnknownNoteNameError
from pypiano.utils import note_name


class KeyColor(StrEnum):
    """Color of a piano key. Members compare equal to their values, so "white" and KeyColor.WHITE work alike."""

    WHITE = "white"
    BLACK = "black"


# The twelve keys of an octave from C, by both of their names. Octave numbers go up at C, so the second names of C and
# B belong to the neighboring octaves: C-4 is also B#-3, and B-4 is also Cb-5
_OCTAVE = (
    ("C", "B#"),
    ("C#", "Db"),
    ("D", "D"),
    ("D#", "Eb"),
    ("E", "Fb"),
    ("F", "E#"),
    ("F#", "Gb"),
    ("G", "G"),
    ("G#", "Ab"),
    ("A", "A"),
    ("A#", "Bb"),
    ("B", "Cb"),
)


@dataclass(frozen=True, order=True)
class PianoKey:
    """A key of an 88 key piano, by its position from left to right: 0 is A-0, 39 is C-4 and 87 is C-8.

    Everything else about the key follows from its position. Keys are immutable, equal when their positions are, and
    sort from left to right. Note names follow scientific pitch notation, in which octave numbers go up at C.

    Attributes:
        key_index: The position of the key, from 0 (A-0) to 87 (C-8)

    """

    key_index: int

    def __post_init__(self) -> None:
        """Check that the key is one of the 88.

        Raises:
            InvalidKeyIndexError: If key_index is outside 0 to 87 (also an IndexError and a ValueError)

        """
        if not 0 <= self.key_index < PianoKeyboard.NUMBER_OF_KEYS:
            msg = f"A piano has 88 keys, so a key index is between 0 and 87. Got {self.key_index}"
            raise InvalidKeyIndexError(msg)

    def __contains__(self, item: str) -> bool:
        """Whether a note string is exactly one of the key's two names, such as "C-4" or "B#-3" for C-4."""
        return item in (self.first_note_string, self.second_note_string)

    @property
    def octave(self) -> int:
        """The octave of the first name, from 0 to 8."""
        return self._pitch // 12

    @property
    def first_identity(self) -> str:
        """The first name without octave, such as "C" or "C#"."""
        return _OCTAVE[self._pitch % 12][0]

    @property
    def second_identity(self) -> str:
        """The second name without octave, such as "B#" or "Db". D, G and A have only one name, so it is the first."""
        return _OCTAVE[self._pitch % 12][1]

    @property
    def second_octave(self) -> int:
        """The octave of the second name: one lower for B#, one higher for Cb, and else the key's own."""
        match self.second_identity:
            case "B#":
                return self.octave - 1
            case "Cb":
                return self.octave + 1
            case _:
                return self.octave

    @property
    def key_color(self) -> KeyColor:
        """Black for the keys whose first name has a sharp, white for the others."""
        return KeyColor.BLACK if "#" in self.first_identity else KeyColor.WHITE

    @property
    def first_note_string(self) -> str:
        """The first name with its octave, such as "C-4"."""
        return f"{self.first_identity}-{self.octave}"

    @property
    def second_note_string(self) -> str:
        """The second name with its octave, such as "B#-3"."""
        return f"{self.second_identity}-{self.second_octave}"

    @property
    def full_note_string(self) -> str:
        """Both names with their octaves, such as "C-4/B#-3"."""
        return f"{self.first_note_string}/{self.second_note_string}"

    @property
    def first_note(self) -> Note:
        """The first name as a mingus Note."""
        return Note(self.first_note_string)

    @property
    def second_note(self) -> Note:
        """The second name as a mingus Note."""
        return Note(self.second_note_string)

    @property
    def frequency(self) -> float:
        """The key's pitch in hertz, 440 for A-4."""
        return self.first_note.to_hertz()

    @property
    def _pitch(self) -> int:
        """Semitones above C-0, as mingus counts them: A-0, the lowest key, is 9."""
        return self.key_index + 9


class PianoKeyboard:
    """Class representing a 88 key piano keyboard."""

    NUMBER_OF_KEYS: int = 88
    NUMBER_OF_WHITE_KEYS: int = 52
    NUMBER_OF_BLACK_KEYS: int = 36

    def __init__(self) -> None:
        """Create the 88 keys from A-0 to C-8."""
        self._keyboard = {index: PianoKey(index) for index in range(self.NUMBER_OF_KEYS)}
        # Both note names of every key, for exact lookups; each name belongs to exactly one key
        self._index_by_name = {
            name: index
            for index, key in self._keyboard.items()
            for name in (key.first_note_string, key.second_note_string)
        }
        self._key_names = frozenset(self._index_by_name)

    def __repr__(self) -> str:
        """Return a string with the key counts and the first and last key of the keyboard."""
        return (
            f"{self.__class__.__name__}(keys={self.NUMBER_OF_KEYS},white_keys={self.NUMBER_OF_WHITE_KEYS},"
            f"black_keys={self.NUMBER_OF_BLACK_KEYS},first_key={self._keyboard[0].full_note_string},"
            f"last_key={self._keyboard[self.NUMBER_OF_KEYS - 1].full_note_string})"
        )

    def __getitem__(self, key: int | str) -> PianoKey | int:
        """Look up a PianoKey by key index, or a key index by note string.

        You can pass in an integer referring to the key index on a piano keyboard from left to right to receive
        the corresponding PianoKey object. Alternatively, you can pass in a string indicating a note to receive the
        corresponding key index on the piano keyboard from left to right.

        Args:
            key: An integer between 0 and 87 or a string indicating a note following the pattern:
                 <NOTE_NAME><ACCIDENTAL>-<OCTAVE>, so for example C-1, A#-1, Bb-2.

        Returns:
            PianoKey object if key is an integer or an integer between 0 and 87 if key is a note string.

        Raises:
            InvalidKeyIndexError: If key is an integer outside 0 to 87 (also an IndexError and a ValueError).
            UnknownNoteNameError: If key is not the name of a key on the keyboard (also an IndexError).

        """
        if isinstance(key, int):
            if not 0 <= key < self.NUMBER_OF_KEYS:
                msg = f"There are only 88 keys on a piano. key must be an integer between 0 and 87. Got {key}"
                raise InvalidKeyIndexError(msg)
            return self._keyboard[key]
        try:
            return self._index_by_name[key]
        except KeyError:
            msg = f"{key} is not a valid note on a piano. Please provide a valid Note between A-0 and C-8/B#-7"
            raise UnknownNoteNameError(msg) from None

    def __iter__(self) -> Iterator[PianoKey]:
        """Define iterating behavior for PianoKeyboard - Yield PianoKeys from left to right."""
        for k in self._keyboard:
            yield self._keyboard[k]

    def __contains__(self, item: str | Note) -> bool:
        """Check if a note is on the piano keyboard.

        Args:
            item: A string representing a note following the pattern <NOTE_NAME><ACCIDENTAL>-<OCTAVE> or
                a mingus.containers.Note object
        Returns:
             Bool if item is contained in the set of notes on the keyboard

        """
        if isinstance(item, Note):
            item = note_name(item)
        return item in self._key_names

    def __len__(self) -> int:
        """Define the len of the keyboard as the number of keys."""
        return len(self._keyboard)

    @property
    def distinct_key_names(self) -> set[str]:
        """Get all distinct key names / note names on the piano keyboard.

        Retrieves a set of distinct notes that can be found on a piano with 88 keys. Returned note names follow the
        mingus note naming convention: <NOTE_NAME><ACCIDENTAL>-<OCTAVE>, so for example C-1, A#-1, Bb-2, etc.

        Returns:
          A set containing note names. Note that the key names in the returned set are not in order as you find them on
          an actual piano keyboard.

          example:

          {'A#-1','A#-2','A#-3','A#-4','A#-5','A#-6','A#-7','A#-8','A-1','A-2','A-3','A-4','A-5','A-6',...}

        """
        # A copy, so callers cannot change the names the keyboard looks up
        return set(self._key_names)

    @property
    def keys(self) -> dict[int, PianoKey]:
        """Return a dictionary of all keys by key index."""
        return self._keyboard

    @property
    def white_keys(self) -> dict[int, PianoKey]:
        """Return a sub dictionary of all white keys from keyboard."""
        return {key: piano_key for key, piano_key in self._keyboard.items() if piano_key.key_color == KeyColor.WHITE}

    @property
    def black_keys(self) -> dict[int, PianoKey]:
        """Return a sub dictionary of all black keys from keyboard."""
        return {key: piano_key for key, piano_key in self._keyboard.items() if piano_key.key_color == KeyColor.BLACK}
