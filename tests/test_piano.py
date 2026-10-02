import unittest
from pathlib import Path
from unittest.mock import patch

import pytest
from mingus.containers import Bar, Note, NoteContainer, Track

from pypiano import piano

from .mock_objects import MockFluidSynthSequencer


@patch("pypiano.piano.FluidSynthSequencer", return_value=MockFluidSynthSequencer())
class PianoTests(unittest.TestCase):
    """Basic test cases."""

    def test_load_sound_fonts(self, mock_fluid_synth_sequencer) -> None:
        p = piano.Piano()
        new_sf_path = "/fantasypath/fantasyfile.sf2"

        p._sound_fonts_loaded = True
        p.load_sound_fonts(new_sf_path)
        assert p._sound_fonts_loaded
        assert p._sound_fonts_path == Path(new_sf_path)

        p._sound_fonts_loaded = False
        p.load_sound_fonts(new_sf_path)
        assert p._sound_fonts_loaded
        assert p._sound_fonts_path == Path(new_sf_path)

    def test_unload_sound_fonts(self, mock_fluid_synth_sequencer) -> None:
        p = piano.Piano()
        assert p._sound_fonts_loaded
        assert p._sound_fonts_loaded is not None

        p._unload_sound_fonts()
        assert not p._sound_fonts_loaded
        assert p._sound_fonts_path is None

    def test_start_audio_output(self, mock_fluid_synth_sequencer) -> None:
        p = piano.Piano()

        # Start with empty audio driver
        assert not p._audio_driver_is_active
        p._start_audio_output()
        assert p._audio_driver_is_active
        # Check for idempotency
        p._start_audio_output()
        assert p._audio_driver_is_active

        p._current_audio_driver = "SomeFantasyDriverName"
        with pytest.raises(ValueError, match="is not a valid audio driver"):
            p._start_audio_output()

    @patch("pypiano.piano.globalfs.delete_fluid_audio_driver", return_value=None)
    def test_stop_audio_output(self, mock_fluid_synth_sequencer, mock_delete_fluid_audio_driver) -> None:
        p = piano.Piano()
        # Start with empty audio driver
        assert not p._audio_driver_is_active
        # Check that p._audio_driver_is_active is still False after calling it again
        p._stop_audio_output()
        assert not p._audio_driver_is_active

        p._audio_driver_is_active = True
        p._stop_audio_output()
        assert not p._audio_driver_is_active

    def test_load_instrument(self, mock_fluid_synth_sequencer) -> None:
        p = piano.Piano()

        with pytest.raises(TypeError):
            p.load_instrument(instrument=1)
        with pytest.raises(ValueError, match="Unknown instrument parameter"):
            p.load_instrument(instrument="FantasyInstrument")
        new_instrument = "Bright Acoustic Piano"
        p.load_instrument(instrument=new_instrument)
        assert p.instrument == new_instrument

        # Test cases for non default sound fonts
        p._sound_fonts_path = "/fantasypath/fantasyfile.sf2"
        with pytest.raises(TypeError):
            p.load_instrument(instrument=new_instrument)

        new_instrument = 1
        p.load_instrument(instrument=new_instrument)
        assert p.instrument == new_instrument

    @patch("pypiano.piano.globalfs.raw_audio_string", return_value=1)
    def test_play(self, mock_fluid_synth_sequencer, mock_raw_audio_string) -> None:

        p = piano.Piano()

        p.play("C-4", recording_file=None)
        assert p._audio_driver_is_active

        p.play("C-4", recording_file="test.wav")
        assert not p._audio_driver_is_active

    def test_lint_music_container(self, mock_fluid_synth_sequencer) -> None:

        p = piano.Piano()
        outside_left = Note("G-0")
        outside_right = Note("D-8")
        with pytest.raises(ValueError, match="Found notes that are not on a piano"):
            p._lint_music_container(music_container=outside_left)
        with pytest.raises(ValueError, match="Found notes that are not on a piano"):
            p._lint_music_container(music_container=outside_right)

        note_container = NoteContainer([outside_left, outside_left])
        with pytest.raises(ValueError, match="Found notes that are not on a piano"):
            p._lint_music_container(music_container=note_container)

        bar = Bar()
        bar.place_notes([outside_left, outside_right], 2)
        with pytest.raises(ValueError, match="Found notes that are not on a piano"):
            p._lint_music_container(music_container=bar)

        track = Track()
        track.add_bar(bar)
        with pytest.raises(ValueError, match="Found notes that are not on a piano"):
            p._lint_music_container(music_container=track)
