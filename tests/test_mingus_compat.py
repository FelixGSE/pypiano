from ctypes import Array, c_void_p, memmove

import numpy as np
import pytest
from mingus.midi import pyfluidsynth

from pypiano import _mingus_compat


def test_compat_should_replace_mingus_helpers_when_imported() -> None:
    # Given pypiano is imported, which imports the compat module
    # When / Then
    assert pyfluidsynth.fluid_synth_write_s16_stereo is _mingus_compat.fluid_synth_write_s16_stereo
    assert pyfluidsynth.raw_audio_string is _mingus_compat.raw_audio_string
    assert pyfluidsynth.Synth.set_channel_type is _mingus_compat.set_channel_type


def test_write_s16_stereo_should_return_int16_samples_when_fluidsynth_fills_the_buffer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given fluidsynth renders two interleaved stereo frames
    rendered = np.array([1, -1, 2, -2], dtype=np.int16).tobytes()
    calls: list[tuple[object, ...]] = []

    def fake_write_s16(*args: object) -> None:
        calls.append(args)
        buf = args[2]
        assert isinstance(buf, Array)
        memmove(buf, rendered, len(rendered))

    monkeypatch.setattr(pyfluidsynth, "fluid_synth_write_s16", fake_write_s16)
    synth = c_void_p()
    # When
    samples = _mingus_compat.fluid_synth_write_s16_stereo(synth, 2)
    # Then
    assert samples.dtype == np.int16
    assert samples.tolist() == [1, -1, 2, -2]
    # Left channel at offset 0 and right channel at offset 1 of the same buffer, both with a stride of 2 samples
    ((passed_synth, length, left, left_offset, left_stride, right, right_offset, right_stride),) = calls
    assert (passed_synth, length) == (synth, 2)
    assert left is right
    assert isinstance(left, Array)
    assert len(left) == 2 * 4  # 2 frames of 2 channels of 2 bytes
    assert (left_offset, left_stride, right_offset, right_stride) == (0, 2, 1, 2)


def test_raw_audio_string_should_return_int16_bytes_when_given_samples() -> None:
    # Given float samples
    samples = np.array([1.0, -2.0, 3.0])
    # When
    raw = _mingus_compat.raw_audio_string(samples)
    # Then
    assert raw == np.array([1, -2, 3], dtype=np.int16).tobytes()


def test_set_channel_type_should_succeed_exactly_when_the_channel_exists() -> None:
    # Given a real FluidSynth synthesizer with mingus' 256 channels, without sound font or audio driver
    synth = pyfluidsynth.Synth()
    try:
        # When / Then
        assert _mingus_compat.set_channel_type(synth, 9, _mingus_compat.CHANNEL_TYPE_MELODIC) == 0
        assert _mingus_compat.set_channel_type(synth, 256, _mingus_compat.CHANNEL_TYPE_MELODIC) == -1
    finally:
        pyfluidsynth.delete_fluid_synth(synth.synth)
        pyfluidsynth.delete_fluid_settings(synth.settings)
