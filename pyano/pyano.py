# -*- coding: utf-8 -*-
"""
"""
import logging
import pkg_resources
import time

from mingus.containers import Note, NoteContainer, Bar, Track
from mingus.midi.fluidsynth import FluidSynthSequencer
from mingus.midi import pyfluidsynth as fs

from typing import Union, List
from pathlib import Path
from .keyboard import PianoKeyboard, PianoKey
from .decorators import record
from .utils import PianoUtils

DEFAULT_SOUND_FONTS = pkg_resources.resource_filename(
    "pyano", "/sound_fonts/FluidR3_GM.sf2"
)

# See docstring of start_audio_output method of FluidSynthSequencer class
# https://github.com/bspaans/python-mingus/blob/f131620eb7353bcfbf1303b24b951a95cad2ac20/mingus/midi/fluidsynth.py#L57
VALID_AUDIO_DRIVERS = (
    None,
    "alsa",
    "oss",
    "jack",
    "portaudio",
    "sndmgr",
    "coreaudio",
    "Direct Sound",
    "dsound",
    "pulseaudio",
)

# See a list of General Midi instruments here https://en.wikipedia.org/wiki/General_MIDI
# Pianos are in section one
DEFAULT_INSTRUMENTS = {
    "Acoustic Grand Piano": 0,
    "Bright Acoustic Piano": 1,
    "Electric Grand Piano": 2,
    "Honky-tonk Piano": 3,
    "Electric Piano 1": 4,
    "Electric Piano 2": 5,
    "Harpsichord": 6,
    "Clavi": 7,
}

# Initialize module logger
logger = logging.getLogger("pyano")
logger.addHandler(logging.NullHandler())


