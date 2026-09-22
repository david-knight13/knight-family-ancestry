"""Layer-1 edge grader for the Knight fan chart.

Rates each parent-child *link* (not the person) using:
  - internal chronology / biology / placeholder checks
  - existing research dossiers and FamilySearch-audit HTML
  - the independently verified Knight patriline (through William Knight Sr.)

Writes:
  data/edge-grades.json          full research state (non-C and flagged edges)
  data/fan-data-clean.json       compact qg/qn/qf fields on each node
"""
from __future__ import annotations

import json, re, datetime
from pathlib import Path
from collections import Counter, defaultdict

HERE = Path(__file__).resolve().parent
PROJ = HERE.parent
DATA = PROJ / "data"
DOCS = PROJ / "docs"

# Independently proven Knight surname line (see Patriotic Heritage tab).
# The link ABOVE William Knight Sr. (Capt. John Knight of Newbury / Gloucestershire)
# is the documented false graft.
KNIGHT_PROVEN = [
    "PD5F-3GQ",  # David
    "PD5N-7MT",  # John Richard
    "PD5F-S2T",  # John R
    "PH3V-5NL",  # Leo Richard
    "KCSK-3DH",  # Dr John Augustus
    "LZYQ-LJT",  # James William
    "LZYQ-LCG",  # John Carey
    "27V5-MGM",  # John Speir
    "LHGR-2DR",  # Robert A Knight Jr
    "LRG8-G9G",  # Robert Knight Sr
    "GVZX-WH6",  # John Knight of Nansemond / Edgecombe
    "LDBB-WHL",  # William Knight Sr of Isle of Wight / Bertie — last proven
]
KNIGHT_FALSE_FATHER = "PS2Y-59Z"  # Capt John Knight Sr, the Newbury graft

PLACEHOLDER_RE = re.compile(
    r"^(miss\s|mr\.?\s|mrs\.?\s|unknown|unk\s|\?|$)|mnu[k]?|\bunk\b|placeholder",
    re.I,
)


def year_span(life: str):
    if not life:
        return None, None
    years = [int(y) for y in re.findall(r"\d{4}", life)]
    b = years[0] if years else None
    d = years[1] if len(years) > 1 else None
    if d is None and re.search(r"Living", life or "", re.I):
        d = None  # still living
    return b, d


_SUFFIX = {"jr", "sr", "ii", "iii", "iv", "md", "phd", "esq"}


def surname(name: str) -> str:
    parts = [p.strip(".,") for p in (name or "").split() if p.strip(".,")]
    parts = [p for p in parts if p.lower().rstrip(".") not in _SUFFIX]
    return parts[-1].lower() if parts else ""


def detect_spouse_copies(by_gp):
    """When both spouses of a couple share the same two parent IDs, the pair
    that does not match the shared grandfather's surname is an in-law graft.
    Returns {(parent_id, child_id): note} for the grafted links only.
    """
    prune = {}
    for c in by_gp.values():
        g, p = c["gen"], c["pos"]
        dad = by_gp.get((g + 1, 2 * p))
        mom = by_gp.get((g + 1, 2 * p + 1))
        if not dad or not mom:
            continue
        df = by_gp.get((g + 2, 4 * p))
        dm = by_gp.get((g + 2, 4 * p + 1))
        mf = by_gp.get((g + 2, 4 * p + 2))
        mm = by_gp.get((g + 2, 4 * p + 3))
        if not df or not mf or df["id"] != mf["id"]:
            continue
        if dm and mm and dm["id"] != mm["id"]:
            continue
        gf = surname(df["name"])
        dad_m = bool(gf) and gf in dad["name"].lower()
        mom_m = bool(gf) and gf in mom["name"].lower()
        note = (
            f"Spouse-copy: {df['name']} attached as parent of both "
            f"{dad['name']} and {mom['name']}."
        )
        if dad_m and not mom_m:
            prune[(mf["id"], mom["id"])] = note + f" Surname matches {dad['name']}."
            if mm:
                prune[(mm["id"], mom["id"])] = note + f" Surname matches {dad['name']}."
        elif mom_m and not dad_m:
            prune[(df["id"], dad["id"])] = note + f" Surname matches {mom['name']}."
            if dm:
                prune[(dm["id"], dad["id"])] = note + f" Surname matches {mom['name']}."
    return prune


