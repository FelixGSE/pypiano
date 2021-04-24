# -*- coding: utf-8 -*-
"""This module does blah blah."""
from typing import Union, Dict, List
from mingus.containers import Note
from collections import namedtuple
import logging


OCTAVE_KEY_NAMES = [("C", "B#"), ("C#", "Db"), ("D", None), ("D#", "Eb"), ("E", "Fb"), ("F", "E#"),
                    ("F#", "Gb"), ("G", None), ("G#", "Ab"), ("A", None), ("A#", "Bb"), ("B", "C#")]

OCTAVE_KEY_COLORS = ["white", "black", "white", "black", "white", "white", "black", "white", "black",
                     "white", "black","white"]

logger = logging.getLogger("pyano.keyboard")
logger.addHandler(logging.NullHandler())


class PianoKey(object):
    """
    """

    def __init__(self, first_identity: str, second_identity: Union[str, None], octave: int, key_color: str) -> None:
        """
        If second identity is none set second to first
        """
        self.first_identity = first_identity
        self.second_identity = second_identity
        self.octave = octave
        self.key_color = key_color

    def __repr__(self) -> str:
        return "{0}(first_identity={1},second_identity={2},octave={3},key_color={4})".format(
            self.__class__.__name__,
            self.first_identity,
            self.second_identity,
            self.octave,
            self.key_color)

    def __str__(self) -> str:
        return "{0}(first_identity={1},second_identity={2},octave={3},key_color={4})".format(
            self.__class__.__name__,
            self.first_identity,
            self.second_identity,
            self.octave,
            self.key_color)

    def __getitem__(self, key: Union[int,str]) -> Union[int,str]:
        if key == 0:
            return self.get_as_string(identity="first")
        elif key == 1:
            return self.get_as_string(identity="second")
        else:
            raise IndexError("PianoKey has only have 2 indices")

    def __contains__(self, item: str) -> bool:
        if item in self.get_as_full_string:
            return True
        else:
            return False

    def get_full_name_as_tts(self,conjunction: str = "or") -> str:
        """Probably shouldn't be included

        """
        first_as_tts = self._accidental_to_text(self.first_identity)
        if self.second_identity is None:
            tts_text = "{name} {octave}".format(name=first_as_tts, octave=self.octave)
        else:
            second_as_tts = self._accidental_to_text(self.second_identity)
            tts_text = "{fist_name} {octave} {conjunction} {second_name} {octave}".format(
                fist_name=first_as_tts,
                conjunction = conjunction,
                octave=self.octave,
                second_name=second_as_tts
            )
        return tts_text

    def _accidental_to_text(self, input_str: str) -> str:
        """

        """
        return input_str.replace("#", " Sharp").replace("b", " Flat")

    def get_as_note(self, identity: str = "first") -> Note:
        """

        """
        if identity == "first":
            return Note(self.first_identity, self.octave)
        elif identity == "second":
            return Note(self.second_identity, self.octave)
        else:
            raise Exception("Invalid identity parameter - Must be 'first' or 'second'. Got {0}".format(identity))

    def get_as_string(self, identity: str = "first") -> str:
        """

        """
        if identity == "first":
            return "{note}-{octave}".format(note=self.first_identity, octave=self.octave)
        elif identity == "second":
            return "{note}-{octave}".format(note=self.second_identity, octave=self.octave)
        else:
            raise Exception("Invalid identity parameter - Must be 'first' or 'second'. Got {0}".format(identity))

    @property
    def get_as_full_string(self) -> str:
        """

        """
        return "{first}-{octave}/{second}-{octave}".format(first=self.first_identity,
                                                           second=self.second_identity,
                                                           octave=self.octave)
    @property
    def key_color(self) -> str:
        """

        """
        return self._key_color

    @key_color.setter
    def key_color(self, color: str) -> None:
        """

        """
        if color not in ("white", "black"):
            raise ValueError("Key color can only be white or black")
        self._key_color = color

    @property
    def frequency(self):
        """

        """
        pass

    @property
    def keyboard_index(self):
        """

        """
        pass

class PianoKeyboard(object):
    """

    """
    number_of_keys = 88
    number_of_white_keys = 52
    number_of_black_keys = 36

    def __init__(self) -> None:
        self._keyboard = self._init_keyboard()

    def __repr__(self) -> str:
        return "{0}(keys={1},white_keys={2},black_keys={3},first_key={4},last_key={5})".format(
            self.__class__.__name__,
            self.number_of_keys,
            self.number_of_white_keys,
            self.number_of_black_keys,
            self._keyboard.get(0).get_as_full_string,
            self._keyboard.get(87).get_as_full_string
        )

    def __str__(self) -> str:
        return "{0}(keys={1},white_keys={2},black_keys={3},first_key={4},last_key={5})".format(
            self.__class__.__name__,
            self.number_of_keys,
            self.number_of_white_keys,
            self.number_of_black_keys,
            self._keyboard.get(0).get_as_full_string,
            self._keyboard.get(87).get_as_full_string
        )

    def __getitem__(self, key: Union[int,str]) -> Union[PianoKey,int]:
        """

        """
        if isinstance(key, int):
            if not 0 <= key <= 87:
                raise IndexError(
                    "There are only 88 keys on a piano. key_index must be an integer between 0 and 87. Got {0}".format(
                        key
                ))
            return self._keyboard[key]
        else:
            if key not in self.available_key_names:
                raise IndexError(
                    "{0} is not a valid note on a piano. Please provide a valid Note between A-0 and C-8/B#-8"
                )
            else:
                """
                may return the piano key object instead
                """
                return [key_index for key_index in self._keyboard.keys() if key in self._keyboard[key_index]][0]

    def __iter__(self):
        """

        """
        for k in self._keyboard:
            yield self._keyboard[k]

    def get_key_by_index(self,key_index: int) -> PianoKey:
        """

        """
        if not 0 <= key_index <= 87:
            raise IndexError(
                "There are only 88 keys on a piano. key_index must be an integer between 0 and 87. Got {0}".format(
                    key_index
            ))

        return self._keyboard[key_index]

    def _init_keyboard(self) -> Dict[int,PianoKey]:
        """

        """
        raw_paino_keys = []
        for idx in range(9):
            for jdx in range(12):
                current_key = PianoKey(OCTAVE_KEY_NAMES[jdx][0], OCTAVE_KEY_NAMES[jdx][1], idx, OCTAVE_KEY_COLORS[jdx])
                raw_paino_keys.append(current_key)

        return {idx: key for idx, key in enumerate(raw_paino_keys[10:98])}

    @property
    def available_key_names(self) -> List[str]:
        """

        """
        available_keys = []
        for k in self._keyboard:
            tmp_key = self._keyboard[k]
            available_keys.extend([tmp_key[0],tmp_key[1]])

        return available_keys

    @property
    def black_keys(self) -> List[PianoKey]:
        pass

    @property
    def white_keys(self) -> List(PianoKey):
        pass


