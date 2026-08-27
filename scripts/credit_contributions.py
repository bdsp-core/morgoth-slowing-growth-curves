"""Build the CRediT author-contribution statement in both renderings from ONE matrix.

Journals print the per-author form; the per-role form (initials against each of the 14 taxonomy terms) is
what the authors actually revise. Keeping both by hand guarantees they drift, and a CRediT statement that
contradicts itself is the kind of thing an editor bounces. So both are generated here from CONTRIB.

Run: python3 scripts/credit_contributions.py            -> prints both, checks they agree
     python3 scripts/credit_contributions.py --write    -> also rewrites the block in docs/manuscript_draft.md
"""
from __future__ import annotations
import argparse, re
from pathlib import Path

MD = Path("docs/manuscript_draft.md")

# Byline order, exactly as the title page lists them. Initials are unique across the 16.
AUTHORS = [
    ("JJ",  "J. Jing"),          ("CS",  "C. Sun"),        ("WG",  "W. Ganglberger"),
    ("ADL", "A. D. Lam"),        ("HS",  "H. Sun"),        ("TZ",  "T. Zhang"),
    ("DMG", "D. M. Goldenholz"), ("FAN", "F. A. Nascimento"), ("DY", "D. Yuan"),
    ("SB",  "S. Beniczky"),      ("JAK", "J. A. Kim"),     ("AFS", "A. F. Struck"),
    ("SFZ", "S. F. Zafar"),      ("RJT", "R. J. Thomas"),  ("MMS", "M. M. Shafi"),
    ("MBW", "M. B. Westover"),
]
ALL = [a for a, _ in AUTHORS]

# The 14 CRediT terms in the taxonomy's canonical order, each with the initials of its contributors.
CONTRIB = {
    "Conceptualization":        ["MBW", "RJT", "MMS"],
    "Data curation":            ["MBW", "WG", "TZ", "DY"],
    "Formal analysis":          ["MBW", "JJ", "CS"],
    "Funding acquisition":      ["MBW"],
    "Investigation":            ["MBW", "ADL", "FAN", "DY", "SB", "JAK", "AFS", "SFZ", "RJT", "MMS"],
    "Methodology":              ["MBW", "JJ", "CS", "WG", "HS", "DMG"],
    "Project administration":   ["MBW"],
    "Resources":                ["MBW", "SB", "RJT", "MMS"],
    "Software":                 ["MBW", "JJ", "CS", "WG", "HS", "TZ"],
    "Supervision":              ["MBW", "SFZ", "RJT", "MMS"],
    "Validation":               ["MBW", "WG", "ADL", "FAN", "SB", "JAK", "AFS", "SFZ"],
    "Visualization":            ["MBW", "CS"],
    "Writing -- original draft":     ["MBW", "JJ", "CS"],
    "Writing -- review & editing":   ALL,
}


def check():
    known = set(ALL)
    for role, who in CONTRIB.items():
        bad = [w for w in who if w not in known]
        assert not bad, f"{role}: unknown initials {bad}"
        assert len(who) == len(set(who)), f"{role}: duplicate initials"
    missing = [a for a in ALL if not any(a in w for w in CONTRIB.values())]
    assert not missing, f"authors with no role at all: {missing}"


def by_role() -> str:
    """Role -> initials. Contributors in byline order, so the reading order matches the title page."""
    order = {a: i for i, a in enumerate(ALL)}
    return "\n".join(f"**{role}:** {', '.join(sorted(who, key=order.__getitem__))}."
                     for role, who in CONTRIB.items())


def by_author() -> str:
    """Author -> roles, derived from the same matrix. This is the form journals typeset."""
    out = []
    for init, name in AUTHORS:
        roles = [r for r, who in CONTRIB.items() if init in who]
        out.append(f"**{name} ({init}):** " + ", ".join(roles) + ".")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write", action="store_true", help="rewrite the block in docs/manuscript_draft.md")
    args = ap.parse_args()
    check()

    # Round-trip: rebuild the matrix from the per-author rendering and require it to equal CONTRIB.
    rebuilt = {r: [] for r in CONTRIB}
    for line in by_author().splitlines():
        init = re.search(r"\(([A-Z]+)\)", line).group(1)
        for role in re.sub(r"^.*?\*\*:? ", "", line).rstrip(".").split(", "):
            role = role.strip()
            if role in rebuilt:
                rebuilt[role].append(init)
    for role in CONTRIB:
        assert sorted(rebuilt[role]) == sorted(CONTRIB[role]), f"renderings disagree on {role}"
    print("[ok] the two renderings agree on all 14 roles\n")
    print("--- by role (initials) ---\n" + by_role())
    print("\n--- by author ---\n" + by_author())

    if args.write:
        src = MD.read_text()
        start = src.index("- **CRediT author contributions.**")
        end = src.index("- **Acknowledgements.**", start)
        block = ("- **CRediT author contributions.** *\\[Draft for each author to confirm or amend before "
                 "submission; initials are given on the title page.\\]*\n" + by_role() + "\n")
        MD.write_text(src[:start] + block + src[end:])
        print(f"\nrewrote the CRediT block in {MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