def is_placeholder(name: str) -> bool:
    n = (name or "").strip()
    if not n or n in {"?", "Unknown", "Deceased"}:
        return True
    if PLACEHOLDER_RE.search(n):
        return True
    if re.fullmatch(r"Mrs\.?\s+\w+", n, re.I):
        return True
    return False


def load_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def parse_tree_audit(html: str):
    """Return (divergence_gp set of (gen,pos), dual_parent_ids)."""
    divergences = set()
    # Priority 1 table rows
    p1 = html.split("Priority 1", 1)[-1].split("Priority 2", 1)[0]
    for m in re.finditer(
        r'<tr class="(resolved|)"><td>(\d+)</td><td>(\d+)</td>', p1
    ):
        if m.group(1) == "resolved":
            continue
        divergences.add((int(m.group(2)), int(m.group(3))))
    p2 = html.split("Priority 2", 1)[-1].split("Priority 3", 1)[0]
    dual_ids = set(re.findall(r"/details/([A-Z0-9-]+)", p2))
    return divergences, dual_ids


def parse_corrections(html: str):
    """Map parent FS id -> (verdict, confidence, note)."""
    out = {}
    # High / medium wrong-parent tables: first column is the wrong parent id.
    # We also catch PRUNE rows.
    # Simpler: reuse the research JSON as primary; corrections HTML is backup.
    for m in re.finditer(
        r'href="https://www.familysearch.org/tree/person/details/([A-Z0-9-]+)"',
        html,
    ):
        out.setdefault(m.group(1), True)
    return out


def apply_research(by_id, nodes_by_id):
    """Return dict parent_id -> {verdict, confidence, note, grade}."""
    verdicts = {}
    files = [
        DATA / "_research_waveA.json",
        DATA / "_research_results.json",
    ]
    for f in files:
        if not f.exists():
            continue
        rows = load_json(f)
        if not isinstance(rows, list):
            continue
        for r in rows:
            if not isinstance(r, dict) or "parent_id" not in r:
                continue
            pid = r["parent_id"]
            v = (r.get("verdict") or "").upper()
            conf = (r.get("confidence") or "low").lower()
            note = r.get("note") or ""
            if v in {"RELINK", "PRUNE"}:
                grade = "F" if conf in {"high", "medium"} else "D"
            elif v in {"UNRESOLVED"}:
                grade = "D"
            elif v in {
                "ACCEPT",
                "FIX_PARENT_DATES",
                "FIX_CHILD_DATES",
                "FIX_PARENT_NAME",
            }:
                grade = "B"
            else:
                continue
            prev = verdicts.get(pid)
            # Keep the more severe grade (F > D > B)
            rank = {"F": 3, "D": 2, "B": 1, "C": 0, "U": 2, "A": 0}
            if prev is None or rank[grade] >= rank[prev["grade"]]:
                verdicts[pid] = {
                    "verdict": v,
                    "confidence": conf,
                    "note": note,
                    "grade": grade,
                    "child_id": r.get("child_id"),
                }
    return verdicts


def linter_flags(parent, child):
    flags = []
    pb, pd = year_span(parent.get("life") or "")
    cb, cd = year_span(child.get("life") or "")
    even = parent["pos"] % 2 == 0  # father
    role = "father" if even else "mother"

    if is_placeholder(parent.get("name") or ""):
        flags.append("placeholder")

    if pb is not None and cb is not None:
        age = cb - pb
        if age < 0:
            flags.append("parent_born_after_child")
        elif age < 12:
            flags.append("parent_under_12")
        elif age < 15:
            flags.append("parent_under_15")
        if role == "mother":
            if age > 55:
                flags.append("mother_over_55")
            elif age > 50:
                flags.append("mother_over_50")
        else:
            if age > 90:
                flags.append("father_over_90")
            elif age > 80:
                flags.append("father_over_80")

    if pd is not None and cb is not None and cb > pd + 1:
        flags.append("child_after_parent_death")

    if pb is not None and cd is not None and pb > cd:
        flags.append("parent_born_after_child_death")

    return flags, role


