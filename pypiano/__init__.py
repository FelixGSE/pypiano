"""Programmatically play piano on top of mingus and fluidsynth."""

from importlib.metadata import version

# Loads mingus' fluidsynth bindings first, so libfluidsynth is found before any other module imports them
from pypiano import _fluidsynth  # noqa: F401
from pypiano.errors import (
    AudioDriverError,
    InstrumentError,
    InstrumentTypeError,
    InvalidKeyIndexError,
    InvalidNoteError,
    PianoClosedError,
    PlaybackOptionError,
    PyPianoError,
    SoundFontError,
    UnknownNoteNameError,
    UnparsableNoteError,
    UnsupportedContainerError,
)
from pypiano.keyboard import KeyColor, NoteIdentity, PianoKey, PianoKeyboard
from pypiano.piano import DEFAULT_INSTRUMENTS, DEFAULT_SOUND_FONTS, AudioDriver, Instrument, Piano

__version__ = version("pypiano")

__all__ = [
    "DEFAULT_INSTRUMENTS",
    "DEFAULT_SOUND_FONTS",
    "AudioDriver",
    "AudioDriverError",
    "Instrument",
    "InstrumentError",
    "InstrumentTypeError",
    "InvalidKeyIndexError",
    "InvalidNoteError",
    "KeyColor",
    "NoteIdentity",
    "Piano",
    "PianoClosedError",
    "PianoKey",
    "PianoKeyboard",
    "PlaybackOptionError",
    "PyPianoError",
    "SoundFontError",
    "UnknownNoteNameError",
    "UnparsableNoteError",
    "UnsupportedContainerError",
    "__version__",
]
