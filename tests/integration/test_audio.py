import array
import subprocess
import sys
import wave
from pathlib import Path

import pytest
from mingus.containers import Bar

from pypiano import Piano

pytestmark = pytest.mark.integration


def read_wav(path: Path) -> tuple[int, int]:
    """Return the number of frames and the peak amplitude of a 16-bit wav file."""
    with wave.open(str(path)) as wav:
        samples = array.array("h", wav.readframes(wav.getnframes()))
        return wav.getnframes(), max(map(abs, samples))


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
        piano.play("C-4", recording_file=recording, record_seconds=1)
    # Then
    frames, peak = read_wav(recording)
    assert frames == 44100
    assert peak > 0


def test_piano_should_record_a_longer_bar_when_tempo_is_slower(tmp_path: Path) -> None:
    # Given the same bar recorded at two tempos
    slow, fast = tmp_path / "slow.wav", tmp_path / "fast.wav"
    # When
    with Piano() as piano:
        piano.play(make_bar("C-4", "E-4", "G-4", "C-5"), recording_file=slow, record_seconds=0.5, bpm=60)
        piano.play(make_bar("C-4", "E-4", "G-4", "C-5"), recording_file=fast, record_seconds=0.5, bpm=240)
    # Then
    (slow_frames, slow_peak), (fast_frames, fast_peak) = read_wav(slow), read_wav(fast)
    assert slow_frames > fast_frames
    assert slow_peak > 0
    assert fast_peak > 0


def test_piano_should_record_louder_note_when_velocity_is_higher(tmp_path: Path) -> None:
    # Given the same note recorded at two velocities
    soft, loud = tmp_path / "soft.wav", tmp_path / "loud.wav"
    # When
    with Piano() as piano:
        piano.play("C-4", recording_file=soft, record_seconds=1, velocity=30)
        piano.play("C-4", recording_file=loud, record_seconds=1, velocity=127)
    # Then
    assert read_wav(loud)[1] > read_wav(soft)[1] > 0


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
piano.play("C-4", recording_file={str(tmp_path / "c4.wav")!r}, record_seconds=0.5)
piano.close()
piano.close()
"""
    # When
    result = subprocess.run(  # noqa: S603 - runs this interpreter on a fixed script
        [sys.executable, "-X", "faulthandler", "-c", script], capture_output=True, text=True, timeout=120, check=False
    )
    # Then a crash would show up as a negative return code (killed by SIGSEGV)
    assert result.returncode == 0, result.stderr
