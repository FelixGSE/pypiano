from dataclasses import FrozenInstanceError

import pytest
from mingus.containers import Note

from pypiano.errors import InvalidKeyIndexError
from pypiano.keyboard import KeyColor, PianoKey, PianoKeyboard


@pytest.fixture
def keyboard() -> PianoKeyboard:
    return PianoKeyboard()


@pytest.fixture
def c4() -> PianoKey:
    return PianoKey(39)


# PianoKey


@pytest.mark.parametrize(
    ("key_index", "names"),
    [
        (0, ("A", "A", 0, "A-0/A-0")),
        (39, ("C", "B#", 4, "C-4/B#-3")),
        (40, ("C#", "Db", 4, "C#-4/Db-4")),
        (43, ("E", "Fb", 4, "E-4/Fb-4")),
        (44, ("F", "E#", 4, "F-4/E#-4")),
        (50, ("B", "Cb", 4, "B-4/Cb-5")),
        (87, ("C", "B#", 8, "C-8/B#-7")),
    ],
    ids=["A-0", "C-4", "C#-4", "E-4", "F-4", "B-4", "C-8"],
)
def test_piano_key_should_derive_its_names_and_octave_from_its_position(
    key_index: int, names: tuple[str, str, int, str]
) -> None:
    # Given a key by its position; octave numbers go up at C, so only B# and Cb are in another octave than the key
    key = PianoKey(key_index)
    # When
    derived = (key.first_identity, key.second_identity, key.octave, key.full_note_string)
    # Then
    assert derived == names


@pytest.mark.parametrize(("key_index", "color"), [(39, KeyColor.WHITE), (40, KeyColor.BLACK), (49, KeyColor.BLACK)])
def test_piano_key_should_be_black_exactly_when_its_first_name_is_sharp(key_index: int, color: KeyColor) -> None:
    # Given C-4, C#-4 and A#-4
    # When / Then
    assert PianoKey(key_index).key_color is color


@pytest.mark.parametrize(("note_string", "expected"), [("C-4", True), ("B#-3", True), ("B#-4", False), ("D-4", False)])
def test_piano_key_should_report_membership_when_checked_for_note_string(
    c4: PianoKey, note_string: str, *, expected: bool
) -> None:
    # Given a C-4 key
    # When
    is_contained = note_string in c4
    # Then
    assert is_contained is expected


def test_piano_key_should_return_mingus_notes_when_asked_for_identities(c4: PianoKey) -> None:
    # Given a C-4 key
    # When
    first, second = c4.first_note, c4.second_note
    # Then
    assert (first.name, first.octave) == ("C", 4)
    assert (second.name, second.octave) == ("B#", 3)


def test_piano_key_should_return_concert_pitch_when_key_is_a4() -> None:
    # Given the A-4 key
    a4 = PianoKey(48)
    # When
    frequency = a4.frequency
    # Then
    assert frequency == pytest.approx(440.0)


def test_piano_key_should_show_its_position_when_represented(c4: PianoKey) -> None:
    # Given a C-4 key
    # When / Then
    assert repr(c4) == "PianoKey(key_index=39)"


def test_piano_key_should_equal_hash_and_sort_by_position_when_compared(c4: PianoKey) -> None:
    # Given C-4, another C-4 and C#-4
    same, c_sharp = PianoKey(39), PianoKey(40)
    # When / Then
    assert same == c4
    assert hash(same) == hash(c4)
    assert len({same, c4}) == 1
    assert c_sharp != c4
    assert sorted([c_sharp, c4]) == [c4, c_sharp]


@pytest.mark.parametrize("attribute", ["key_index", "octave"])
def test_piano_key_should_raise_frozen_instance_error_when_an_attribute_is_assigned(
    c4: PianoKey, attribute: str
) -> None:
    # Given a C-4 key
    # When / Then
    with pytest.raises(FrozenInstanceError):
        setattr(c4, attribute, 40)
    assert c4.key_index == 39


@pytest.mark.parametrize("key_index", [-1, 88])
def test_piano_key_should_raise_invalid_key_index_error_when_not_one_of_the_88(key_index: int) -> None:
    # Given a position left of A-0 or right of C-8
    # When / Then
    with pytest.raises(
        InvalidKeyIndexError, match=rf"^A piano has 88 keys, so a key index is between 0 and 87\. Got {key_index}$"
    ):
        PianoKey(key_index)


# PianoKeyboard


def test_keyboard_should_have_88_keys_when_created(keyboard: PianoKeyboard) -> None:
    # Given a new keyboard
    # When
    keys = keyboard.keys
    # Then
    assert len(keys) == len(keyboard) == 88


def test_keyboard_should_have_52_white_and_36_black_keys_when_created(keyboard: PianoKeyboard) -> None:
    # Given a new keyboard
    # When
    white_keys, black_keys = keyboard.white_keys, keyboard.black_keys
    # Then
    assert len(white_keys) == 52
    assert len(black_keys) == 36
    assert {key.key_color for key in white_keys.values()} == {KeyColor.WHITE}
    assert {key.key_color for key in black_keys.values()} == {KeyColor.BLACK}


