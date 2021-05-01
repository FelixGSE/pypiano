# -*- coding: utf-8 -*-
"""

"""
import logging

from typing import Union, Dict, List
from mingus.containers import Note
from collections import namedtuple
from .utils import PianoUtils


base_key = namedtuple("base_key", ["first", "second", "color"])
BASE_OCTAVE_PATTERN = (
    base_key("C", "B#", "white"),
    base_key("C#", "Db", "black"),
    base_key("D", "D", "white"),
    base_key("D#", "Eb", "black"),
    base_key("E", "Fb", "white"),
    base_key("F", "E#", "white"),
    base_key("F#", "Gb", "black"),
    base_key("G", "G", "white"),
    base_key("G#", "Ab", "black"),
    base_key("A", "A", "white"),
    base_key("A#", "Bb", "black"),
    base_key("B", "C#", "white"),
)

logger = logging.getLogger("pyano.keyboard")
logger.addHandler(logging.NullHandler())


class PianoKey(object):
    """Class representing a single key on an 88 key piano keyboard"""

    def __init__(
        self,
        first_identity: str,
        second_identity: Union[str, None],
        octave: int,
        key_color: str,
        key_index: int = None,
    ) -> None:
        """"""
        self.first_identity = first_identity
        self.second_identity = second_identity
        self.octave = octave
        self.key_color = key_color
        self.key_index = key_index

    def __repr__(self) -> str:
        return "{0}(first_identity={1},second_identity={2},octave={3},key_color={4},key_index={5})".format(
            self.__class__.__name__,
            self.first_identity,
            self.second_identity,
            self.octave,
            self.key_color,
            self.key_index,
        )

    def __getitem__(self, key: Union[int, str]) -> Union[int, str]:
        """"""
        if key == 0:
            return self.get_as_string(identity="first")
        elif key == 1:
            return self.get_as_string(identity="second")
        else:
            raise IndexError("Out of range. PianoKey has only two indices")

    def __contains__(self, item: str) -> bool:
        """"""
        if item in self.full_note_string:
            return True
        else:
            return False

    def get_as_note(self, identity: str = "first") -> Note:
        """"""
        if identity == "first":
            return Note(self.first_identity, self.octave)
        elif identity == "second":
            return Note(self.second_identity, self.octave)
        else:
            raise Exception(
                "Invalid identity parameter - Must be 'first' or 'second'. Got {0}".format(
                    identity
                )
            )

    def get_as_string(self, identity: str = "first") -> str:
        """"""
        if identity == "first":
            return "{note}-{octave}".format(
                note=self.first_identity, octave=self.octave
            )
        elif identity == "second":
            return "{note}-{octave}".format(
                note=self.second_identity, octave=self.octave
            )
        else:
            raise Exception(
                "Invalid identity parameter - Must be 'first' or 'second'. Got {0}".format(
                    identity
                )
            )

    @property
    def full_note_string(self) -> str:
        """"""
        return "{first}-{octave}/{second}-{octave}".format(
            first=self.first_identity, second=self.second_identity, octave=self.octave
        )

    @property
    def key_color(self) -> str:
        """"""
        return self._key_color

    @key_color.setter
    def key_color(self, color: str) -> None:
        """"""
        if color not in ("white", "black"):
            raise ValueError("Key color can only be white or black")
        self._key_color = color

    @property
    def key_index(self):
        """"""
        return self._key_index

    @key_index.setter
    def key_index(self, key_index: int) -> None:
        """"""
        self._key_index = key_index

    @property
    def frequency(self):
        """"""
        return self.get_as_note().to_hertz()


class PianoKeyboard(object):
    """Class representing a 88 key piano keyboard"""

    NUMBER_OF_KEYS: int = 88
    NUMBER_OF_WHITE_KEYS: int = 52
    NUMBER_OF_BLACK_KEYS: int = 36

    def __init__(self) -> None:
        """"""
        self._keyboard = PianoKeyboard._init_keyboard()

    def __repr__(self) -> str:
        return "{0}(keys={1},white_keys={2},black_keys={3},first_key={4},last_key={5})".format(
            self.__class__.__name__,
            self.NUMBER_OF_KEYS,
            self.NUMBER_OF_WHITE_KEYS,
            self.NUMBER_OF_BLACK_KEYS,
            self._keyboard.get(0).full_note_string,
            self._keyboard.get(87).full_note_string,
        )

    def __getitem__(self, key: Union[int, str]) -> Union[PianoKey, int]:
        """Defines indexing behavior for PianoKeyboard objects

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
            if not 0 <= key <= 87:
                raise IndexError(
                    "There are only 88 keys on a piano. key must be an integer between 0 and 87. Got {0}".format(
                        key
                    )
                )
            return self._keyboard[key]
        else:

            if key not in self.distinct_key_names:
                raise IndexError(
                    "{0} is not a valid note on a piano. Please provide a valid Note between A-0 and C-8/B#-8"
                )
            else:
                return [
                    key_index
                    for key_index in self._keyboard.keys()
                    if key in self._keyboard[key_index]
                ][0]

    def __iter__(self):
        """"""
        for k in self._keyboard:
            yield self._keyboard[k]

    def __contains__(self, item: Union[str, Note]) -> bool:
        """"""
        if isinstance(item, Note):
            item = PianoUtils.note_to_string(item)
        return item in self.distinct_key_names

    def __len__(self):
        """"""
        return len(self._keyboard)

    @staticmethod
    def _init_keyboard() -> Dict[int, PianoKey]:
        """"""
        raw_piano_keyboard = []
        for idx in range(10):
            for jdx in range(12):
                tmp_base_key = BASE_OCTAVE_PATTERN[jdx]
                current_key = PianoKey(
                    tmp_base_key.first, tmp_base_key.second, idx, tmp_base_key.color
                )
                raw_piano_keyboard.append(current_key)

        kb = {}
        for index, key in enumerate(raw_piano_keyboard[21:109]):
            key.key_index = index
            kb.update({index: key})

        return kb

    @property
    def distinct_key_names(self) -> set[str]:
        """Get all distinct key names / note names on the piano keyboard

        Retrieves a set of distinct notes that can be found an a piano with 88 keys. Returned note names follow the
        mingus note naming convention: <NOTE_NAME><ACCIDENTAL>-<OCTAVE>, so for example C-1, A#-1, Bb-2, etc.

        Returns:
          A set containing note names. Note that the key names in the returned set are not in order as you find them on
          an an actual piano keyboard.

          example:

          {'A#-1','A#-2','A#-3','A#-4','A#-5','A#-6','A#-7','A#-8','A-1','A-2','A-3','A-4','A-5','A-6',...}

        """
        available_keys = []

        for k in self._keyboard:
            tmp_key = self._keyboard[k]
            available_keys.extend([tmp_key[0], tmp_key[1]])

        return set(available_keys)

    @property
    def black_keys(self) -> List[PianoKey]:
        """"""
        pass

    @property
    def white_keys(self) -> List[PianoKey]:
        pass
