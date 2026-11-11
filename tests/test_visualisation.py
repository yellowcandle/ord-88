"""Behaviour of the Section 88 plate: aggregation, provenance and rendered output.

The plate is a build artefact of several CSVs, so the tests assert *relationships*
between the source files and the rendered page rather than snapshot numbers. A stale
sub_*.csv (the bug these tests exist to catch) breaks the provenance tests instead of
silently changing a number.
"""

import csv
import hashlib
import io
import json
import pathlib
import re
import sys
import unittest
import urllib.error
from collections import Counter
from contextlib import redirect_stderr
from email.message import Message
from html.parser import HTMLParser
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import apply_rescue
import build_site
import classify_sub

ROOT = pathlib.Path(__file__).resolve().parent.parent
MONTHS = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]


def read_rows(name):
    with (ROOT / name).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


class ScheduleParser(HTMLParser):
    """Collect the cells of every table row in the rendered page."""

    def __init__(self):
        super().__init__()
        self.rows = []
        self._row = None
        self._cell = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell = []

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._cell is not None and self._row is not None:
            self._row.append("".join(self._cell).strip())
            self._cell = None
        elif tag == "tr" and self._row is not None:
            self.rows.append(self._row)
            self._row = None


class AggregateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = build_site.aggregate(ROOT)
        cls.labelled = read_rows("s88list_categorised.csv")

    def test_register_total_matches_the_source_rows(self):
        with (ROOT / "s88list.csv").open(encoding="utf-8-sig", newline="") as handle:
            register = [row for row in csv.reader(handle)][1:]
        self.assertEqual(self.data["total"], len(self.labelled))
        self.assertEqual(
            self.data["total"], len([row for row in register if any(c.strip() for c in row)])
        )

    def test_register_date_is_read_from_the_register(self):
        with (ROOT / "s88list.csv").open(encoding="utf-8-sig", newline="") as handle:
            stamp = next(row for row in csv.reader(handle) if row and "/" in row[0])[0].strip()
        day, month, year = stamp.split("/")
        self.assertEqual(self.data["as_at"], f"{int(day)} {MONTHS[int(month) - 1]} {year}")
        self.assertEqual(self.data["as_at_zh"], f"{year}年{int(month)}月{int(day)}日")

    def test_purposes_partition_the_register(self):
        purposes = self.data["purposes"]
        self.assertEqual(sum(row["count"] for row in purposes), self.data["total"])
        # Each share is rounded to one decimal, so the printed column may miss 100 by
        # up to half a tenth per row — never by a whole category.
        self.assertAlmostEqual(
            sum(row["share"] for row in purposes), 100.0, delta=0.05 * len(purposes)
        )
        self.assertEqual(
            [row["count"] for row in purposes],
            sorted((row["count"] for row in purposes), reverse=True),
        )
        for row in purposes:
            self.assertTrue(row["en"] and row["zh"], row)

    def test_stage_one_merges_the_smallest_purposes(self):
        stage1 = self.data["stage1"]
        self.assertEqual(len(stage1), 7)
        self.assertEqual(sum(row["height"] for row in stage1), 560)
        self.assertEqual(sum(row["count"] for row in stage1), self.data["total"])
        self.assertEqual(
            stage1[-1]["count"], sum(row["count"] for row in self.data["purposes"][6:])
        )

    def test_traditions_fill_their_height_budget(self):
        traditions = self.data["traditions"]
        self.assertEqual(len(traditions), 5)
        self.assertEqual(traditions[0]["en"], "Protestant Christian")
        self.assertEqual(sum(row["height"] for row in traditions), 300)
        self.assertEqual(sum(row["count"] for row in traditions), self.data["religious_total"])

    def test_every_religious_organisation_has_a_faith_label(self):
        """sub_religion.csv is positional: it must be regenerated with the categorisation."""
        religious = [row for row in self.labelled if row["code"] == "REL"]
        labels = read_rows("sub_religion.csv")
        self.assertEqual(
            len(labels),
            len(religious),
            "sub_religion.csv is stale — re-run classify_sub.py religion",
        )
        for index, (org, label) in enumerate(zip(religious, labels)):
            self.assertEqual(
                (label["english_name"], label["chinese_name"]),
                (org["english_name"], org["chinese_name"]),
                f"sub_religion.csv row {index} does not match s88list_categorised.csv — re-run classify_sub.py religion",
            )
            self.assertRegex(label["result"], r"^[A-Z]{2,6}/")
        self.assertEqual(self.data["religious_unclassified"], 0)
        self.assertEqual(self.data["religious_total"], self.data["religious_band"])

    def test_every_community_organisation_has_a_community_label(self):
        community = [row for row in self.labelled if row["code"] == "COM"]
        labels = read_rows("sub_community.csv")
        self.assertEqual(
            len(labels),
            len(community),
            "sub_community.csv is stale — re-run classify_sub.py community",
        )
        for index, (org, label) in enumerate(zip(community, labels)):
            self.assertEqual(
                (label["english_name"], label["chinese_name"]),
                (org["english_name"], org["chinese_name"]),
                f"sub_community.csv row {index} does not match s88list_categorised.csv — re-run classify_sub.py community",
            )
            self.assertIn(label["result"], build_site.COMMUNITY)
        self.assertEqual(self.data["community_unclassified"], 0)

    def test_denominations_resolve_protestant_christian(self):
        rows = self.data["denominations"]
        self.assertEqual(len(rows), self.data["denomination_count"])
        self.assertEqual(sum(row["count"] for row in rows), self.data["denomination_total"])
        self.assertEqual(self.data["denomination_total"], self.data["traditions"][0]["count"])

    def test_height_allocation_never_exceeds_its_budget(self):
        self.assertEqual(sum(build_site.allocate([1, 1, 1, 1000], 560)), 560)
        self.assertEqual(len(build_site.allocate([4582, 2645, 2275], 300, minimum=12)), 3)
        self.assertEqual(sum(build_site.allocate([4582, 2645, 2275], 300, minimum=12)), 300)
        self.assertEqual(build_site.allocate([], 560), [])
        self.assertEqual(sum(build_site.allocate([0, 0, 0], 560)), 560)
        with self.assertRaises(ValueError):
            build_site.allocate([1, 1], 561)
        self.assertEqual(build_site.share(0, 0), 0.0)


