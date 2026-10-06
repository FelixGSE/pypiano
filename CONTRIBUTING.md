# Contributing to PyPiano

Bug reports and pull requests are welcome. For larger changes, please open an issue first to discuss what you would like
to change.

## Development setup

The devcontainer (`.devcontainer/`, see its [README](.devcontainer/README.md)) has everything installed. Outside of it,
install [uv](https://docs.astral.sh/uv/) and the FluidSynth library, then run `make install`. Common commands go through
`make` (`make help` lists them all):

```bash
make install           # uv sync
make lint              # run all pre-commit hooks on all files
make test              # pytest; make test-all runs every supported Python version
make coverage          # pytest with coverage, fails below COVERAGE_MIN (default 100, e.g. make coverage COVERAGE_MIN=90)
make mutation          # mutation testing: changes the code in small ways and fails if no test notices (MUTATION_MIN, default 100)
make test-integration  # tests with real audio: records notes and runs the README example
make test-lowest       # all tests with the oldest dependency versions pyproject.toml allows, on Python 3.11
make soundfont         # build the piano sound font from Debian's FluidR3_GM if it is missing
make soundfont-check   # rebuild it and compare byte by byte with the bundled file
make play              # play a note via audio output (needs a sound device, so not inside the container)
make record            # record a note to demo.wav
make record NOTE=A-4 INSTRUMENT="Honky-tonk Piano" OUTPUT=a4.wav RECORD_SECONDS=3
```

## Pull requests

Please add or update tests with your change: `make lint` must pass, `make coverage` requires 100% line and branch
coverage, and `make mutation` requires every mutant to be caught. A surviving mutant is a code change no test notices;
its diff shows which test is missing. If a mutant cannot change behavior (an equivalent mutant), mark the line with
`# pragma: no mutate` and say why.

Pull request titles follow [Conventional Commits](https://www.conventionalcommits.org/), for example
`feat: add a sustain pedal` or `fix: accept B#-7`, because pull requests are squash-merged and the title becomes the
commit message that decides the next version. `feat` starts a minor release, `fix`, `perf` and `deps` a patch release,
and a `!` (as in `feat!:`) or a `BREAKING CHANGE:` footer marks a breaking change. Other types (`docs`, `refactor`,
`test`, `build`, `ci`, `chore`) don't start a release. A check on every pull request enforces the format.

## The sound font

`pypiano/sound_fonts/FluidR3_GM_pianos.sf2` (19 MB) holds the eight General MIDI pianos (bank 0, programs 0 to 7) of
FluidR3_GM by Frank Wen, as packaged in Debian's
[fluid-soundfont](https://packages.debian.org/source/stable/fluid-soundfont). The full font is 148 MB with 189
presets. The pianos keep their stereo samples, and rendering every piano at several notes gives byte-identical audio
with the full font.

`scripts/build_sound_font.py` (`make soundfont`) builds the file:

1. it downloads Debian's source archive and verifies it against the checksum Debian publishes; once Debian's archive
   no longer has this version, it comes from snapshot.debian.org, which keeps every file Debian ever published,
2. it extracts `FluidR3_GM.sf2` and verifies its checksum,
3. it cuts the presets listed in `scripts/sound_font_recipe.toml` out with
   [sf2-cutter](https://github.com/FelixGSE/sf2-cutter), whose release is pinned and checksum-verified in
   `.devcontainer/Dockerfile`,
4. it verifies the result against the checksum in the script.

The build is deterministic. `make soundfont-check` rebuilds the file and compares it byte by byte with the bundled one,
which CI does on every pull request; a test checks that the file contains only the SoundFont 2 chunks, exactly the
eight pianos and the FluidR3 attribution. If you change how the file is built, update the checksum in
`scripts/build_sound_font.py`.

Releases come with signed build provenance for the wheel, the sdist and the sound font in them, which
`gh attestation verify <file> --repo FelixGSE/pypiano` checks, for example on a downloaded wheel or on the sound font
from it.

## Releasing

[release-please](https://github.com/googleapis/release-please) keeps a release pull request open that bumps the
version (`pyproject.toml`, `uv.lock`) and adds the changelog entry. Merging it tags the release, creates the GitHub
release, runs the tests, attaches the built package and publishes it to PyPI with
[trusted publishing](https://docs.pypi.org/trusted-publishers/) (no API token; the `pypi` environment of this
repository). If a job of that run fails, "Re-run failed jobs" retries it for the same release; release-please creates
each release only once, so a new run would not.
