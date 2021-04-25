# -*- coding: utf-8 -*-
"""

"""
import os
import requests
import tempfile
import tarfile
import logging
from pathlib import Path
from shutil import copyfile, rmtree
from typing import Union
from tqdm import tqdm

BASE_URL = "http://deb.debian.org/debian/pool/main/f"
PACKAGE_NAME = "fluid-soundfont"
PACKAGE_VERSION = 3.1
FILE_EXTENSION = "orig.tar.gz"
UNPACK_DIR = "fluid-soundfont-3.1"
LICENSE_SOURCE_FILE_NAME = "COPYING"
LICENSE_TARGET_FILE_NAME = "LICENSE-FluidR3_GM_sf2.txt"
SOUND_FONT_FILE_NAME = "FluidR3_GM.sf2"
DOWNLOAD_DIR_NAME = "temp"

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


def get_latest_package_version(url: str):
    """TO DO: Infer latest package version

    """
    pass


def check_signature(file_path: str):
    """TO DO: Check signature

    """
    pass


def download_file(url: str, target_dir: Union[str, Path]) -> None:
    """

    """
    target_path = Path(target_dir)
    r = requests.get(url, stream=True)

    http_status = r.status_code

    if http_status != 200:
        raise Exception("Request was not successfull. Got response {0}".format(http_status))

    total = int(r.headers.get('content-length', 0))

    with open(target_path, 'wb') as file, tqdm(
            desc=str(target_path.absolute()),
            total=total,
            unit='iB',
            unit_scale=True,
            unit_divisor=1024,
    ) as bar:
        for data in r.iter_content(chunk_size=1024):
            size = file.write(data)
            bar.update(size)


def unpack_tar(archive_file: Union[str, Path], target_file: str) -> None:
    """

    """
    with tarfile.open(archive_file, "r:gz") as tar:
        tar.extractall(path=target_file)


def main() -> None:
    """

    """
    package_root_path = Path(__file__).parents[1]

    download_dir = Path.joinpath(package_root_path, DOWNLOAD_DIR_NAME)

    if not download_dir.exists():
        os.mkdir(download_dir)

    tar_file_name = "{package_name}_{package_version}.{extension}".format(
        package_name=PACKAGE_NAME,
        package_version=PACKAGE_VERSION,
        extension=FILE_EXTENSION)

    download_url = "{base_url}/{package_name}/{file_name}".format(
        base_url=BASE_URL,
        package_name=PACKAGE_NAME,
        file_name=tar_file_name
    )

    download_file_path= Path.joinpath(download_dir, tar_file_name)
    sound_font_target_dir = Path(package_root_path, "pyano/sound_fonts")
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
