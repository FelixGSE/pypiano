import unittest

import pytest
from mingus.containers import Note

from pypiano.keyboard import PianoKey, PianoKeyboard


class KeyboardTests(unittest.TestCase):
    """Basic test cases."""

    def setUp(self) -> None:
        self.keyboard = PianoKeyboard()

    def test_keys(self) -> None:
        assert len(self.keyboard.keys) == 88

    def test_white_keys(self) -> None:
        assert len(self.keyboard.white_keys) == 52

    def test_black_keys(self) -> None:
        assert len(self.keyboard.black_keys) == 36


def test_piano_key_should_return_second_identity_when_asked_for_second_note_string() -> None:
    # Given a C#-4 key, whose second identity is Db-4
    key = PianoKey("C#", "Db", 4, "black")
    # When
    note_string = key.second_note_string
    # Then
    assert note_string == "Db-4"
    assert key[1] == "Db-4"


def test_keyboard_keys_should_have_identities_of_equal_pitch_when_created() -> None:
    # Given a new keyboard
    keyboard = PianoKeyboard()
    # When
    pitches = [(int(Note(key.first_note_string)), int(Note(key.second_note_string))) for key in keyboard]
    # Then
    assert all(first == second for first, second in pitches)


@pytest.mark.parametrize(
    ("first", "second"),
    [("C-4", "B#-3"), ("B-4", "Cb-5"), ("A-0", "A-0"), ("C-8", "B#-7")],
    ids=["C has B# of the octave below", "B has Cb of the octave above", "lowest key", "highest key"],
)
def test_keyboard_should_find_same_key_when_looked_up_by_either_identity(first: str, second: str) -> None:
    # Given a new keyboard
    keyboard = PianoKeyboard()
    # When
    key_index = keyboard[first]
    # Then
    assert keyboard[second] == key_index
    assert second in keyboard


if __name__ == "__main__":
    unittest.main()
