"""Build the piano sound font PyPiano bundles from Debian's FluidR3_GM, reproducibly.

PyPiano bundles only the eight General MIDI pianos (bank 0, programs 0 to 7) of FluidR3_GM. This script

1. downloads Debian's fluid-soundfont source archive and verifies it against the checksum Debian publishes,
2. extracts FluidR3_GM.sf2 and verifies it against its known checksum,
3. cuts the eight pianos out with sf2-cutter (version pinned in .devcontainer/Dockerfile), as described
   in scripts/sound_font_recipe.toml,
4. verifies the result against PIANOS_SHA256. The same input and sf2-cutter version always produce the same bytes, so
   anyone can rebuild the bundled file and compare.

Existing files are never overwritten. A correct sound font is left in place; any other file at its path is an error,
and the license is only written if it is missing.

Run with: make soundfont (build if missing), make soundfont-check (rebuild and compare with the bundled file, as CI
does), or uv run scripts/build_sound_font.py [--check]
"""

import argparse
import hashlib
import logging
import os
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path

import requests
from tqdm import tqdm

# fluid-soundfont 3.1, checksum from Debian's fluid-soundfont_3.1-6.dsc
ARCHIVE_URL = "https://deb.debian.org/debian/pool/main/f/fluid-soundfont/fluid-soundfont_3.1.orig.tar.gz"
ARCHIVE_SHA256 = "2621acaa1c78e4abdb24bdd163230cc577e61276936d6aa6e3180582142f0343"
SOUND_FONT_MEMBER = "fluid-soundfont-3.1/FluidR3_GM.sf2"
LICENSE_MEMBER = "fluid-soundfont-3.1/COPYING"
# The full FluidR3_GM.sf2 in the archive (148 MB, 189 presets)
FULL_SOUND_FONT_SHA256 = "74594e8f4250680adf590507a306655a299935343583256f3b722c48a1bc1cb0"
# The eight pianos cut out by sf2-cutter 0.1.0 with the recipe and bank name below (19 MB)
PIANOS_SHA256 = "6da99144bcf97b85d6e38c54006dcf0b22afba98d3515da0a37c29e833f92a51"
BANK_NAME = "Fluid R3 GM pianos"

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
RECIPE_PATH = REPOSITORY_ROOT / "scripts" / "sound_font_recipe.toml"
SOUND_FONT_PATH = REPOSITORY_ROOT / "pypiano" / "sound_fonts" / "FluidR3_GM_pianos.sf2"
LICENSE_PATH = REPOSITORY_ROOT / "licenses" / "LICENSE-FluidR3_GM_sf2.txt"
# The verified archive is kept here, so rebuilding (and CI with a cache) downloads it only once
ARCHIVE_CACHE = Path(os.environ.get("PYPIANO_ARCHIVE_CACHE", Path.home() / ".cache" / "pypiano"))

REQUEST_TIMEOUT_SECONDS = 30
CHUNK_SIZE = 1024 * 1024

logger = logging.getLogger("build_sound_font")


class ChecksumError(RuntimeError):
    """Raised when a downloaded, extracted or built file does not have the expected sha256."""


class ExistingFileError(RuntimeError):
    """Raised instead of overwriting a file that is not the expected sound font."""


def sha256_of(path: Path) -> str:
    """Return the hex sha256 of a file."""
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify(path: Path, expected_sha256: str) -> None:
    """Raise ChecksumError if the file does not have the expected sha256."""
    actual = sha256_of(path)
    if actual != expected_sha256:
        msg = f"{path.name} has sha256 {actual}, expected {expected_sha256}"
        raise ChecksumError(msg)