class ProvenanceTest(unittest.TestCase):
    def test_manifest_matches_this_register(self):
        meta = json.loads((ROOT / "categorisation_meta.json").read_text(encoding="utf-8"))
        self.assertEqual(
            meta["source_sha256"], hashlib.sha256((ROOT / "s88list.csv").read_bytes()).hexdigest()
        )
        self.assertEqual(meta["rows"], len(read_rows("s88list_categorised.csv")))
        if (ROOT / "sub_rescue.csv").exists():
            self.assertIn("sub_rescue.csv", meta.get("applied", []))

    def test_manifest_sub_file_hashes_are_current(self):
        meta = json.loads((ROOT / "categorisation_meta.json").read_text(encoding="utf-8"))
        for name, digest in meta["sub_files"].items():
            self.assertEqual(digest, hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), name)

    def test_category_counts_matches_the_categorisation(self):
        counts = json.loads((ROOT / "category_counts.json").read_text(encoding="utf-8"))
        rows = read_rows("s88list_categorised.csv")
        self.assertEqual(counts["total"], len(rows))
        self.assertEqual(counts["counts"], dict(Counter(row["code"] for row in rows)))

    def test_categorisation_rows_follow_the_register(self):
        with (ROOT / "s88list.csv").open(encoding="utf-8-sig", newline="") as handle:
            register = list(csv.reader(handle))[1:]
        register = [row for row in register if any(cell.strip() for cell in row)]
        labelled = read_rows("s88list_categorised.csv")
        self.assertEqual(
            [(row[1].strip(), row[2].strip()) for row in register],
            [(row["english_name"].strip(), row["chinese_name"].strip()) for row in labelled],
        )


class BuildGuardTest(unittest.TestCase):
    def test_incomplete_inputs_refuse_to_render(self):
        data = build_site.aggregate(ROOT)
        data["religious_unclassified"] = 1
        with (
            mock.patch.object(build_site, "aggregate", return_value=data),
            mock.patch.object(build_site, "render", side_effect=AssertionError("must not render")),
            redirect_stderr(io.StringIO()),
        ):
            self.assertEqual(build_site.main([]), 2)


