import importlib.util
import json
import subprocess
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "mutation_score.py"


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("mutation_score", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def script(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> ModuleType:
    """The script with its stats file in tmp_path and mutmut replaced."""
    module = load_script()
    monkeypatch.setattr(module, "STATS_PATH", tmp_path / "mutmut-cicd-stats.json")
    run = MagicMock(name="subprocess.run")
    run.side_effect = lambda args, **_: subprocess.CompletedProcess(
        args,
        0,
        stdout="    a.x_f__mutmut_1: timeout\n    a.x_f__mutmut_2: survived\n    a.x_f__mutmut_3: no tests\n"
        "    a.x_f__mutmut_4: not checked\n    a.x_f__mutmut_5: skipped\n    a.x_f__mutmut_6: caught by type check\n"
        if args[1] == "results"
        else f"diff of {args[2]}",
    )
    monkeypatch.setattr(module.subprocess, "run", run)
    return module


def write_stats(script: ModuleType, **stats: int) -> None:
    script.STATS_PATH.write_text(json.dumps(stats))


@pytest.mark.parametrize(
    ("stats", "expected"),
    [
        ({"killed": 9, "survived": 1, "total": 10}, (90.0, 9, 10)),
        (
            {
                "killed": 5,
                "segfault": 1,
                "timeout": 1,
                "caught_by_type_check": 1,
                "suspicious": 1,
                "no_tests": 1,
                "total": 10,
            },
            (80.0, 8, 10),
        ),
        ({"killed": 4, "skipped": 3, "total": 7}, (100.0, 4, 4)),
        ({"killed": 2, "not_checked": 6, "check_was_interrupted_by_user": 2, "total": 10}, (20.0, 2, 10)),
        ({"killed": 2}, (0.0, 2, 0)),
        ({"skipped": 3, "total": 3}, (0.0, 0, 0)),
        ({}, (0.0, 0, 0)),
    ],
    ids=[
        "killed and survived",
        "crashes, hangs and type check rejections count as caught",
        "skipped mutants are not counted",
        "unchecked mutants count against the score",
        "no total",
        "only skipped mutants",
        "nothing counted",
    ],
)
def test_mutation_score_should_count_caught_mutants_among_all_but_skipped_ones_when_given_stats(
    script: ModuleType, stats: dict[str, int], expected: tuple[float, int, int]
) -> None:
    # Given mutmut's statistics
    # When
    result = script.mutation_score(stats)
    # Then
    assert result == expected


def test_main_should_pass_when_score_reaches_the_minimum(
    script: ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # Given a run where every mutant was caught
    write_stats(script, killed=10, total=10)
    # When
    exit_code = script.main(["--min", "100"])
    # Then
    assert exit_code == 0
    assert capsys.readouterr().out == "Mutation score: 100.0% (10 of 10 mutants caught), minimum 100%\n"


def test_main_should_fail_and_show_the_uncaught_mutants_when_score_is_below_the_minimum(
    script: ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # Given a run with mutants that no test caught
    write_stats(script, killed=7, timeout=1, survived=1, no_tests=1, not_checked=1, skipped=1, total=12)
    # When
    exit_code = script.main(["--min", "95"])
    # Then the mutants not caught are shown, but not the caught or skipped ones
    out = capsys.readouterr().out
    assert exit_code == 1
    assert "Mutation score: 72.7% (8 of 11 mutants caught), minimum 95%" in out
    assert "Not caught: a.x_f__mutmut_2\ndiff of a.x_f__mutmut_2" in out
    assert "Not caught: a.x_f__mutmut_3\ndiff of a.x_f__mutmut_3" in out
    assert "Not caught: a.x_f__mutmut_4\ndiff of a.x_f__mutmut_4" in out
    for caught_or_skipped in ("a.x_f__mutmut_1", "a.x_f__mutmut_5", "a.x_f__mutmut_6"):
        assert caught_or_skipped not in out


@pytest.mark.parametrize("minimum", ["100", "0"])
def test_main_should_fail_when_no_mutant_was_counted(
    script: ModuleType, capsys: pytest.CaptureFixture[str], minimum: str
) -> None:
    # Given a run without mutants to count, whatever the minimum
    write_stats(script, skipped=2, total=2)
    # When
    exit_code = script.main(["--min", minimum])
    # Then
    assert exit_code == 1
    assert capsys.readouterr().out == (
        f"Mutation score: 0.0% (0 of 0 mutants caught), minimum {minimum}%\n"
        "No mutants to count, so the run checked nothing; see mutmut's output above.\n"
    )
