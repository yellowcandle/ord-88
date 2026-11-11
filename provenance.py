"""Provenance for the register classification and its positional sub-files.

``categorisation_meta.json`` records which register snapshot the labels belong to
and which model/prompt produced them. The build tests compare the recorded source
hash with ``s88list.csv`` so a same-size snapshot swap cannot pass silently.

A manifest is only advanced by a stage that is allowed to change its source:
``classify_or.py`` rewrites the categorisation and passes ``source_changed=True``;
the sub-classifiers and the rescue merge must leave the source hash alone.

Usage:
    python3 provenance.py --legacy   # seed a manifest only when none exists
    python3 provenance.py            # print the current manifest
"""
from __future__ import annotations

import csv
import datetime
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
META = ROOT / "categorisation_meta.json"
SUB_FILES = ("sub_religion.csv", "sub_community.csv", "sub_rescue.csv")


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def row_count(path: pathlib.Path) -> int:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def check_source() -> None:
    """Refuse to use labels that do not belong to the current inputs."""
    if not META.exists():
        return
    try:
        meta = json.loads(META.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise SystemExit(f"{META.name} is unreadable ({error}); fix or delete it") from None
    previous = meta.get("source_sha256")
    if previous and previous != sha256(ROOT / "s88list.csv"):
        raise SystemExit(
            "s88list.csv changed since the manifest was written; re-run classify_or.py first"
        )
    rows = meta.get("rows")
    if rows is not None and rows != row_count(ROOT / "s88list_categorised.csv"):
        raise SystemExit(
            "s88list_categorised.csv row count changed since the manifest was written; re-run classify_or.py"
        )
    for name, digest in meta.get("sub_files", {}).items():
        path = ROOT / name
        if not path.exists():
            raise SystemExit(f"{name} is missing; re-run its classifier or update the manifest")
        if sha256(path) != digest:
            raise SystemExit(f"{name} changed since the manifest was written; re-run its classifier")


def write_meta(
    *,
    model: str | None = None,
    prompt_version: str | None = None,
    fallback_rows: int | None = None,
    updated_by: list[str] | None = None,
    stage: str | None = None,
    source_changed: bool = False,
    applied: list[str] | None = None,
    note: str | None = None,
) -> dict:
    """Merge one stage's provenance into the manifest.

    ``source_changed`` is only for the pass that rewrites the categorisation from
    the current ``s88list.csv``. Any other pass that finds a different source hash
    refuses to run, so an old label set cannot be re-stamped as current.
    """
    meta: dict = {}
    if META.exists():
        try:
            meta = json.loads(META.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise SystemExit(f"{META.name} is unreadable ({error}); fix or delete it") from None

    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    current_sha = sha256(ROOT / "s88list.csv")
    previous_sha = meta.get("source_sha256")
    if previous_sha and previous_sha != current_sha and not source_changed:
        raise SystemExit(
            "s88list.csv changed since the manifest was written; "
            "re-run classify_or.py before updating sub-labels or provenance"
        )
    if source_changed:
        meta["applied"] = []
        meta.pop("stages", None)

    meta.update(
        {
            "source": "s88list.csv",
            "source_sha256": current_sha,
            "rows": row_count(ROOT / "s88list_categorised.csv"),
            "generated_at": now,
        }
    )
    sub_files = {name: sha256(ROOT / name) for name in SUB_FILES if (ROOT / name).exists()}
    meta["sub_files"] = sub_files
    if applied is not None:
        meta["applied"] = applied

    by = list(updated_by or [])
    if by:
        previous = meta.get("updated_by", [])
        meta["updated_by"] = previous + [item for item in by if item not in previous]

    recorded = {
        key: value
        for key, value in {
            "model": model,
            "prompt_version": prompt_version,
            "fallback_rows": fallback_rows,
        }.items()
        if value is not None
    }
    if stage:
        stage_record = {"at": now, "by": by, **recorded}
        if applied is not None:
            stage_record["applied"] = applied
        if note:
            stage_record["note"] = note
        meta.setdefault("stages", {})[stage] = stage_record
    entry = {"at": now, "by": by, **recorded}
    if stage:
        entry["stage"] = stage
    meta.setdefault("history", []).append(entry)
    meta.update(recorded)
    if note:
        meta["note"] = note

    try:
        META.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except OSError as error:
        raise SystemExit(f"cannot write {META.name}: {error}") from None
    return meta


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if "--legacy" in args:
        if META.exists():
            print(f"{META.name} already exists; refusing to overwrite it", file=sys.stderr)
            return 1
        meta = write_meta(
            model="unknown (pre-manifest)",
            prompt_version="pre-manifest",
            fallback_rows=None,
            updated_by=["provenance.py --legacy"],
            stage="legacy",
        )
        print(f"wrote {META.name}: {meta['rows']} rows from {meta['source']}")
        return 0
    if META.exists():
        print(META.read_text(encoding="utf-8"), end="")
        return 0
    print(f"{META.name} does not exist; run a classifier or `provenance.py --legacy`", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
