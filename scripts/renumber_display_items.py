#!/usr/bin/env python3
"""Renumber references and supplementary figures into first-citation order.

Clinical Neurophysiology wants Vancouver references numbered in citation order, and the round-1 review
caught that neither sequence was: the first reference cited in the Introduction was [13], and the first
supplementary figure called out in the text was S7. Doing this by hand invites exactly the kind of dangling
pointer the review found, so it is mechanical, idempotent, and verified after the fact.

Run LAST, after all prose edits, since inserting a citation anywhere changes every number after it.

Run: python3 scripts/renumber_display_items.py [--check]
"""
from __future__ import annotations
import argparse
import re
import sys
from pathlib import Path

MD = Path("docs/manuscript_draft.md")
SUPP_MD = Path("docs/supplementary_material.md")
SPLIT = "## References"
CITE = re.compile(r"\\\[([0-9]+(?:\s*(?:--|–|-)\s*[0-9]+)?(?:\s*,\s*[0-9]+(?:\s*(?:--|–|-)\s*[0-9]+)?)*)\\\]")
REF_ENTRY = re.compile(r"^(\d+)\.\s", re.M)
SUPP = re.compile(r"Figure S(\d+)")


def expand(tok: str) -> list[int]:
    out = []
    for part in tok.split(","):
        part = re.sub(r"[–—]", "-", part.strip()).replace("--", "-")
        m = re.fullmatch(r"(\d+)\s*-\s*(\d+)", part)
        if m:
            out += list(range(int(m.group(1)), int(m.group(2)) + 1))
        elif part.isdigit():
            out.append(int(part))
    return out


def collapse(nums: list[int]) -> str:
    """[3,4,5,9] -> '3--5,9'."""
    nums = sorted(dict.fromkeys(nums))
    parts, i = [], 0
    while i < len(nums):
        j = i
        while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
            j += 1
        run = nums[i:j + 1]
        # a 2-long run must stay a comma pair: "23,24". Collapsing it to a range is wrong, and emitting
        # only its first element silently DROPS a citation.
        parts.append(f"{run[0]}--{run[-1]}" if len(run) >= 3 else ",".join(str(n) for n in run))
        i = j + 1
    return ",".join(parts)


def citation_order(body: str) -> list[int]:
    seen: list[int] = []
    for m in CITE.finditer(body):
        for n in expand(m.group(1)):
            if n not in seen:
                seen.append(n)
    return seen


def renumber_refs(body: str, refs: str, supp: str) -> tuple[str, str, str, dict[int, int]]:
    # The supplement has no reference list of its own and cites the main one. References cited in the main
    # text are numbered first, in main-text order; those cited only in the supplement follow, in its order.
    order = citation_order(body)
    order += [n for n in citation_order(supp) if n not in order]
    listed = [int(m.group(1)) for m in REF_ENTRY.finditer(refs)]
    missing = [n for n in order if n not in listed]
    if missing:
        sys.exit(f"cited but not in the reference list: {missing}")
    uncited = [n for n in listed if n not in order]
    if uncited:
        sys.exit(f"in the reference list but never cited: {uncited}")
    mapping = {old: new for new, old in enumerate(order, 1)}

    def sub(text: str, label: str) -> str:
        before = sum(len(expand(m.group(1))) for m in CITE.finditer(text))
        text = CITE.sub(lambda m: "\\[" + collapse([mapping[n] for n in expand(m.group(1))]) + "\\]", text)
        after = sum(len(expand(m.group(1))) for m in CITE.finditer(text))
        if after != before:
            sys.exit(f"{label}: citation count changed during renumber: {before} -> {after} (a citation was dropped)")
        return text

    body, supp = sub(body, "main text"), sub(supp, "supplement")

    # split the list into entries, reorder, renumber
    entries: dict[int, str] = {}
    idx = [(m.start(), int(m.group(1))) for m in REF_ENTRY.finditer(refs)]
    for k, (pos, num) in enumerate(idx):
        end = idx[k + 1][0] if k + 1 < len(idx) else len(refs)
        entries[num] = refs[pos:end].rstrip()
    head = refs[: idx[0][0]]
    lines = []
    for old in order:
        text = REF_ENTRY.sub("", entries[old], count=1)
        lines.append(f"{mapping[old]}. {text}")
    return body, head + "\n".join(lines) + "\n", supp, mapping


def supp_order(body: str, supp: str) -> list[int]:
    """Supplementary figures in first-citation order: the main text first, then the supplement's own text."""
    order: list[int] = []
    for text in (body, supp):
        for m in SUPP.finditer(text):
            if int(m.group(1)) not in order:
                order.append(int(m.group(1)))
    return order


def renumber_supp(body: str, refs: str, supp: str) -> tuple[str, str, str, dict[int, int]]:
    mapping = {old: new for new, old in enumerate(supp_order(body, supp), 1)}
    if not mapping:
        return body, refs, supp, mapping
    sub = lambda m: f"Figure S{mapping.get(int(m.group(1)), int(m.group(1)))}"  # noqa: E731
    return SUPP.sub(sub, body), SUPP.sub(sub, refs), SUPP.sub(sub, supp), mapping


def reorder_supp_legends(back: str) -> str:
    """Put the supplementary-figure legend bullets in numeric order after renumbering."""
    lines = back.split("\n")
    idx = [i for i, l in enumerate(lines) if l.startswith("- **Figure S")]
    if not idx:
        return back
    lo, hi = min(idx), max(idx)
    if lines[lo:hi + 1] != [lines[i] for i in range(lo, hi + 1)]:
        return back
    block, others = [], []
    for i in range(lo, hi + 1):
        (block if lines[i].startswith("- **Figure S") else others).append(lines[i])
    if others:                      # non-bullet lines interleaved: leave alone rather than reshuffle prose
        return back
    block.sort(key=lambda l: int(re.search(r"Figure S(\d+)", l).group(1)))
    return "\n".join(lines[:lo] + block + lines[hi + 1:])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="verify ordering, change nothing")
    a = ap.parse_args()
    src = MD.read_text()
    body, refs = src.split(SPLIT, 1)
    supp = SUPP_MD.read_text()

    order_before = citation_order(body)
    order_before += [n for n in citation_order(supp) if n not in order_before]
    supp_first = supp_order(body, supp)
    ok = order_before == sorted(order_before) and supp_first == sorted(supp_first)
    if a.check:
        print("references in citation order:", order_before == sorted(order_before))
        print("supplementary in citation order:", supp_first == sorted(supp_first))
        sys.exit(0 if ok else 1)

    body, refs, supp, rmap = renumber_refs(body, refs, supp)
    body, refs, supp, smap = renumber_supp(body, refs, supp)
    refs = reorder_supp_legends(refs)
    supp = reorder_supp_legends(supp)
    MD.write_text(body + SPLIT + refs)
    SUPP_MD.write_text(supp)

    moved_r = {o: n for o, n in rmap.items() if o != n}
    moved_s = {o: n for o, n in smap.items() if o != n}
    print(f"references renumbered: {len(moved_r)} of {len(rmap)} moved")
    if moved_r:
        print("   " + ", ".join(f"[{o}]->[{n}]" for o, n in sorted(moved_r.items())))
    print(f"supplementary figures renumbered: {len(moved_s)} of {len(smap)} moved")
    if moved_s:
        print("   " + ", ".join(f"S{o}->S{n}" for o, n in sorted(moved_s.items())))


if __name__ == "__main__":
    main()
