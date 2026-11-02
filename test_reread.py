# Tests for reread.py. By MV2 of Munim, Inc., made with AI agents (Anthropic Claude). Apache-2.0.
import csv
import os
import tempfile
import unittest

import jam_attrition as ja
import reread as rr

BASE_AT = "2026-11-01 20:11:01"


def base_row(slug, sub_end, n0, listed):
    return {"slug": slug, "status": "ok", "sub_end": sub_end, "n0": n0, "listed": listed, "vanished": n0 - listed}


def now_row(slug, n0, listed, status="ok", http=200):
    return {"slug": slug, "http": http, "status": status, "n0": n0, "listed": listed}


class Compare(unittest.TestCase):
    def setUp(self):
        self.b = base_row("some-jam", "2025-06-01 00:00:00", 100, 95)

    def test_losses_are_listed_before_minus_now(self):
        c = rr.compare(self.b, now_row("some-jam", 100, 92), BASE_AT)
        self.assertEqual((c["cmp"], c["lost"]), ("ok", 3))
        self.assertAlmostEqual(c["age_base"], 1.42, places=1)

    def test_a_loss_at_the_very_bottom_is_seen(self):
        # the last-ranked entry leaves: N0 drops by one and so does L; V cannot see it, D can
        c = rr.compare(self.b, now_row("some-jam", 99, 94), BASE_AT)
        self.assertEqual((c["cmp"], c["lost"]), ("ok", 1))

    def test_entries_that_come_back_count_negative(self):
        c = rr.compare(self.b, now_row("some-jam", 100, 96), BASE_AT)
        self.assertEqual((c["cmp"], c["lost"]), ("ok", -1))

    def test_tie_span_pages_still_give_the_listed_count(self):
        c = rr.compare(self.b, now_row("some-jam", 98, 95, status="tie_span"), BASE_AT)
        self.assertEqual((c["cmp"], c["lost"]), ("ok", 0))

    def test_jam_gone_renumbered_and_unreadable(self):
        self.assertEqual(rr.compare(self.b, {"slug": "some-jam", "http": 404, "status": "http_404"}, BASE_AT)["cmp"],
                         "jam_gone")
        self.assertEqual(rr.compare(self.b, now_row("some-jam", 101, 96), BASE_AT)["cmp"], "renumbered")
        for now in ({"slug": "some-jam", "status": "not_fetched"}, now_row("some-jam", None, None, "no_ranks"),
                    now_row("some-jam", 100, 90, "inconsistent"), {"slug": "some-jam", "http": 0, "status": "http_0"}):
            c = rr.compare(self.b, now, BASE_AT)
            self.assertEqual((c["cmp"], c["lost"]), ("unreadable", None))


def fleet(n_young=40, n_old=40, young_lost=2, old_lost=0, listed=100):
    """Comparison rows for young jams (about half a year old at the base read) and old ones (6 years)."""
    rows = []
    for i in range(n_young):
        b = base_row("young-%d" % i, "2026-05-01 00:00:00", listed, listed)
        rows.append(rr.compare(b, now_row(b["slug"], listed, listed - (young_lost if i % 2 == 0 else 0)), BASE_AT))
    for i in range(n_old):
        b = base_row("old-%d" % i, "2020-05-01 00:00:00", listed, listed)
        rows.append(rr.compare(b, now_row(b["slug"], listed, listed - (old_lost if i % 4 == 0 else 0)), BASE_AT))
    return rows


