#!/usr/bin/env python3
# Gate: read no jam page until the pre-registration is public. By MV2 of Munim, Inc., made with AI agents.
# Apache-2.0.
"""Waits until PREREGISTRATION.md is on the main branch of munimtechnologies/jam-attrition and contains
--must, then checks that the public jam_attrition.py is the one in this folder (line endings aside), and writes
both SHA-256 hashes and when they were seen to --out. Exit 1 if either never matches, so the data run
that follows it (with &&) never starts."""

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.request

RAW = "https://raw.githubusercontent.com/munimtechnologies/jam-attrition/main/"


def get(name):
    req = urllib.request.Request(RAW + name + "?t=%d" % time.time(), headers={"User-Agent": "MV2-jam-study"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--must", default="Pre-registration: vanished entries in itch.io jam results")
    ap.add_argument("--wait-minutes", type=float, default=90)
    a = ap.parse_args(argv)
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "jam_attrition.py"), "rb") as f:
        local = f.read()
    end = time.time() + a.wait_minutes * 60
    while True:
        try:
            pre = get("PREREGISTRATION.md")
            code = get("jam_attrition.py")
            same = code.replace(b"\r\n", b"\n") == local.replace(b"\r\n", b"\n")  # line endings may differ
            if a.must.encode() in pre and same:
                seen = {"seen_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "preregistration_sha256": hashlib.sha256(pre).hexdigest(),
                        "code_sha256": hashlib.sha256(code).hexdigest()}
                with open(a.out, "w", encoding="utf-8") as f:
                    json.dump(seen, f, indent=1)
                print("pre-registration and code are public:", json.dumps(seen))
                return 0
            print("public files found but not matching yet; waiting")
        except Exception as e:  # 404 until they are committed
            print("not public yet (%s); waiting" % type(e).__name__)
        if time.time() > end:
            print("pre-registration or code never matched; reading no data")
            return 1
        time.sleep(120)


if __name__ == "__main__":
    sys.exit(main())
