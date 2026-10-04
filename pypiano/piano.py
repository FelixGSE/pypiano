"""Play and record music containers on an 88 key piano."""

import copy
import logging
import math
import time
from importlib.resources import files
from pathlib import Path
from types import TracebackType
from typing import Literal, Self, TypeAlias

from mingus.containers import Bar, Note, NoteContainer, Track
from mingus.midi import pyfluidsynth as globalfs
from mingus.midi.fluidsynth import FluidSynthSequencer

from pypiano._mingus_compat import CHANNEL_TYPE_MELODIC  # importing it also patches mingus (see its docstring)
from pypiano.errors import (
    AudioDriverError,
    InstrumentError,
    InstrumentTypeError,
    InvalidKeyIndexError,
    InvalidNoteError,
    PianoClosedError,
    PlaybackOptionError,
    SoundFontError,
    UnsupportedContainerError,
)
from pypiano.keyboard import PianoKey, PianoKeyboard
from pypiano.utils import note_name, notes_in

# MIDI channel 10, which General MIDI reserves for drums; mingus counts channels from 0
DRUM_CHANNEL = 9

DEFAULT_SOUND_FONTS = Path(str(files("pypiano") / "sound_fonts" / "FluidR3_GM_pianos.sf2"))

# The audio drivers of FluidSynth 2.0 to 2.6 (src/drivers/fluid_adriver.c). Which of them a FluidSynth has depends on
# its version (2.4.4 added sdl3, 2.5 removed sdl2), the platform and how it was built; see Synth.audio_drivers(), or
# `fluidsynth -a help`
AudioDriver: TypeAlias = Literal[
    "alsa",
    "coreaudio",
    "dart",
    "dsound",
    "file",
    "jack",
    "kai",
    "oboe",
    "opensles",
    "oss",
    "pipewire",
    "portaudio",
    "pulseaudio",
    "sdl2",
    "sdl3",
    "sndman",
    "wasapi",
    "waveout",
]

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

# Sample rate fluidsynth renders at, used for wav recordings
WAV_SAMPLE_FREQUENCY = 44100

# Range of MIDI velocities and mingus' default tempo for bars and tracks
MAX_VELOCITY = 127
DEFAULT_BPM = 120

# The mingus containers Piano.play turns its input into, and the sequencer method that plays each of them
MusicContainer: TypeAlias = Note | NoteContainer | Bar | Track
PLAY_METHODS: dict[type, str] = {
    Note: "play_Note",
    NoteContainer: "play_NoteContainer",
    Bar: "play_Bar",
    Track: "play_Track",
}

# Initialize module logger
logger = logging.getLogger("pypiano")
logger.addHandler(logging.NullHandler())


