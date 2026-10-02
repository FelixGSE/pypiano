"""Download the default FluidR3_GM sound font and its license from Debian into the package.

The repository stores the sound font with Git LFS. When it is not available, for example without git-lfs or while the
repository's LFS budget is used up, this script fetches the same file from Debian's fluid-soundfont source package. The
archive is verified against the checksum Debian publishes and the sound font against the checksum of the file in the
repository, so the result is byte for byte the file Git LFS would check out.

Existing files are never overwritten. A correct sound font is left in place; any other file at its path, such as a Git
LFS pointer, is an error, and the license is only written if it is missing.

Run with: make soundfont, or uv run scripts/get_default_sf_file.py
"""

import argparse
import hashlib
import logging
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
# Checksum of the sound font in the repository, the oid of its Git LFS pointer
SOUND_FONT_SHA256 = "74594e8f4250680adf590507a306655a299935343583256f3b722c48a1bc1cb0"

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOUND_FONT_PATH = REPOSITORY_ROOT / "pypiano" / "sound_fonts" / "FluidR3_GM.sf2"
LICENSE_PATH = REPOSITORY_ROOT / "licenses" / "LICENSE-FluidR3_GM_sf2.txt"

REQUEST_TIMEOUT_SECONDS = 30
CHUNK_SIZE = 1024 * 1024

logger = logging.getLogger("get_default_sf_file")


class ChecksumError(RuntimeError):
    """Raised when a downloaded or extracted file does not have the expected sha256."""


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


class ExistingFileError(RuntimeError):
    """Raised instead of overwriting a file that is not the expected sound font."""


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


def install_sound_font(sound_font_path: Path, license_path: Path) -> None:
    """Download the archive and install the verified sound font, and its license if that is missing."""
    with tempfile.TemporaryDirectory() as tmp:
        work_dir = Path(tmp)
        archive = work_dir / "fluid-soundfont.orig.tar.gz"
        logger.info("Downloading %s", ARCHIVE_URL)
        download(ARCHIVE_URL, archive)
        verify(archive, ARCHIVE_SHA256)

        sound_font_path.parent.mkdir(parents=True, exist_ok=True)
        # Extract next to the target and rename only after verifying, so a failed run never leaves a partial sound
        # font behind. A rename only works within one file system, so it cannot start in the temporary directory
        partial = sound_font_path.with_name(sound_font_path.name + ".part")
        try:
            extract(archive, SOUND_FONT_MEMBER, partial)
            verify(partial, SOUND_FONT_SHA256)
            if sound_font_path.exists():
                msg = f"{sound_font_path} appeared during the download; not overwriting it"
                raise ExistingFileError(msg)
            partial.rename(sound_font_path)
        finally:
            partial.unlink(missing_ok=True)

        copying = work_dir / "COPYING"
        extract(archive, LICENSE_MEMBER, copying)
        # The repository keeps the license with a single trailing newline
        license_text = copying.read_text().rstrip() + "\n"
        if not license_path.exists():
            license_path.parent.mkdir(parents=True, exist_ok=True)
            license_path.write_text(license_text)
        elif license_path.read_text() != license_text:
            logger.warning("Leaving %s unchanged, it differs from the license in the archive", license_path)


def main(argv: list[str] | None = None) -> int:
    """Install the sound font if it is missing; never overwrite an existing file."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if SOUND_FONT_PATH.exists():
        if sha256_of(SOUND_FONT_PATH) == SOUND_FONT_SHA256:
            logger.info("Sound font already in place: %s", SOUND_FONT_PATH)
            return 0
        logger.error(
            "%s exists but is not the expected sound font (for example a Git LFS pointer). Not overwriting it: run "
            "`git lfs pull`, or delete the file and run this script again.",
            SOUND_FONT_PATH,
        )
        return 1
    install_sound_font(SOUND_FONT_PATH, LICENSE_PATH)
    logger.info("Installed %s", SOUND_FONT_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
