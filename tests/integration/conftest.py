import os

import pytest

from pypiano import DEFAULT_SOUND_FONTS

# A Git LFS pointer file is about 130 bytes; the sound font is about 148 MB
MIN_SOUND_FONT_BYTES = 1_000_000


@pytest.fixture(autouse=True)
def require_sound_font() -> None:
    """Skip when the sound font is only a Git LFS pointer, or fail if PYPIANO_REQUIRE_INTEGRATION is set (CI)."""
    if DEFAULT_SOUND_FONTS.stat().st_size >= MIN_SOUND_FONT_BYTES:
        return
    msg = f"{DEFAULT_SOUND_FONTS} is not the real sound font (run git lfs pull, or delete it and run make soundfont)"
    if os.environ.get("PYPIANO_REQUIRE_INTEGRATION"):
        pytest.fail(msg)
    pytest.skip(msg)