class Analyse(unittest.TestCase):
    def test_counts_cohorts_and_grades(self):
        rows = fleet(n_young=60, n_old=60)
        s = rr.analyse(rows, BASE_AT, "2026-12-03 10:00:00", "r1", iters=200)
        self.assertEqual(s["usable_jams"], 120)
        self.assertEqual(s["lost"], 60)
        self.assertAlmostEqual(s["overall"]["pooled"], 60 / 12000, places=4)
        self.assertEqual(s["cohorts"]["lt1"]["jams"], 60)
        self.assertEqual(s["cohorts"]["ge5"]["lost"], 0)
        self.assertEqual(s["q5_jams_with_loss"]["k"], 30)
        self.assertEqual(s["grades"]["Q1"], "held")
        self.assertEqual(s["grades"]["Q2"], "held")      # 0.5% is the top of the r1 range, inclusive
        self.assertEqual(s["grades"]["Q3"], "held")
        self.assertEqual(s["grades"]["Q4"], "held")
        self.assertEqual(s["grades"]["Q5"], "held")      # 30 of 120 = 25%

    def test_no_losses_fail_q1_and_q2(self):
        s = rr.analyse(fleet(60, 60, young_lost=0), BASE_AT, "2026-12-03 10:00:00", "r1", iters=200)
        self.assertEqual(s["grades"]["Q1"], "failed")
        self.assertEqual(s["grades"]["Q2"], "failed")
        self.assertEqual(s["grades"]["Q3"], "failed")
        self.assertEqual(s["grades"]["Q5"], "failed")

    def test_old_jams_losing_more_fails_q3(self):
        s = rr.analyse(fleet(60, 60, young_lost=0, old_lost=4), BASE_AT, "2026-12-03 10:00:00", "r1", iters=200)
        self.assertEqual(s["grades"]["Q3"], "failed")

    def test_too_many_jams_gone_fails_q4(self):
        rows = fleet(60, 60)
        for i in range(3):
            rows.append(rr.compare(base_row("gone-%d" % i, "2022-01-01 00:00:00", 50, 50),
                                   {"slug": "gone-%d" % i, "http": 404, "status": "http_404"}, BASE_AT))
        s = rr.analyse(rows, BASE_AT, "2026-12-03 10:00:00", "r1", iters=200)
        self.assertEqual(s["q4_jams_gone"]["k"], 3)
        self.assertEqual(s["grades"]["Q4"], "failed")    # 3 of 123 = 2.4% > 1%
        s2 = rr.analyse(rows, BASE_AT, "2027-05-10 10:00:00", "r2", iters=200)
        self.assertEqual(s2["grades"]["Q4"], "held")     # the r2 limit is 3%

    def test_outside_the_window_or_too_unreadable_is_not_graded(self):
        rows = fleet(60, 60)
        early = rr.analyse(rows, BASE_AT, "2026-11-20 10:00:00", "r1", iters=50)
        self.assertEqual(set(early["grades"].values()), {"not graded"})
        late = rr.analyse(rows, BASE_AT, "2026-12-20 10:00:00", "r1", iters=50)
        self.assertEqual(set(late["grades"].values()), {"not graded"})
        for i in range(20):
            rows.append(rr.compare(base_row("odd-%d" % i, "2022-01-01 00:00:00", 50, 50),
                                   {"slug": "odd-%d" % i, "status": "not_fetched"}, BASE_AT))
        s = rr.analyse(rows, BASE_AT, "2026-12-03 10:00:00", "r1", iters=50)
        self.assertGreater(s["reader_check"]["unusable_share"], 0.10)
        self.assertEqual(set(s["grades"].values()), {"not graded"})

    def test_too_few_young_jams_leaves_q3_ungraded(self):
        s = rr.analyse(fleet(20, 100), BASE_AT, "2026-12-03 10:00:00", "r1", iters=50)
        self.assertEqual(s["grades"]["Q3"], "not graded")

    def test_window_edges_are_inclusive(self):
        self.assertAlmostEqual(rr.elapsed_days(BASE_AT, "2026-11-29 20:11:01"), 28.0)
        s = rr.analyse(fleet(60, 60), BASE_AT, "2026-11-29 20:11:01", "r1", iters=50)
        self.assertNotEqual(s["grades"]["Q1"], "not graded")


class Files(unittest.TestCase):
    def test_base_frame_is_the_eligible_set_and_offline_mode_runs(self):
        rows = [
            dict(slug="kept", http=200, status="ok", sub_start="2024-01-01 00:00:00", sub_end="2024-01-10 00:00:00",
                 pages=2, page1_entries=20, n0=40, listed=38, vanished=2),
            dict(slug="too-small", http=200, status="ok", sub_start="2024-01-01 00:00:00",
                 sub_end="2024-01-10 00:00:00", pages=1, page1_entries=8, n0=8, listed=8, vanished=0),
            dict(slug="too-new", http=200, status="ok", sub_start="2026-10-01 00:00:00",
                 sub_end="2026-10-10 00:00:00", pages=2, page1_entries=20, n0=40, listed=40, vanished=0),
            dict(slug="odd", http=200, status="inconsistent", sub_start="2024-01-01 00:00:00",
                 sub_end="2024-01-10 00:00:00", pages=2, page1_entries=20, n0=30, listed=38, vanished=-8),
        ]
        with tempfile.TemporaryDirectory() as d:
            base = os.path.join(d, "jams.csv")
            ja.write_rows(rows, base)
            frame = rr.base_frame(ja.read_rows(base))
            self.assertEqual([r["slug"] for r in frame], ["kept"])
            now = os.path.join(d, "now.csv")
            ja.write_rows([dict(slug="kept", http=200, status="ok", pages=2, page1_entries=20, n0=40, listed=36)], now)
            out = os.path.join(d, "out")
            self.assertEqual(rr.main(["--label", "r1", "--out", out, "--base", base, "--from-csv", now,
                                      "--read-at", "2026-12-02 12:00:00", "--iters", "20"]), 0)
            with open(os.path.join(out, "compare.csv"), newline="", encoding="utf-8") as f:
                got = list(csv.DictReader(f))
            self.assertEqual([(g["slug"], g["cmp"], g["lost"]) for g in got], [("kept", "ok", "2")])
            self.assertTrue(os.path.exists(os.path.join(out, "summary-r1.json")))


if __name__ == "__main__":
    unittest.main()
