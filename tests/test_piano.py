# -*- coding: utf-8 -*-
import unittest
from unittest.mock import patch
from pypiano import piano
from pathlib import Path
from .mock_objects import MockFluidSynthSequencer
from mingus.containers import Note, NoteContainer, Bar, Track


@patch("pypiano.piano.FluidSynthSequencer", return_value=MockFluidSynthSequencer())
class PianoTests(unittest.TestCase):
    """Basic test cases."""

    def test_load_sound_fonts(self, mock_fluid_synth_sequencer) -> None:
        p = piano.Piano()
        new_sf_path = "/fantasypath/fantasyfile.sf2"

        p._sound_fonts_loaded = True
        p.load_sound_fonts(new_sf_path)
        self.assertEqual(p._sound_fonts_loaded, True)
        self.assertEqual(p._sound_fonts_path, Path(new_sf_path))

        p._sound_fonts_loaded = False
        p.load_sound_fonts(new_sf_path)
        self.assertEqual(p._sound_fonts_loaded, True)
        self.assertEqual(p._sound_fonts_path, Path(new_sf_path))

    def test_unload_sound_fonts(self, mock_fluid_synth_sequencer) -> None:
        p = piano.Piano()
        self.assertEqual(p._sound_fonts_loaded, True)
        self.assertNotEqual(p._sound_fonts_loaded, None)

        p._unload_sound_fonts()
        self.assertEqual(p._sound_fonts_loaded, False)
        self.assertEqual(p._sound_fonts_path, None)

    def test_start_audio_output(self, mock_fluid_synth_sequencer) -> None:
        p = piano.Piano()

        # Start with empty audio driver
        self.assertEqual(p._audio_driver_is_active, False)
        p._start_audio_output()
        self.assertEqual(p._audio_driver_is_active, True)
        # Check for idempotency
        p._start_audio_output()
        self.assertEqual(p._audio_driver_is_active, True)

        p._current_audio_driver = "SomeFantasyDriverName"
        self.assertRaises(ValueError, p._start_audio_output)

    @patch("pypiano.piano.globalfs.delete_fluid_audio_driver", return_value=None)
    def test_stop_audio_output(self, mock_fluid_synth_sequencer, mock_delete_fluid_audio_driver) -> None:
        p = piano.Piano()
        # Start with empty audio driver
        self.assertEqual(p._audio_driver_is_active, False)
        # Check that p._audio_driver_is_active is still False after calling it again
        p._stop_audio_output()
        self.assertEqual(p._audio_driver_is_active, False)

        p._audio_driver_is_active = True
        p._stop_audio_output()
        self.assertEqual(p._audio_driver_is_active, False)

    def test_load_instrument(self, mock_fluid_synth_sequencer) -> None:
        p = piano.Piano()

        self.assertRaises(TypeError, p.load_instrument, instrument=1)
        self.assertRaises(ValueError, p.load_instrument, instrument="FantasyInstrument")
        new_instrument = "Bright Acoustic Piano"
        p.load_instrument(instrument=new_instrument)
        self.assertEqual(p.instrument, new_instrument)

        # Test cases for non default sound fonts
        p._sound_fonts_path = "/fantasypath/fantasyfile.sf2"
        self.assertRaises(TypeError, p.load_instrument, instrument=new_instrument)

        new_instrument = 1
        p.load_instrument(instrument=new_instrument)
        self.assertEqual(p.instrument, new_instrument)

    @patch("pypiano.piano.globalfs.raw_audio_string", return_value=1)
    def test_play(self, mock_fluid_synth_sequencer, mock_raw_audio_string):

        p = piano.Piano()

        p.play("C-4", recording_file=None)
        self.assertEqual(p._audio_driver_is_active, True)

        p.play("C-4", recording_file="test.wav")
        self.assertEqual(p._audio_driver_is_active, False)

    def test_lint_music_container(self, mock_fluid_synth_sequencer):

        p = piano.Piano()
        outside_left = Note("G-0")
        outside_right = Note("D-8")
        self.assertRaises(ValueError, p._lint_music_container, music_container=outside_left)
        self.assertRaises(ValueError, p._lint_music_container, music_container=outside_right)

        note_container = NoteContainer([outside_left, outside_left])
        self.assertRaises(ValueError, p._lint_music_container, music_container=note_container)

        bar = Bar()
        bar.place_notes([outside_left, outside_right], 2)
        self.assertRaises(ValueError, p._lint_music_container, music_container=bar)

        track = Track()
        track.add_bar(bar)
        self.assertRaises(ValueError, p._lint_music_container, music_container=track)
