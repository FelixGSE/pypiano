"""Patches for mingus 0.6.1 (the latest release) to work with numpy >= 2.3.

mingus.midi.pyfluidsynth still uses numpy.fromstring in binary mode and ndarray.tostring, both removed in numpy 2.3.
The replacements below are the same functions using numpy.frombuffer and ndarray.tobytes. All callers in mingus look
these functions up on the module at call time, so replacing the module attributes is sufficient.

The patch is process-wide: any other code using mingus.midi.pyfluidsynth in the same process gets these functions too.
They behave the same as mingus' originals, apart from working with current numpy.

They are adapted from mingus.midi.pyfluidsynth (pyFluidSynth, Copyright 2008-2009 Nathan Whitehead, released under the
LGPL), which PyPiano uses under the terms of the GPL.

mingus' Synth also has no method to change a channel's type, which PyPiano needs to turn off the drum channel. The
set_channel_type method added below binds fluid_synth_set_channel_type the way mingus binds the other functions.
"""

from ctypes import c_int, c_void_p, create_string_buffer

import numpy as np
from mingus.midi import pyfluidsynth


def fluid_synth_write_s16_stereo(synth: c_void_p, length: int) -> np.ndarray:
    """Return generated samples in stereo 16-bit format as a numpy array."""
    buf = create_string_buffer(length * 4)
    pyfluidsynth.fluid_synth_write_s16(synth, length, buf, 0, 2, buf, 1, 2)
    return np.frombuffer(buf.raw, dtype=np.int16)


def raw_audio_string(data: np.ndarray) -> bytes:
    """Return the samples as 16-bit signed bytes to send to the soundcard or a wav file."""
    return data.astype(np.int16).tobytes()


# fluid_midi_channel_type in FluidSynth's synth.h
CHANNEL_TYPE_MELODIC = 0

fluid_synth_set_channel_type = pyfluidsynth.cfunc(
    "fluid_synth_set_channel_type", c_int, ("synth", c_void_p, 1), ("chan", c_int, 1), ("type", c_int, 1)
)


def set_channel_type(self: pyfluidsynth.Synth, chan: int, channel_type: int) -> int:
    """Make a channel melodic or a drum channel. Returns 0 (FLUID_OK), or -1 (FLUID_FAILED) for an invalid channel."""
    return fluid_synth_set_channel_type(self.synth, chan, channel_type)


# Deliberate monkeypatch: type checkers treat each module function as its own type, so the assignments are ignored.
pyfluidsynth.fluid_synth_write_s16_stereo = fluid_synth_write_s16_stereo  # ty: ignore[invalid-assignment]
pyfluidsynth.raw_audio_string = raw_audio_string  # ty: ignore[invalid-assignment]
pyfluidsynth.Synth.set_channel_type = set_channel_type  # ty: ignore[unresolved-attribute]
