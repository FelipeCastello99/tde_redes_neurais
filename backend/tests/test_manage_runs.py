from __future__ import annotations

import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT / "scripts"))

import manage_runs  # noqa: E402


def make_run(
    name: str = "run",
    status: str = "done",
    target: str = "fatal_binario",
    day: int = 1,
    metrics: dict | None = None,
) -> manage_runs.RunInfo:
    return manage_runs.RunInfo(
        id=uuid.uuid4(),
        name=name,
        status=status,
        target=target,
        created_at=datetime(2026, 1, day, 12, tzinfo=UTC),
        n_test=100,
        metrics=metrics,
    )


def test_resolve_prefix_unique() -> None:
    run_id = uuid.uuid4()
    assert manage_runs.resolve_prefix(str(run_id)[:8], [run_id]) == run_id
    assert manage_runs.resolve_prefix(str(run_id)[:8].upper(), [run_id]) == run_id


def test_resolve_prefix_rejects_short_or_invalid() -> None:
    run_id = uuid.uuid4()
    with pytest.raises(manage_runs.RunLookupError, match="ao menos 8"):
        manage_runs.resolve_prefix(str(run_id)[:7], [run_id])
    with pytest.raises(manage_runs.RunLookupError, match="hexadecimais"):
        manage_runs.resolve_prefix("zzzzzzzz", [run_id])


def test_resolve_prefix_missing() -> None:
    with pytest.raises(manage_runs.RunLookupError, match="nenhum run"):
        manage_runs.resolve_prefix("deadbeef", [uuid.uuid4()])


def test_resolve_prefix_ambiguous() -> None:
    shared = "aaaaaaaa"
    ids = [uuid.UUID(f"{shared}-0000-0000-0000-000000000001"),
           uuid.UUID(f"{shared}-0000-0000-0000-000000000002")]
    with pytest.raises(manage_runs.RunLookupError, match="ambíguo"):
        manage_runs.resolve_prefix(shared, ids)


def test_is_demo_run_only_matches_seeded_run() -> None:
    assert manage_runs.is_demo_run(make_run(name="Demo — PRF 2024")) is True
    assert manage_runs.is_demo_run(make_run(name="demo — prf 2024")) is True
    assert manage_runs.is_demo_run(make_run(name="Rápido (Demo)")) is False


def test_select_prune_keeps_recent_and_skips_active_and_demo() -> None:
    newest = make_run(name="r1", day=6)
    demo = make_run(name="Demo — PRF 2024", day=5)
    active = make_run(name="r3", status="running", day=4)
    middle = make_run(name="r4", day=3)
    oldest = make_run(name="r5", status="failed", day=2)

    selected = manage_runs.select_prune_candidates(
        [oldest, middle, active, demo, newest], keep=2
    )

    assert [run.name for run in selected] == ["r4", "r5"]


def test_select_prune_status_filter() -> None:
    done = make_run(name="ok", day=4)
    failed = make_run(name="bad", status="failed", day=3)
    canceled = make_run(name="canceled", status="canceled", day=2)

    selected = manage_runs.select_prune_candidates(
        [done, failed, canceled], keep=1, statuses={"failed"}
    )

    assert selected == [failed]


def test_select_prune_can_include_demo() -> None:
    newest = make_run(name="r1", day=3)
    demo = make_run(name="Demo — PRF 2024", day=2)

    assert manage_runs.select_prune_candidates([newest, demo], keep=1) == []
    assert manage_runs.select_prune_candidates(
        [newest, demo], keep=1, include_demo=True
    ) == [demo]


def test_select_prune_rejects_negative_keep() -> None:
    with pytest.raises(ValueError, match="negativo"):
        manage_runs.select_prune_candidates([], keep=-1)


def test_scan_artifacts_classifies_directories(tmp_path: Path) -> None:
    runs_dir = tmp_path / "runs"
    known = uuid.uuid4()
    missing = uuid.uuid4()
    orphan = uuid.uuid4()

    (runs_dir / str(known)).mkdir(parents=True)
    (runs_dir / str(orphan)).mkdir()
    (runs_dir / "not-a-uuid").mkdir()
    (runs_dir / "arquivo.txt").write_text("ignorado")

    report = manage_runs.scan_artifacts(runs_dir, [known, missing])

    assert report.healthy == 1
    assert report.orphans == [runs_dir / str(orphan)]
    assert report.broken == [missing]
    assert report.invalid == [runs_dir / "not-a-uuid"]
    assert report.has_issues is True


def test_scan_artifacts_clean_directory(tmp_path: Path) -> None:
    runs_dir = tmp_path / "runs"
    known = uuid.uuid4()
    (runs_dir / str(known)).mkdir(parents=True)

    report = manage_runs.scan_artifacts(runs_dir, [known])

    assert report.has_issues is False
    assert report.healthy == 1


def test_directory_size_sums_nested_files(tmp_path: Path) -> None:
    (tmp_path / "a.bin").write_bytes(b"x" * 10)
    nested = tmp_path / "sub"
    nested.mkdir()
    (nested / "b.bin").write_bytes(b"y" * 5)

    assert manage_runs.directory_size(tmp_path) == 15
    assert manage_runs.directory_size(tmp_path / "ausente") == 0


def test_fatal_f1_binary_and_three_classes() -> None:
    binary = {
        "precision_recall_f1": {
            "per_class": [
                {"class_index": 0, "f1": 0.8},
                {"class_index": 1, "f1": 0.31},
            ]
        }
    }
    three = {
        "precision_recall_f1": {
            "per_class": [
                {"class_index": 0, "f1": 0.6},
                {"class_index": 1, "f1": 0.5},
                {"class_index": 2, "f1": 0.42},
            ]
        }
    }

    assert manage_runs.fatal_f1(make_run(metrics=binary)) == pytest.approx(0.31)
    assert manage_runs.fatal_f1(
        make_run(target="gravidade_3_classes", metrics=three)
    ) == pytest.approx(0.42)
    assert manage_runs.fatal_f1(make_run(metrics=None)) is None


def test_format_bytes() -> None:
    assert manage_runs.format_bytes(512) == "512 B"
    assert manage_runs.format_bytes(2048) == "2.0 KB"
    assert manage_runs.format_bytes(5 * 1024 * 1024) == "5.0 MB"
