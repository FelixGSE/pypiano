"""Load mingus' fluidsynth bindings, finding Homebrew's libfluidsynth on macOS.

mingus.midi.pyfluidsynth looks up libfluidsynth once, when it is imported, with ctypes.util.find_library. On macOS that
only searches DYLD_FALLBACK_LIBRARY_PATH, or ~/lib, /usr/local/lib, /lib and /usr/lib when it is unset, so Homebrew's
/opt/homebrew/lib on Apple Silicon is not found. If the library is missing there, this module imports mingus with
Homebrew's lib directory prepended to that search path, and restores the variable afterwards: mingus keeps the full
path it found. It runs before anything else in pypiano imports mingus.midi.pyfluidsynth.
"""

import os
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from ctypes.util import find_library
from importlib import import_module
from pathlib import Path

MINGUS_FLUIDSYNTH_MODULE = "mingus.midi.pyfluidsynth"
FALLBACK_LIBRARY_PATH = "DYLD_FALLBACK_LIBRARY_PATH"
MACOS_LIBRARY_NAME = "libfluidsynth.dylib"
HOMEBREW_PREFIXES = ("/opt/homebrew", "/usr/local")
# Searched by dyld and ctypes when DYLD_FALLBACK_LIBRARY_PATH is unset (see `man dyld`)
DYLD_DEFAULT_FALLBACK = (str(Path("~/lib").expanduser()), "/usr/local/lib", "/lib", "/usr/lib")

INSTALL_HINTS = {
    "darwin": "Install it with `brew install fluid-synth`.",
    "linux": "Install it with your package manager, e.g. `sudo apt install libfluidsynth3` on Debian or Ubuntu.",
}


def homebrew_library_dir() -> Path | None:
    """Return the Homebrew lib directory that contains libfluidsynth, if any."""
    prefixes = [os.environ["HOMEBREW_PREFIX"]] if os.environ.get("HOMEBREW_PREFIX") else []
    for prefix in [*prefixes, *HOMEBREW_PREFIXES]:
        library_dir = Path(prefix) / "lib"
        if (library_dir / MACOS_LIBRARY_NAME).exists():
            return library_dir
    return None


@contextmanager
def prepended_fallback_library_path(library_dir: Path) -> Iterator[None]:
    """Search library_dir first while the block runs, keeping the directories that were searched before."""
    original = os.environ.get(FALLBACK_LIBRARY_PATH)
    # Setting the variable replaces dyld's default fallback directories, so keep them when it was unset
    searched_before = original or os.pathsep.join(DYLD_DEFAULT_FALLBACK)
    os.environ[FALLBACK_LIBRARY_PATH] = os.pathsep.join([str(library_dir), searched_before])
    try:
        yield
    finally:
        if original is None:
            del os.environ[FALLBACK_LIBRARY_PATH]
        else:
            os.environ[FALLBACK_LIBRARY_PATH] = original


def load_mingus_fluidsynth() -> None:
    """Import mingus.midi.pyfluidsynth, raising an ImportError with install instructions if libfluidsynth is missing."""
    library_dir = homebrew_library_dir() if sys.platform == "darwin" and find_library("fluidsynth") is None else None
    try:
        if library_dir is None:
            import_module(MINGUS_FLUIDSYNTH_MODULE)
        else:
            with prepended_fallback_library_path(library_dir):
                import_module(MINGUS_FLUIDSYNTH_MODULE)
    except ImportError as error:
        hint = INSTALL_HINTS.get(sys.platform, "See https://www.fluidsynth.org/ for how to install it.")
        msg = f"PyPiano needs the FluidSynth library (libfluidsynth), but it could not be found. {hint}"
        raise ImportError(msg) from error


load_mingus_fluidsynth()