class Piano(FluidSynthSequencer):
    """Class representing a Piano with 88 keys based on mingus

    """

    def __init__(
            self,
            audio_driver: Union[str, None] = None,
            instrument: str = "Acoustic Grand Piano",
    ) -> None:

        super().__init__()

        # Load sound fonts
        self.sound_fonts_path = Path(DEFAULT_SOUND_FONTS)
        self._init_sf_file()

        self.audio_driver = audio_driver

        # Set a variable to signal other parts of the program whether an audio output is currently active
        self._audio_driver_is_active = False
        self._start_audio_output(self.audio_driver)

        # Set instrument
        self.instrument = instrument
        self._init_instrument()

        # Create a piano keyboard
        self.keyboard = PianoKeyboard()

    def _start_audio_output(self, audio_driver: Union[str, None] = None) -> None:
        """Start audio output

        """
        if audio_driver not in VALID_AUDIO_DRIVERS:
            raise ValueError(
                "{driver} is not a valid audio driver. Must be one of: {allowed_drivers}".format(
                    driver=audio_driver, allowed_drivers=VALID_AUDIO_DRIVERS
                )
            )
        if not self._audio_driver_is_active:
            self.start_audio_output(audio_driver)
            self.fs.program_reset()
            self._audio_driver_is_active = True
        else:
            logger.warning("Audio output seems to be already active")

    def _stop_audio_output(self) -> None:
        """Private method to stop audio output

        Method is used to stop audio output, for example if there is a switch between audio output and recording.
        It is a thin wrapper for the fluidsynth function fs.delete_fluid_audio_driver. Function should ensure that
        fs.delete_fluid_audio_driver is not called twice because this seems to to cause segmentation fault:
            [1]    4059 segmentation fault  python3
        """
        if self._audio_driver_is_active:
            fs.delete_fluid_audio_driver(self.fs.audio_driver)
            self._audio_driver_is_active = False
        else:
            logger.warning("Audio output seems to be already inactive")

    @property
    def instrument(self) -> None:
        return self._instrument

    @instrument.setter
    def instrument(self, instrument: str) -> None:

        if instrument not in tuple(DEFAULT_INSTRUMENTS.keys()):
            raise ValueError(
                "Unknown instrument parameter. Instrument must be in {instrument}".format(
                    instrument=instrument
                )
            )

        self.set_instrument(channel=1, instr=DEFAULT_INSTRUMENTS[instrument], bank=0)
        self._instrument = instrument

    def _init_sf_file(self) -> None:
        """

        """
        logger.debug(
            "Attempting to load sound fonts from {file}".format(file=self.sound_fonts_path)
        )

        if not self.load_sound_font(str(self.sound_fonts_path)):
            logger.exception(
                "Could not load sound fonts from {file_path}".format(
                    file_path=self.sound_fonts_path
                )
            )
            raise Exception("Oh no")

        logger.debug(
            "Successfully initialized sound fonts from {file_path}".format(
                file_path=self.sound_fonts_path
            )
        )

    def _init_instrument(self) -> None:
        """

        """
        if self.instrument not in tuple(DEFAULT_INSTRUMENTS.keys()):
            raise ValueError(
                "Unknown instrument parameter. Instrument must be in {instrument}".format(
                    instrument=instrument
                )
            )

        self.set_instrument(channel=1, instr=DEFAULT_INSTRUMENTS[self.instrument], bank=0)

    @record
    def play_note(self, note: Union[Note, str],
                  recording_file: Union[str, None] = None,
                  seconds: int = 4,
                  stop_recording=True) -> None:
        """

        """
        self.play_Note(note)

    @record
    def play_note_container(self, note_container: Union[NoteContainer, List[Note], List[str]],
                            recording_file: Union[str, None] = None,
                            seconds: int = 4,
                            stop_recording=True) -> None:
        """

        """
        self.play_NoteContainer(note_container)

    @record
    def play_note_container(self, note_container: Union[NoteContainer, List[Note], List[str]],
                            recording_file: Union[str, None] = None,
                            seconds: int = 4,
                            stop_recording=True) -> None:
        """

        """
        self.play_NoteContainer(note_container)

    @record
    def play_bar(self, bar: Union[Bar, List[Note], List[str]],
                 recording_file: Union[str, None] = None,
                 seconds: int = 4,
                 stop_recording=True) -> None:
        """

        """
        self.play_Bar(bar)

    def play(self,
             notes: Union[str, Note, NoteContainer, Bar, Track, PianoKey],
             recording_file: Union[str, Path, None] = None,
             record_seconds: int = 4,
             stop_recording: bool = True
             ) -> None:
        """

        """

        if recording_file is None:

            if not self._audio_driver_is_active:
                self._start_audio_output()
            self._play_music_container(notes)

        else:

            self._stop_audio_output()
            self.start_recording(recording_file)
            self.fs.program_reset()
            self._play_music_container(notes)
            samples = fs.raw_audio_string(self.fs.get_samples(int(record_seconds * 44100)))
            self.wav.writeframes(bytes(samples))

            if stop_recording:
                self.wav.close()
                self._start_audio_output()

    def _play_music_container(self,
                              music_container: Union[str, Note, NoteContainer, Bar, Track, PianoKey]) -> None:
        """

        """
        self._lint_music_container(music_container)

        if isinstance(music_container, str) or isinstance(music_container, Note):
            self.play_Note(music_container)
        elif isinstance(music_container, NoteContainer):
            self.play_NoteContainer(music_container)
        elif isinstance(music_container, Bar):
            self.play_Bar(music_container)
        elif isinstance(music_container, Track):
            self.play_Track(music_container)

    def stop(self, music_container: Union[str, Note, NoteContainer, Bar, Track, PianoKey]) -> None:
        """Currently not working

        """
        if isinstance(music_container, str):
            try:
                note = Note(music_container)
                self.stop_Note(note)
            except Exception as e:
                raise ValueError("If a string is passed it must have the form <NOTE_NAME><ACCIDENTAL>-<Ocatave>")
        elif isinstance(music_container, NoteContainer):
            self.stop_NoteContainer(music_container)
        else:
            # At the moment there is no dedicated low level method to stop Bars and Tracks, therefore in case of
            # A Bar or Track is passed, everything will be stopped
            self.stop_everything()

    @staticmethod
    def pause(duration: int) -> None:
        """

        """
        time.sleep(duration)

    def _lint_music_container(self, music_container: Union[str, Note, NoteContainer, Bar]) -> None:
        """

        """
        if isinstance(music_container, str):
            note = Note(music_container)
            distinct_notes_in_container = {PianoUtils.note_to_string(note)}
        elif isinstance(music_container, Note):
            distinct_notes_in_container = {PianoUtils.note_to_string(music_container)}
        elif isinstance(music_container, NoteContainer):
            distinct_notes_in_container = set(PianoUtils.note_container_to_note_string_list(music_container))
        elif isinstance(music_container,Bar):
            distinct_notes_in_container = set(PianoUtils.bar_to_note_string_list(music_container))
        elif isinstance(music_container, Track):
            distinct_notes_in_container = set(PianoUtils.track_to_note_string_list(music_container))
        else:
            raise Exception("OMG")

        diff = distinct_notes_in_container - self.keyboard.distinct_key_names
        if len(diff) > 0:
            raise ValueError(
                "Found notes that are not on a piano with 88 keys. Invalid notes in container: {0}".format(diff)
            )