IMPOSSIBLE = {
    "parent_born_after_child",
    "parent_under_12",
    "mother_over_55",
    "father_over_90",
    "child_after_parent_death",
    "parent_born_after_child_death",
}
SUSPECT = {
    "parent_under_15",
    "mother_over_50",
    "father_over_80",
}


def grade_of(flags, research, parent, is_proven_line, is_false_graft, is_divergent, is_dual, gen):
    """Return (grade, verdict, note, climb)."""
    note_bits = []
    # False Newbury graft sits above the last proven Knight.
    if is_false_graft:
        return (
            "F",
            "PRUNE",
            "Disproven father of William Knight Sr. — the Pilgrim/Newbury Capt. John Knight graft; the Knight surname line ends at William.",
            False,
        )
    if is_proven_line:
        return (
            "A",
            "ACCEPT",
            "Independently verified Knight paternal line (wills, census, land, family records).",
            True,
        )
    # Close family (the kids, their parents, their grandparents)
    if gen <= 2:
        return ("A", "ACCEPT", "Family records — living memory / close family.", True)

    if research:
        g = research["grade"]
        v = research["verdict"]
        n = research["note"]
        climb = g in {"A", "B", "C"}
        return g, v, n, climb

    if "placeholder" in flags:
        return ("U", "UNRESOLVED", "Placeholder or unnamed parent.", False)

    if flags & IMPOSSIBLE:
        why = ", ".join(sorted(flags & IMPOSSIBLE)).replace("_", " ")
        return ("F", "UNRESOLVED", "Impossible chronology: " + why + ".", False)

    if is_divergent:
        return (
            "D",
            "UNRESOLVED",
            "FamilySearch preferred pedigree now shows a different person at this slot.",
            False,
        )
    if is_dual:
        return (
            "D",
            "UNRESOLVED",
            "FamilySearch flags multiple parent-sets for this person (merge or detach).",
            False,
        )
    if flags & SUSPECT:
        why = ", ".join(sorted(flags & SUSPECT)).replace("_", " ")
        return ("D", "UNRESOLVED", "Suspicious chronology: " + why + ".", False)

    # Default: present, no red flags, not independently proven
    return ("C", "PENDING", "", True)


