"""Check the mutation score of the last mutmut run against a minimum.

Reads mutants/mutmut-cicd-stats.json (written by mutmut export-cicd-stats). The score is the share of caught mutants
among all mutants of the run, apart from skipped ones, which mutmut leaves out of its own score too. A mutant counts as
caught when a test failed (killed), crashed (segfault) or hung (timeout), or when the type checker rejected it. Every
other status counts against the score, also mutants mutmut never checked, so a broken or interrupted run fails; a run
without any mutant to count fails as well. Below the minimum, every mutant that was not caught is printed with its diff,
so it is clear which change the tests did not notice.

Run with: make mutation, or uv run scripts/mutation_score.py --min 100
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

STATS_PATH = Path("mutants/mutmut-cicd-stats.json")
# Statuses as mutmut 3 writes them to the stats file; total is the number of all mutants
CAUGHT = ("killed", "segfault", "timeout", "caught_by_type_check")
EXCLUDED = ("skipped",)


def mutation_score(stats: dict[str, int]) -> tuple[float, int, int]:
    """Return the score in percent, the number of caught mutants and the number of counted mutants.

    Counted are all mutants but the excluded ones. Without any, the score is 0.
    """
    caught = sum(stats.get(status, 0) for status in CAUGHT)
    counted = stats.get("total", 0) - sum(stats.get(status, 0) for status in EXCLUDED)
    return (100.0 * caught / counted if counted > 0 else 0.0), caught, counted


def uncaught_mutants() -> list[str]:
    """Return the names of the counted mutants that mutmut reports as not caught."""
    # Lists every mutant that was not killed, as "    <name>: <status>"
    results = subprocess.run(["mutmut", "results"], capture_output=True, text=True, check=True).stdout  # noqa: S607 - mutmut from the project environment
    return [
        line.split(":")[0].strip()
        for line in results.splitlines()
        if line.rsplit(":", 1)[-1].strip().replace(" ", "_") not in (*CAUGHT, *EXCLUDED)
    ]


def main(argv: list[str] | None = None) -> int:
    """Print the mutation score and fail if it is below the minimum or if no mutant was counted."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--min", type=float, default=100.0, help="minimum mutation score in percent")
    args = parser.parse_args(argv)

    score, caught, counted = mutation_score(json.loads(STATS_PATH.read_text()))
    print(f"Mutation score: {score:.1f}% ({caught} of {counted} mutants caught), minimum {args.min:g}%")  # noqa: T201
    if counted <= 0:
        print("No mutants to count, so the run checked nothing; see mutmut's output above.")  # noqa: T201
        return 1
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
