"""Compact remaining-C/D queue for snippet-batch grading.

Token rules for the next research pass — do not violate:
  1. Run grade_edges.py first (linter + spouse-copy + overrides). No LLM.
  2. pack_queue.py emits data/grade-queue.jsonl — one short line per open link.
  3. Grade in packs of 12–15. For each pack:
       - at most ONE web_search per person (query is on the line)
       - use search snippets only; never open_page / never fetch a FamilySearch profile
       - one JSON list of grades back; no prose essays
  4. Spawn a research subagent ONLY for leftover D/gold after the snippet pass,
     and only one person (or one couple) per agent.
  5. Never re-research a (parent_id, child_id) already in research_overrides.json.
  6. Never pack a link that sits beyond a Broken (F) parent — that branch is not ancestral.

Usage:
  python scripts/grade_edges.py
  python scripts/pack_queue.py --min-gen 6 --max-gen 7
"""
from __future__ import annotations

import argparse, json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"


def beyond_f(n, by):
    """True when a Broken (F) parent-link sits between this person and the root."""
    g, p = n["gen"], n["pos"]
    while g > 0:
        g -= 1
        p //= 2
        inner = by.get((g, p))
        if inner and inner.get("qg") == "F":
            return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-gen", type=int, default=6)
    ap.add_argument("--max-gen", type=int, default=7)
    ap.add_argument("--grades", default="C,D")
    args = ap.parse_args()
    want = set(args.grades.split(","))

    fan = json.loads((DATA / "fan-data-clean.json").read_text(encoding="utf-8"))
    ovs = json.loads((DATA / "research_overrides.json").read_text(encoding="utf-8"))
    covered = {(r.get("parent_id"), r.get("child_id")) for r in ovs}
    by = {(n["gen"], n["pos"]): n for n in fan["nodes"]}

    rows = []
    skipped_beyond = 0
    for n in sorted(fan["nodes"], key=lambda x: (x["gen"], x["pos"])):
        g = n.get("qg") or "C"
        if n["gen"] < args.min_gen or n["gen"] > args.max_gen or g not in want:
            continue
        ch = by.get((n["gen"] - 1, n["pos"] // 2))
        cid = ch["id"] if ch else None
        if (n["id"], cid) in covered or (n["id"], None) in covered:
            continue
        if beyond_f(n, by):
            skipped_beyond += 1
            continue
        q = f"{n['name']} {n.get('life','')} {ch['name'] if ch else ''}".strip()
        rows.append(
            {
                "g": n["gen"],
                "p": n["pos"],
                "grade": g,
                "pid": n["id"],
                "cid": cid,
                "parent": f"{n['name']} {n.get('life','')}".strip(),
                "child": f"{ch['name']} {ch.get('life','')}".strip() if ch else "",
                "src": n.get("src") or 0,
                "bp": (n.get("bp") or "")[:40],
                "q": q,
            }
        )

    out = DATA / "grade-queue.jsonl"
    out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + ("\n" if rows else ""), encoding="utf-8")
    print(f"wrote {len(rows)} links to {out}")
    from collections import Counter
    print("by gen", Counter(r["g"] for r in rows))
    print("by grade", Counter(r["grade"] for r in rows))
    if skipped_beyond:
        print(f"skipped {skipped_beyond} beyond an F")


if __name__ == "__main__":
    main()
