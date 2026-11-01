# Tests for jam_attrition.py. By MV2 of Munim, Inc., made with AI agents. Apache-2.0.
import unittest

import jam_attrition as ja

# Copied from a real results page (Game Off 2025, results page 1), tags as itch.io writes them.
HEADER = ('<div class="jam_summary"><div class="responsive_column"><h2>Results</h2><p><strong>709 entries</strong> '
          'were submitted between <span class="date_format" data-format="MMMM Do YYYY [at] h:mm A">2025-11-01 '
          '20:37:00</span> and <span class="date_format" data-format="MMMM Do YYYY [at] h:mm A">2025-12-01 '
          '21:37:00</span>. <strong>10,414 ratings</strong> were given to <strong>699 entries</strong> (98.6%) '
          'between <span class="date_format" data-format="MMMM Do YYYY [at] h:mm A">2025-12-01 21:37:00</span> '
          'and <span class="date_format">2026-01-08 21:37:00</span>.')
PAGER = ('<div class="pager"><a class="next_page button" href="?page=2">Next <span class="icon icon-arrow-right" '
         'aria-hidden="true"></span></a><span class="pager_label">Page 1 of <a href="?page=35">35</a></span></div>')


def entry(rank):
    sfx = {1: "st", 2: "nd", 3: "rd"}.get(rank % 10 if rank % 100 not in (11, 12, 13) else 0, "th")
    return ('<div class="game_rank"><div class="game_summary"><h2><a href="https://someone.itch.io/game">Game</a>'
            '</h2><h3>Ranked <strong class="ordinal_rank">%d%s</strong> with 17 ratings (Score: 4.118)</h3>'
            '<p><a href="/jam/test-jam/rate/1" class="forward_link">View submission page</a></p></div></div>'
            % (rank, sfx))


def results_page(ranks, pager=""):
    return HEADER + "".join(entry(r) for r in ranks) + pager


# Game Off 2019, results page 11 of 11, as read on 2026-11-01 (ranks only).
GO19_LAST = [211, 215] + [216] * 5 + [221] + [222] * 3 + [225] * 2 + [227] * 6
GO19_FIRST = list(range(1, 13)) + list(range(14, 22))   # 20 entries, rank 13 missing


class Parsing(unittest.TestCase):
    def test_header(self):
        h = ja.parse_header(HEADER)
        self.assertEqual(h["submitted"], 709)
        self.assertEqual((h["ratings"], h["rated"], h["rated_pct"]), (10414, 699, 98.6))
        self.assertEqual((h["sub_start"], h["sub_end"]), ("2025-11-01 20:37:00", "2025-12-01 21:37:00"))

    def test_header_absent(self):
        self.assertEqual(ja.parse_header("<p>nothing</p>")["sub_end"], None)

    def test_ranks_and_suffixes(self):
        self.assertEqual(ja.parse_ranks(results_page([1, 2, 3, 4, 11, 12, 13, 21, 22, 23, 101])),
                         [1, 2, 3, 4, 11, 12, 13, 21, 22, 23, 101])

    def test_page_count(self):
        self.assertEqual(ja.page_count(PAGER), 35)
        self.assertEqual(ja.page_count('<a href="?page=2">Next</a> <a href="?page=7">7</a>'), 7)
        self.assertEqual(ja.page_count("<p>one page</p>"), 1)

    def test_listing(self):
        page = ('<a href="/jam/alpha">Alpha</a> <a href="/jam/alpha/results">Results</a> '
                '<a href="https://itch.io/jam/beta">Beta</a> <a href="/jam/beta/entries">x</a> '
                '<a href="/jams/past?page=2">Next</a>')
        self.assertEqual(ja.parse_listing(page), [("alpha", True), ("beta", False)])

    def test_frame_drops_chrome(self):
        common = '<a href="/jam/featured">F</a>'
        pages = [common + '<a href="/jam/j%d">J</a><a href="/jam/j%d/results">R</a>' % (i, i)
                 for i in range(ja.CHROME_PAGES)]
        frame = ja.frame_from_listings(pages)
        self.assertNotIn("featured", [s for s, _ in frame])
        self.assertEqual(len(frame), ja.CHROME_PAGES)
        self.assertTrue(all(h for _, h in frame))


class Counting(unittest.TestCase):
    def test_game_off_2019(self):
        r = ja.count_jam(GO19_FIRST, GO19_LAST, 11)
        self.assertEqual(r["status"], "ok")
        self.assertEqual((r["n0"], r["listed"], r["vanished"]), (232, 219, 13))
        self.assertEqual((r["top_slots"], r["top_vanished"]), (21, 1))
        self.assertEqual((r["bottom_slots"], r["bottom_vanished"]), (18, 0))

    def test_single_page(self):
        r = ja.count_jam([1, 2, 2, 5, 6], [], 1)
        self.assertEqual((r["n0"], r["listed"], r["vanished"]), (6, 5, 1))
        self.assertEqual((r["top_slots"], r["top_vanished"]), (6, 1))
        self.assertIsNone(r["bottom_slots"])

    def test_ties_at_the_end_are_not_losses(self):
        r = ja.count_jam([1, 2, 3, 3, 3], [], 1)
        self.assertEqual(r["vanished"], 0)

    def test_carry(self):
        first = list(range(1, 16)) + [16] * 5
        r = ja.count_jam(first, [16, 16, 16], 2, carry=5)
        self.assertEqual((r["n0"], r["listed"], r["vanished"], r["status"]), (23, 23, 0, "ok"))

    def test_bad_pages(self):
        self.assertEqual(ja.count_jam([], [], 1)["status"], "no_ranks")
        self.assertEqual(ja.count_jam([1, 2], [], 3)["status"], "last_page_empty")
        self.assertEqual(ja.count_jam(list(range(1, 19)), [30], 2)["status"], "page_size")
        self.assertEqual(ja.count_jam(list(range(1, 21)), [25, 22], 2)["status"], "inconsistent")


