# PyPiano

PyPiano is a python library to programmatically play piano. It is an easy-to-use abstraction layer on top of the
[python-mingus](https://bspaans.github.io/python-mingus/) package providing a simple user interface to play mingus music containers, such as Notes,
NoteContainers, Bars and Tracks. It bundles a default sound fonts file to enable playing and recording audio out
of the box. By default, 8 different pianos are available. It allows playing Piano via audio output or recording music to wav files.

## Installation

PyPiano needs Python 3.11 or newer and the [FluidSynth](https://www.fluidsynth.org/) library:

```bash
sudo apt install libfluidsynth3   # Debian / Ubuntu
brew install fluid-synth          # macOS
```

The bundled sound font is stored with [Git LFS](https://git-lfs.com/), so install and set up `git-lfs` first. Then
install PyPiano from GitHub with pip or uv:

```bash
pip install git+https://github.com/FelixGSE/pypiano.git
uv add git+https://github.com/FelixGSE/pypiano.git
```

Installing from GitHub currently fails, because the repository has used up its Git LFS budget and the sound font
cannot be downloaded (see [Known issues](#known-issues)).

## Usage

```python
from pypiano import Piano
from mingus.containers import Note

p = Piano()

# Play a simple C-4 via audio
p.play("C-4")

# Play a mingus Note
note = Note("C-4")
p.play(note)

# Record a Note to a wav file
p.play(note, recording_file="my_first_recording.wav", record_seconds=2)

# Use a different instrument
p.load_instrument("Honky-tonk Piano")
p.play(note)

# play() returns immediately while the note keeps sounding, so keep a script running until it has finished
p.pause(2)
```

The same code works with more complex mingus containers like NoteContainers, Bars and Tracks. You can also pass a
key index from 0 (A-0) to 87 (C-8), or a `PianoKey` from `p.keyboard`.

Note names follow [scientific pitch notation](https://en.wikipedia.org/wiki/Scientific_pitch_notation), like mingus:
octave numbers go up at C, so middle C is `C-4` and A-4 is 440 Hz. Every key can be addressed by either of its names,
for example `C#-4` or `Db-4`. The octave boundary applies to enharmonic names too: `B#-3` is the same key as `C-4`, and
`Cb-5` is the same key as `B-4`.

## Development

The devcontainer (`.devcontainer/`) has everything installed. Common commands go through `make`:

```bash
make install   # uv sync
make lint      # run all pre-commit hooks on all files
make test      # pytest; make test-all runs every supported Python version
make coverage  # pytest with coverage, fails below COVERAGE_MIN (default 100, e.g. make coverage COVERAGE_MIN=90)
make play      # play a note via audio output (needs a sound device, so not inside the container)
make record    # record a note to demo.wav
make record NOTE=A-4 INSTRUMENT="Honky-tonk Piano" OUTPUT=a4.wav RECORD_SECONDS=3
```

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.
Please add or update tests with your change: `make lint` must pass, and `make coverage` requires 100% line and branch
coverage.

The sound font is checked in with [Git LFS](https://git-lfs.com/). With `git-lfs` installed,
`pypiano/sound_fonts/FluidR3_GM.sf2` is downloaded when you clone; otherwise install `git-lfs` and run `git lfs pull`.

## Known issues

- **Sound font size and Git LFS budget** ([#13](https://github.com/FelixGSE/pypiano/issues/13)): the default sound font
  comes from the Debian [fluid-soundfont](https://packages.debian.org/source/stable/fluid-soundfont) package (see
  `scripts/get_default_sf_file.py`). It is 148 MB and contains 194 instruments, of which PyPiano uses 8. Because of its
  size the repository has used up its Git LFS budget, so installing from GitHub fails, and the package is too large to
  publish to PyPI.
- **FluidSynth not found on macOS with Apple Silicon** ([#16](https://github.com/FelixGSE/pypiano/issues/16)): mingus does
  not search Homebrew's `/opt/homebrew/lib`. The `make` targets work around this; elsewhere, set
  `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib` when running Python.

## License
- PyPiano is distributed under MIT license - Check corresponding [license file](https://github.com/FelixGSE/pypiano/blob/master/licenses/LICENSE-PyPiano)
- Default sound fonts are distributed under MIT license - Check corresponding [license file](https://github.com/FelixGSE/pypiano/blob/master/licenses/LICENSE-FluidR3_GM_sf2.txt)
