# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "requests>=2.34.2",
#     "tqdm>=4.70.1",
# ]
# ///

"""Download the FluidR3_GM sound font and its license from Debian into the package.

Run with: uv run scripts/get_default_sf_file.py
"""

import logging
import tarfile
from pathlib import Path
from shutil import copyfile, rmtree

import requests
from tqdm import tqdm

BASE_URL = "http://deb.debian.org/debian/pool/main/f"
PACKAGE_NAME = "fluid-soundfont"
PACKAGE_VERSION = 3.1
FILE_EXTENSION = "orig.tar.gz"
UNPACK_DIR = "fluid-soundfont-3.1"
LICENSE_SOURCE_FILE_NAME = "COPYING"
LICENSE_TARGET_FILE_NAME = "LICENSE-PyPiano-FluidR3_GM_sf2.txt"
SOUND_FONT_FILE_NAME = "FluidR3_GM.sf2"
DOWNLOAD_DIR_NAME = "temp"
REQUEST_TIMEOUT_SECONDS = 30

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


def get_latest_package_version(url: str) -> None:
    """TO DO: Infer latest package version."""


def check_signature(file_path: str) -> None:
    """TO DO: Check signature."""


def download_file(url: str, target_dir: str | Path) -> None:
    """Download a file with a progress bar."""
    target_path = Path(target_dir)
    r = requests.get(url, stream=True, timeout=REQUEST_TIMEOUT_SECONDS)
    r.raise_for_status()

    total = int(r.headers.get("content-length", 0))

    with (
        target_path.open("wb") as file,
        tqdm(
            desc=str(target_path.absolute()),
            total=total,
            unit="iB",
            unit_scale=True,
            unit_divisor=1024,
        ) as bar,
    ):
        for data in r.iter_content(chunk_size=1024):
            size = file.write(data)
            bar.update(size)


def unpack_tar(archive_file: str | Path, target_file: str) -> None:
    """Extract a .tar.gz archive, rejecting members that would escape the target directory."""
    with tarfile.open(archive_file, "r:gz") as tar:
        tar.extractall(path=target_file, filter="data")


def main() -> None:
    """Download the sound font and copy it and its license into the package."""
    package_root_path = Path(__file__).parents[1]

    download_dir = Path.joinpath(package_root_path, DOWNLOAD_DIR_NAME)

    download_dir.mkdir(exist_ok=True)

    tar_file_name = f"{PACKAGE_NAME}_{PACKAGE_VERSION}.{FILE_EXTENSION}"

    download_url = f"{BASE_URL}/{PACKAGE_NAME}/{tar_file_name}"

    download_file_path = Path.joinpath(download_dir, tar_file_name)
    sound_font_target_dir = Path(package_root_path, "pypiano/sound_fonts")
    download_file(download_url, download_file_path)

    unpack_tar(download_file_path, str(download_dir.absolute()))

    license_target_dir = Path.joinpath(package_root_path, "licenses")
    license_source_path = str(Path.joinpath(download_dir, UNPACK_DIR, LICENSE_SOURCE_FILE_NAME).absolute())
    license_target_path = str(Path.joinpath(license_target_dir, LICENSE_TARGET_FILE_NAME).absolute())
    copyfile(license_source_path, license_target_path)

    sound_font_source_path = str(Path.joinpath(download_dir, UNPACK_DIR, SOUND_FONT_FILE_NAME).absolute())
    sound_font_target_path = str(Path.joinpath(sound_font_target_dir, SOUND_FONT_FILE_NAME).absolute())
    copyfile(sound_font_source_path, sound_font_target_path)

    rmtree(download_dir)

    logger.info("DONE")


if __name__ == "__main__":
    main()