class Piano:
    """Class representing a Piano with 88 keys based on mingus.

    Class to programmatically play piano via audio output or record music to a wav file. Abstraction layer on top of
    mingus.midi.fluidsynth.FluidSynthSequencer.

    Attributes:
        sound_fonts_path: Optional string or Path object pointing to a *.sf2 files. PyPiano ships sound fonts by default
        audio_driver: Optional FluidSynth audio driver to play through, such as "pipewire", "pulseaudio", "coreaudio" or
            "wasapi", or None for FluidSynth's default. Which drivers exist depends on the platform and how FluidSynth
            was built
        instrument: Optional argument to set the instrument that should be used. If default sound fonts are used you can
            choose one of the following pianos sounds:
            ("Acoustic Grand Piano", "Bright Acoustic Piano", "Electric Grand Piano", "Honky-tonk Piano",
             "Electric Piano 1", "Electric Piano 2", "Harpsichord", "Clavi"). If different sound fonts are provided
             you should also pass an integer with the instrument number

    """

    def __init__(
        self,
        sound_fonts_path: str | Path = DEFAULT_SOUND_FONTS,
        audio_driver: AudioDriver | None = None,
        instrument: str | int = "Acoustic Grand Piano",
        *,
        sequencer: FluidSynthSequencer | None = None,
    ) -> None:
        """Load the sound fonts and instrument. Audio output is started lazily on the first play.

        Args:
            sound_fonts_path: Path to a *.sf2 sound font file. Defaults to the one bundled with PyPiano
            audio_driver: FluidSynth audio driver to use for playback, None for FluidSynth's default
            instrument: Instrument name for the default sound fonts, or instrument number for other sound fonts
            sequencer: mingus sequencer to play through. Defaults to a new FluidSynthSequencer; pass one to customize
                or replace it, for example in tests

        """
        self._sequencer = FluidSynthSequencer() if sequencer is None else sequencer
        # FluidSynth gives the drum channel the drum bank 128, which the bundled sound font, with only pianos, lacks, so
        # every program reset warned "No preset found on channel 9". PyPiano plays on channel 1 only, so the drum
        # channel becomes a normal one on bank 0, like the other channels.
        self._sequencer.fs.set_channel_type(DRUM_CHANNEL, CHANNEL_TYPE_MELODIC)  # ty: ignore[unresolved-attribute] - added by _mingus_compat
        self._sequencer.fs.bank_select(DRUM_CHANNEL, 0)
        # The state flags marked "no mutate" are only ever checked for truthiness or overwritten before use, so mutation
        # testing's False -> None (or True) changes cannot change behavior; they are excluded as equivalent mutants
        self._closed = False  # pragma: no mutate

        self._sound_fonts_path: Path | None = None  # pragma: no mutate
        # Set variable to track if sound fonts are loaded
        self._sound_fonts_loaded = False  # pragma: no mutate
        # Whether the loaded sound fonts are PyPiano's default ones, which take instrument names instead of numbers
        self._uses_default_sound_fonts = False  # pragma: no mutate
        self.load_sound_fonts(sound_fonts_path)

        # Audio output is lazily loaded when self.play method is called the first time without recording
        self._current_audio_driver = audio_driver
        # Set a variable to track if audio output is currently active
        self._audio_driver_is_active = False  # pragma: no mutate

        # Set instrument
        self.load_instrument(instrument)

        # Initialize a piano keyboard
        self.keyboard = PianoKeyboard()

    def __enter__(self) -> Self:
        """Use the Piano as a context manager that closes it on exit."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Close the Piano."""
        self.close()

    def close(self) -> None:
        """Stop audio output and release FluidSynth's synthesizer. Calling it again does nothing.

        After closing, play, load_sound_fonts and load_instrument raise PianoClosedError.
        """
        if self._closed:
            return
        self._stop_audio_output()
        self._unload_sound_fonts()
        synth = self._sequencer.fs
        globalfs.delete_fluid_synth(synth.synth)
        globalfs.delete_fluid_settings(synth.settings)
        # mingus' FluidSynthSequencer.__del__ calls Synth.delete() on garbage collection, which frees these handles
        # again and crashes. With NULL handles FluidSynth's delete functions do nothing
        synth.synth = None
        synth.settings = None
        self._closed = True
        logger.debug("Closed the piano")  # pragma: no mutate

    def _ensure_open(self) -> None:
        if self._closed:
            msg = "The piano is closed"
            raise PianoClosedError(msg)

    def load_sound_fonts(self, sound_fonts_path: str | Path) -> None:
        """Load sound fonts from a given path."""
        self._ensure_open()
        logger.debug("Attempting to load sound fonts from %s", sound_fonts_path)  # pragma: no mutate

        if self._sound_fonts_loaded:
            self._unload_sound_fonts()

        if not self._sequencer.load_sound_font(str(sound_fonts_path)):
            msg = f"Could not load sound fonts from {sound_fonts_path}"
            raise SoundFontError(msg)

        self._sound_fonts_loaded = True
        self._sound_fonts_path = Path(sound_fonts_path)
        # Compare resolved paths, so the default file loaded through another path still counts as the default
        self._uses_default_sound_fonts = self._sound_fonts_path.resolve() == DEFAULT_SOUND_FONTS.resolve()

        logger.debug("Successfully initialized sound fonts from %s", sound_fonts_path)  # pragma: no mutate

    def _unload_sound_fonts(self) -> None:
        """Unload a given sound font file.

        Safely unload current sound font file. Method controls if a sound font file is already loaded via
        self._sound_fonts_loaded.
        """
        logger.debug("Unloading current active sound fonts from file: %s", self._sound_fonts_path)  # pragma: no mutate

        if self._sound_fonts_loaded:
            self._sequencer.fs.sfunload(self._sequencer.sfid)
            self._sound_fonts_loaded = False  # pragma: no mutate
            self._sound_fonts_path = None
            self._uses_default_sound_fonts = False  # pragma: no mutate
        else:
            logger.debug("No active sound fonts")  # pragma: no mutate

    def _start_audio_output(self) -> None:
        """Private method to start audio output.

        This method in conjunction with self._stop_audio_output should be used to safely start and stop audio output,
        for example when there is switch between audio output and recording audio to a file (check doc string of
        self._stop_audio_output for more details why this necessary). This method replaces
        mingus.midi.fluidsynth.FluidSynthSequencer
        """
        logger.debug("Starting audio output using driver: %s", self._current_audio_driver)  # pragma: no mutate

        driver = self._current_audio_driver
        if driver is not None and driver not in (available := self._sequencer.fs.audio_drivers()):  # ty: ignore[unresolved-attribute] - added by _mingus_compat
            msg = f"FluidSynth has no audio driver {driver!r}. This FluidSynth has: {', '.join(available)}"
            raise AudioDriverError(msg)
        if not self._audio_driver_is_active:
            self._sequencer.start_audio_output(self._current_audio_driver)
            # It seems to be necessary to reset the program after starting audio output
            # mingus.midi.pyfluidsynth.program_reset() is calling fluidsynth fluid_synth_program_reset()
            # https://www.fluidsynth.org/api/group__midi__messages.html#ga8a0e442b5013876affc685b88a6e3f49
            self._sequencer.fs.program_reset()
            self._audio_driver_is_active = True
        else:
            logger.debug("Audio output seems to be already active")  # pragma: no mutate

    def _stop_audio_output(self) -> None:
        """Private method to stop audio output.

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
            globalfs.delete_fluid_audio_driver(self._sequencer.fs.audio_driver)
            # mingus never resets this handle; its Synth.delete(), which FluidSynthSequencer.__del__ calls on garbage
            # collection, would delete the driver a second time
            self._sequencer.fs.audio_driver = None
            # It seems to be necessary to reset the program after starting audio output
            # mingus.midi.pyfluidsynth.program_reset() is calling fluidsynth fluid_synth_program_reset()
            # https://www.fluidsynth.org/api/group__midi__messages.html#ga8a0e442b5013876affc685b88a6e3f49
            self._sequencer.fs.program_reset()
            self._audio_driver_is_active = False  # pragma: no mutate
        else:
            logger.debug("Audio output seems to be already inactive")  # pragma: no mutate

    def load_instrument(self, instrument: str | int) -> None:
        """Change the piano instrument.

        Load an instrument that should be used for playing or recording music. If PyPiano default sound fonts are used
        you can choose one of the following instruments:
            ("Acoustic Grand Piano", "Bright Acoustic Piano", "Electric Grand Piano", "Honky-tonk Piano",
             "Electric Piano 1", "Electric Piano 2", "Harpsichord", "Clavi")

        Args:
            instrument: String with the name of the instrument to be used for default sound fonts. If different sound
                fonts are used an integer with the instrument number should be provided.

        """
        self._ensure_open()
        logger.debug("Setting instrument: %s", instrument)  # pragma: no mutate

        # If default sound fonts are used, check if the provided instrument string is contained in the valid
        # instruments. If different sound fonts are provided, checks are disabled
        if self._uses_default_sound_fonts:
            if isinstance(instrument, int):
                msg = "When using default sound fonts you must pass a string for instrument parameter"
                raise InstrumentTypeError(msg)

            if instrument not in tuple(DEFAULT_INSTRUMENTS.keys()):
                msg = f"Unknown instrument parameter. Instrument must be one of: {tuple(DEFAULT_INSTRUMENTS.keys())}"
                raise InstrumentError(msg)

            self._sequencer.set_instrument(channel=1, instr=DEFAULT_INSTRUMENTS[instrument], bank=0)
            self.instrument = instrument

        else:
            if isinstance(instrument, str):
                msg = "When using non default sound fonts you must pass an integer for instrument parameter"
                raise InstrumentTypeError(msg)

            self._sequencer.set_instrument(channel=1, instr=instrument, bank=0)
            self.instrument = instrument

    def play(
        self,
        music_container: str | int | Note | NoteContainer | Bar | Track | PianoKey,
        recording_file: str | Path | None = None,
        record_seconds: float = 4,
        *,
        bpm: float = DEFAULT_BPM,
        velocity: int | None = None,
    ) -> None:
        """Play a provided music container and control recording settings.

        Central user facing method of Piano class to play or record a given music container. Handles setting
        up audio output or recording to audio file and handles switching between playing audio and recording to wav
        file.

        Args:
            music_container: A music container such as Notes, NoteContainers, etc. describing a piece of music
            recording_file: Path to a wav file where audio should be saved to. If passed music_container will be
                recorded
            record_seconds: The duration of recording in seconds
            bpm: Tempo in beats per minute for Bars and Tracks. Notes and NoteContainers ignore it
            velocity: How hard the keys are struck, from 0 to 127. None keeps each note's own velocity (mingus'
                default is 64). A given velocity applies to every note; the music container passed in is not changed

        Raises:
            InvalidNoteError: If the music container has notes that are not on a piano with 88 keys
            InvalidKeyIndexError: If a key index is outside 0 to 87
            UnsupportedContainerError: If the music container type is not supported
            AudioDriverError: If FluidSynth has no audio driver of the configured name
            PlaybackOptionError: If bpm or record_seconds is not a positive finite number, or velocity is not an
                integer from 0 to 127
            PianoClosedError: If the piano was closed

        """
        self._ensure_open()
        self._check_playback_options(bpm=bpm, velocity=velocity, record_seconds=record_seconds)
        container = self._normalize(music_container)
        self._validate(container)
        if velocity is not None:
            container = self._with_velocity(container, velocity)

        if recording_file is None:
            logger.debug("Playing music container: %s via audio", container)  # pragma: no mutate
            self._start_audio_output()
            self._play_container(container, bpm)

        else:
            logger.debug("Recording music container: %s to file %s", container, recording_file)  # pragma: no mutate
            self._stop_audio_output()
            self._sequencer.start_recording(str(recording_file))
            self._play_container(container, bpm)

            samples = globalfs.raw_audio_string(
                self._sequencer.fs.get_samples(int(record_seconds * WAV_SAMPLE_FREQUENCY)),
            )
            self._sequencer.wav.writeframes(bytes(samples))

            self._sequencer.wav.close()

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
            delattr(self._sequencer, "wav")

            logger.debug("Finished recording to %s", recording_file)  # pragma: no mutate

    def _normalize(self, music_container: str | int | Note | NoteContainer | Bar | Track | PianoKey) -> MusicContainer:
        """Turn what play accepts into a mingus music container.

        A note string is parsed into a Note once, a key index or PianoKey becomes the Note of its first identity, and
        mingus containers are returned unchanged.

        Raises:
            InvalidKeyIndexError: If a key index is outside 0 to 87
            UnsupportedContainerError: If the music container type is not supported

        """
        if isinstance(music_container, str):
            return Note(music_container)
        if isinstance(music_container, PianoKey):
            return music_container.first_note
        if isinstance(music_container, int):
            if music_container not in self.keyboard.keys:
                msg = f"Key index must be between 0 and {len(self.keyboard) - 1}. Got {music_container}"
                raise InvalidKeyIndexError(msg)
            return self.keyboard.keys[music_container].first_note
        if isinstance(music_container, (Note, NoteContainer, Bar, Track)):
            return music_container
        msg = f"Unsupported music container type: {type(music_container)}"
        raise UnsupportedContainerError(msg)

    @staticmethod
    def _check_playback_options(*, bpm: float, velocity: int | None, record_seconds: float) -> None:
        """Check the playback options of play before anything is played.

        Raises:
            PlaybackOptionError: If bpm or record_seconds is not a positive finite number, or velocity is not an
                integer from 0 to 127

        """
        for name, value in (("bpm", bpm), ("record_seconds", record_seconds)):
            if not math.isfinite(value) or value <= 0:
                msg = f"{name} must be a positive finite number. Got {value}"
                raise PlaybackOptionError(msg)
        # bool is an int subclass, and mingus would silently truncate a float
        if velocity is not None and (
            isinstance(velocity, bool) or not isinstance(velocity, int) or not 0 <= velocity <= MAX_VELOCITY
        ):
            msg = f"velocity must be an integer between 0 and {MAX_VELOCITY}. Got {velocity!r}"
            raise PlaybackOptionError(msg)

    def _validate(self, container: MusicContainer) -> None:
        """Check that every note of a music container is on a piano with 88 keys.

        Notes are compared by pitch, so any spelling works, also those the keyboard has no name for, such as C##-4
        (which is D-4).

        Raises:
            InvalidNoteError: If the music container has notes that are not on a piano with 88 keys

        """
        lowest, highest = (
            int(self.keyboard.keys[0].first_note),
            int(self.keyboard.keys[len(self.keyboard) - 1].first_note),
        )
        invalid_notes = {note_name(note) for note in notes_in(container) if not lowest <= int(note) <= highest}
        if invalid_notes:
            msg = f"Found notes that are not on a piano with 88 keys. Invalid notes in container: {invalid_notes}"
            raise InvalidNoteError(msg)

    @staticmethod
    def _with_velocity(container: MusicContainer, velocity: int) -> MusicContainer:
        """Return a copy of the music container with every note set to the velocity.

        mingus plays each note with the velocity stored on the Note, which overrides the velocity argument of its play
        methods, and Bars and Tracks take no velocity at all. Setting it on a copy covers every container type without
        changing the caller's notes.

        """
        container = copy.deepcopy(container)
        for note in notes_in(container):
            note.velocity = velocity
        return container

    def _play_container(self, container: MusicContainer, bpm: float) -> None:
        """Play a music container with the mingus sequencer method for its type (or the closest base type)."""
        method = next(PLAY_METHODS[cls] for cls in type(container).__mro__ if cls in PLAY_METHODS)
        # play_Bar and play_Track take the tempo; play_Note and play_NoteContainer take none
        options = {"bpm": bpm} if method in {"play_Bar", "play_Track"} else {}
        logger.debug("Playing music container: %s with %s %s", container, method, options)  # pragma: no mutate
        getattr(self._sequencer, method)(container, **options)

    @staticmethod
    def pause(seconds: int) -> None:
        """Pause further execution for a given time.

        Args:
            seconds: Time to pause further execution in seconds

        """
        time.sleep(seconds)
