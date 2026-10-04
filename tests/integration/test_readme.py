import re
import subprocess
import sys
from pathlib import Path

import pytest

from tests.integration.test_audio import read_wav

pytestmark = pytest.mark.integration

README = Path(__file__).resolve().parents[2] / "README.md"


def usage_example() -> str:
    """Return the first Python code block of the README, its usage example."""
    match = re.search(r"```python\n(.*?)```", README.read_text(), re.DOTALL)
    assert match is not None, "README.md has no ```python block"
    return match.group(1)


def test_readme_example_should_run_and_record_when_executed(tmp_path: Path) -> None:
    # Given the README's usage example, run where it can write its recording
    example = usage_example()
    assert "my_first_recording.wav" in example
    # When it runs in its own interpreter, so a crash in FluidSynth cannot take pytest down
    result = subprocess.run(  # noqa: S603 - runs this interpreter on the README example
        [sys.executable, "-X", "faulthandler", "-c", example],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    # Then it exits cleanly (without a sound device, playback only logs a FluidSynth error) and records audio
    assert result.returncode == 0, result.stderr
    # FluidSynth used to warn that the drum channel has no preset, because the bundled sound font has only pianos
    assert "No preset found" not in result.stderr
    frames, peak = read_wav(tmp_path / "my_first_recording.wav")
    assert frames == 2 * 44100
    assert peak > 0