class Reading(unittest.TestCase):
    def fake(self, pages):
        calls = []

        def fetch(url):
            calls.append(url)
            return (200, pages[url]) if url in pages else (404, "")
        return fetch, calls

    def test_read_jam_two_requests(self):
        base = "https://itch.io/jam/go19/results"
        fetch, calls = self.fake({base: results_page(GO19_FIRST, PAGER.replace("35", "11")),
                                  base + "?page=11": results_page(GO19_LAST)})
        r = ja.read_jam("go19", fetch)
        self.assertEqual(len(calls), 2)
        self.assertEqual((r["status"], r["n0"], r["vanished"], r["submitted"]), ("ok", 232, 13, 709))

    def test_read_jam_tie_carry(self):
        base = "https://itch.io/jam/t/results"
        first = list(range(1, 21))
        prev = list(range(21, 36)) + [36] * 5
        fetch, calls = self.fake({base: results_page(first, PAGER.replace("35", "3")),
                                  base + "?page=2": results_page(prev),
                                  base + "?page=3": results_page([36, 36])})
        r = ja.read_jam("t", fetch)
        self.assertEqual(len(calls), 3)
        self.assertEqual((r["status"], r["n0"], r["listed"], r["vanished"]), ("ok", 42, 42, 0))

    def test_read_jam_404(self):
        fetch, _ = self.fake({})
        self.assertEqual(ja.read_jam("gone", fetch)["status"], "http_404")


def row(sub_end, n0, vanished, top_v=0, bottom_v=0):
    return {"slug": "x", "http": 200, "status": "ok", "sub_end": sub_end, "n0": n0, "listed": n0 - vanished,
            "vanished": vanished, "pages": 5, "top_slots": 20, "top_vanished": top_v, "bottom_slots": 10,
            "bottom_vanished": bottom_v, "rated": n0, "submitted": n0 - vanished}


class Grading(unittest.TestCase):
    READ_AT = "2026-11-01 15:00:00"

    def test_all_hold(self):
        rows = [row("2019-08-04 21:00:00", 100, 5, 0, 2) for _ in range(40)]
        rows += [row("2026-03-01 00:00:00", 100, 1, 0, 1) for _ in range(40)]
        s = ja.analyse(rows, self.READ_AT, iters=200)
        self.assertEqual(s["cohorts"]["ge5"]["pooled"], 0.05)
        self.assertEqual(s["cohorts"]["lt1"]["pooled"], 0.01)
        self.assertEqual(s["p1_diff_ge5_minus_lt2"]["diff"], 0.04)
        self.assertEqual(s["p6_bottom_vs_top"]["jams"], 40)
        self.assertEqual(s["grades"], {"P1": "held", "P2": "held", "P3": "held", "P4": "held", "P5": "held",
                                       "P6": "held"})

    def test_small_cohorts_not_graded(self):
        rows = [row("2019-08-04 21:00:00", 100, 5) for _ in range(10)]
        s = ja.analyse(rows, self.READ_AT, iters=50)
        self.assertEqual(s["grades"]["P1"], "not graded")
        self.assertEqual(s["grades"]["P3"], "not graded")

    def test_failures(self):
        rows = [row("2019-08-04 21:00:00", 100, 30, 0, 0) for _ in range(40)]
        rows += [row("2026-03-01 00:00:00", 100, 5) for _ in range(40)]
        g = ja.analyse(rows, self.READ_AT, iters=200)["grades"]
        self.assertEqual((g["P1"], g["P2"], g["P3"], g["P6"]), ("held", "failed", "failed", "failed"))

    def test_late_and_small_jams_left_out(self):
        rows = [row("2026-10-15 00:00:00", 100, 0), row("2020-01-01 00:00:00", 9, 1)]
        self.assertEqual(ja.analyse(rows, self.READ_AT, iters=10)["eligible_jams"], 0)

    def test_reader_check_blocks_grades(self):
        rows = [row("2019-08-04 21:00:00", 100, 5) for _ in range(40)]
        rows += [row("2026-03-01 00:00:00", 100, 1) for _ in range(40)]
        rows += [dict(row("2020-01-01 00:00:00", 100, 0), status="inconsistent") for _ in range(10)]
        g = ja.analyse(rows, self.READ_AT, iters=50)["grades"]
        self.assertEqual(set(g.values()), {"not graded"})

    def test_csv_round_trip(self):
        import os
        import tempfile
        rows = [row("2019-08-04 21:00:00", 100, 5, 0, 2) for _ in range(40)]
        rows += [row("2026-03-01 00:00:00", 100, 1, 0, 1) for _ in range(40)]
        rows.append({"slug": "late", "http": 404, "status": "http_404"})
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "jams.csv")
            ja.write_rows(rows, p)
            back = ja.read_rows(p)
        self.assertEqual(len(back), 81)
        self.assertEqual(back[0]["n0"], 100)
        self.assertIsNone(back[-1]["n0"])
        a = ja.analyse(rows, self.READ_AT, iters=50)
        b = ja.analyse(back, self.READ_AT, iters=50)
        self.assertEqual(a["grades"], b["grades"])
        self.assertEqual(a["cohorts"], b["cohorts"])

    def test_spearman(self):
        rho, p = ja.spearman([1, 2, 3, 4, 5, 6, 7, 8], [1, 2, 3, 4, 5, 6, 7, 8], 500, 1)
        self.assertEqual(rho, 1.0)
        self.assertLess(p, 0.01)


if __name__ == "__main__":
    unittest.main()