class RescuePipelineTest(unittest.TestCase):
    @staticmethod
    def row(english, code="OTH", date="01/01/2020"):
        return {
            "code": code,
            "category": "",
            "english_name": english,
            "chinese_name": "",
            "effective_date": date,
        }

    def test_merge_changes_only_reclassified_oth_rows(self):
        rows = [self.row("A"), self.row("B"), self.row("C", code="EDU")]
        rescue = [
            {"result": "REL", "english_name": "A", "chinese_name": ""},
            {"result": "OTH", "english_name": "B", "chinese_name": ""},
        ]
        merged, changed = apply_rescue.merge(rows, rescue)
        self.assertEqual(changed, 1)
        self.assertEqual([row["code"] for row in merged], ["REL", "OTH", "EDU"])
        self.assertEqual(merged[0]["category"], "Religious 宗教")

    def test_merge_rejects_a_stale_rescue_file(self):
        rows = [self.row("A")]
        rescue = [{"result": "REL", "english_name": "B", "chinese_name": ""}]
        with self.assertRaises(ValueError):
            apply_rescue.merge(rows, rescue)

    def test_merge_recognises_an_applied_file(self):
        rows = [self.row("B")]
        rescue = [
            {"result": "REL", "english_name": "A", "chinese_name": ""},
            {"result": "OTH", "english_name": "B", "chinese_name": ""},
        ]
        with self.assertRaises(apply_rescue.AlreadyApplied):
            apply_rescue.merge(rows, rescue)

    def test_the_committed_rescue_file_is_already_applied(self):
        if not (ROOT / "sub_rescue.csv").exists():
            self.skipTest("no rescue file in this checkout")
        with self.assertRaises(apply_rescue.AlreadyApplied):
            apply_rescue.merge(read_rows("s88list_categorised.csv"), read_rows("sub_rescue.csv"))

    def test_previous_alignment_reuses_labels_and_spots_insertions(self):
        old = [self.row("A"), self.row("B"), self.row("B"), self.row("D")]
        new = [
            self.row("A"),
            self.row("X"),
            self.row("B"),
            self.row("B"),
            self.row("D"),
            self.row("Y"),
        ]
        self.assertEqual(
            classify_sub.align_previous(old, ["a", "b1", "b2", "d"], new),
            ["a", None, "b1", "b2", "d", None],
        )

    def test_previous_alignment_rejects_removals(self):
        old = [self.row("A"), self.row("B")]
        new = [self.row("A")]
        with self.assertRaises(SystemExit):
            classify_sub.align_previous(old, ["a", "b"], new)

    def test_non_retryable_http_error_fails_fast(self):
        error = urllib.error.HTTPError(
            "https://example.invalid", 401, "unauthorized", Message(), None
        )
        self.addCleanup(error.close)
        with (
            mock.patch.object(classify_sub.urllib.request, "urlopen", side_effect=error),
            mock.patch.object(classify_sub.time, "sleep") as sleep,
        ):
            self.assertIsNone(
                classify_sub.call(["a name"], "header {N}", "rescue", set(), attempts=4)
            )
        sleep.assert_not_called()


class RenderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = build_site.aggregate(ROOT)
        cls.html = build_site.render(cls.data)

    def test_every_purpose_is_ranked_once(self):
        parser = ScheduleParser()
        parser.feed(self.html)
        rows = [row for row in parser.rows if len(row) == 4 and row[0].isdigit()]
        self.assertEqual(len(rows), len(self.data["purposes"]))
        for row, purpose in zip(rows, self.data["purposes"]):
            self.assertIn(purpose["en"], row[1])

    def test_page_states_the_register_date(self):
        self.assertIn(self.data["as_at"], self.html)
        self.assertIn(self.data["as_at_zh"], self.html)

    def test_counts_are_grouped_and_bilingual(self):
        top = self.data["purposes"][0]
        self.assertIn(f"{top['count']:,}", self.html)
        self.assertIn(f"{top['share']:.1f}%", self.html)
        self.assertIn(top["zh"], self.html)

    def test_numbers_are_not_repeated_as_raw_digits(self):
        self.assertNotIn(f">{self.data['total']}<", self.html)
        self.assertNotIn("[X]", self.html)

    def test_tradition_bands_stack_without_overlapping(self):
        """Regression: bands were absolutely positioned with no `top`, so they all
        painted at y=0 and hid every tradition but the last."""
        bands = re.findall(r'<div class="trad-band" style="top:(\d+)px;--trad-h:(\d+)px', self.html)
        self.assertEqual(len(bands), len(self.data["traditions"]))
        tops = [int(top) for top, _ in bands]
        heights = [int(height) for _, height in bands]
        self.assertEqual(tops[0], 0)
        for index in range(1, len(tops)):
            self.assertEqual(
                tops[index],
                tops[index - 1] + heights[index - 1],
                f"band {index} must start where band {index - 1} ends",
            )
        self.assertEqual(tops[-1] + heights[-1], 300)

    def test_tradition_legend_lists_every_merged_tradition(self):
        self.assertEqual(self.html.count("Other traditions · 其餘傳統"), 1)
        for row in self.data["traditions"][1:]:
            self.assertIn(row["en"], self.html)


if __name__ == "__main__":
    unittest.main()
