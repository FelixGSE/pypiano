# Changelog

All notable changes to this project are documented in this file. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Changed

- **License:** PyPiano is now licensed under GPL-3.0-or-later, like mingus, which it builds on. Releases up to and
  including 0.1.2 were published under the MIT license.
- **Python versions:** Python 3.11 or newer is required. 3.11 to 3.14 are tested.
- **Packaging:** moved to `pyproject.toml` and uv. Dependencies are bumped to current releases, and the runtime
  dependencies are reduced to mingus and numpy.
- `Piano.play()` accepts a `pathlib.Path` for `recording_file` and a float for `record_seconds`.
- PyPiano logs at `DEBUG` instead of `INFO` when it plays, records or changes the instrument.

### Added

- `pypiano.__version__`.
- `PianoKey`, `PianoKeyboard`, `DEFAULT_INSTRUMENTS` and `DEFAULT_SOUND_FONTS` are exported from `pypiano`.
- `py.typed` marker, so type checkers use PyPiano's type hints.
- `make soundfont` downloads the default sound font from Debian and verifies it, for clones where Git LFS cannot
  provide it.
- `Piano.play()` accepts a key index (0 to 87) and a `PianoKey`.

### Fixed

- **Recording with numpy 2.3 or newer:** mingus 0.6.1 uses numpy functions that numpy 2.3 removed. PyPiano patches
  them.
- **macOS with Apple Silicon:** PyPiano finds Homebrew's libfluidsynth (#16).
- **Second note names:** `PianoKey.second_note_string` returned the first identity. The second names of C and B now
  follow scientific pitch notation (`C-4` is `B#-3`, `B-4` is `Cb-5`).
- `Piano.play()` rejected key indexes and `PianoKey`s, even though its signature accepted them.

## 0.1.2 - 2022-01-15

- Fixed the type hint of `PianoKeyboard.distinct_key_names` (#7).

## 0.1.1 - 2021-05-21

- Included the sound font files in the release.

## 0.1.0 - 2021-05-20

- Fixed the package description on PyPI.

## 0.0.1 - 2021-05-02

- First release.
