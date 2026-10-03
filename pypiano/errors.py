"""Exceptions raised by PyPiano.

Every exception derives from PyPianoError, so `except PyPianoError` catches anything PyPiano raises on purpose. Each one
also derives from the built-in exception PyPiano raised before, so existing `except ValueError` (or `IndexError`,
`TypeError`, `RuntimeError`) clauses keep working.
"""


class PyPianoError(Exception):
    """Base class of all PyPiano errors."""


class SoundFontError(PyPianoError, RuntimeError):
    """A sound font file could not be loaded."""


class AudioDriverError(PyPianoError, ValueError):
    """The audio driver is not one FluidSynth supports."""


class InstrumentError(PyPianoError, ValueError):
    """The instrument name is not one of the default sound font's instruments."""


class InstrumentTypeError(PyPianoError, TypeError):
    """The instrument has the wrong type for the loaded sound font (a name for the default one, a number otherwise)."""


class InvalidNoteError(PyPianoError, ValueError):
    """A note is not on a piano with 88 keys."""


class UnknownNoteNameError(InvalidNoteError, IndexError):
    """A note name is not the name of any key on the keyboard."""


class InvalidKeyIndexError(PyPianoError, ValueError, IndexError):
    """A key index is outside 0 to 87."""


class UnsupportedContainerError(PyPianoError, TypeError):
    """The object passed to play is not a supported music container."""