def main():
    data = load_json(DATA / "fan-data-clean.json")
    nodes = data["nodes"]
    by_gp = {(n["gen"], n["pos"]): n for n in nodes}
    by_id = defaultdict(list)
    for n in nodes:
        by_id[n["id"]].append(n)

    audit_html = (DOCS / "TREE-AUDIT.html").read_text(encoding="utf-8")
    divergences, dual_ids = parse_tree_audit(audit_html)
    research = apply_research(by_id, by_id)

    overrides = []
    ov_path = DATA / "research_overrides.json"
    if ov_path.exists():
        overrides = load_json(ov_path)
    ov_by_parent = {r["parent_id"]: r for r in overrides if r.get("parent_id") and not r.get("child_id")}
    ov_by_pair = {
        (r["parent_id"], r["child_id"]): r
        for r in overrides
        if r.get("parent_id") and r.get("child_id")
    }

    def find_override(parent_id, child_id):
        if child_id and (parent_id, child_id) in ov_by_pair:
            return ov_by_pair[(parent_id, child_id)]
        return ov_by_parent.get(parent_id)

    # Apply life corrections before the linter sees the dates
    for r in overrides:
        if r.get("parent_id") and r.get("life"):
            for n in by_id.get(r["parent_id"], []):
                n["life"] = r["life"]

    unknowns = set()
    unk_path = DATA / "_unknowns_dossier.json"
    if unk_path.exists():
        for row in load_json(unk_path):
            if isinstance(row, dict) and row.get("id"):
                unknowns.add(row["id"])

    proven = set(KNIGHT_PROVEN)
    spouse_copy = detect_spouse_copies(by_gp)
    edges = []
    counts = Counter()

    # Strip previous grade fields so a re-run is idempotent
    for n in nodes:
        for k in ("qg", "qn", "qf", "qv"):
            n.pop(k, None)

    for n in nodes:
        g, p = n["gen"], n["pos"]
        if g == 0:
            n["qg"] = "A"
            n["qv"] = "ACCEPT"
            n["qn"] = "Root — family records."
            counts["A"] += 1
            continue

        child = by_gp.get((g - 1, p // 2))
        flags, role = linter_flags(n, child) if child else ([], "father" if p % 2 == 0 else "mother")
        flagset = set(flags)
        if n["id"] in unknowns and "placeholder" not in flagset:
            flagset.add("placeholder")
            flags.append("placeholder")

        is_proven = n["id"] in proven
        is_false = n["id"] == KNIGHT_FALSE_FATHER
        is_div = (g, p) in divergences
        is_dual = n["id"] in dual_ids
        res = research.get(n["id"])

        grade, verdict, note, climb = grade_of(
            flagset, res, n, is_proven, is_false, is_div, is_dual, g
        )
        # Proven-line people also appear via pedigree collapse on other slots;
        # only the incoming Knight-line edge (the one whose child is also proven,
        # or gen<=2) should stay A. Other appearances fall through to linter
        # unless they really are the patriline slot (even pos, child also proven).
        if is_proven and child and child["id"] not in proven and g > 2:
            # collapsed appearance on another line — don't auto-A
            grade, verdict, note, climb = grade_of(
                flagset, res, n, False, is_false, is_div, is_dual, g
            )

        sc_note = spouse_copy.get((n["id"], child["id"])) if child else None
        if sc_note:
            grade, verdict, note, climb = "F", "PRUNE", sc_note, False

        ov = find_override(n["id"], child["id"] if child else None)
        if ov and ov.get("grade"):
            grade = ov["grade"]
            verdict = ov.get("verdict") or verdict
            if ov.get("note"):
                note = ov["note"]
            climb = ov["climb"] if "climb" in ov else grade in {"A", "B", "C"}

        counts[grade] += 1
        n["qg"] = grade
        n["qv"] = verdict
        if note:
            n["qn"] = note[:400]
        if flags:
            n["qf"] = flags

        if grade != "C" or flags:
            edges.append(
                {
                    "gen": g,
                    "pos": p,
                    "child_id": child["id"] if child else None,
                    "child_name": child["name"] if child else None,
                    "parent_id": n["id"],
                    "parent_name": n["name"],
                    "role": role,
                    "grade": grade,
                    "verdict": verdict,
                    "climb": climb,
                    "flags": flags,
                    "note": note,
                }
            )

    data["meta"]["quality"] = dict(counts)
    data["meta"]["qualityAt"] = datetime.date.today().isoformat()

    # Compact node fields: drop C-with-no-note to keep the payload small.
    # The chart treats missing qg as Unevaluated (N); graded C keeps qg+qn.
    for n in nodes:
        if n.get("qg") == "C" and not n.get("qn") and not n.get("qf"):
            n.pop("qg", None)
            n.pop("qv", None)

    (DATA / "fan-data-clean.json").write_text(
        json.dumps(data, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    payload = {
        "meta": {
            "generated": datetime.date.today().isoformat(),
            "counts": dict(counts),
            "nodes": len(nodes),
            "storedEdges": len(edges),
        },
        "edges": edges,
    }
    (DATA / "edge-grades.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    print("grade counts:", dict(counts))
    print("stored edges:", len(edges))
    print("spouse-copy prunes:", len(spouse_copy))
    print("divergences used:", len(divergences), "dual-parent ids:", len(dual_ids))
    print("research verdicts:", len(research))


if __name__ == "__main__":
    main()
