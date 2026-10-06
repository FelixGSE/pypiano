"""Check the built wheel the way users get it: installed, outside the repository.

make test-package (CI job "Built package") builds the sdist and the wheel, installs the wheel into a fresh venv and runs
this script with that venv's Python. It checks that pypiano comes from the installed wheel, ships its sound font,
py.typed and both license files, and records an audible note with the real FluidSynth.

Run with: make test-package
"""

import array
import sys
import tempfile
import wave
from importlib.metadata import files, version
from pathlib import Path

import pypiano

# The bundled sound font is 19 MB; a missing or truncated file is much smaller
MIN_SOUND_FONT_BYTES = 10_000_000
# FluidSynth dithers its output, so even silence peaks at 1; a C-4 peaks at several hundred
AUDIBLE_PEAK = 50
FRAMES_PER_SECOND = 44100


def check(condition: object, problem: str) -> None:
    """Stop with the problem if the condition is false."""
    if not condition:
        sys.exit(f"Package check failed: {problem}")


def record_c4(directory: Path) -> tuple[int, int]:
    """Record C-4 for one second and return the number of frames and the peak of the recording."""
    recording = directory / "c4.wav"
    with pypiano.Piano() as piano:
        piano.record("C-4", recording, seconds=1)
    with wave.open(str(recording)) as wav:
        frames = wav.getnframes()
        peak = max(map(abs, array.array("h", wav.readframes(frames))))
    return frames, peak


def main() -> None:
    """Check the installed package and print what was checked."""
    package_dir = Path(pypiano.__file__).parent
    check(Path(sys.prefix) in package_dir.parents, f"pypiano was imported from {package_dir}, not from this venv")
    check(pypiano.__version__ == version("pypiano"), f"__version__ {pypiano.__version__} differs from the metadata")
    check((package_dir / "py.typed").is_file(), "py.typed is missing")
    sound_font = pypiano.DEFAULT_SOUND_FONTS
    check(sound_font.is_file(), f"the sound font is missing: {sound_font}")
    check(sound_font.stat().st_size > MIN_SOUND_FONT_BYTES, f"the sound font is too small: {sound_font}")
    license_files = {path.name for path in files("pypiano") or [] if "licenses" in path.parts}
    check({"LICENSE", "LICENSE-FluidR3_GM_sf2.txt"} <= license_files, f"license files missing, found {license_files}")
    with tempfile.TemporaryDirectory() as directory:
        frames, peak = record_c4(Path(directory))
    check(frames == FRAMES_PER_SECOND, f"the one-second recording has {frames} frames")
    check(peak > AUDIBLE_PEAK, f"the recording is silent (peak {peak})")
    print(f"pypiano {pypiano.__version__} from {package_dir}: recorded C-4 with peak {peak}, all checks passed")  # noqa: T201


if __name__ == "__main__":
    main()
