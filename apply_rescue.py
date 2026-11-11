#!/usr/bin/env python3
"""Fold sub_rescue.csv into s88list_categorised.csv.

sub_rescue.csv is positional over the OTH rows. Names are checked before anything
is written, so a regenerated register cannot silently mislabel. The write is
atomic and the command is safe to re-run: once applied, it recognises the result
and does nothing.
"""
import csv
import json
import os
import pathlib
import tempfile
from collections import Counter

from provenance import write_meta
from taxonomy import CATEGORY_LABELS

CATS = "s88list_categorised.csv"
RESCUE = "sub_rescue.csv"


class AlreadyApplied(Exception):
    """The rescue output has already been merged."""


def name(row):
    return (row["english_name"].strip(), row["chinese_name"].strip())


def read_rows(path):
    try:
        with open(path, encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))
    except OSError as error:
        raise SystemExit(f"cannot read {path}: {error}") from None


def merge(rows, rescue):
    """Return (new rows, changed count). Raise AlreadyApplied or ValueError."""
    rows = [dict(row) for row in rows]
    oth = [row for row in rows if row["code"] == "OTH"]
    rescue_oth = Counter(name(row) for row in rescue if row["result"].strip().upper() == "OTH")
    current = Counter(name(row) for row in oth)
    if len(oth) != len(rescue):
        if current == rescue_oth:
            raise AlreadyApplied
        raise ValueError(
            f"{len(oth)} OTH rows but {len(rescue)} rescue rows — re-run `classify_sub.py rescue`"
        )

    changed = 0
    for row, hit in zip(oth, rescue, strict=True):
        if name(row) != name(hit):
            raise ValueError(f"stale sub_rescue.csv at {name(row)} — re-run `classify_sub.py rescue`")
        code = hit["result"].strip().upper()
        if code == "OTH":
            continue
        if code not in CATEGORY_LABELS:
            raise ValueError(f"unknown category {code!r} for {name(row)}")
        row["code"] = code
        row["category"] = CATEGORY_LABELS[code]
        changed += 1
    return rows, changed


def write_rows(path, rows):
    fd, temporary = tempfile.mkstemp(dir=".", prefix=".categorised-", suffix=".csv")
    try:
        with os.fdopen(fd, "w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        os.replace(temporary, path)
    except OSError as error:
        pathlib.Path(temporary).unlink(missing_ok=True)
        raise SystemExit(f"cannot write {path}: {error}") from None


def write_counts(rows):
    counts = Counter(row["code"] for row in rows)
    try:
        with open("category_counts.json", "w", encoding="utf-8") as handle:
            json.dump({"total": len(rows), "counts": dict(counts), "labels": CATEGORY_LABELS},
                      handle, ensure_ascii=False, indent=2)
    except OSError as error:
        raise SystemExit(f"cannot write category_counts.json: {error}") from None


def main() -> int:
    rows = read_rows(CATS)
    rescue = read_rows(RESCUE)
    try:
        rows, changed = merge(rows, rescue)
    except AlreadyApplied:
        rows = read_rows(CATS)
        write_counts(rows)
        write_meta(updated_by=["apply_rescue.py"])
        print(f"{RESCUE} is already merged; category_counts.json refreshed; nothing to do")
        return 0
    except ValueError as error:
        raise SystemExit(str(error)) from None
    write_rows(CATS, rows)
    write_counts(rows)
    write_meta(applied=[RESCUE], updated_by=["apply_rescue.py"])
    print(f"applied {changed} rescues; {len(rows) - changed} rows unchanged")
    print("Next: refresh the positional sub-files, then rebuild:")
    print("  python3 classify_sub.py religion --since HEAD")
    print("  python3 classify_sub.py community --since HEAD")
    print("  python3 build_site.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
