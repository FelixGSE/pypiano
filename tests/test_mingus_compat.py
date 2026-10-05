from ctypes import Array, c_void_p, memmove
from pathlib import Path
from unittest.mock import MagicMock, call

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
    assert pyfluidsynth.Synth.audio_drivers is _mingus_compat.audio_drivers
    assert pyfluidsynth.Synth.start is _mingus_compat.start


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


def test_audio_drivers_should_return_fluidsynths_drivers_when_called() -> None:
    # Given a real FluidSynth synthesizer
    synth = pyfluidsynth.Synth()
    try:
        # When
        drivers = _mingus_compat.audio_drivers(synth)
    finally:
        pyfluidsynth.delete_fluid_synth(synth.synth)
        pyfluidsynth.delete_fluid_settings(synth.settings)
    # Then every FluidSynth has the file driver. Names beyond AudioDriver's, from a newer FluidSynth, are fine: the type
    # only guides type checkers, and play() accepts every driver this FluidSynth reports
    assert isinstance(drivers, tuple)
    assert "file" in drivers


@pytest.mark.parametrize(
    ("driver", "settings_calls"),
    [("pipewire", [call.setstr("settings", b"audio.driver", b"pipewire")]), (None, [])],
    ids=["given driver", "FluidSynth's default"],
)
def test_start_should_set_the_driver_and_create_it_when_called(
    monkeypatch: pytest.MonkeyPatch, driver: str | None, settings_calls: list[object]
) -> None:
    # Given FluidSynth's calls replaced, so their arguments can be checked without a sound device
    fluidsynth = MagicMock()
    monkeypatch.setattr(pyfluidsynth, "fluid_settings_setstr", fluidsynth.setstr)
    monkeypatch.setattr(pyfluidsynth, "new_fluid_audio_driver", fluidsynth.new_driver)
    synth = MagicMock(settings="settings", synth="synth")
    # When
    _mingus_compat.start(synth, driver)
    # Then
    assert fluidsynth.mock_calls == [*settings_calls, call.new_driver("settings", "synth")]
    assert synth.audio_driver is fluidsynth.new_driver.return_value


# Starts a real audio driver. It is also an integration test so that mutation testing, which runs only unit tests, never
# runs it: mutants that pass NULL to FluidSynth make it abort the process, which mutmut counts as "suspicious", not as
# caught. mutmut runs a mutant's tests in a random order, so the mocked test above could not reliably catch them first.
@pytest.mark.integration
def test_start_should_start_a_driver_outside_mingus_list_when_fluidsynth_has_it(tmp_path: Path) -> None:
    # Given a real FluidSynth synthesizer whose file driver writes to a temporary file; mingus only knows FluidSynth 1's
    # drivers, which don't include it
    synth = pyfluidsynth.Synth()
    pyfluidsynth.fluid_settings_setstr(synth.settings, b"audio.file.name", str(tmp_path / "out.raw").encode())
    try:
        # When
        _mingus_compat.start(synth, "file")
        started = synth.audio_driver
        pyfluidsynth.delete_fluid_audio_driver(started)
        _mingus_compat.start(synth, "SomeFantasyDriverName")
        unknown = synth.audio_driver
    finally:
        pyfluidsynth.delete_fluid_synth(synth.synth)
        pyfluidsynth.delete_fluid_settings(synth.settings)
    # Then the file driver starts, and an unknown one leaves no driver (FluidSynth logs an error)
    assert started is not None
    assert unknown is None
