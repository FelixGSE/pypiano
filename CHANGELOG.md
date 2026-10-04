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
- `Piano.close()` releases FluidSynth's synthesizer, and `Piano` works as a context manager (`with Piano() as p:`).
  After closing, `play()`, `load_sound_fonts()` and `load_instrument()` raise `PianoClosedError`.
- `Piano.play()` takes `bpm` (tempo of Bars and Tracks, default 120) and `velocity` (0 to 127 for every note, default
  `None` keeps each note's own velocity). A given velocity is applied to a copy, so the caller's notes don't change.
- `make test-integration` runs tests that record real audio and run the README example; CI runs them in their own
  job. `make test` and `make coverage` leave them out.
- `Piano(sequencer=...)` accepts the mingus sequencer to play through, which makes the piano testable without
  FluidSynth.
- **Exceptions:** `pypiano.PyPianoError` is the base of all errors PyPiano raises on purpose. The subclasses are
  `SoundFontError`, `AudioDriverError`, `InstrumentError`, `InstrumentTypeError`, `InvalidNoteError`,
  `UnknownNoteNameError`, `InvalidKeyIndexError`, `UnsupportedContainerError`, `PlaybackOptionError` and
  `PianoClosedError`. Each also derives from the built-in
  exception raised before (`ValueError`, `TypeError`, `IndexError` or `RuntimeError`), so existing `except` clauses
  keep working. An out-of-range key index raises `InvalidKeyIndexError` from both `Piano.play()` and
  `PianoKeyboard[...]`, which is both a `ValueError` and an `IndexError`. Before, the two raised different exceptions.

### Fixed

- **Recording with numpy 2.3 or newer:** mingus 0.6.1 uses numpy functions that numpy 2.3 removed. PyPiano patches
  them.
- **macOS with Apple Silicon:** PyPiano finds Homebrew's libfluidsynth (#16).
- **Second note names:** `PianoKey.second_note_string` returned the first identity. The second names of C and B now
  follow scientific pitch notation (`C-4` is `B#-3`, `B-4` is `Cb-5`).
- `Piano.play()` rejected key indexes and `PianoKey`s, even though its signature accepted them.
- **Bars and tracks with rests crashed `Piano.play()`** with `TypeError: 'NoneType' object is not iterable`. mingus
  stores a rest as `None`, which the note validation didn't expect.
- **Instrument names were rejected** when the default sound font was loaded through a different path, for example a
  relative one, because PyPiano compared paths instead of the resolved files.
- **Note lookups matched parts of names:** `keyboard["C"]` returned the key B-0, and `"-4" in key` was `True`. Note
  names are now matched exactly, in `PianoKeyboard[...]`, in `in` checks and when `Piano.play()` validates notes.

### Removed

- **`pypiano.utils` helpers:** `note_to_string`, `note_container_to_note_string_list`, `bar_to_note_string_list` and
  `track_to_note_string_list` are replaced by `notes_in()`, which yields the notes of any mingus container, and
  `note_name()`. The module wasn't part of the exported API.

## 0.1.2 - 2022-01-15

- Fixed the type hint of `PianoKeyboard.distinct_key_names` (#7).

## 0.1.1 - 2021-05-21

- Included the sound font files in the release.

## 0.1.0 - 2021-05-20

- Fixed the package description on PyPI.

## 0.0.1 - 2021-05-02

- First release.
