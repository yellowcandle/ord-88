"""Provenance for the register classification and its positional sub-files.

``categorisation_meta.json`` records which register snapshot the labels belong to
and which model/prompt produced them. The build tests compare the recorded source
hash with ``s88list.csv`` so a same-size snapshot swap cannot pass silently.

Usage:
    python3 provenance.py --legacy   # backfill the manifest for pre-manifest data
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


def write_meta(**fields) -> dict:
    """Merge ``fields`` into the manifest with the current source identity."""
    meta: dict = {}
    if META.exists():
        try:
            meta = json.loads(META.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise SystemExit(f"{META.name} is unreadable ({error}); fix or delete it") from None
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    meta.update(
        {
            "source": "s88list.csv",
            "source_sha256": sha256(ROOT / "s88list.csv"),
            "rows": row_count(ROOT / "s88list_categorised.csv"),
            "generated_at": now,
        }
    )
    sub_files = {name: sha256(ROOT / name) for name in SUB_FILES if (ROOT / name).exists()}
    if sub_files:
        meta["sub_files"] = sub_files

    updated_by = fields.pop("updated_by", [])
    if updated_by:
        previous = meta.get("updated_by", [])
        meta["updated_by"] = previous + [item for item in updated_by if item not in previous]
    entry = {"at": now, "by": updated_by}
    entry.update({key: fields[key] for key in ("model", "prompt_version", "fallback_rows") if key in fields})
    meta.setdefault("history", []).append(entry)

    meta.update(fields)
    META.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return meta


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if "--legacy" in args:
        meta = write_meta(
            model="unknown (pre-manifest)",
            prompt_version="pre-manifest",
            fallback_rows=None,
            updated_by=["provenance.py --legacy"],
        )
        print(f"wrote {META.name}: {meta['rows']} rows from {meta['source']}")
        return 0
    if META.exists():
        print(META.read_text(encoding="utf-8"), end="")
        return 0
    print(f"{META.name} does not exist; run `provenance.py --legacy` or a classifier", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
