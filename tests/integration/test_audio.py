import array
import subprocess
import sys
import time
import wave
from pathlib import Path

import pytest
from mingus.containers import Bar, Note

from pypiano import DEFAULT_SOUND_FONTS, Piano, PlaybackOptionError, SoundFontError

pytestmark = pytest.mark.integration

# FluidSynth dithers its 16-bit output, so even silence peaks at 1; a soft C-4 (velocity 30) peaks at about 130
SILENCE_PEAK = 1
AUDIBLE_PEAK = 50


def read_wav(path: Path) -> tuple[int, int]:
    """Return the number of frames and the peak amplitude of a 16-bit wav file."""
    with wave.open(str(path)) as wav:
        samples = array.array("h", wav.readframes(wav.getnframes()))
        return wav.getnframes(), max(map(abs, samples))


def peak_between(path: Path, start: float, end: float) -> int:
    """Return the peak amplitude of a 16-bit stereo wav file from start to end, in seconds."""
    with wave.open(str(path)) as wav:
        samples = array.array("h", wav.readframes(wav.getnframes()))
    return max(map(abs, samples[round(start * 44100) * 2 : round(end * 44100) * 2]))


def read_frames(path: Path) -> bytes:
    """Return the audio of a wav file."""
    with wave.open(str(path)) as wav:
        return wav.readframes(wav.getnframes())


def make_bar(*notes: str) -> Bar:
    bar = Bar()
    for note in notes:
        bar.place_notes(note, 4)
    return bar


def test_piano_should_record_audible_note_when_recording_to_a_file(tmp_path: Path) -> None:
    # Given a piano with the real sound font and FluidSynth
    recording = tmp_path / "c4.wav"
    # When
    with Piano() as piano:
        piano.record("C-4", recording, seconds=1)
    # Then
    frames, peak = read_wav(recording)
    assert frames == 44100
    assert peak > AUDIBLE_PEAK


def test_piano_should_record_a_longer_bar_when_tempo_is_slower(tmp_path: Path) -> None:
    # Given the same bar recorded at two tempos
    slow, fast = tmp_path / "slow.wav", tmp_path / "fast.wav"
    # When
    with Piano() as piano:
        piano.record(make_bar("C-4", "E-4", "G-4", "C-5"), slow, bpm=60)
        piano.record(make_bar("C-4", "E-4", "G-4", "C-5"), fast, bpm=240)
    # Then
    (slow_frames, slow_peak), (fast_frames, fast_peak) = read_wav(slow), read_wav(fast)
    # Four quarter notes take 4 seconds at 60 bpm and 1 second at 240 bpm, each followed by its fade
    assert 4 * 44100 < slow_frames < 6 * 44100
    assert 44100 < fast_frames < 3 * 44100
    assert slow_peak > AUDIBLE_PEAK
    assert fast_peak > AUDIBLE_PEAK


def test_piano_should_record_louder_note_when_velocity_is_higher(tmp_path: Path) -> None:
    # Given the same note recorded at two velocities
    soft, loud = tmp_path / "soft.wav", tmp_path / "loud.wav"
    # When
    with Piano() as piano:
        piano.record("C-4", soft, seconds=1, velocity=30)
        piano.record("C-4", loud, seconds=1, velocity=127)
    # Then
    assert read_wav(loud)[1] > read_wav(soft)[1] > AUDIBLE_PEAK


def test_piano_should_record_silence_when_a_loud_recording_came_before(tmp_path: Path) -> None:
    # Given a loud recording, whose note and reverb would still sound when it ends
    loud, silent = tmp_path / "loud.wav", tmp_path / "silent.wav"
    # When the same piano records a note at velocity 0 next
    with Piano() as piano:
        piano.record("C-4", loud, seconds=1, velocity=127)
        piano.record("C-4", silent, seconds=1, velocity=0)
    # Then nothing of the loud recording carries over
    assert read_wav(silent)[1] <= SILENCE_PEAK


def test_piano_should_record_audibly_when_sound_fonts_were_loaded_again(tmp_path: Path) -> None:
    # Given a piano whose sound fonts are replaced, here by the same file, and a piano that kept them
    reloaded, kept = tmp_path / "reloaded.wav", tmp_path / "kept.wav"
    # When both record the same note on the Clavi
    with Piano(instrument="Clavi") as piano:
        piano.load_sound_fonts(DEFAULT_SOUND_FONTS)
        piano.record("C-4", reloaded, seconds=1)
    with Piano(instrument="Clavi") as piano:
        piano.record("C-4", kept, seconds=1)
    # Then the reloaded piano still plays the Clavi
    assert read_wav(reloaded)[1] > AUDIBLE_PEAK
    assert read_frames(reloaded) == read_frames(kept)


def test_piano_should_keep_playing_its_sound_fonts_when_new_ones_cannot_be_loaded(tmp_path: Path) -> None:
    # Given a piano playing the Clavi, and a sound font file that doesn't exist
    after_failure, unchanged = tmp_path / "after_failure.wav", tmp_path / "unchanged.wav"
    # When loading it fails, and the piano records afterwards
    with Piano(instrument="Clavi") as piano:
        with pytest.raises(SoundFontError):
            piano.load_sound_fonts(tmp_path / "missing.sf2")
        piano.record("C-4", after_failure, seconds=1)
        instrument = piano.instrument
    with Piano(instrument="Clavi") as piano:
        piano.record("C-4", unchanged, seconds=1)
    # Then it plays the Clavi of the sound fonts it had
    assert instrument == "Clavi"
    assert read_frames(after_failure) == read_frames(unchanged)


