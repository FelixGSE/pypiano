"""Model of an 88 key piano keyboard."""

from collections.abc import Iterator
from typing import NamedTuple

from mingus.containers import Note

from pypiano.utils import note_to_string


class BaseKey(NamedTuple):
    """Note identities and color of a key within one octave.

    The second identity of C (B#) belongs to the octave below and the one of B (Cb) to the octave above, which
    second_octave_offset expresses: C-4 is B#-3 and B-4 is Cb-5.
    """

    first: str
    second: str
    color: str
    second_octave_offset: int = 0


BASE_PIANO_OCTAVE_PATTERN = (
    BaseKey("C", "B#", "white", second_octave_offset=-1),
    BaseKey("C#", "Db", "black"),
    BaseKey("D", "D", "white"),
    BaseKey("D#", "Eb", "black"),
    BaseKey("E", "Fb", "white"),
    BaseKey("F", "E#", "white"),
    BaseKey("F#", "Gb", "black"),
    BaseKey("G", "G", "white"),
    BaseKey("G#", "Ab", "black"),
    BaseKey("A", "A", "white"),
    BaseKey("A#", "Bb", "black"),
    BaseKey("B", "Cb", "white", second_octave_offset=1),
)


class PianoKey:
    """Class representing a single key on an 88 key piano keyboard.

    Note names follow scientific pitch notation: octave numbers go up at C. A key's two identities are the same pitch,
    so the second identity of C-4 is B#-3 and the one of B-4 is Cb-5.

    Attributes:
        first_identity: The first note identity of a given piano key
        second_identity: The second note identity of a given piano key
        octave: An integer indicating the octave number of a given piano key
        key_color: The color of the key - Can be either black or white
        key_index: The key index on where to find a given piano key on a piano keyboard from left to right
        second_octave: The octave of the second identity. Defaults to octave; differs for C (B# of the octave below)
            and B (Cb of the octave above)

    """

    def __init__(  # noqa: PLR0913 - one argument per key attribute
        self,
        first_identity: str,
        second_identity: str,
        octave: int,
        key_color: str,
        key_index: int | None = None,
        *,
        second_octave: int | None = None,
    ) -> None:
        """Create a piano key from its note identities, octave, color and position."""
        self.first_identity = first_identity
        self.second_identity = second_identity
        self.octave = octave
        self.second_octave = octave if second_octave is None else second_octave
        self.key_color = key_color
        self.key_index = key_index

    def __repr__(self) -> str:
        """Return a string with all attributes of the piano key."""
        return (
            f"{self.__class__.__name__}(first_identity={self.first_identity},second_identity={self.second_identity},"
            f"octave={self.octave},second_octave={self.second_octave},key_color={self.key_color},"
            f"key_index={self.key_index})"
        )

    def __getitem__(self, key: int) -> str:
        """Return the first or second note string of the PianoKey for index 0 or 1."""
        if key == 0:
            return self.first_note_string
        if key == 1:
            return self.second_note_string
        msg = "Out of range. PianoKey has only two indices"
        raise IndexError(msg)

    def __contains__(self, item: str) -> bool:
        """Check if a string representing a note matches one of the note identities of a given PianoKey."""
        return item in self.full_note_string

    @property
    def key_color(self) -> str:
        """Get key color of a given PianoKey object."""
        return self._key_color

    @key_color.setter
    def key_color(self, color: str) -> None:
        """Set key color of a given PianoKey object."""
        if color not in ("white", "black"):
            msg = "Key color can only be white or black"
            raise ValueError(msg)
        self._key_color = color

    @property
    def key_index(self) -> int | None:
        """Get key index of a given PianoKey object."""
        return self._key_index

    @key_index.setter
    def key_index(self, key_index: int | None) -> None:
        """Set key index of a given PianoKey object."""
        self._key_index = key_index

    @property
    def full_note_string(self) -> str:
        """Get both PianoKey note identities as a combined string."""
        return f"{self.first_note_string}/{self.second_note_string}"

    @property
    def first_note_string(self) -> str:
        """Get the first identity of a given piano key as a note string."""
        return f"{self.first_identity}-{self.octave}"

    @property
    def second_note_string(self) -> str:
        """Get the second identity of a given piano key as a note string."""
        return f"{self.second_identity}-{self.second_octave}"

    @property
    def first_note(self) -> Note:
        """Get the first identity of the piano key as a mingus.containers.Note."""
        return Note(f"{self.first_identity}-{self.octave}")

    @property
    def second_note(self) -> Note:
        """Get the second identity of the piano key as a mingus.containers.Note."""
        return Note(self.second_note_string)

    @property
    def frequency(self) -> float:
        """Get frequency of a given PianoKey. See docstring of mingus.containers.Note.to_hertz for more details."""
        return self.first_note.to_hertz()

    def get_as_note(self, identity: str = "first") -> Note:
        """Get first or second PianoKey identity as a mingus.containers.Note.

        Args:
            identity: Parameter indicating whether first or second PianoKey identity should be fetched. Must be either
                'first' or 'second'
        Returns
            A mingus.containers.Note object with first or second note identity
        Raises:
            ValueError: If identity is not 'first' or 'second'

        """
        if identity == "first":
            return Note(self.first_identity, self.octave)
        if identity == "second":
            return self.second_note
        msg = f"Invalid identity parameter - Must be 'first' or 'second'. Got {identity}"
        raise ValueError(msg)

    def get_as_string(self, identity: str = "first") -> str:
        """Get first or second PianoKey identity as a note string.

        Args:
            identity: Parameter indicating whether first or second PianoKey identity should be fetched. Must be either
                'first' or 'second'
        Returns
            A string representing a note following the pattern: <NOTE_NAME><ACCIDENTAL>-<OCTAVE>
        Raises:
            ValueError: If identity is not 'first' or 'second'

        """
        if identity == "first":
            return f"{self.first_identity}-{self.octave}"
        if identity == "second":
            return self.second_note_string
        msg = f"Invalid identity parameter - Must be 'first' or 'second'. Got {identity}"
        raise ValueError(msg)