def test_keyboard_should_span_a0_to_c8_when_iterated(keyboard: PianoKeyboard) -> None:
    # Given a new keyboard
    # When
    keys = list(keyboard)
    # Then
    assert keys[0].first_note_string == "A-0"
    assert keys[-1].first_note_string == "C-8"
    assert [key.key_index for key in keys] == list(range(88))


def test_keyboard_should_return_piano_key_when_indexed_with_key_index(keyboard: PianoKeyboard) -> None:
    # Given a new keyboard
    # When
    key = keyboard[39]
    # Then
    assert isinstance(key, PianoKey)
    assert key.first_note_string == "C-4"


@pytest.mark.parametrize("key_index", [-1, 88])
def test_keyboard_should_raise_index_error_when_key_index_is_out_of_range(
    keyboard: PianoKeyboard, key_index: int
) -> None:
    # Given a new keyboard
    # When / Then
    with pytest.raises(IndexError, match="only 88 keys"):
        keyboard[key_index]


def test_keyboard_should_return_key_index_when_indexed_with_note_string(keyboard: PianoKeyboard) -> None:
    # Given a new keyboard
    # When
    key_index = keyboard["C-4"]
    # Then
    assert key_index == 39


def test_keyboard_should_raise_index_error_when_note_is_not_on_the_keyboard(keyboard: PianoKeyboard) -> None:
    # Given a new keyboard
    # When / Then
    with pytest.raises(IndexError, match="not a valid note on a piano"):
        keyboard["G-0"]


@pytest.mark.parametrize(
    ("note", "expected"),
    [("A-0", True), ("C-8", True), (Note("C-4"), True), ("G-0", False), (Note("D-8"), False)],
)
def test_keyboard_should_report_membership_when_checked_for_note(
    keyboard: PianoKeyboard, note: str | Note, *, expected: bool
) -> None:
    # Given a new keyboard
    # When
    is_contained = note in keyboard
    # Then
    assert is_contained is expected


def test_keyboard_should_show_key_counts_and_range_when_represented(keyboard: PianoKeyboard) -> None:
    # Given a new keyboard
    # When
    representation = repr(keyboard)
    # Then
    assert representation == ("PianoKeyboard(keys=88,white_keys=52,black_keys=36,first_key=A-0/A-0,last_key=C-8/B#-7)")


def test_keyboard_keys_should_have_identities_of_equal_pitch_when_created(keyboard: PianoKeyboard) -> None:
    # Given a new keyboard
    # When
    pitches = [(int(Note(key.first_note_string)), int(Note(key.second_note_string))) for key in keyboard]
    # Then
    assert all(first == second for first, second in pitches)


@pytest.mark.parametrize(
    ("first", "second"),
    [("C-4", "B#-3"), ("B-4", "Cb-5"), ("A-0", "A-0"), ("C-8", "B#-7")],
    ids=["C has B# of the octave below", "B has Cb of the octave above", "lowest key", "highest key"],
)
def test_keyboard_should_find_same_key_when_looked_up_by_either_identity(
    keyboard: PianoKeyboard, first: str, second: str
) -> None:
    # Given a new keyboard
    # When
    key_index = keyboard[first]
    # Then
    assert keyboard[second] == key_index
    assert second in keyboard


@pytest.mark.parametrize("partial_name", ["C", "-4", "4/", "b-5", "C-4/B#-3", ""])
def test_keyboard_should_raise_index_error_when_note_name_is_only_part_of_a_key_name(
    keyboard: PianoKeyboard, partial_name: str
) -> None:
    # Given a string that is only a substring of a key's names
    # When / Then
    with pytest.raises(IndexError, match="not a valid note on a piano"):
        keyboard[partial_name]
    assert partial_name not in keyboard


@pytest.mark.parametrize("partial_name", ["C", "-4", "B#", "C-4/B#-3"])
def test_piano_key_should_not_contain_note_name_when_it_is_only_part_of_a_key_name(
    c4: PianoKey, partial_name: str
) -> None:
    # Given a C-4 key and a substring of its names
    # When
    is_contained = partial_name in c4
    # Then
    assert not is_contained


def test_keyboard_should_find_every_key_when_looked_up_by_either_of_its_names(keyboard: PianoKeyboard) -> None:
    # Given a new keyboard
    # When
    found = [(keyboard[key.first_note_string], keyboard[key.second_note_string]) for key in keyboard]
    # Then
    assert found == [(index, index) for index in range(88)]


def test_keyboard_should_return_a_copy_when_asked_for_distinct_key_names(keyboard: PianoKeyboard) -> None:
    # Given the set of key names
    names = keyboard.distinct_key_names
    # When it is changed by the caller
    names.clear()
    # Then the keyboard still knows all names
    assert "C-4" in keyboard
    assert len(keyboard.distinct_key_names) == 154
