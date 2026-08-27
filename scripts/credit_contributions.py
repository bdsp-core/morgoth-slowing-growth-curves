"""Propagate the CRediT statement from docs/credit_contributions.md into the manuscript.

docs/credit_contributions.md is the source of truth: the authors edit its two tables. This script parses
them, checks them, rewrites the CRediT block in docs/manuscript_draft.md, and refreshes the generated
per-author rendering at the bottom of the source file.

Two renderings exist because they serve different readers -- the per-role form (initials against each of
the 14 taxonomy terms) is what authors revise, the per-author form is what journals typeset. Maintaining
both by hand guarantees they drift, and a CRediT statement that contradicts itself is the kind of thing an
editor bounces, so both are generated here from one table.

Run: python3 scripts/credit_contributions.py            -> parse, check, print both renderings
     python3 scripts/credit_contributions.py --write    -> also update the manuscript and this file
"""
from __future__ import annotations
import argparse, re
from pathlib import Path

SRC = Path("docs/credit_contributions.md")
MD = Path("docs/manuscript_draft.md")
GEN = "<!-- GENERATED BELOW THIS LINE — do not edit; run scripts/credit_contributions.py --write -->"

# The taxonomy, in canonical order. A role in the source file that is not on this list is a typo, not a new
# role -- CRediT is a closed vocabulary, and a journal's submission form will only accept these 14.
ROLES = ["Conceptualization", "Data curation", "Formal analysis", "Funding acquisition", "Investigation",
         "Methodology", "Project administration", "Resources", "Software", "Supervision", "Validation",
         "Visualization", "Writing -- original draft", "Writing -- review & editing"]


def _rows(section: str, text: str) -> list[list[str]]:
    """The body rows of the pipe table under a given '## N. Title' heading."""
    body = text.split(section, 1)[1].split("\n## ", 1)[0]
    out = []
    for line in body.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if all(set(c) <= set("-: ") for c in cells):        # the |---| separator
            continue
        if cells and cells[0].lower() in ("initials", "credit role"):
            continue
        out.append(cells)
    return out


def parse(text: str):
    authors = [(r[0], r[1]) for r in _rows("## 1. Authors and initials", text)]
    contrib = {}
    for r in _rows("## 2. Contributions", text):
        role = r[0]
        contrib[role] = [w.strip() for w in r[1].split(",") if w.strip()] if len(r) > 1 else []
    notes = [l.strip()[2:].strip() for l in
             text.split("## 3. Notes carried into the manuscript", 1)[1].split("\n## ", 1)[0].splitlines()
             if l.strip().startswith("- ")]
    return authors, contrib, notes


def check(authors, contrib):
    inits = [a for a, _ in authors]
    assert len(inits) == len(set(inits)), f"duplicate initials in the author table: {inits}"
    unknown_roles = [r for r in contrib if r not in ROLES]
    assert not unknown_roles, f"not CRediT roles (closed vocabulary): {unknown_roles}"
    absent = [r for r in ROLES if r not in contrib]
    assert not absent, f"roles missing from the contributions table: {absent}"
    known = set(inits)
    for role, who in contrib.items():
        bad = [w for w in who if w not in known]
        assert not bad, f"{role}: initials not in the author table: {bad}"
        assert len(who) == len(set(who)), f"{role}: an author is listed twice"
    orphan = [a for a in inits if not any(a in w for w in contrib.values())]
    assert not orphan, f"authors with no role at all (CRediT requires at least one): {orphan}"


def by_role(authors, contrib) -> str:
    order = {a: i for i, (a, _) in enumerate(authors)}
    return "\n".join(f"**{r}:** {', '.join(sorted(contrib[r], key=order.__getitem__))}." for r in ROLES)


def by_author(authors, contrib) -> str:
    return "\n".join(f"**{name} ({init}):** " + ", ".join(r for r in ROLES if init in contrib[r]) + "."
                     for init, name in authors)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    text = SRC.read_text()
    authors, contrib, notes = parse(text)
    check(authors, contrib)

    role_view, author_view = by_role(authors, contrib), by_author(authors, contrib)

    # Round-trip: rebuild the matrix from the per-author rendering and require it to equal the source table.
    rebuilt = {r: [] for r in ROLES}
    for line in author_view.splitlines():
        init = re.search(r"\(([A-Za-z]+)\):", line).group(1)
        for role in line.split(":**", 1)[1].rstrip(".").split(", "):
            if role.strip():
                rebuilt[role.strip()].append(init)
    for r in ROLES:
        assert sorted(rebuilt[r]) == sorted(contrib[r]), f"the two renderings disagree on {r}"
    print(f"[ok] {len(authors)} authors, 14 roles, both renderings agree\n")
    print("--- by role (initials) ---\n" + role_view)
    print("\n--- by author ---\n" + author_view)
    for n in notes:
        print("\nnote: " + n)

    if args.write:
        block = ("- **CRediT author contributions.** *\\[Draft for each author to confirm or amend before "
                 "submission; initials are given on the title page.\\]*\n" + role_view + "\n")
        for n in notes:
            block += "\n" + n + "\n"
        m = MD.read_text()
        start = m.index("- **CRediT author contributions.**")
        end = m.index("- **Acknowledgements.**", start)
        MD.write_text(m[:start] + block + m[end:])
        print(f"\nrewrote the CRediT block in {MD}")

        SRC.write_text(text.split(GEN)[0] + GEN + "\n\n## Per-author rendering (generated)\n\n"
                       "The form journals typeset. Generated from the table above; edit that, not this.\n\n"
                       + author_view + "\n")
        print(f"refreshed the generated section of {SRC}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
