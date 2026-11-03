"""Behaviour of the Section 88 plate: aggregation and rendered output."""
import html
import pathlib
import unittest
from html.parser import HTMLParser

import build_site

ROOT = pathlib.Path(__file__).resolve().parent.parent


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
        if tag in ("td", "th") and self._cell is not None:
            self._row.append("".join(self._cell).strip())
            self._cell = None
        elif tag == "tr" and self._row is not None:
            self.rows.append(self._row)
            self._row = None


class AggregateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = build_site.aggregate(ROOT)

    def test_register_date_comes_from_the_register(self):
        self.assertEqual(self.data["as_at"], "30 September 2026")

    def test_register_total_and_purpose_count(self):
        self.assertEqual(self.data["total"], 17623)
        self.assertEqual(len(self.data["purposes"]), 17)
        self.assertEqual(self.data["purposes"][0]["count"], 4621)

    def test_purpose_shares_are_of_the_whole_register(self):
        shares = {p["en"]: p["share"] for p in self.data["purposes"]}
        self.assertEqual(shares["Religious"], 26.2)
        self.assertEqual(shares["Education"], 14.7)
        self.assertEqual(sum(p["count"] for p in self.data["purposes"]), 17623)

    def test_stage_one_merges_the_eleven_smallest(self):
        stage1 = self.data["stage1"]
        self.assertEqual(len(stage1), 7)
        self.assertEqual(stage1[-1]["count"], 3356)
        self.assertEqual(stage1[-1]["share"], 19.0)
        self.assertEqual(sum(row["height"] for row in stage1), 560)

    def test_traditions_resolve_the_religious_band(self):
        traditions = self.data["traditions"]
        self.assertEqual([t["en"] for t in traditions][0], "Protestant Christian")
        self.assertEqual(traditions[0]["count"], 3410)
        self.assertEqual(traditions[0]["share"], 74.4)
        self.assertEqual(sum(t["count"] for t in traditions), 4582)
        self.assertEqual(sum(t["height"] for t in traditions), 300)

    def test_denominations_resolve_protestant_christian(self):
        rows = self.data["denominations"]
        self.assertEqual(len(rows), 13)
        self.assertEqual((rows[0]["en"], rows[0]["count"]), ("Independent", 1111))
        self.assertEqual((rows[-1]["en"], rows[-1]["count"]), ("Unstated", 2))
        self.assertEqual(sum(r["count"] for r in rows), 3410)

    def test_height_allocation_never_exceeds_its_budget(self):
        self.assertEqual(sum(build_site.allocate([1, 1, 1, 1000], 560)), 560)
        self.assertEqual(sum(build_site.allocate([4582, 2645, 2275], 300, minimum=12)), 300)

    def test_community_labels_are_kept_for_future_views(self):
        rows = self.data["community"]
        self.assertEqual(len(rows), 8)
        self.assertEqual(sum(r["count"] for r in rows), 254)


class RenderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = build_site.aggregate(ROOT)
        cls.html = build_site.render(cls.data)

    def test_every_purpose_is_ranked_once(self):
        parser = ScheduleParser()
        parser.feed(self.html)
        rows = [row for row in parser.rows if len(row) == 4 and row[0].isdigit()]
        self.assertEqual(len(rows), 17)
        for row, purpose in zip(rows, self.data["purposes"]):
            self.assertIn(purpose["en"], row[1])

    def test_page_states_the_register_date(self):
        self.assertIn("30 September 2026", self.html)
        self.assertIn("2026年9月30日", self.html)

    def test_counts_are_grouped_and_bilingual(self):
        self.assertIn("4,621", self.html)
        self.assertIn("26.2%", self.html)
        self.assertIn("宗教", self.html)

    def test_numbers_are_not_repeated_as_raw_digits(self):
        self.assertNotIn(">4621<", self.html)
        self.assertNotIn("[X]", self.html)


if __name__ == "__main__":
    unittest.main()
