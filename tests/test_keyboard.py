# -*- coding: utf-8 -*-
import unittest
from pyano.keyboard import PianoKeyboard


class KeyboardTests(unittest.TestCase):
    """Basic test cases."""

    def setUp(self) -> None:
        self.keyboard = PianoKeyboard()

    def test_init_keyboard(self):
        self.assertEqual(len(PianoKeyboard._create_keyboard_dict()), 88)

    def test_white_keys(self):
        self.assertEqual(len(self.keyboard.white_keys), 52)

    def test_black_keys(self):
        self.assertEqual(len(self.keyboard.black_keys), 36)


if __name__ == "__main__":
    unittest.main()
