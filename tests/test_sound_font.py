"""Structure of the bundled sound font: only the expected chunks, the eight pianos and the attribution, and exactly the
file scripts/build_sound_font.py builds from Debian's FluidR3_GM."""

import hashlib
import importlib.util
import struct
from collections.abc import Iterator
from pathlib import Path

import pytest

from pypiano import DEFAULT_INSTRUMENTS, DEFAULT_SOUND_FONTS

BUILD_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_sound_font.py"
PIANO_PRESETS = [
    (0, 0, "Yamaha Grand Piano"),
    (0, 1, "Bright Yamaha Grand"),
    (0, 2, "Electric Piano"),
    (0, 3, "Honky Tonk"),
    (0, 4, "Rhodes EP"),
    (0, 5, "Legend EP 2"),
    (0, 6, "Harpsichord"),
    (0, 7, "Clavinet"),
]
# The SoundFont 2 layout: an INFO list, the sample data and the preset data, nothing else
EXPECTED_LISTS = {
    b"INFO": {b"ifil", b"isng", b"INAM", b"ICRD", b"IENG", b"IPRD", b"ICOP", b"ICMT", b"ISFT"},
    b"sdta": {b"smpl"},
    b"pdta": {b"phdr", b"pbag", b"pmod", b"pgen", b"inst", b"ibag", b"imod", b"igen", b"shdr"},
}


def chunks(data: bytes, start: int, end: int) -> Iterator[tuple[bytes, int, int]]:
    """Yield the id, data offset and size of each RIFF chunk between start and end."""
    offset = start
    while offset < end:
        chunk_id, size = data[offset : offset + 4], struct.unpack("<I", data[offset + 4 : offset + 8])[0]
        assert offset + 8 + size <= end, f"chunk {chunk_id!r} runs past its container"
        yield chunk_id, offset + 8, size
        offset += 8 + size + (size & 1)


@pytest.fixture(scope="module")
def sound_font() -> bytes:
    return DEFAULT_SOUND_FONTS.read_bytes()


@pytest.fixture(scope="module")
def lists(sound_font: bytes) -> dict[bytes, dict[bytes, bytes]]:
    """The sub-chunks of each top-level LIST, by id."""
    assert sound_font[:4] == b"RIFF"
    assert sound_font[8:12] == b"sfbk"
    assert struct.unpack("<I", sound_font[4:8])[0] == len(sound_font) - 8
    result: dict[bytes, dict[bytes, bytes]] = {}
    for chunk_id, offset, size in chunks(sound_font, 12, len(sound_font)):
        assert chunk_id == b"LIST"
        kind = sound_font[offset : offset + 4]
        result[kind] = {
            sub_id: sound_font[sub_offset : sub_offset + sub_size]
            for sub_id, sub_offset, sub_size in chunks(sound_font, offset + 4, offset + size)
        }
    return result


def test_sound_font_should_be_the_reproducible_build_when_bundled(sound_font: bytes) -> None:
    # Given the checksum the build script verifies its output against
    spec = importlib.util.spec_from_file_location("build_sound_font", BUILD_SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    script = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(script)
    # When / Then (CI rebuilds it from Debian's archive with make soundfont-check)
    assert script.SOUND_FONT_PATH.name == DEFAULT_SOUND_FONTS.name
    assert hashlib.sha256(sound_font).hexdigest() == script.PIANOS_SHA256


def test_sound_font_should_contain_only_the_soundfont_2_chunks_when_parsed(
    lists: dict[bytes, dict[bytes, bytes]],
) -> None:
    # Given the parsed chunk layout
    # When / Then: no extra chunks and no 24-bit sample extension
    assert {kind: set(sub) for kind, sub in lists.items()} == EXPECTED_LISTS


def test_sound_font_should_contain_exactly_the_eight_pianos_when_parsed(
    lists: dict[bytes, dict[bytes, bytes]],
) -> None:
    # Given the preset headers (38 bytes each, the last is the terminal "EOP" record)
    records = lists[b"pdta"][b"phdr"]
    presets = []
    for offset in range(0, len(records) - 38, 38):
        name, program, bank = struct.unpack("<20sHH", records[offset : offset + 24])
        presets.append((bank, program, name.split(b"\0")[0].decode("latin-1")))
    # When / Then (the file stores presets in no particular order)
    assert sorted(presets) == PIANO_PRESETS
    assert sorted(DEFAULT_INSTRUMENTS.values()) == [program for _, program, _ in PIANO_PRESETS]


def test_sound_font_should_keep_the_fluidr3_attribution_and_record_sf2_cutter_when_parsed(
    lists: dict[bytes, dict[bytes, bytes]],
) -> None:
    # Given the INFO chunk
    info = {key.decode(): value.rstrip(b"\0").decode("latin-1") for key, value in lists[b"INFO"].items()}
    # When / Then
    assert info["INAM"] == "Fluid R3 GM pianos"
    assert info["IENG"] == "Frank Wen"
    assert info["ICOP"] == "Frank Wen 2000-2002, 2008; Toby Smithe 2008"
    assert info["ICMT"] == "Licensed under the MIT License."
    assert info["ISFT"].endswith(":sf2-cutter v0.1.0")
