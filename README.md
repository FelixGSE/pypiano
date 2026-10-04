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

Then install PyPiano from GitHub with pip or uv:

```bash
pip install git+https://github.com/FelixGSE/pypiano.git
uv add git+https://github.com/FelixGSE/pypiano.git
```

## Usage

```python
from pypiano import Piano
from mingus.containers import Bar, Note

# The with block releases FluidSynth when it ends; without it, call p.close() when done
with Piano() as p:
    # Play a simple C-4 via audio
    p.play("C-4")

    # Play a mingus Note, louder (velocity 0 to 127)
    note = Note("C-4")
    p.play(note, velocity=110)

    # Record a Note to a wav file
    p.play(note, recording_file="my_first_recording.wav", record_seconds=2)

    # Play a Bar at a given tempo
    bar = Bar()
    for name in ("C-4", "E-4", "G-4", "C-5"):
        bar.place_notes(name, 4)
    p.play(bar, bpm=90)

    # Use a different instrument
    p.load_instrument("Honky-tonk Piano")
    p.play(note)

    # play() returns immediately for notes while they keep sounding, so keep a script running until they finish
    p.pause(2)
```

The same code works with more complex mingus containers like NoteContainers, Bars and Tracks. You can also pass a
key index from 0 (A-0) to 87 (C-8), or a `PianoKey` from `p.keyboard`.

Note names follow [scientific pitch notation](https://en.wikipedia.org/wiki/Scientific_pitch_notation), like mingus:
octave numbers go up at C, so middle C is `C-4` and A-4 is 440 Hz. Every key can be addressed by either of its names,
for example `C#-4` or `Db-4`. The octave boundary applies to enharmonic names too: `B#-3` is the same key as `C-4`, and
`Cb-5` is the same key as `B-4`.

Importing `pypiano` changes mingus' fluidsynth bindings (`mingus.midi.pyfluidsynth`) for the whole process:

- It loads the FluidSynth library through mingus; on macOS it also looks in Homebrew's lib directory.
- It replaces two functions, so recording works with numpy 2.3 or newer.
- It replaces `Synth.start`, which only accepted FluidSynth 1's audio drivers, with a version that accepts every driver.
- It adds the `Synth` methods `audio_drivers` and `set_channel_type`.

Other code in the same process that uses mingus' fluidsynth bindings gets these changes too.

## Development

The devcontainer (`.devcontainer/`) has everything installed. Common commands go through `make`:

```bash
make install   # uv sync
make soundfont         # build the piano sound font from Debian's FluidR3_GM if it is missing
make soundfont-check   # rebuild it and compare byte by byte with the bundled file
make lint      # run all pre-commit hooks on all files
make test      # pytest; make test-all runs every supported Python version
make coverage  # pytest with coverage, fails below COVERAGE_MIN (default 100, e.g. make coverage COVERAGE_MIN=90)
make mutation  # mutation testing: changes the code in small ways and fails if no test notices (MUTATION_MIN, default 100)
make test-integration  # tests with real audio: records notes and runs the README example
make test-lowest       # all tests with the oldest dependency versions pyproject.toml allows, on Python 3.11
make play      # play a note via audio output (needs a sound device, so not inside the container)
make record    # record a note to demo.wav
make record NOTE=A-4 INSTRUMENT="Honky-tonk Piano" OUTPUT=a4.wav RECORD_SECONDS=3
```

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.
Please add or update tests with your change: `make lint` must pass, `make coverage` requires 100% line and branch
coverage, and `make mutation` requires every mutant to be caught. A surviving mutant is a code change no test notices;
its diff shows which test is missing. If a mutant cannot change behavior (an equivalent mutant), mark the line with
`# pragma: no mutate` and say why.

The bundled sound font is built with `make soundfont` (see [The bundled sound font](#the-bundled-sound-font)); the
devcontainer has the tool it needs. If you change how it is built, update the checksum in
`scripts/build_sound_font.py`, and CI checks that the result is reproducible.

Pull request titles follow [Conventional Commits](https://www.conventionalcommits.org/), for example
`feat: add a sustain pedal` or `fix: accept B#-7`, because pull requests are squash-merged and the title becomes the
commit message that decides the next version. `feat` starts a minor release, `fix`, `perf` and `deps` a patch release,
and a `!` (as in `feat!:`) or a `BREAKING CHANGE:` footer marks a breaking change. Other types (`docs`, `refactor`,
`test`, `build`, `ci`, `chore`) don't start a release. A check on every pull request enforces the format.

### Releasing

[release-please](https://github.com/googleapis/release-please) keeps a release pull request open that bumps the
version (`pyproject.toml`, `uv.lock`) and adds the changelog entry. Merging it tags the release, creates the GitHub
release, runs the tests and attaches the built package. Publishing to PyPI happens in the same workflow once the
repository variable `PUBLISH_TO_PYPI` is `true`.

## The bundled sound font

`pypiano/sound_fonts/FluidR3_GM_pianos.sf2` (19 MB) holds the eight General MIDI pianos (bank 0, programs 0 to 7) of
FluidR3_GM by Frank Wen, as packaged in Debian's
[fluid-soundfont](https://packages.debian.org/source/stable/fluid-soundfont). The full font is 148 MB with 189
presets, of which PyPiano uses these eight. The pianos keep their stereo samples, and they sound exactly like the full
font: rendering every piano at several notes gives byte-identical audio with both.

The file is not hand-made. `scripts/build_sound_font.py` (`make soundfont`) builds it:

1. it downloads Debian's source archive and verifies it against the checksum Debian publishes,
2. it extracts `FluidR3_GM.sf2` and verifies its checksum,
3. it cuts the presets listed in `scripts/sound_font_recipe.toml` out with
   [sf2-cutter](https://github.com/FelixGSE/sf2-cutter), whose release is pinned and checksum-verified in
   `.devcontainer/Dockerfile`,
4. it verifies the result against the checksum in the script.

The build is deterministic, so you can check the bundled file yourself:

```bash
make soundfont-check   # rebuild from Debian's archive and compare byte by byte with the bundled file
sha256sum pypiano/sound_fonts/FluidR3_GM_pianos.sf2   # 6da99144bcf97b85d6e38c54006dcf0b22afba98d3515da0a37c29e833f92a51
```

CI runs `make soundfont-check` on every pull request, and a test checks that the file contains only the SoundFont 2
chunks, exactly the eight pianos and the FluidR3 attribution. Releases come with signed build provenance for the
package and the sound font:

```bash
gh attestation verify FluidR3_GM_pianos.sf2 --repo FelixGSE/pypiano
gh attestation verify pypiano-0.2.0-py3-none-any.whl --repo FelixGSE/pypiano
```

## License

PyPiano is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License
as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
See [LICENSE](LICENSE). Copyright (C) 2021-2026 FelixGSE.

PyPiano builds on [mingus](https://github.com/bspaans/python-mingus), which is licensed under GPL-3.0-or-later as well.
Releases up to and including 0.1.2 were published under the MIT license.

The bundled sound font, a subset of FluidR3_GM, is distributed under the MIT license, see
[licenses/LICENSE-FluidR3_GM_sf2.txt](licenses/LICENSE-FluidR3_GM_sf2.txt). The package metadata therefore declares the
license expression `GPL-3.0-or-later AND MIT`.
