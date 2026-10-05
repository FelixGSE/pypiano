"""Play and record music containers on an 88 key piano."""

import copy
import errno
import logging
import math
import numbers
import os
import time
import wave
from collections.abc import Iterator
from enum import StrEnum
from importlib.resources import files
from pathlib import Path
from types import TracebackType
from typing import Literal, Self, TypeAlias

import numpy as np
from mingus.containers import Bar, Note, NoteContainer, Track
from mingus.containers.mt_exceptions import NoteFormatError
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
    UnparsableNoteError,
    UnsupportedContainerError,
)
from pypiano.keyboard import PianoKey, PianoKeyboard
from pypiano.utils import note_name, notes_in

# MIDI channel 10, which General MIDI reserves for drums; mingus counts channels from 0
DRUM_CHANNEL = 9
# The channel PyPiano selects the instrument on and plays every note on, mingus' default channel
PLAY_CHANNEL = 1
# MIDI control change "All Sound Off": silences every voice of a channel at once, without a release
ALL_SOUND_OFF = 120
# MIDI control change "All Notes Off": releases every note of a channel, which then fades out like a released key
ALL_NOTES_OFF = 123

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


class Instrument(StrEnum):
    """The eight pianos of General MIDI, which the bundled sound font has.

    Members compare equal to their General MIDI names, so "Clavi" and Instrument.CLAVI work alike. They are in General
    MIDI's order (https://en.wikipedia.org/wiki/General_MIDI), so program is the program number, which selects the same
    piano in any other General MIDI sound font.
    """

    ACOUSTIC_GRAND_PIANO = "Acoustic Grand Piano"
    BRIGHT_ACOUSTIC_PIANO = "Bright Acoustic Piano"
    ELECTRIC_GRAND_PIANO = "Electric Grand Piano"
    HONKY_TONK_PIANO = "Honky-tonk Piano"
    ELECTRIC_PIANO_1 = "Electric Piano 1"
    ELECTRIC_PIANO_2 = "Electric Piano 2"
    HARPSICHORD = "Harpsichord"
    CLAVI = "Clavi"

    @property
    def program(self) -> int:
        """General MIDI program number, counted from 0."""
        return list(Instrument).index(self)


# Program number by name, of the instruments the bundled sound font has. Derived from Instrument, which load_instrument
# checks names against, so changing this dict changes nothing
DEFAULT_INSTRUMENTS = {instrument.value: instrument.program for instrument in Instrument}

# Sample rate fluidsynth renders at, used for wav recordings, and the size of one frame: 2 channels of 16-bit samples
WAV_SAMPLE_FREQUENCY = 44100
BYTES_PER_FRAME = 4
# A recording that has to be longer than its music is filled up a second at a time
PAD_CHUNK_FRAMES = WAV_SAMPLE_FREQUENCY
# FluidSynth dithers its 16-bit output, so even silence peaks at 1
SILENCE_PEAK = 1
# While stopped voices and the reverb fade, FluidSynth renders 10 ms at a time (441 frames), for at most 5 seconds
FADE_CHUNK_FRAMES = 441
MAX_FADE_SECONDS = 5

# Range of MIDI velocities, mingus' default tempo for bars and tracks, and how long a Note or NoteContainer sounds
MAX_VELOCITY = 127
DEFAULT_BPM = 120
DEFAULT_DURATION = 1.0

# What Piano.play and Piano.record take, the mingus containers they turn it into, and the sequencer methods that play
# and stop each of them. Bars and Tracks stop their notes themselves, after each note's value at the tempo
MusicInput: TypeAlias = str | int | Note | NoteContainer | Bar | Track | PianoKey
MusicContainer: TypeAlias = Note | NoteContainer | Bar | Track
PLAY_METHODS: dict[type, tuple[str, str | None]] = {
    Note: ("play_Note", "stop_Note"),
    NoteContainer: ("play_NoteContainer", "stop_NoteContainer"),
    Bar: ("play_Bar", None),
    Track: ("play_Track", None),
}

# Initialize module logger
logger = logging.getLogger("pypiano")
logger.addHandler(logging.NullHandler())


