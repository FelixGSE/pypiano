"""Patches for mingus 0.6.1 (the latest release) to work with numpy >= 2.3.

mingus.midi.pyfluidsynth still uses numpy.fromstring in binary mode and ndarray.tostring, both removed in numpy 2.3.
The replacements below are the same functions using numpy.frombuffer and ndarray.tobytes. All callers in mingus look
these functions up on the module at call time, so replacing the module attributes is sufficient.
"""

from ctypes import c_void_p, create_string_buffer

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


pyfluidsynth.fluid_synth_write_s16_stereo = fluid_synth_write_s16_stereo
pyfluidsynth.raw_audio_string = raw_audio_string
