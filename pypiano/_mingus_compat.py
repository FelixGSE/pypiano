"""Patches for mingus 0.6.1 (the latest release), applied to mingus.midi.pyfluidsynth when pypiano is imported.

- numpy >= 2.3: mingus still uses numpy.fromstring in binary mode and ndarray.tostring, both removed in numpy 2.3.
  fluid_synth_write_s16_stereo and raw_audio_string are replaced by the same functions using numpy.frombuffer and
  ndarray.tobytes. All callers in mingus look these functions up on the module at call time, so replacing the module
  attributes is sufficient.
- Audio drivers: Synth.start asserts that the audio driver is one of FluidSynth 1's, which rejects current ones such as
  pipewire or wasapi. It is replaced by the same method without that list. The added Synth.audio_drivers returns the
  drivers the loaded FluidSynth was built with, so PyPiano can check a driver name against them.
- Drum channel: mingus' Synth has no method to change a channel's type, which PyPiano needs to turn off the drum
  channel. The added Synth.set_channel_type binds fluid_synth_set_channel_type the way mingus binds the other functions.

The patches are process-wide: any other code using mingus.midi.pyfluidsynth in the same process gets them too. The
replaced functions and Synth.start behave like mingus' originals, apart from working with current numpy and FluidSynth.

They are adapted from mingus.midi.pyfluidsynth (pyFluidSynth, Copyright 2008-2009 Nathan Whitehead, released under the
LGPL), which PyPiano uses under the terms of the GPL.
"""

from ctypes import CFUNCTYPE, c_char_p, c_int, c_void_p, create_string_buffer

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


# fluid_settings_foreach_option_t: called with the data pointer, the setting's name and one of its options
FOREACH_OPTION = CFUNCTYPE(None, c_void_p, c_char_p, c_char_p)

fluid_settings_foreach_option = pyfluidsynth.cfunc(
    "fluid_settings_foreach_option",
    None,
    ("settings", c_void_p, 1),
    ("name", c_char_p, 1),
    ("data", c_void_p, 1),
    ("func", FOREACH_OPTION, 1),
)


def audio_drivers(self: pyfluidsynth.Synth) -> tuple[str, ...]:
    """Return the names of the audio drivers this FluidSynth was built with, such as ("alsa", "file", "jack")."""
    drivers: list[str] = []
    fluid_settings_foreach_option(
        self.settings,
        b"audio.driver",
        None,
        FOREACH_OPTION(lambda _data, _name, option: drivers.append(option.decode())),
    )
    return tuple(drivers)


def start(self: pyfluidsynth.Synth, driver: str | None = None) -> None:
    """Start the audio driver, or FluidSynth's default one when driver is None.

    Like mingus' Synth.start, without its list of FluidSynth 1 drivers. When the driver cannot start, for example
    without a sound device, FluidSynth logs an error and audio_driver is None.
    """
    if driver is not None:
        pyfluidsynth.fluid_settings_setstr(self.settings, b"audio.driver", driver.encode())
    self.audio_driver = pyfluidsynth.new_fluid_audio_driver(self.settings, self.synth)


# Deliberate monkeypatch: type checkers treat each module function as its own type, so the assignments are ignored.
pyfluidsynth.fluid_synth_write_s16_stereo = fluid_synth_write_s16_stereo  # ty: ignore[invalid-assignment]
pyfluidsynth.raw_audio_string = raw_audio_string  # ty: ignore[invalid-assignment]
pyfluidsynth.Synth.set_channel_type = set_channel_type  # ty: ignore[unresolved-attribute]
pyfluidsynth.Synth.audio_drivers = audio_drivers  # ty: ignore[unresolved-attribute]
pyfluidsynth.Synth.start = start
