#!/usr/bin/env python3
# jam-attrition re-read: how many entries leave finished itch.io jams' results within a known time.
# By MV2 of Munim, Inc., made with AI agents (Anthropic Claude). Apache-2.0.
"""The 1 November 2026 count (data/jams.csv) saw, in one reading, how many entries had vanished from
the results of 1,352 finished jams since results day. This script reads the same jams again and
counts, for each one, how many entries are listed now against then:

  D  entries that left the list since the base read = L_base - L_now

Unlike V, D also sees entries lost from the very bottom of a list, and it does not depend on rank
numbers, so a host who skipped rank numbers by hand cannot inflate it. The predictions it grades are in
PREREGISTRATION-reread.md, written before any re-read.

    python reread.py --label r1 --out out                       (live re-read, about 45 minutes)
    python reread.py --label r1 --out out --from-csv out/now.csv --read-at "YYYY-MM-DD HH:MM:SS"

The reader, its politeness rules (one request per --delay seconds, a User-Agent naming MV2 and his
email, only /jam/<slug>/results pages) and the page parsing are jam_attrition.py 0.1.0's, unchanged.
No game, author or entry is recorded: only each jam's slug, dates and counts.
"""

import argparse
import csv
import datetime as dt
import json
import os
import sys
import time

import jam_attrition as ja

VERSION = "0.2.0"
BASE_CSV = os.path.join("data", "jams.csv")
BASE_READ_AT = "2026-11-01 20:11:01"
# Predictions are graded only when the re-read began this many days (inclusive) after the base read.
WINDOWS = {"r1": (28.0, 45.0), "r2": (170.0, 200.0)}
# Pre-registered limits per read: (Q2 low, Q2 high, Q4 max share of jams gone, Q5 low, Q5 high).
BOUNDS = {"r1": (0.0001, 0.005, 0.01, 0.03, 0.50), "r2": (0.001, 0.03, 0.03, 0.10, 0.80)}
COLUMNS = ["slug", "sub_end", "age_base", "n0_base", "listed_base", "http_now", "status_now", "n0_now",
           "listed_now", "cmp", "lost"]


def base_frame(rows):
    """The jams counted in the base read: exactly jam_attrition's eligible set."""
    return ja.eligible(rows)


def compare(base, now, base_read_at):
    """One row per jam: how the re-read compares with the base read.

    cmp is one of: ok (lost = L_base - L_now, negative if entries came back), jam_gone (the results
    page now answers 404 or 410), renumbered (more ranked entries than before: the results were
    re-ranked, so lists cannot be compared), unreadable (anything else, including not fetched)."""
    out = {"slug": base["slug"], "sub_end": base["sub_end"],
           "age_base": round(ja.age_years(base["sub_end"], base_read_at), 4),
           "n0_base": base["n0"], "listed_base": base["listed"], "http_now": now.get("http"),
           "status_now": now.get("status"), "n0_now": now.get("n0"), "listed_now": now.get("listed"),
           "cmp": "unreadable", "lost": None}
    if now.get("http") in (404, 410):
        out["cmp"] = "jam_gone"
    elif now.get("status") in ("ok", "tie_span") and now.get("listed") is not None and now.get("n0") is not None:
        if now["n0"] > base["n0"]:
            out["cmp"] = "renumbered"
        else:
            out["cmp"] = "ok"
            out["lost"] = base["listed"] - now["listed"]
    return out


def elapsed_days(base_read_at, read_at):
    return (ja.parse_time(read_at) - ja.parse_time(base_read_at)).total_seconds() / 86400


def loss_share(rows):
    den = sum(r["listed_base"] for r in rows)
    return sum(r["lost"] for r in rows) / den if den else None


def analyse(cmp_rows, base_read_at, read_at, label, iters=2000, seed=20261202):
    s = {"version": VERSION, "label": label, "base_read_at_utc": base_read_at, "read_at_utc": read_at,
         "elapsed_days": round(elapsed_days(base_read_at, read_at), 2), "base_jams": len(cmp_rows)}
    counts = {}
    for r in cmp_rows:
        counts[r["cmp"]] = counts.get(r["cmp"], 0) + 1
    s["cmp_counts"] = dict(sorted(counts.items()))
    bad = counts.get("unreadable", 0) + counts.get("renumbered", 0)
    s["reader_check"] = {"unusable": bad, "unusable_share": ja.r4(bad / len(cmp_rows)) if cmp_rows else None}
    ok = [r for r in cmp_rows if r["cmp"] == "ok"]
    s["usable_jams"] = len(ok)
    s["listed_base"] = sum(r["listed_base"] for r in ok)
    s["lost"] = sum(r["lost"] for r in ok)
    s["came_back"] = -sum(r["lost"] for r in ok if r["lost"] < 0)
    s["overall"] = {"pooled": ja.r4(loss_share(ok)), "ci95": ja.boot(ok, loss_share, iters, seed)}
    s["cohorts"] = {}
    groups = {}
    for name, lo, hi in ja.COHORTS:
        g = [r for r in ok if lo <= r["age_base"] < hi]
        groups[name] = g
        s["cohorts"][name] = {"jams": len(g), "listed_base": sum(r["listed_base"] for r in g),
                              "lost": sum(r["lost"] for r in g), "pooled": ja.r4(loss_share(g)),
                              "ci95": ja.boot(g, loss_share, iters, seed),
                              "jams_with_loss": sum(1 for r in g if r["lost"] >= 1)}
    young, old = groups["lt1"], groups["ge5"]
    diff = loss_share(young) - loss_share(old) if young and old else None
    s["q3_young_minus_old"] = {"diff": ja.r4(diff), "ci95": ja.boot_diff(young, old, loss_share, iters, seed)}
    gone = counts.get("jam_gone", 0)
    s["q4_jams_gone"] = {"k": gone, "n": len(cmp_rows), "share": ja.r4(gone / len(cmp_rows)) if cmp_rows else None}
    k = sum(1 for r in ok if r["lost"] >= 1)
    s["q5_jams_with_loss"] = {"k": k, "n": len(ok), "share": ja.r4(k / len(ok)) if ok else None,
                              "wilson95": ja.wilson(k, len(ok))}
    days = elapsed_days(base_read_at, read_at)
    pooled = loss_share(ok)
    s["exploratory_yearly_rate"] = ja.r4(pooled * 365.25 / days) if pooled is not None and days > 0 else None
    s["grades"] = grade(s)
    return s


