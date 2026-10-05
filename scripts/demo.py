"""Play or record a note with PyPiano to check that the setup works.

Usage:
    uv run scripts/demo.py play [--note C-4] [--instrument "Acoustic Grand Piano"]
    uv run scripts/demo.py record [--note C-4] [--output demo.wav] [--seconds 2]
"""

import argparse
import logging
from pathlib import Path

from pypiano import Piano

logger = logging.getLogger("pypiano.demo")

# fluidsynth plays asynchronously, so keep the process alive until the note has sounded
PLAY_SECONDS = 2


def main() -> None:
    """Parse the command line and play or record the note."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["play", "record"])
    parser.add_argument("--note", default="C-4", help="note in mingus notation, e.g. C-4, A#-3")
    parser.add_argument("--instrument", default="Acoustic Grand Piano")
    parser.add_argument("--output", type=Path, default=Path("demo.wav"), help="wav file for record")
    parser.add_argument("--seconds", type=int, default=2, help="recording length for record")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    piano = Piano(instrument=args.instrument)
    if args.command == "play":
        logger.info("Playing %s on %s via audio output", args.note, args.instrument)
        piano.play(args.note)
        piano.pause(PLAY_SECONDS)
    else:
        piano.record(args.note, args.output, seconds=args.seconds)
        logger.info("Recorded %s on %s to %s", args.note, args.instrument, args.output.resolve())


if __name__ == "__main__":
    main()