class Piano:
    """Class representing a Piano with 88 keys based on mingus.

    Class to programmatically play piano via audio output or record music to a wav file. Abstraction layer on top of
    mingus.midi.fluidsynth.FluidSynthSequencer. A Piano is not thread-safe: use each one from one thread at a time.

    Attributes:
        sound_fonts_path: Optional string or Path object pointing to a *.sf2 files. PyPiano ships sound fonts by default
        audio_driver: Optional FluidSynth audio driver to play through, such as "pipewire", "pulseaudio", "coreaudio" or
            "wasapi", or None for FluidSynth's default. Which drivers exist depends on the platform and how FluidSynth
            was built
        instrument: The instrument to play. With the default sound fonts, an Instrument or its name, such as
            Instrument.CLAVI or "Clavi". With other sound fonts, an Instrument or a program number

    """

    def __init__(
        self,
        sound_fonts_path: str | Path = DEFAULT_SOUND_FONTS,
        audio_driver: AudioDriver | None = None,
        instrument: Instrument | str | int = Instrument.ACOUSTIC_GRAND_PIANO,
        *,
        sequencer: FluidSynthSequencer | None = None,
    ) -> None:
        """Load the sound fonts and instrument. Audio output is started lazily on the first play.

        Args:
            sound_fonts_path: Path to a *.sf2 sound font file. Defaults to the one bundled with PyPiano
            audio_driver: FluidSynth audio driver to use for playback, None for FluidSynth's default
            instrument: An Instrument or its name for the default sound fonts; an Instrument or a program number for
                other sound fonts
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
        # Without load_sound_fonts' re-selection of the instrument, which is selected below
        self._load_sound_fonts(sound_fonts_path)

        # Audio output starts lazily, the first time play is called
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

        After closing, play, record, load_sound_fonts and load_instrument raise PianoClosedError.
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
        """Replace the loaded sound fonts with those from a given path.

        The instrument stays selected if the new sound fonts take it: an Instrument always, a program number only if
        they are not the default ones. Otherwise Instrument.ACOUSTIC_GRAND_PIANO (program 0) is selected. If the new
        sound fonts cannot be loaded, the loaded ones and the instrument stay in use.

        Raises:
            SoundFontError: If FluidSynth cannot load the sound fonts
            PianoClosedError: If the piano was closed

        """
        self._ensure_open()
        self._load_sound_fonts(sound_fonts_path)
        # Channels keep pointing to the unloaded sound fonts, so they play nothing until an instrument is selected again
        try:
            self.load_instrument(self.instrument)
        except (InstrumentError, InstrumentTypeError):
            self.load_instrument(Instrument.ACOUSTIC_GRAND_PIANO)

    def _load_sound_fonts(self, sound_fonts_path: str | Path) -> None:
        """Load sound fonts and unload the previous ones, which stay loaded if the new ones fail to load.

        Raises:
            SoundFontError: If FluidSynth cannot load the sound fonts

        """
        logger.debug("Attempting to load sound fonts from %s", sound_fonts_path)  # pragma: no mutate

        # Through FluidSynth directly, because mingus' load_sound_font replaces the id of the loaded sound fonts with -1
        # when loading fails
        sfid = self._sequencer.fs.sfload(str(sound_fonts_path))
        if sfid == -1:
            msg = f"Could not load sound fonts from {sound_fonts_path}"
            raise SoundFontError(msg)
        if self._sound_fonts_loaded:
            self._sequencer.fs.sfunload(self._sequencer.sfid)
        self._sequencer.sfid = sfid

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
            if self._sequencer.fs.audio_driver is None:
                # FluidSynth logged why, e.g. there is no sound device. Notes play unheard; the next play tries again
                logger.warning(
                    "FluidSynth could not start the %s audio driver, so nothing is heard. The next play tries again",
                    driver or "default",
                )
                return
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

    def load_instrument(self, instrument: Instrument | str | int) -> None:
        """Change the instrument that plays and records.

        Args:
            instrument: An Instrument or its name, such as Instrument.CLAVI or "Clavi", which selects its General MIDI
                program. With other sound fonts than the default ones, a program number works too

        Raises:
            InstrumentError: If a name is not an Instrument's, with the default sound fonts
            InstrumentTypeError: If a program number is given for the default sound fonts, or a name that is not an
                Instrument's for other ones
            PianoClosedError: If the piano was closed

        """
        self._ensure_open()
        logger.debug("Setting instrument: %s", instrument)  # pragma: no mutate

        if isinstance(instrument, str):
            try:
                instrument = Instrument(instrument)
            except ValueError:
                if self._uses_default_sound_fonts:
                    msg = f"Unknown instrument {instrument!r}. Instrument must be one of: {', '.join(Instrument)}"
                    raise InstrumentError(msg) from None
                msg = f"Unknown instrument {instrument!r}. Other sound fonts take a program number or an Instrument"
                raise InstrumentTypeError(msg) from None

        if isinstance(instrument, Instrument):
            program = instrument.program
        elif self._uses_default_sound_fonts:
            # The default sound fonts have only the eight pianos; a number would silently select nothing
            msg = "The default sound fonts take an Instrument or its name, not a program number"
            raise InstrumentTypeError(msg)
        else:
            program = instrument

        self._sequencer.set_instrument(channel=PLAY_CHANNEL, instr=program, bank=0)
        self.instrument = instrument

    def play(
        self,
        music_container: MusicInput,
        *,
        duration: float = DEFAULT_DURATION,
        bpm: float = DEFAULT_BPM,
        velocity: int | None = None,
    ) -> None:
        """Play a music container through the audio output, and return when it has finished.

        A Note or NoteContainer, and so a note string, key index or PianoKey, sounds for duration seconds. A Bar or
        Track takes as long as its notes at the tempo. The notes are released at the end and fade out after play
        returns, unless the piano is closed right away, for example by leaving a with block. Without a sound device,
        play takes just as long. Every note plays on channel 1, where the instrument is selected, whatever channel its
        Note has.

        Args:
            music_container: A music container such as Notes, NoteContainers, etc. describing a piece of music, a key
                index, a PianoKey, or a note string such as "C#-4". A note string without an octave, such as "C", is
                in octave 4, mingus' default
            duration: How long a Note or NoteContainer sounds, in seconds. Bars and Tracks ignore it
            bpm: Tempo in beats per minute for Bars and Tracks. Notes and NoteContainers ignore it
            velocity: How hard the keys are struck, from 0 to 127. None keeps each note's own velocity (mingus'
                default is 64). A given velocity applies to every note; the music container passed in is not changed

        Raises:
            InvalidNoteError: If the music container has notes that are not on a piano with 88 keys
            UnparsableNoteError: If a note string is not a note name with an optional octave. It is an InvalidNoteError
                and mingus' NoteFormatError
            InvalidKeyIndexError: If a key index is outside 0 to 87
            UnsupportedContainerError: If the music container type is not supported
            AudioDriverError: If FluidSynth has no audio driver of the configured name
            PlaybackOptionError: If duration or bpm, also a bpm set on a NoteContainer in a Bar, is not a positive
                finite number, or velocity is not an integer from 0 to 127
            PianoClosedError: If the piano was closed

        """
        container = self._prepare(music_container, velocity=velocity, duration=duration, bpm=bpm)
        logger.debug("Playing music container: %s via audio", container)  # pragma: no mutate
        self._start_audio_output()
        self._play_container(container, bpm, duration)

    def record(  # noqa: PLR0913 - the music, the file, and one keyword argument per option
        self,
        music_container: MusicInput,
        path: str | Path,
        *,
        seconds: float | None = None,
        duration: float = DEFAULT_DURATION,
        bpm: float = DEFAULT_BPM,
        velocity: int | None = None,
    ) -> None:
        """Record a music container to a wav file, with the same timing as play.

        FluidSynth renders the music as fast as it can, instead of in real time, and nothing is heard. A recording
        starts in silence: notes still sounding from before are stopped first. The audio stays in memory until the
        file is written, about 176 kB per second of it, so a recording that fails while rendering leaves an existing
        file as it was. The path is checked before anything is rendered.

        Args:
            music_container: What to record, as for play
            path: The wav file to write (16-bit stereo at 44100 Hz)
            seconds: The length of the recording, in seconds. None records the music and then its fade until
                FluidSynth is silent, which takes at most 5 seconds more. A number gives exactly that length: the music
                is cut off, or its fade and silence fill the rest
            duration: How long a Note or NoteContainer sounds, in seconds, as for play
            bpm: Tempo in beats per minute for Bars and Tracks, as for play
            velocity: How hard the keys are struck, from 0 to 127, as for play

        Raises:
            InvalidNoteError: If the music container has notes that are not on a piano with 88 keys
            UnparsableNoteError: If a note string is not a note name with an optional octave
            InvalidKeyIndexError: If a key index is outside 0 to 87
            UnsupportedContainerError: If the music container type is not supported
            PlaybackOptionError: If seconds, duration or bpm, also a bpm set on a NoteContainer in a Bar, is not a
                positive finite number, or velocity is not an integer from 0 to 127
            PianoClosedError: If the piano was closed
            TypeError: If path is not a str or a path
            FileNotFoundError: If the directory of path does not exist
            IsADirectoryError: If path is a directory
            MemoryError: If a recording of seconds does not fit into memory

        """
        # seconds is the only option that may be None
        lengths = {} if seconds is None else {"seconds": seconds}
        container = self._prepare(music_container, velocity=velocity, duration=duration, bpm=bpm, **lengths)
        path = self._check_path(path)
        logger.debug("Recording music container: %s to file %s", container, path)  # pragma: no mutate
        # With a length, the memory for all of it is taken now, so a length that cannot fit fails before rendering
        recording = _WavBuffer(None if seconds is None else round(seconds * WAV_SAMPLE_FREQUENCY))
        self._stop_audio_output()
        # Without audio output FluidSynth renders only while recording, so notes still sounding from before would
        # carry over into the file
        self._stop_sounds()
        # mingus' sleep, which play_Bar and play_Track call for each note's value and _play_container for a Note's
        # duration, renders that time into the sequencer's wav instead of waiting, as long as it has one. See also
        # https://github.com/bspaans/python-mingus/issues/77
        self._sequencer.wav = recording  # ty: ignore[invalid-assignment] - mingus only calls writeframes on it
        try:
            self._play_container(container, bpm, duration)
            if seconds is None:
                for samples in self._render_until_silent():
                    recording.writeframes(globalfs.raw_audio_string(samples))
            else:
                self._fill_up(recording)
            self._write_wav(path, recording.frames)
        finally:
            # Without the wav attribute, mingus' sleep waits in real time again, as play_Bar needs for audio output
            delattr(self._sequencer, "wav")
            # Notes still sounding at the end would carry over into the next recording, or play aloud afterwards
            self._stop_sounds()

        logger.debug("Finished recording to %s", path)  # pragma: no mutate

    def _fill_up(self, recording: "_WavBuffer") -> None:
        """Render the frames a recording of a given length still misses after the music, a second at a time."""
        missing = recording.missing_frames
        for start in range(0, missing, PAD_CHUNK_FRAMES):
            samples = self._sequencer.fs.get_samples(min(PAD_CHUNK_FRAMES, missing - start))
            recording.writeframes(globalfs.raw_audio_string(samples))

    @staticmethod
    def _check_path(path: str | Path) -> Path:
        """Return the path to record to, after the checks that can fail before anything is rendered.

        Raises:
            TypeError: If path is not a str or a path
            FileNotFoundError: If its directory does not exist
            IsADirectoryError: If it is a directory

        """
        path = Path(os.fspath(path))
        if not path.parent.is_dir():
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), str(path.parent))
        if path.is_dir():
            raise IsADirectoryError(errno.EISDIR, os.strerror(errno.EISDIR), str(path))
        return path

    @staticmethod
    def _write_wav(path: Path, frames: bytes | bytearray) -> None:
        """Write 16-bit stereo frames to a wav file."""
        # wave only opens a str path itself, on Python 3.14 too
        with wave.open(str(path), "wb") as wav:
            wav.setnchannels(BYTES_PER_FRAME // 2)
            wav.setsampwidth(2)
            wav.setframerate(WAV_SAMPLE_FREQUENCY)
            wav.writeframes(frames)

    def _prepare(self, music_container: MusicInput, *, velocity: int | None, **positive: float) -> MusicContainer:
        """Check the options and the music container, and return the mingus container to play or record.

        Args:
            music_container: What play or record was given
            velocity: The velocity option of play or record
            positive: The options that must be positive finite numbers, by name

        Raises:
            PianoClosedError: If the piano was closed
            PlaybackOptionError: If an option is invalid, see _check_playback_options
            InvalidNoteError, InvalidKeyIndexError, UnsupportedContainerError: As _normalize and _validate raise them

        """
        self._ensure_open()
        self._check_playback_options(velocity=velocity, **positive)
        container = self._normalize(music_container)
        self._validate(container)
        return self._for_playback(container, velocity)

    def _normalize(self, music_container: MusicInput) -> MusicContainer:
        """Turn what play and record accept into a mingus music container.

        A note string is parsed into a Note once, a key index or PianoKey becomes the Note of its first identity, and
        mingus containers are returned unchanged.

        Raises:
            UnparsableNoteError: If a note string is not a note name with an optional octave
            InvalidKeyIndexError: If a key index is outside 0 to 87
            UnsupportedContainerError: If the music container type is not supported

        """
        if isinstance(music_container, str):
            try:
                return Note(music_container)
            # mingus raises NoteFormatError for an unknown name, ValueError for an octave that is not a number, and
            # IndexError for an empty string
            except (NoteFormatError, ValueError, IndexError) as error:
                msg = f"Not a note name with an optional octave, such as 'C#-4' or 'Bb-2': {music_container!r}"
                raise UnparsableNoteError(msg) from error
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
    def _check_playback_options(*, velocity: int | None, **positive: float) -> None:
        """Check the options of play or record before anything is played.

        Raises:
            PlaybackOptionError: If an option in positive is not a positive finite number, or velocity is not an
                integer from 0 to 127

        """
        for name, value in positive.items():
            # bool is an int subclass, and None or a str would fail only inside mingus, after playing started
            if isinstance(value, bool) or not isinstance(value, numbers.Real) or not math.isfinite(value) or value <= 0:
                msg = f"{name} must be a positive finite number. Got {value}"
                raise PlaybackOptionError(msg)
        # bool is an int subclass, and mingus would silently truncate a float
        if velocity is not None and (
            isinstance(velocity, bool) or not isinstance(velocity, int) or not 0 <= velocity <= MAX_VELOCITY
        ):
            msg = f"velocity must be an integer between 0 and {MAX_VELOCITY}. Got {velocity!r}"
            raise PlaybackOptionError(msg)

    def _validate(self, container: MusicContainer) -> None:
        """Check that every note of a music container is on a piano with 88 keys, and the tempo set inside it.

        Notes are compared by pitch, so any spelling works, also those the keyboard has no name for, such as C##-4
        (which is D-4). A NoteContainer in a Bar can carry a bpm attribute, which changes the tempo from there on.

        Raises:
            InvalidNoteError: If the music container has notes that are not on a piano with 88 keys
            PlaybackOptionError: If a bpm set on a NoteContainer in a Bar is not a positive finite number

        """
        lowest, highest = (
            int(self.keyboard.keys[0].first_note),
            int(self.keyboard.keys[len(self.keyboard) - 1].first_note),
        )
        invalid_notes = {note_name(note) for note in notes_in(container) if not lowest <= int(note) <= highest}
        if invalid_notes:
            msg = f"Found notes that are not on a piano with 88 keys. Invalid notes in container: {invalid_notes}"
            raise InvalidNoteError(msg)
        bars = container.bars if isinstance(container, Track) else [container] if isinstance(container, Bar) else []
        for bar in bars:
            # Each entry of a Bar is its beat, its note value and its NoteContainer, or None for a rest
            for _, _, notes in bar:
                bpm = getattr(notes, "bpm", DEFAULT_BPM)
                if not math.isfinite(bpm) or bpm <= 0:
                    msg = f"bpm of a NoteContainer in a Bar must be a positive finite number. Got {bpm}"
                    raise PlaybackOptionError(msg)

    @staticmethod
    def _for_playback(container: MusicContainer, velocity: int | None) -> MusicContainer:
        """Return the music container, or a copy whose notes all play on PLAY_CHANNEL and, if given, at the velocity.

        mingus plays each note with the channel and velocity stored on the Note, which override the arguments of its
        play methods, and Bars and Tracks take no velocity at all. The instrument is only selected on PLAY_CHANNEL, so
        notes on other channels would be silent or play another instrument. Setting both on a copy covers every
        container type without changing the caller's notes; a container that needs no change is played as it is.

        """
        if velocity is None and all(note.channel == PLAY_CHANNEL for note in notes_in(container)):
            return container
        container = copy.deepcopy(container)
        for note in notes_in(container):
            note.channel = PLAY_CHANNEL
            if velocity is not None:
                note.velocity = velocity
        return container

    def _stop_sounds(self) -> None:
        """Stop every voice on PLAY_CHANNEL and let the sound fade, so nothing from before carries over.

        Without audio output FluidSynth only advances while samples are rendered, so the stopped voices' fade and the
        reverb tail would otherwise sound at the start of the next recording, or once audio output starts. They are
        rendered away instead, until FluidSynth is silent, for at most MAX_FADE_SECONDS.
        """
        self._sequencer.fs.cc(PLAY_CHANNEL, ALL_SOUND_OFF, 0)
        for _ in self._render_until_silent():
            pass

    def _render_until_silent(self) -> Iterator[np.ndarray]:
        """Render FluidSynth's output 10 ms at a time, as 16-bit samples, up to and including the first silent chunk.

        It stops after MAX_FADE_SECONDS, even if FluidSynth never falls silent.
        """
        for _ in range(MAX_FADE_SECONDS * WAV_SAMPLE_FREQUENCY // FADE_CHUNK_FRAMES):
            samples = self._sequencer.fs.get_samples(FADE_CHUNK_FRAMES)
            yield samples
            if samples.min() >= -SILENCE_PEAK and samples.max() <= SILENCE_PEAK:
                return

    def _play_container(self, container: MusicContainer, bpm: float, duration: float) -> None:
        """Play a music container with the mingus sequencer methods for its type (or the closest base type).

        A Bar or Track times and stops its notes itself at the tempo. A Note or NoteContainer is stopped after
        duration: mingus' sleep waits that long, or renders it while recording.
        """
        play, stop = next(PLAY_METHODS[cls] for cls in type(container).__mro__ if cls in PLAY_METHODS)
        logger.debug("Playing music container: %s with %s", container, play)  # pragma: no mutate
        try:
            if stop is None:
                getattr(self._sequencer, play)(container, bpm=bpm)
            else:
                getattr(self._sequencer, play)(container)
                self._sequencer.sleep(duration)
                # The object that was played: mingus stops each note on the channel stored on it
                getattr(self._sequencer, stop)(container)
        finally:
            # Releases what is still held after an error or Ctrl+C, so no note keeps sounding
            self._sequencer.fs.cc(PLAY_CHANNEL, ALL_NOTES_OFF, 0)

    @staticmethod
    def pause(seconds: int) -> None:
        """Pause further execution for a given time.

        Args:
            seconds: Time to pause further execution in seconds

        """
        time.sleep(seconds)


class _WavBuffer:
    """The 16-bit stereo frames of a recording, collected in memory.

    It stands in for mingus' wav file: mingus' sleep writes the frames it renders to the sequencer's wav with
    writeframes. Without a length it grows with what is written. With one, the memory for exactly that many frames is
    taken up front, and frames beyond it are dropped, so music longer than the recording takes no more memory.
    """

    def __init__(self, length: int | None) -> None:
        """Create an empty buffer, of length frames if given."""
        self._fixed = length is not None
        self._frames = bytearray(BYTES_PER_FRAME * (length or 0))
        self._written = 0

    @property
    def frames(self) -> bytearray:
        """The frames collected so far, or all of them for a buffer of a given length."""
        return self._frames

    @property
    def missing_frames(self) -> int:
        """How many frames a buffer of a given length still misses."""
        return (len(self._frames) - self._written) // BYTES_PER_FRAME

    def writeframes(self, frames: bytes) -> None:
        """Add rendered frames, up to the length if the buffer has one."""
        if not self._fixed:
            self._frames.extend(frames)
            return
        end = min(self._written + len(frames), len(self._frames))
        self._frames[self._written : end] = frames[: end - self._written]
        self._written = end
