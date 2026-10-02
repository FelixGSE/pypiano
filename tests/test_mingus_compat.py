from ctypes import Array, c_char, c_void_p, memmove

import numpy as np
import pytest
from mingus.midi import pyfluidsynth

from pypiano import _mingus_compat


def test_compat_should_replace_mingus_helpers_when_imported() -> None:
    # Given pypiano is imported, which imports the compat module
    # When / Then
    assert pyfluidsynth.fluid_synth_write_s16_stereo is _mingus_compat.fluid_synth_write_s16_stereo
    assert pyfluidsynth.raw_audio_string is _mingus_compat.raw_audio_string


def test_write_s16_stereo_should_return_int16_samples_when_fluidsynth_fills_the_buffer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given fluidsynth renders two interleaved stereo frames
    rendered = np.array([1, -1, 2, -2], dtype=np.int16).tobytes()

    def fake_write_s16(_synth: object, _length: int, buf: Array[c_char], *_offsets: object) -> None:
        memmove(buf, rendered, len(rendered))

    monkeypatch.setattr(pyfluidsynth, "fluid_synth_write_s16", fake_write_s16)
    # When
    samples = _mingus_compat.fluid_synth_write_s16_stereo(c_void_p(), 2)
    # Then
    assert samples.dtype == np.int16
    assert samples.tolist() == [1, -1, 2, -2]


def test_raw_audio_string_should_return_int16_bytes_when_given_samples() -> None:
    # Given float samples
    samples = np.array([1.0, -2.0, 3.0])
    # When
    raw = _mingus_compat.raw_audio_string(samples)
    # Then
    assert raw == np.array([1, -2, 3], dtype=np.int16).tobytes()
