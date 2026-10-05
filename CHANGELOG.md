# Changelog

All notable changes to this project are documented in this file, and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html). From 0.2.0 on, the entries are written by
[release-please](https://github.com/googleapis/release-please) from the
[Conventional Commits](https://www.conventionalcommits.org/) titles of the merged pull requests.

## [0.2.0](https://github.com/FelixGSE/pypiano/compare/v0.1.2...v0.2.0) (2026-10-05)


### ⚠ BREAKING CHANGES

* make `Piano.instrument` read-only; `load_instrument()` changes the instrument
* rename the internal `pypiano.utils` module to `pypiano._utils`
* remove `DEFAULT_INSTRUMENTS`; `Instrument` lists the instruments, and each member has its General MIDI `program`
* make `play()` return when the music has finished; a Note or NoteContainer sounds for `duration` seconds (1 by default) and is then released
* record with `Piano.record(music, path, seconds=...)`; `play()` no longer takes `recording_file` and `record_seconds`
* remove `pypiano.piano.VALID_AUDIO_DRIVERS`; the loaded FluidSynth's own drivers decide, and a driver it lacks raises `AudioDriverError`
* require Python 3.11 or newer; 3.11 to 3.14 are tested
* remove the `pypiano.utils` helpers `note_to_string` and the `*_to_note_string_list` functions, which were internal
* relicense PyPiano under GPL-3.0-or-later, like mingus, which it builds on (releases up to and including 0.1.2 were MIT)
* remove the full `FluidR3_GM.sf2`; `DEFAULT_SOUND_FONTS` points to `FluidR3_GM_pianos.sf2`, which has only the eight pianos, without General MIDI programs 8 to 127 or the drum kits

### Features

* accept a `pathlib.Path` for `recording_file` and a float for `record_seconds` ([931f8a1](https://github.com/FelixGSE/pypiano/commit/931f8a1798222f5291a4164c4ab852ac722e36f8))
* accept a key index (0 to 87) and a `PianoKey` in `Piano.play()` ([931f8a1](https://github.com/FelixGSE/pypiano/commit/931f8a1798222f5291a4164c4ab852ac722e36f8))
* accept the mingus sequencer to play through as `Piano(sequencer=...)` ([931f8a1](https://github.com/FelixGSE/pypiano/commit/931f8a1798222f5291a4164c4ab852ac722e36f8))
* add `bpm` (tempo of bars and tracks) and `velocity` (0 to 127, applied to a copy of the notes) to `Piano.play()` ([931f8a1](https://github.com/FelixGSE/pypiano/commit/931f8a1798222f5291a4164c4ab852ac722e36f8))
* add `Piano.close()` and support `with Piano() as p:`; a closed piano raises `PianoClosedError` ([931f8a1](https://github.com/FelixGSE/pypiano/commit/931f8a1798222f5291a4164c4ab852ac722e36f8))
* add `PyPianoError` and its subclasses; each also derives from the built-in exception raised before, and an out-of-range key index raises `InvalidKeyIndexError` everywhere ([931f8a1](https://github.com/FelixGSE/pypiano/commit/931f8a1798222f5291a4164c4ab852ac722e36f8))
* add `sdl3`, `kai` and `dart` to the `AudioDriver` type ([b41335c](https://github.com/FelixGSE/pypiano/commit/b41335c4917dae94adb6b66ecf4e787b64284cd7))
* add the `AudioDriver` type with FluidSynth's driver names ([a903ae0](https://github.com/FelixGSE/pypiano/commit/a903ae05862637a637dbcd66c90781657e1af0e0))
* add the `Instrument` enum of General MIDI pianos; members equal their names, and with other sound fonts an `Instrument` or its name selects its program number ([5671340](https://github.com/FelixGSE/pypiano/commit/56713404171148c29e86506d319a2824e3b680c2))
* add the `KeyColor` enum, which `PianoKey.key_color` returns, and the `NoteIdentity` type for `get_as_note()` and `get_as_string()` ([5671340](https://github.com/FelixGSE/pypiano/commit/56713404171148c29e86506d319a2824e3b680c2))
* bundle only the eight pianos of FluidR3_GM (19 MB instead of 148 MB), built reproducibly from Debian's archive with sf2-cutter and stored without Git LFS, so installing from GitHub works again ([#13](https://github.com/FelixGSE/pypiano/issues/13)) ([e5415a4](https://github.com/FelixGSE/pypiano/commit/e5415a41d83156416e0075fe82939ccb6295e51c))
* export `__version__`, `PianoKey`, `PianoKeyboard`, `DEFAULT_INSTRUMENTS`, `DEFAULT_SOUND_FONTS` and the errors, and ship `py.typed` ([931f8a1](https://github.com/FelixGSE/pypiano/commit/931f8a1798222f5291a4164c4ab852ac722e36f8))
* make `Piano.instrument` read-only; `load_instrument()` changes the instrument ([f5b9a3b](https://github.com/FelixGSE/pypiano/commit/f5b9a3b632cc831f5e8b59f29094f456bc827978))
* make `play()` return when the music has finished; a Note or NoteContainer sounds for `duration` seconds (1 by default) and is then released ([f493536](https://github.com/FelixGSE/pypiano/commit/f4935365c5072d676b304b442e7e83b83429b36d))
* record the music and its fade until silent by default, or exactly `seconds` long, and write the file only once the recording is rendered ([f493536](https://github.com/FelixGSE/pypiano/commit/f4935365c5072d676b304b442e7e83b83429b36d))
* record with `Piano.record(music, path, seconds=...)`; `play()` no longer takes `recording_file` and `record_seconds` ([0b2893e](https://github.com/FelixGSE/pypiano/commit/0b2893eb4cca494b9473316215c292e681ec3e94))
* relicense PyPiano under GPL-3.0-or-later, like mingus, which it builds on (releases up to and including 0.1.2 were MIT) ([931f8a1](https://github.com/FelixGSE/pypiano/commit/931f8a1798222f5291a4164c4ab852ac722e36f8))
* remove `DEFAULT_INSTRUMENTS`; `Instrument` lists the instruments, and each member has its General MIDI `program` ([f5b9a3b](https://github.com/FelixGSE/pypiano/commit/f5b9a3b632cc831f5e8b59f29094f456bc827978))
* remove the `pypiano.utils` helpers `note_to_string` and the `*_to_note_string_list` functions, which were internal ([931f8a1](https://github.com/FelixGSE/pypiano/commit/931f8a1798222f5291a4164c4ab852ac722e36f8))
* remove the full `FluidR3_GM.sf2`; `DEFAULT_SOUND_FONTS` points to `FluidR3_GM_pianos.sf2`, which has only the eight pianos, without General MIDI programs 8 to 127 or the drum kits ([e5415a4](https://github.com/FelixGSE/pypiano/commit/e5415a41d83156416e0075fe82939ccb6295e51c))
* rename the internal `pypiano.utils` module to `pypiano._utils` ([f5b9a3b](https://github.com/FelixGSE/pypiano/commit/f5b9a3b632cc831f5e8b59f29094f456bc827978))
* require Python 3.11 or newer; 3.11 to 3.14 are tested ([931f8a1](https://github.com/FelixGSE/pypiano/commit/931f8a1798222f5291a4164c4ab852ac722e36f8))


### Bug Fixes

* accept every audio driver FluidSynth has, such as pipewire, wasapi or sdl2, and list them when a name is unknown ([a903ae0](https://github.com/FelixGSE/pypiano/commit/a903ae05862637a637dbcd66c90781657e1af0e0))
* accept instrument names when the default sound font is loaded through another path ([931f8a1](https://github.com/FelixGSE/pypiano/commit/931f8a1798222f5291a4164c4ab852ac722e36f8))
* close the wav file when a recording fails, which left later playback of bars and tracks writing into it ([31f12ab](https://github.com/FelixGSE/pypiano/commit/31f12abaa99f93297eda996681382e33d51c44f0))
* declare the license as `GPL-3.0-or-later AND MIT`, since the package ships the MIT-licensed sound font ([b41335c](https://github.com/FelixGSE/pypiano/commit/b41335c4917dae94adb6b66ecf4e787b64284cd7))
* find Homebrew's libfluidsynth on macOS with Apple Silicon ([#16](https://github.com/FelixGSE/pypiano/issues/16)) ([931f8a1](https://github.com/FelixGSE/pypiano/commit/931f8a1798222f5291a4164c4ab852ac722e36f8))
* keep playing after `load_sound_fonts()`, which left playback silent; a sound font that fails to load now leaves the loaded one and the instrument in use ([31f12ab](https://github.com/FelixGSE/pypiano/commit/31f12abaa99f93297eda996681382e33d51c44f0))
* log at DEBUG instead of INFO when playing, recording or changing the instrument ([931f8a1](https://github.com/FelixGSE/pypiano/commit/931f8a1798222f5291a4164c4ab852ac722e36f8))
* lower the numpy minimum from 2.4.6 to 1.23.2, the oldest with wheels for Python 3.11 ([b41335c](https://github.com/FelixGSE/pypiano/commit/b41335c4917dae94adb6b66ecf4e787b64284cd7))
* match note names exactly in keyboard lookups and `in` checks instead of matching parts of names ([931f8a1](https://github.com/FelixGSE/pypiano/commit/931f8a1798222f5291a4164c4ab852ac722e36f8))
* play bars and tracks that contain rests, which crashed with a `TypeError` ([931f8a1](https://github.com/FelixGSE/pypiano/commit/931f8a1798222f5291a4164c4ab852ac722e36f8))
* play key indexes and `PianoKey`s, which `play()` rejected although its signature accepted them ([931f8a1](https://github.com/FelixGSE/pypiano/commit/931f8a1798222f5291a4164c4ab852ac722e36f8))
* play notes on any MIDI channel with the selected instrument, which only channel 1 had ([31f12ab](https://github.com/FelixGSE/pypiano/commit/31f12abaa99f93297eda996681382e33d51c44f0))
* play notes spelled with double accidentals, such as `C##-4`, by checking pitches instead of spellings ([a7f9fb3](https://github.com/FelixGSE/pypiano/commit/a7f9fb3d9bb3d10e980b6e0819803e0cfeff2abb))
* raise `PlaybackOptionError` before playing when `bpm`, `duration` or `seconds` is not a number, such as `None` or `True` ([f493536](https://github.com/FelixGSE/pypiano/commit/f4935365c5072d676b304b442e7e83b83429b36d))
* raise `PlaybackOptionError` for an invalid `bpm` set on a NoteContainer in a Bar, which crashed inside mingus ([f493536](https://github.com/FelixGSE/pypiano/commit/f4935365c5072d676b304b442e7e83b83429b36d))
* raise `UnparsableNoteError`, an `InvalidNoteError` that is also mingus' `NoteFormatError`, for note strings mingus can't parse, such as `"H-4"` or `""` ([012f6fe](https://github.com/FelixGSE/pypiano/commit/012f6fed1a494f22234db7fbfb653d9c3b37f81e))
* record with numpy 2.3 or newer, which removed functions mingus 0.6.1 still uses ([931f8a1](https://github.com/FelixGSE/pypiano/commit/931f8a1798222f5291a4164c4ab852ac722e36f8))
* reject `record_seconds` values that are not positive finite numbers ([a7f9fb3](https://github.com/FelixGSE/pypiano/commit/a7f9fb3d9bb3d10e980b6e0819803e0cfeff2abb))
* reject `velocity` values that are not integers, such as `True` or `64.5` ([a7f9fb3](https://github.com/FelixGSE/pypiano/commit/a7f9fb3d9bb3d10e980b6e0819803e0cfeff2abb))
* reject NaN and infinite `bpm` ([a7f9fb3](https://github.com/FelixGSE/pypiano/commit/a7f9fb3d9bb3d10e980b6e0819803e0cfeff2abb))
* remove `pypiano.piano.VALID_AUDIO_DRIVERS`; the loaded FluidSynth's own drivers decide, and a driver it lacks raises `AudioDriverError` ([a903ae0](https://github.com/FelixGSE/pypiano/commit/a903ae05862637a637dbcd66c90781657e1af0e0))
* return the second identity from `PianoKey.second_note_string`, with B# and Cb in scientific pitch notation (`C-4` is `B#-3`, `B-4` is `Cb-5`) ([931f8a1](https://github.com/FelixGSE/pypiano/commit/931f8a1798222f5291a4164c4ab852ac722e36f8))
* start every recording in silence, without notes or reverb from earlier `play()` calls ([31f12ab](https://github.com/FelixGSE/pypiano/commit/31f12abaa99f93297eda996681382e33d51c44f0))
* stop FluidSynth's warning that the drum channel has no preset ([#42](https://github.com/FelixGSE/pypiano/issues/42)) ([11211b3](https://github.com/FelixGSE/pypiano/commit/11211b3382a506cd3e9ff33bd4385fc8b0bd5e27))
* try the audio driver again on the next `play()` when FluidSynth could not start it, and log a warning ([31f12ab](https://github.com/FelixGSE/pypiano/commit/31f12abaa99f93297eda996681382e33d51c44f0))


### Dependencies

* bump dependencies to current releases and reduce the runtime dependencies to mingus and numpy ([931f8a1](https://github.com/FelixGSE/pypiano/commit/931f8a1798222f5291a4164c4ab852ac722e36f8))

## 0.1.2 - 2022-01-15

- Fixed the type hint of `PianoKeyboard.distinct_key_names` (#7).

## 0.1.1 - 2021-05-21

- Included the sound font files in the release.

## 0.1.0 - 2021-05-20

- Fixed the package description on PyPI.

## 0.0.1 - 2021-05-02

- First release.
