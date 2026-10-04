import pytest
from mingus.containers import Note

from pypiano.keyboard import KeyColor, NoteIdentity, PianoKey, PianoKeyboard


@pytest.fixture
def keyboard() -> PianoKeyboard:
    return PianoKeyboard()


@pytest.fixture
def c4() -> PianoKey:
    return PianoKey("C", "B#", 4, "white", key_index=39, second_octave=3)


# PianoKey


def test_piano_key_should_combine_both_identities_when_asked_for_full_note_string(c4: PianoKey) -> None:
    # Given a C-4 key
    # When
    full_note_string = c4.full_note_string
    # Then
    assert full_note_string == "C-4/B#-3"


def test_piano_key_should_return_first_note_string_when_indexed_with_zero(c4: PianoKey) -> None:
    # Given a C-4 key
    # When
    note_string = c4[0]
    # Then
    assert note_string == "C-4"


def test_piano_key_should_return_second_note_string_when_indexed_with_one(c4: PianoKey) -> None:
    # Given a C-4 key
    # When
    note_string = c4[1]
    # Then
    assert note_string == c4.second_note_string == "B#-3"


def test_piano_key_should_default_second_octave_to_octave_when_not_given() -> None:
    # Given a C#-4 key created without a second octave
    key = PianoKey("C#", "Db", 4, "black")
    # When
    note_string = key.second_note_string
    # Then
    assert note_string == "Db-4"


@pytest.mark.parametrize(("color", "expected"), [("white", KeyColor.WHITE), (KeyColor.BLACK, KeyColor.BLACK)])
def test_piano_key_should_store_a_key_color_when_given_a_color_or_its_name(
    color: KeyColor | str, expected: KeyColor
) -> None:
    # Given a color as an enum member or as the plain string it equals
    # When
    key = PianoKey("C", "B#", 4, color)
    # Then
    assert key.key_color is expected
    assert key.key_color == expected.value


def test_piano_key_should_raise_index_error_when_indexed_beyond_its_two_identities(c4: PianoKey) -> None:
    # Given a C-4 key
    # When / Then
    with pytest.raises(IndexError, match=r"^Out of range\. PianoKey has only two indices$"):
        c4[2]


@pytest.mark.parametrize(("note_string", "expected"), [("C-4", True), ("B#-3", True), ("B#-4", False), ("D-4", False)])
def test_piano_key_should_report_membership_when_checked_for_note_string(
    c4: PianoKey, note_string: str, *, expected: bool
) -> None:
    # Given a C-4 key
    # When
    is_contained = note_string in c4
    # Then
    assert is_contained is expected


def test_piano_key_should_raise_value_error_when_color_is_neither_black_nor_white() -> None:
    # Given an invalid key color
    # When / Then
    with pytest.raises(ValueError, match="white or black"):
        PianoKey("C", "B#", 4, "red")


def test_piano_key_should_return_mingus_notes_when_asked_for_identities(c4: PianoKey) -> None:
    # Given a C-4 key
    # When
    first, second = c4.first_note, c4.second_note
    # Then
    assert (first.name, first.octave) == ("C", 4)
    assert (second.name, second.octave) == ("B#", 3)


def test_piano_key_should_return_concert_pitch_when_key_is_a4() -> None:
    # Given the A-4 key
    a4 = PianoKey("A", "A", 4, "white")
    # When
    frequency = a4.frequency
    # Then
    assert frequency == pytest.approx(440.0)


@pytest.mark.parametrize(("identity", "expected"), [("first", ("C", 4)), ("second", ("B#", 3))])
def test_piano_key_should_return_note_when_identity_is_valid(
    c4: PianoKey, identity: NoteIdentity, expected: tuple[str, int]
) -> None:
    # Given a C-4 key
    # When
    note = c4.get_as_note(identity)
    # Then
    assert (note.name, note.octave) == expected


@pytest.mark.parametrize(("identity", "expected"), [("first", "C-4"), ("second", "B#-3")])
def test_piano_key_should_return_note_string_when_identity_is_valid(
    c4: PianoKey, identity: NoteIdentity, expected: str
) -> None:
    # Given a C-4 key
    # When
    note_string = c4.get_as_string(identity)
    # Then
    assert note_string == expected


@pytest.mark.parametrize("method", ["get_as_note", "get_as_string"])
def test_piano_key_should_raise_value_error_when_identity_is_invalid(c4: PianoKey, method: str) -> None:
    # Given a C-4 key
    # When / Then
    with pytest.raises(ValueError, match="Must be 'first' or 'second'"):
        getattr(c4, method)("third")


def test_piano_key_should_show_all_attributes_when_represented(c4: PianoKey) -> None:
    # Given a C-4 key
    # When
    representation = repr(c4)
    # Then
    assert representation == (
        "PianoKey(first_identity=C,second_identity=B#,octave=4,second_octave=3,key_color=white,key_index=39)"
    )


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


def test_piano_key_should_return_first_identity_when_no_identity_is_given(c4: PianoKey) -> None:
    # Given a C-4 key
    # When
    note, note_string = c4.get_as_note(), c4.get_as_string()
    # Then
    assert (note.name, note.octave) == ("C", 4)
    assert note_string == "C-4"
