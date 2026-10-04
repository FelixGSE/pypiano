"""Programmatically play piano on top of mingus and fluidsynth."""

from importlib.metadata import version

# Loads mingus' fluidsynth bindings first, so libfluidsynth is found before any other module imports them
from pypiano import _fluidsynth  # noqa: F401
from pypiano.keyboard import PianoKey, PianoKeyboard
from pypiano.piano import DEFAULT_INSTRUMENTS, DEFAULT_SOUND_FONTS, Piano

__version__ = version("pypiano")

__all__ = ["DEFAULT_INSTRUMENTS", "DEFAULT_SOUND_FONTS", "Piano", "PianoKey", "PianoKeyboard", "__version__"]