@pytest.mark.parametrize("channel", [0, 2, 9])
def test_piano_should_play_the_instrument_when_a_note_is_on_another_channel(tmp_path: Path, channel: int) -> None:
    # Given a C-4 on another channel than 1, where no instrument is selected, and one on channel 1
    other, first = tmp_path / "other.wav", tmp_path / "first.wav"
    # When both are recorded on the Clavi
    with Piano(instrument="Clavi") as piano:
        piano.record(Note("C-4", channel=channel), other, seconds=1)
    with Piano(instrument="Clavi") as piano:
        piano.record(Note("C-4"), first, seconds=1)
    # Then both sound the same
    assert read_wav(other)[1] > AUDIBLE_PEAK
    assert read_frames(other) == read_frames(first)


def test_piano_should_play_through_a_driver_mingus_does_not_know_when_fluidsynth_has_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given FluidSynth's file driver, which writes to fluidsynth.raw or .wav in the working directory instead of a sound
    # device, and which mingus' list of FluidSynth 1 drivers lacks
    monkeypatch.chdir(tmp_path)
    # When
    with Piano(audio_driver="file") as piano:
        piano.play("C-4")
    # Then
    (output,) = tmp_path.glob("fluidsynth.*")
    assert output.stat().st_size > 0


def test_piano_should_play_as_long_as_the_music_when_playing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Given FluidSynth's file driver, which renders in real time like a sound device
    monkeypatch.chdir(tmp_path)
    with Piano(audio_driver="file") as piano:
        # The first play starts the audio driver, which is not part of the timing
        piano.play("C-4", duration=0.1)
        # When a note sounds for 0.3 seconds, and four quarter notes at 240 bpm take a second
        start = time.monotonic()
        piano.play("C-4", duration=0.3)
        note_seconds = time.monotonic() - start
        start = time.monotonic()
        piano.play(make_bar("C-4", "E-4", "G-4", "C-5"), bpm=240)
        bar_seconds = time.monotonic() - start
    # Then play returns when the music has finished; the upper limits leave room for a busy CI runner
    assert 0.3 <= note_seconds < 0.8
    assert 1 <= bar_seconds < 1.5


def test_piano_should_record_the_music_and_its_fade_until_silent_when_no_length_is_given(tmp_path: Path) -> None:
    # Given a note that sounds for half a second
    recording = tmp_path / "c4.wav"
    # When
    with Piano() as piano:
        piano.record("C-4", recording, duration=0.5)
    # Then the recording holds the note, then its fade, which ends in silence within 5 seconds
    frames, _ = read_wav(recording)
    assert 0.5 * 44100 < frames < 5.5 * 44100
    assert peak_between(recording, 0, 0.5) > AUDIBLE_PEAK
    assert peak_between(recording, (frames - 441) / 44100, frames / 44100) <= SILENCE_PEAK


@pytest.mark.parametrize(("seconds", "frames"), [(1.15, 50715), (0.25, 11025), (3, 132300)])
def test_piano_should_record_exactly_the_given_length_when_seconds_is_given(
    tmp_path: Path, seconds: float, frames: int
) -> None:
    # Given a note that sounds for a second, so a shorter recording cuts it off and a longer one holds its fade
    recording = tmp_path / "c4.wav"
    # When
    with Piano() as piano:
        piano.record("C-4", recording, seconds=seconds)
    # Then
    assert read_wav(recording)[0] == frames


def test_piano_should_sound_longer_when_the_duration_is_longer(tmp_path: Path) -> None:
    # Given the same note recorded with two durations
    short, long = tmp_path / "short.wav", tmp_path / "long.wav"
    # When
    with Piano() as piano:
        piano.record("C-4", short, duration=0.5, seconds=2)
        piano.record("C-4", long, duration=1.5, seconds=2)
    # Then the note held for 1.5 seconds still sounds after a second, when the one released after 0.5 has faded
    assert peak_between(long, 1, 1.2) > AUDIBLE_PEAK > peak_between(short, 1, 1.2)


def test_piano_should_leave_no_file_when_a_bpm_set_in_a_bar_is_invalid(tmp_path: Path) -> None:
    # Given a bar whose second NoteContainer sets a tempo of 0, which mingus would divide by
    bar = make_bar("C-4", "E-4")
    bar.bar[1][2].bpm = 0
    recording = tmp_path / "bar.wav"
    # When / Then
    with Piano() as piano, pytest.raises(PlaybackOptionError):
        piano.record(bar, recording)
    assert list(tmp_path.iterdir()) == []


def test_python_should_exit_cleanly_when_a_closed_piano_is_garbage_collected(tmp_path: Path) -> None:
    # Given a script that plays, records, closes twice and lets mingus' FluidSynthSequencer.__del__ run at exit,
    # which used to free FluidSynth's synth a second time and crash
    script = f"""
from pypiano import Piano
piano = Piano()
piano.play("C-4")
piano.record("C-4", {str(tmp_path / "c4.wav")!r}, seconds=0.5)
piano.close()
piano.close()
"""
    # When
    result = subprocess.run(  # noqa: S603 - runs this interpreter on a fixed script
        [sys.executable, "-X", "faulthandler", "-c", script], capture_output=True, text=True, timeout=120, check=False
    )
    # Then a crash would show up as a negative return code (killed by SIGSEGV)
    assert result.returncode == 0, result.stderr