def grade(s):
    """Grades exactly as written in PREREGISTRATION-reread.md."""
    label = s["label"]
    names = ["Q1", "Q2", "Q3", "Q4", "Q5"]
    lo_days, hi_days = WINDOWS[label]
    rc = s["reader_check"]["unusable_share"]
    if rc is None or rc > 0.10 or not (lo_days <= s["elapsed_days"] <= hi_days) or s["usable_jams"] < 100:
        return {n: "not graded" for n in names}
    q2lo, q2hi, q4max, q5lo, q5hi = BOUNDS[label]
    g = {}
    o = s["overall"]
    if o["pooled"] is None or o["ci95"] is None:
        g["Q1"] = g["Q2"] = "not graded"
    else:
        g["Q1"] = "held" if o["pooled"] > 0 and o["ci95"][0] > 0 else "failed"
        g["Q2"] = "held" if q2lo <= o["pooled"] <= q2hi else "failed"
    c = s["cohorts"]
    q3 = s["q3_young_minus_old"]
    if c["lt1"]["jams"] < 30 or c["ge5"]["jams"] < 30 or q3["diff"] is None or q3["ci95"] is None:
        g["Q3"] = "not graded"
    else:
        g["Q3"] = "held" if q3["diff"] > 0 and q3["ci95"][0] > 0 else "failed"
    g["Q4"] = "held" if s["q4_jams_gone"]["share"] <= q4max else "failed"
    q5 = s["q5_jams_with_loss"]["share"]
    g["Q5"] = "not graded" if q5 is None else ("held" if q5lo <= q5 <= q5hi else "failed")
    return g


def write_cmp(rows, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(COLUMNS)
        for r in rows:
            w.writerow(["" if r.get(k) is None else r.get(k) for k in COLUMNS])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--label", required=True, choices=sorted(WINDOWS))
    ap.add_argument("--out", default="out")
    ap.add_argument("--base", default=BASE_CSV)
    ap.add_argument("--base-read-at", default=BASE_READ_AT)
    ap.add_argument("--delay", type=float, default=1.0)
    ap.add_argument("--deadline-minutes", type=float, default=150)
    ap.add_argument("--iters", type=int, default=2000)
    ap.add_argument("--from-csv", default=None, help="a saved now.csv: re-analyse without the network")
    ap.add_argument("--read-at", default=None, help="'YYYY-MM-DD HH:MM:SS' UTC (needed with --from-csv)")
    a = ap.parse_args(argv)
    frame = base_frame(ja.read_rows(a.base))
    os.makedirs(a.out, exist_ok=True)
    start = time.monotonic()

    def log(msg):
        print("[%6.0f s] %s" % (time.monotonic() - start, msg), flush=True)

    if a.from_csv:
        if not a.read_at:
            ap.error("--from-csv needs --read-at")
        now_rows, read_at = ja.read_rows(a.from_csv), a.read_at
    else:
        read_at = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        fetch = ja.Fetcher(a.delay, log)
        deadline = start + a.deadline_minutes * 60
        now_rows = []
        for i, b in enumerate(frame):
            if time.monotonic() >= deadline:
                now_rows.append({"slug": b["slug"], "status": "not_fetched"})
                continue
            try:
                now_rows.append(ja.read_jam(b["slug"], fetch))
            except Exception as e:  # one odd page must not stop the run; it counts as unreadable
                log("  %s: %s" % (b["slug"], type(e).__name__))
                now_rows.append({"slug": b["slug"], "status": "error"})
            if i % 100 == 99:
                log("  jams read: %d of %d" % (i + 1, len(frame)))
        # Save the raw re-read before any analysis, so a later crash cannot lose it.
        ja.write_rows(now_rows, os.path.join(a.out, "now.csv"))
        with open(os.path.join(a.out, "read_at.txt"), "w", encoding="utf-8") as f:
            f.write(read_at + "\n")
    by_slug = {r["slug"]: r for r in now_rows}
    cmp_rows = [compare(b, by_slug.get(b["slug"], {"status": "not_fetched"}), a.base_read_at) for b in frame]
    write_cmp(cmp_rows, os.path.join(a.out, "compare.csv"))
    s = analyse(cmp_rows, a.base_read_at, read_at, a.label, a.iters)
    with open(os.path.join(a.out, "summary-%s.json" % a.label), "w", encoding="utf-8") as f:
        json.dump(s, f, indent=1)
    log("done: %d jams; grades %s" % (len(cmp_rows), json.dumps(s["grades"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
