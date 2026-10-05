import array
import subprocess
import sys
import wave
from pathlib import Path

import pytest
from mingus.containers import Bar, Note

from pypiano import DEFAULT_SOUND_FONTS, Piano, SoundFontError

pytestmark = pytest.mark.integration

# FluidSynth dithers its 16-bit output, so even silence peaks at 1; a soft C-4 (velocity 30) peaks at about 130
SILENCE_PEAK = 1
AUDIBLE_PEAK = 50


def read_wav(path: Path) -> tuple[int, int]:
    """Return the number of frames and the peak amplitude of a 16-bit wav file."""
    with wave.open(str(path)) as wav:
        samples = array.array("h", wav.readframes(wav.getnframes()))
        return wav.getnframes(), max(map(abs, samples))


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
        piano.record(make_bar("C-4", "E-4", "G-4", "C-5"), slow, seconds=0.5, bpm=60)
        piano.record(make_bar("C-4", "E-4", "G-4", "C-5"), fast, seconds=0.5, bpm=240)
    # Then
    (slow_frames, slow_peak), (fast_frames, fast_peak) = read_wav(slow), read_wav(fast)
    assert slow_frames > fast_frames
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
