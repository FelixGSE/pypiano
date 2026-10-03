from unittest.mock import MagicMock

import numpy as np
import pytest
from mingus.midi import pyfluidsynth

from pypiano.piano import Piano


@pytest.fixture
def sequencer() -> MagicMock:
    """A mock of mingus' FluidSynthSequencer, which needs libfluidsynth and a sound font."""
    mock = MagicMock(name="FluidSynthSequencer()")
    mock.load_sound_font.return_value = True
    mock.fs.get_samples.return_value = np.zeros(8, dtype=np.int16)
    return mock


@pytest.fixture
def delete_audio_driver(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Replace the low level fluidsynth call that deletes the audio driver."""
    mock = MagicMock(name="delete_fluid_audio_driver")
    monkeypatch.setattr(pyfluidsynth, "delete_fluid_audio_driver", mock)
    return mock


@pytest.fixture
def delete_synth(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Replace the low level fluidsynth calls that free the synthesizer and its settings on close."""
    mock = MagicMock(name="fluidsynth deletes")
    monkeypatch.setattr(pyfluidsynth, "delete_fluid_synth", mock.delete_fluid_synth)
    monkeypatch.setattr(pyfluidsynth, "delete_fluid_settings", mock.delete_fluid_settings)
    return mock


@pytest.fixture
def piano(sequencer: MagicMock, delete_audio_driver: MagicMock, delete_synth: MagicMock) -> Piano:  # noqa: ARG001 - requested for their patches
    """A Piano with the default sound fonts on top of the mocked sequencer."""
    return Piano(sequencer=sequencer)
