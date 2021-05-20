# -*- coding: utf-8 -*-
"""
"""
import logging
import pkg_resources
import time

from mingus.containers import Note, NoteContainer, Bar, Track
from mingus.midi.fluidsynth import FluidSynthSequencer
from mingus.midi import pyfluidsynth as globalfs

from typing import Union
from pathlib import Path
from .keyboard import PianoKeyboard, PianoKey

from .utils import (
    note_to_string,
    note_container_to_note_string_list,
    bar_to_note_string_list,
    track_to_note_string_list,
)

DEFAULT_SOUND_FONTS = Path(pkg_resources.resource_filename("pypiano", "/sound_fonts/FluidR3_GM.sf2"))

# Valid audio driver are taken from docstring of mingus.midi.fluidsynth.FluidSynthSequencer.start_audio_output() method
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

# See a list of General Midi instruments here https://en.wikipedia.org/wiki/General_MIDI. Pianos are in section one
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
logger = logging.getLogger("pypiano")
logger.addHandler(logging.NullHandler())


class Piano(object):
    """Class representing a Piano with 88 keys based on mingus

    Class to programmatically play piano via audio output or record music to a wav file. Abstraction layer on top of
    mingus.midi.fluidsynth.FluidSynthSequencer.

    Attributes
        sound_fonts_path: Optional string or Path object pointing to a *.sf2 files. PyPiano ships sound fonts by default
        audio_driver: Optional argument specifying audio driver to use. Following audio drivers could be used:
            (None, "alsa", "oss", "jack", "portaudio", "sndmgr", "coreaudio","Direct Sound", "dsound", "pulseaudio").
            Not all drivers will be available for every platform
        instrument: Optional argument to set the instrument that should be used. If default sound fonts are used you can
            choose one of the following pianos sounds:
            ("Acoustic Grand Piano", "Bright Acoustic Piano", "Electric Grand Piano", "Honky-tonk Piano",
             "Electric Piano 1", "Electric Piano 2", "Harpsichord", "Clavi"). If different sound fonts are provided
             you should also pass an integer with the instrument number
    """

    def __init__(
        self,
        sound_fonts_path: Union[str, Path] = DEFAULT_SOUND_FONTS,
        audio_driver: Union[str, None] = None,
        instrument: Union[str, int] = "Acoustic Grand Piano",
    ) -> None:

        self.__fluid_synth_sequencer = FluidSynthSequencer()

        self._sound_fonts_path = Path(sound_fonts_path)
        # Set variable to track if sound fonts are loaded
        self._sound_fonts_loaded = False
        self.load_sound_fonts(self._sound_fonts_path)

        # Audio output is lazily loaded when self.play method is called the first time without recording
        self._current_audio_driver = audio_driver
        # Set a variable to track if audio output is currently active
        self._audio_driver_is_active = False

        # Set instrument
        self.instrument = instrument
        self.load_instrument(self.instrument)

        # Initialize a piano keyboard
        self.keyboard = PianoKeyboard()

    def load_sound_fonts(self, sound_fonts_path: Union[str, Path]) -> None:
        """Load sound fonts from a given path"""
        logger.debug("Attempting to load sound fonts from {file}".format(file=sound_fonts_path))

        if self._sound_fonts_loaded:

            self._unload_sound_fonts()

        if not self.__fluid_synth_sequencer.load_sound_font(str(sound_fonts_path)):
            raise Exception("Could not load sound fonts from {file}".format(file=sound_fonts_path))

        self._sound_fonts_loaded = True
        self._sound_fonts_path = Path(sound_fonts_path)

        logger.debug("Successfully initialized sound fonts from {file_path}".format(file_path=sound_fonts_path))

    def _unload_sound_fonts(self) -> None:
        """Unload a given sound font file

        Safely unload current sound font file. Method controls if a sound font file is already loaded via
        self._sound_fonts_loaded.
        """

        logger.debug("Unloading current active sound fonts from file: {0}".format(self._sound_fonts_path))

        if self._sound_fonts_loaded:
            self.__fluid_synth_sequencer.fs.sfunload(self.__fluid_synth_sequencer.sfid)
            self._sound_fonts_loaded = False
            self._sound_fonts_path = None
        else:
            logger.debug("No active sound fonts")

    def _start_audio_output(self) -> None:
        """Private method to start audio output

        This method in conjunction with self._stop_audio_output should be used to safely start and stop audio output,
        for example when there is switch between audio output and recording audio to a file (check doc string of
        self._stop_audio_output for more details why this necessary). This method replaces
        mingus.midi.fluidsynth.FluidSynthSequencer
        """

        logger.debug("Starting audio output using driver: {driver}".format(driver=self._current_audio_driver))

        # That is actually already done by the low level method and is included here again for transparency
        if self._current_audio_driver not in VALID_AUDIO_DRIVERS:
            raise ValueError(
                "{driver} is not a valid audio driver. Must be one of: {allowed_drivers}".format(
                    driver=self._current_audio_driver,
                    allowed_drivers=VALID_AUDIO_DRIVERS,
                )
            )
        if not self._audio_driver_is_active:
            self.__fluid_synth_sequencer.start_audio_output(self._current_audio_driver)
            # It seems to be necessary to reset the program after starting audio output
            # mingus.midi.pyfluidsynth.program_reset() is calling fluidsynth fluid_synth_program_reset()
            # https://www.fluidsynth.org/api/group__midi__messages.html#ga8a0e442b5013876affc685b88a6e3f49
            self.__fluid_synth_sequencer.fs.program_reset()
            self._audio_driver_is_active = True
        else:
            logger.debug("Audio output seems to be already active")

    def _stop_audio_output(self) -> None:
        """Private method to stop audio output

        Method is used to safely stop audio output via deleting an active audio driver, for example if there
        is a switch between audio output and recording. This method should be used in conjunction with
        self._start_audio_output(). It is a thin wrapper around the  mingus.midi.pyfluidsynth.delete_fluid_audio_driver
        and ensures that mingus.midi.pyfluidsynth.delete_fluid_audio_driver is not called twice because this seems to
        result in segmentation fault:

            [1]    4059 segmentation fault  python3

        Tracking is done via checking and setting self._audio_driver_is_active attribute. This method basically
        replaces mingus.midi.pyfluidsynth.delete() (which is also basically a wrapper for
        mingus.midi.pyfluidsynth.delete_fluid_audio_driver), because the delete method from the mingus package seems not
        safe to use and results in a crash if for some reason is called after an audio driver was already deleted and
        there isn't currently an active one. Despite the mingus.midi.pyfluidsynth.delete method seems to attempt to
        check if an audio driver is present and tries to avoid such a scenario via checking
        mingus.midi.pyfluidsynth.audio_driver argument for None. However once an audio driver was initialized the
        audio_driver argument seems to be never set back to None and therefore it seems you can't rely on checking that
        argument to know if an audio is active.

        I am not sure if it is a good way to do it that way and if it has any side effects, but it seems to work so far
        and enables switching between recording to a file and playing audio output without initializing a new object.
        """
        if self._audio_driver_is_active:
            globalfs.delete_fluid_audio_driver(self.__fluid_synth_sequencer.fs.audio_driver)
            # It seems to be necessary to reset the program after starting audio output
            # mingus.midi.pyfluidsynth.program_reset() is calling fluidsynth fluid_synth_program_reset()
            # https://www.fluidsynth.org/api/group__midi__messages.html#ga8a0e442b5013876affc685b88a6e3f49
            self.__fluid_synth_sequencer.fs.program_reset()
            self._audio_driver_is_active = False
        else:
            logger.debug("Audio output seems to be already inactive")

    def load_instrument(self, instrument: Union[str, int]) -> None:
        """Method to change the piano instrument

        Load an instrument that should be used for playing or recording music. If PyPiano default sound fonts are used
        you can choose one of the following instruments:
            ("Acoustic Grand Piano", "Bright Acoustic Piano", "Electric Grand Piano", "Honky-tonk Piano",
             "Electric Piano 1", "Electric Piano 2", "Harpsichord", "Clavi")
        Args
            instrument: String with the name of the instrument to be used for default sound founts. If different sound
                fonts are used an integer with the instrument number should be provided.
        """
        logger.info("Setting instrument: {0}".format(instrument))

        # If default sound fonts are used, check if the provided instrument string is contained in the valid
        # instruments. If different sound fonts are provided, checks are disabled
        if self._sound_fonts_path == DEFAULT_SOUND_FONTS:

            if isinstance(instrument, int):
                raise TypeError("When using default sound fonts you must pass a string for instrument parameter")

            if instrument not in tuple(DEFAULT_INSTRUMENTS.keys()):
                raise ValueError(
                    "Unknown instrument parameter. Instrument must be one of: {instrument}".format(
                        instrument=tuple(DEFAULT_INSTRUMENTS.keys())
                    )
                )

            self.__fluid_synth_sequencer.set_instrument(channel=1, instr=DEFAULT_INSTRUMENTS[instrument], bank=0)
            self.instrument = instrument

        else:

            if isinstance(instrument, str):
                raise TypeError("When using non default sound fonts you must pass an integer for instrument parameter")

            self.__fluid_synth_sequencer.set_instrument(channel=1, instr=instrument, bank=0)
            self.instrument = instrument

    def play(
        self,
        music_container: Union[str, int, Note, NoteContainer, Bar, Track, PianoKey],
        recording_file: Union[str, None] = None,
        record_seconds: int = 4,
    ) -> None:
        """Function to play a provided music container and control recording settings

        Central user facing method of Piano class to play or record a given music container. Handles setting
        up audio output or recording to audio file and handles switching between playing audio and recording to wav
        file.

        Args
            music_container: A music container such as Notes, NoteContainers, etc. describing a piece of music
            recording_file: Path to a wav file where audio should be saved to. If passed music_container will be
                recorded
            record_seconds: The duration of recording in seconds
        """

        # Check a given music container for invalid notes. See docstring of self._lint_music_container for more details
        self._lint_music_container(music_container)

        if recording_file is None:

            logger.info("Playing music container: {music_container} via audio".format(music_container=music_container))
            self._start_audio_output()
            self._play_music_container(music_container)

        else:

            logger.info(
                "Recording music container: {music_container} to file {recording_file}".format(
                    music_container=music_container, recording_file=recording_file
                )
            )
            self._stop_audio_output()
            self.__fluid_synth_sequencer.start_recording(recording_file)
            self._play_music_container(music_container)

            WAV_SAMPLE_FREQUENCY = 44100

            samples = globalfs.raw_audio_string(
                self.__fluid_synth_sequencer.fs.get_samples(int(record_seconds * WAV_SAMPLE_FREQUENCY))
            )
            self.__fluid_synth_sequencer.wav.writeframes(bytes(samples))

            self.__fluid_synth_sequencer.wav.close()

            # It seems we have to delete the wav attribute after recording in order to enable switching between
            # audio output and recording for all music containers. The
            # mingus.midi.fluidsynth.FluidSynthSequencer.play_Bar and
            # mingus.midi.fluidsynth.FluidSynthSequencer.play_Track use the
            # mingus.midi.fluidsynth.FluidSynthSequencer.sleep methods internally which is for some reason also used
            # to record in mingus.
            # See also my issue in the mingus repository: https://github.com/bspaans/python-mingus/issues/77
            # When wav attribute is present sleep tries to write to the wave file and if not the method just sleeps.
            # If we do not delete the wav attribute it is still there as None and play_Bar tries to write to the file
            # resulting in AttributeError: 'NoneType' object has no attribute 'write'
            delattr(self.__fluid_synth_sequencer, "wav")

            logger.info("Finished recording to {recording_file}".format(recording_file=recording_file))

    def _play_music_container(
        self,
        music_container: Union[str, int, Note, NoteContainer, Bar, Track, PianoKey],
    ) -> None:
        """Private method to call the appropriate low level play method for given music container class

        mingus.midi.fluidsynth exposes a few different methods to play different music containers, such as Notes or
        NoteContainers, etc. This should be abstracted for the user and this function calls the appropriate low level
        play method from mingus.midi.fluidsynth

        Args
            music_container: A music container such as Notes, NoteContainers, etc. describing a piece of music
        """

        logger.debug(
            "Attempting to play music container: {music_container} of type: {container_type}".format(
                music_container=music_container,
                container_type=str(type(music_container)),
            )
        )

        if isinstance(music_container, str):
            self.__fluid_synth_sequencer.play_Note(Note(music_container))
        elif isinstance(music_container, int):
            # FIX ME: Added another type check to fix mypy error
            piano_key = self.keyboard[music_container]
            if isinstance(piano_key, int):
                raise TypeError("This should not happen")
            self.__fluid_synth_sequencer.play_Note(piano_key.first_note)
        elif isinstance(music_container, Note):
            self.__fluid_synth_sequencer.play_Note(music_container)
        elif isinstance(music_container, NoteContainer):
            self.__fluid_synth_sequencer.play_NoteContainer(music_container)
        elif isinstance(music_container, Bar):
            self.__fluid_synth_sequencer.play_Bar(music_container)
        elif isinstance(music_container, Track):
            self.__fluid_synth_sequencer.play_Track(music_container)

        logger.debug(
            "Done playing music container: {music_container} of type: {container_type}".format(
                music_container=music_container,
                container_type=str(type(music_container)),
            )
        )

    def _lint_music_container(self, music_container: Union[str, Note, NoteContainer, Bar, Track]) -> None:
        """Check a music container for invalid notes

        Method checks a given music container like mingus.containers.Note or more complex containers like Tracks, etc.
        for notes that can't be found on a piano with 88 keys. In case a string is passed it also checks whether it can
        be parsed as a mingus.containers.Note.

        Args
            music_container: A music container such as Notes, NoteContainers, etc. describing a piece of music

        Raises
            ValueError: If illegal notes in given music container are found
        """

        logger.debug(
            "Checking music container: {container} of class {container_type} for invalid notes".format(
                container=music_container, container_type=str(type(music_container))
            )
        )

        if isinstance(music_container, str):
            note = Note(music_container)
            distinct_notes_in_container = {note_to_string(note)}
        elif isinstance(music_container, Note):
            distinct_notes_in_container = {note_to_string(music_container)}
        elif isinstance(music_container, NoteContainer):
            distinct_notes_in_container = set(note_container_to_note_string_list(music_container))
        elif isinstance(music_container, Bar):
            distinct_notes_in_container = set(bar_to_note_string_list(music_container))
        elif isinstance(music_container, Track):
            distinct_notes_in_container = set(track_to_note_string_list(music_container))
        else:
            raise Exception("Unexpected Error")

        diff = distinct_notes_in_container - self.keyboard.distinct_key_names
        if len(diff) > 0:
            raise ValueError(
                "Found notes that are not on a piano with 88 keys. Invalid notes in container: {0}".format(diff)
            )

        logger.debug(
            "Music container: {container} of class {container_type} looks good".format(
                container=music_container, container_type=str(type(music_container))
            )
        )

    @staticmethod
    def pause(seconds: int) -> None:
        """Pause further execution for a given time

        Args
            duration: Time to pause further execution in seconds
        """
        time.sleep(seconds)
