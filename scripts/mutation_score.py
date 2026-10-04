"""Check the mutation score of the last mutmut run against a minimum.

Reads mutants/mutmut-cicd-stats.json (written by mutmut export-cicd-stats). A mutant counts as caught when a test failed
(killed), crashed (segfault) or hung (timeout). Below the minimum, every mutant that was not caught is printed with its
diff, so it is clear which change the tests did not notice.

Run with: make mutation, or uv run scripts/mutation_score.py --min 100
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

STATS_PATH = Path("mutants/mutmut-cicd-stats.json")
CAUGHT = ("killed", "segfault", "timeout")
NOT_CAUGHT = ("survived", "no_tests", "suspicious")


def mutation_score(stats: dict[str, int]) -> tuple[float, int, int]:
    """Return the score in percent, the number of caught mutants and the number of tested mutants."""
    caught = sum(stats.get(status, 0) for status in CAUGHT)
    tested = caught + sum(stats.get(status, 0) for status in NOT_CAUGHT)
    return (100.0 * caught / tested if tested else 100.0), caught, tested


def uncaught_mutants() -> list[str]:
    """Return the names of the mutants mutmut reports as not caught."""
    results = subprocess.run(["mutmut", "results"], capture_output=True, text=True, check=True).stdout  # noqa: S607 - mutmut from the project environment
    return [
        line.split(":")[0].strip()
        for line in results.splitlines()
        if line.rsplit(":", 1)[-1].strip().replace(" ", "_") in NOT_CAUGHT
    ]


def main(argv: list[str] | None = None) -> int:
    """Print the mutation score and fail if it is below the minimum."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--min", type=float, default=100.0, help="minimum mutation score in percent")
    args = parser.parse_args(argv)

    score, caught, tested = mutation_score(json.loads(STATS_PATH.read_text()))
    print(f"Mutation score: {score:.1f}% ({caught} of {tested} mutants caught), minimum {args.min:g}%")  # noqa: T201
    if score >= args.min:
        return 0

    for name in uncaught_mutants():
        diff = subprocess.run(["mutmut", "show", name], capture_output=True, text=True, check=True).stdout  # noqa: S603, S607 - name comes from mutmut
        print(f"\nNot caught: {name}\n{diff}")  # noqa: T201
    print("\nAdd or tighten a test so it fails for these changes, or mark an equivalent mutant with")  # noqa: T201
    print("'# pragma: no mutate' and the reason why the change cannot alter behavior.")  # noqa: T201
    return 1


if __name__ == "__main__":
    sys.exit(main())
