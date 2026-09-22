"""Merge data/attachments.json onto matching people in fan-data-clean.json."""
from __future__ import annotations

import json
from pathlib import Path

PROJ = Path(__file__).resolve().parent.parent
DATA = PROJ / "data"


def main():
    atts = json.loads((DATA / "attachments.json").read_text(encoding="utf-8"))
    fan_path = DATA / "fan-data-clean.json"
    data = json.loads(fan_path.read_text(encoding="utf-8"))
    applied = 0
    for n in data["nodes"]:
        rec = atts.get(n.get("id"))
        if not rec:
            continue
        if rec.get("atts"):
            n["atts"] = rec["atts"]
        if rec.get("story"):
            n["story"] = rec["story"]
        if rec.get("dp"):
            n["dp"] = rec["dp"]
        if "mem" in rec:
            n["mem"] = rec["mem"]
        extra = rec.get("events") or []
        if extra:
            existing = n.get("ev") or []
            seen = {(e.get("t"), e.get("ti"), e.get("d")) for e in existing}
            merged = list(existing)
            prepend = []
            for e in extra:
                key = (e.get("t"), e.get("ti"), e.get("d"))
                if key not in seen:
                    prepend.append(e)
                    seen.add(key)
            merged = prepend + merged
            for e in merged:
                if e.get("ti") == "Immigration" and not e.get("desc"):
                    e["desc"] = (
                        "FamilySearch records 1849; the 19 Feb 1922 Times-Picayune "
                        "obituary says he came as a boy in 1841 with his father."
                    )
            n["ev"] = merged
        applied += 1
    fan_path.write_text(
        json.dumps(data, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print(f"applied attachments to {applied} node-positions; {len(atts)} people")


if __name__ == "__main__":
    main()
