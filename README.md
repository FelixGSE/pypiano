# PyPiano

PyPiano plays and records piano from Python. You play note names such as `"C-4"`, or the Notes, NoteContainers, Bars
and Tracks of [mingus](https://github.com/bspaans/python-mingus), through your speakers or into a wav file.
[FluidSynth](https://www.fluidsynth.org/) does the sound, and a sound font with eight pianos is included, so it works
out of the box.

## Installation

PyPiano needs Python 3.11 or newer and the FluidSynth library:

```bash
sudo apt install libfluidsynth3   # Debian / Ubuntu
brew install fluid-synth          # macOS
```

Then install PyPiano from PyPI with pip or uv:

```bash
pip install pypiano
uv add pypiano
```

The development version installs from GitHub: `pip install git+https://github.com/FelixGSE/pypiano.git`.

## Usage

```python
from pypiano import Instrument, Piano
from mingus.containers import Bar, Note

# The with block releases FluidSynth when it ends; without it, call p.close() when done
with Piano() as p:
    # Play a simple C-4 via audio; play() returns when the note has sounded for a second
    p.play("C-4")

    # Play a mingus Note for two seconds, louder (velocity 0 to 127)
    note = Note("C-4")
    p.play(note, duration=2, velocity=110)

    # Record a Note to a wav file
    p.record(note, "my_first_recording.wav", seconds=2)

    # Play a Bar at a given tempo
    bar = Bar()
    for name in ("C-4", "E-4", "G-4", "C-5"):
        bar.place_notes(name, 4)
    p.play(bar, bpm=90)

    # Use a different instrument; its name, "Honky-tonk Piano", works too
    p.load_instrument(Instrument.HONKY_TONK_PIANO)
    p.play(note)
```

`play()` takes a note name, a key index from 0 (A-0) to 87 (C-8), a `PianoKey` from `p.keyboard`, or any mingus Note,
NoteContainer, Bar or Track, and plays it through the audio output. It returns when the music has finished: a note or
chord sounds for `duration` seconds (1 by default), a Bar or Track as long as its notes take at `bpm`. The notes then
fade out, unless the piano is closed right away. `velocity` sets how hard every note is struck.

`record()` takes the same and writes a wav file instead, rendered faster than real time and without sound. Without
`seconds` the recording ends when the fade has died away; with it, the recording is exactly that long.

### Note names

Note names follow [scientific pitch notation](https://en.wikipedia.org/wiki/Scientific_pitch_notation), like mingus:
octave numbers go up at C, so middle C is `C-4` and A-4 is 440 Hz. Every key has both of its names, for example `C#-4`
and `Db-4`, and the octave boundary applies to them too: `B#-3` is the same key as `C-4`, and `Cb-5` the same as `B-4`.
`play()` also takes a name without an octave, such as `"C"`, in octave 4.

### Instruments

The included sound font has the eight General MIDI pianos, as `Instrument` members or by their names. The default
is the Acoustic Grand Piano.

| Instrument                         | Name                      |
| ---------------------------------- | ------------------------- |
| `Instrument.ACOUSTIC_GRAND_PIANO`  | `"Acoustic Grand Piano"`  |
| `Instrument.BRIGHT_ACOUSTIC_PIANO` | `"Bright Acoustic Piano"` |
| `Instrument.ELECTRIC_GRAND_PIANO`  | `"Electric Grand Piano"`  |
| `Instrument.HONKY_TONK_PIANO`      | `"Honky-tonk Piano"`      |
| `Instrument.ELECTRIC_PIANO_1`      | `"Electric Piano 1"`      |
| `Instrument.ELECTRIC_PIANO_2`      | `"Electric Piano 2"`      |
| `Instrument.HARPSICHORD`           | `"Harpsichord"`           |
| `Instrument.CLAVI`                 | `"Clavi"`                 |

Any other General MIDI sound font works too, and then program numbers select its instruments, for example the violin:
`Piano("FluidR3_GM.sf2", instrument=40)`.

### Audio output

FluidSynth uses its default audio driver. To choose another one, pass its name, for example
`Piano(audio_driver="pipewire")`. Which drivers there are depends on how FluidSynth was built; an unknown name raises
`AudioDriverError` with the list. Without a sound device, playing logs a warning and nothing is heard, while recording
to a file works as usual.

### Errors

PyPiano's own errors derive from `PyPianoError`, for example `InvalidNoteError` for a note outside the 88 keys. Each
one also derives from the built-in exception it stands for, such as `ValueError` or `TypeError`.

### Good to know

Importing `pypiano` adjusts mingus' FluidSynth bindings (`mingus.midi.pyfluidsynth`) for the whole process: it finds
Homebrew's FluidSynth on macOS, makes recording work with numpy 2.3 or newer, and accepts every audio driver of
FluidSynth 2. Other code in the same process that uses these bindings gets the same changes.

## The included sound font

The bundled sound font holds the eight pianos of FluidR3_GM by Frank Wen, cut reproducibly from Debian's
[fluid-soundfont](https://packages.debian.org/source/stable/fluid-soundfont) package with
[sf2-cutter](https://github.com/FelixGSE/sf2-cutter) to a pinned checksum
([details](https://github.com/FelixGSE/pypiano/blob/HEAD/CONTRIBUTING.md#the-sound-font)).

## Contributing

Bug reports and pull requests are welcome. [CONTRIBUTING.md](https://github.com/FelixGSE/pypiano/blob/HEAD/CONTRIBUTING.md)
explains the development setup, the checks and how releases work. Changes are listed in the
[changelog](https://github.com/FelixGSE/pypiano/blob/HEAD/CHANGELOG.md).

## License

PyPiano is free software under the GNU General Public License, version 3 or later, like mingus, which it builds on. See
[LICENSE](https://github.com/FelixGSE/pypiano/blob/HEAD/LICENSE). Copyright (C) 2021-2026 FelixGSE. Releases up to and
including 0.1.2 were published under the MIT license.

The included sound font is under the MIT license, see
[LICENSE-FluidR3_GM_sf2.txt](https://github.com/FelixGSE/pypiano/blob/HEAD/licenses/LICENSE-FluidR3_GM_sf2.txt).