def download(url: str, target: Path) -> None:
    """Download a file with a progress bar."""
    with requests.get(url, stream=True, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        response.raise_for_status()
        total = int(response.headers.get("content-length", 0))
        with (
            target.open("wb") as file,
            tqdm(desc=target.name, total=total, unit="B", unit_scale=True, unit_divisor=1024) as progress,
        ):
            for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                progress.update(file.write(chunk))


def cached_archive() -> Path:
    """Return the verified source archive, downloading it into the cache unless a verified copy is there."""
    archive = ARCHIVE_CACHE / "fluid-soundfont_3.1.orig.tar.gz"
    if archive.is_file() and sha256_of(archive) == ARCHIVE_SHA256:
        logger.info("Using the cached %s", archive)
        return archive
    ARCHIVE_CACHE.mkdir(parents=True, exist_ok=True)
    partial = archive.with_name(archive.name + ".part")
    try:
        logger.info("Downloading %s", ARCHIVE_URL)
        download(ARCHIVE_URL, partial)
        verify(partial, ARCHIVE_SHA256)
        partial.replace(archive)
    finally:
        partial.unlink(missing_ok=True)
    return archive


def extract(archive: Path, member: str, target: Path) -> None:
    """Extract a single member of a .tar.gz archive to target."""
    with tarfile.open(archive, "r:gz") as tar:
        source = tar.extractfile(member)
        if source is None:
            msg = f"{member} in {archive.name} is not a regular file"
            raise ValueError(msg)
        with source, target.open("wb") as file:
            while chunk := source.read(CHUNK_SIZE):
                file.write(chunk)


def sf2_cutter() -> str:
    """Return the path of the sf2-cutter executable."""
    executable = shutil.which("sf2-cutter")
    if executable is None:
        msg = "sf2-cutter not found; it is installed in the devcontainer (see .devcontainer/Dockerfile)"
        raise FileNotFoundError(msg)
    return executable


def cut_pianos(full_sound_font: Path, target: Path) -> None:
    """Cut the presets of the recipe out of the full sound font into target, and verify the result."""
    result = subprocess.run(  # noqa: S603 - sf2-cutter with fixed arguments
        [
            sf2_cutter(),
            "extract",
            str(full_sound_font),
            "--config",
            str(RECIPE_PATH),
            "--name",
            BANK_NAME,
            "-o",
            str(target),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        # sf2-cutter warns about every one-directional stereo link in FluidR3; show its output only if it failed
        msg = f"sf2-cutter failed with exit code {result.returncode}:\n{result.stdout}{result.stderr}"
        raise RuntimeError(msg)
    verify(target, PIANOS_SHA256)


def build(work_dir: Path, target: Path) -> Path:
    """Build the piano sound font into target and return the COPYING file from the archive (in work_dir)."""
    archive = cached_archive()
    full_sound_font = work_dir / "FluidR3_GM.sf2"
    extract(archive, SOUND_FONT_MEMBER, full_sound_font)
    verify(full_sound_font, FULL_SOUND_FONT_SHA256)
    cut_pianos(full_sound_font, target)
    copying = work_dir / "COPYING"
    extract(archive, LICENSE_MEMBER, copying)
    return copying


def install_sound_font(sound_font_path: Path, license_path: Path) -> None:
    """Build the verified sound font into place, and write its license if that is missing."""
    with tempfile.TemporaryDirectory() as tmp:
        sound_font_path.parent.mkdir(parents=True, exist_ok=True)
        # Build next to the target and rename only after verifying, so a failed run never leaves a partial sound
        # font behind. A rename only works within one file system, so it cannot start in the temporary directory
        partial = sound_font_path.with_name(sound_font_path.name + ".part")
        try:
            copying = build(Path(tmp), partial)
            if sound_font_path.exists():
                msg = f"{sound_font_path} appeared during the build; not overwriting it"
                raise ExistingFileError(msg)
            partial.rename(sound_font_path)
        finally:
            partial.unlink(missing_ok=True)

        # The repository keeps the license with a single trailing newline
        license_text = copying.read_text().rstrip() + "\n"
        if not license_path.exists():
            license_path.parent.mkdir(parents=True, exist_ok=True)
            license_path.write_text(license_text)
        elif license_path.read_text() != license_text:
            logger.warning("Leaving %s unchanged, it differs from the license in the archive", license_path)


def check_reproducible(sound_font_path: Path) -> int:
    """Rebuild the sound font and compare it with the bundled file; return the exit code."""
    with tempfile.TemporaryDirectory() as tmp:
        rebuilt = Path(tmp) / sound_font_path.name
        build(Path(tmp), rebuilt)
        if not sound_font_path.is_file() or sha256_of(sound_font_path) != sha256_of(rebuilt):
            logger.error("%s is not the file the build produces (sha256 %s)", sound_font_path, PIANOS_SHA256)
            return 1
    logger.info("%s is byte-identical to the rebuilt sound font (sha256 %s)", sound_font_path, PIANOS_SHA256)
    return 0


def main(argv: list[str] | None = None) -> int:
    """Build the sound font if it is missing, or with --check, rebuild it and compare with the bundled file."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--check", action="store_true", help="rebuild and compare with the bundled file instead of installing"
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if args.check:
        return check_reproducible(SOUND_FONT_PATH)
    if SOUND_FONT_PATH.exists():
        if sha256_of(SOUND_FONT_PATH) == PIANOS_SHA256:
            logger.info("Sound font already in place: %s", SOUND_FONT_PATH)
            return 0
        logger.error(
            "%s exists but is not the expected sound font. Not overwriting it: delete the file and run this script "
            "again.",
            SOUND_FONT_PATH,
        )
        return 1
    install_sound_font(SOUND_FONT_PATH, LICENSE_PATH)
    logger.info("Installed %s", SOUND_FONT_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