class PianoKeyboard:
    """Class representing a 88 key piano keyboard."""

    NUMBER_OF_KEYS: int = 88
    NUMBER_OF_WHITE_KEYS: int = 52
    NUMBER_OF_BLACK_KEYS: int = 36

    def __init__(self) -> None:
        """Create the 88 keys from A-0 to C-8."""
        self._keyboard = PianoKeyboard._create_keyboard_dict()

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
            IndexError
               If key is less than zero or greater than 87 or if the note name is not in the set of notes on a piano
               keyboard.

        """
        if isinstance(key, int):
            if not 0 <= key < self.NUMBER_OF_KEYS:
                msg = f"There are only 88 keys on a piano. key must be an integer between 0 and 87. Got {key}"
                raise IndexError(msg)
            return self._keyboard[key]
        for key_index in self._keyboard:
            if key in self._keyboard[key_index]:
                return key_index

        msg = f"{key} is not a valid note on a piano. Please provide a valid Note between A-0 and C-8/B#-7"
        raise IndexError(msg)

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
            item = note_to_string(item)
        return item in self.distinct_key_names

    def __len__(self) -> int:
        """Define the len of the keyboard as the number of keys."""
        return len(self._keyboard)

    @staticmethod
    def _create_keyboard_dict() -> dict[int, PianoKey]:
        """Generate the piano dictionary.

        Method generates a piano dictionary with key_index from left to right as its key and a corresponding
        PianoKey object as Value
        """
        raw_piano_keyboard = []
        for idx in range(10):
            for jdx in range(12):
                tmp_base_key = BASE_PIANO_OCTAVE_PATTERN[jdx]
                current_key = PianoKey(
                    tmp_base_key.first,
                    tmp_base_key.second,
                    idx,
                    tmp_base_key.color,
                    second_octave=idx + tmp_base_key.second_octave_offset,
                )
                raw_piano_keyboard.append(current_key)

        kb = {}
        for index, key in enumerate(raw_piano_keyboard[9:97]):
            key.key_index = index
            kb.update({index: key})

        return kb

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
        available_keys = []

        for k in self._keyboard:
            tmp_key = self._keyboard[k]
            available_keys.extend([tmp_key[0], tmp_key[1]])

        return set(available_keys)

    @property
    def keys(self) -> dict[int, PianoKey]:
        """Return a dictionary of all keys by key index."""
        return self._keyboard

    @property
    def white_keys(self) -> dict[int, PianoKey]:
        """Return a sub dictionary of all white keys from keyboard."""
        return {key: piano_key for key, piano_key in self._keyboard.items() if "white" in piano_key.key_color}

    @property
    def black_keys(self) -> dict[int, PianoKey]:
        """Return a sub dictionary of all black keys from keyboard."""
        return {key: piano_key for key, piano_key in self._keyboard.items() if "black" in piano_key.key_color}
