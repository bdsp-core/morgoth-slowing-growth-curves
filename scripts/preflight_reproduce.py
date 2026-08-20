#!/usr/bin/env python3
"""Can this machine actually regenerate the paper? Check every input the contract table names.

REPRODUCE.md carries a "paper item -> script -> input -> output" table. That table is a promise, and until
now nothing checked it. This parses it and, for every paper item, reports whether the producing script
exists, whether each declared input is present locally, and whether the declared output is there — so the
gap between "documented" and "reproducible" is a list rather than a surprise partway through a 24-hour run.

Exit code is 0 only when every item could run.

Run: python3 scripts/preflight_reproduce.py [--json]
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path

CONTRACT = Path("REPRODUCE.md")
ROW = re.compile(r"^\|\s*\*\*(?P<item>[^*]+)\*\*(?P<rest>.*?)\|\s*$", re.M)
CODE = re.compile(r"`([^`]+)`")

# Inputs named in the table are shorthand; these resolve to real paths.
PREFIX = ["data/derived/", "data/manifest/", "data/raw/", "results/", "figures/", ""]
# Things the table names that are not files (prose, or an upstream dataset referenced by description).
NOT_A_PATH = re.compile(r"^(scripts?/|—|-|source EDFs|SAI-100|ON-100|gate tables|manifest|panel|"
                        r"expert|votes|band_dtr|\.\.\.)", re.I)


def expand_braces(tok: str) -> list[str]:
    """`figures/x/{a,b}.png` -> both paths; `dir/*.png` stays a glob."""
    m = re.search(r"\{([^}]*)\}", tok)
    if not m:
        return [tok]
    return [tok[:m.start()] + alt.strip() + tok[m.end():] for alt in m.group(1).split(",")]


def resolve(token: str) -> tuple[bool, str]:
    """Does this input token correspond to something present on disk?"""
    tok = token.strip().rstrip(",")
    if not tok or NOT_A_PATH.match(tok):
        return True, f"{tok} (not a checkable path)"
    if "{" in tok or "*" in tok:
        for cand in expand_braces(tok):
            for pre in PREFIX:
                base = pre + cand
                if "*" in base:
                    root = Path(base).parent
                    if root.exists() and list(root.glob(Path(base).name)):
                        break
                elif Path(base).exists():
                    break
            else:
                return False, cand
        return True, tok
    for pre in PREFIX:
        p = Path(pre + tok)
        if p.exists():
            return True, str(p)
        # hive-partitioned tables are named without the trailing slash
        if p.is_dir() or Path(str(p).rstrip("/")).is_dir():
            return True, str(p)
    return False, tok


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if not CONTRACT.exists():
        sys.exit(f"{CONTRACT} not found")
    text = CONTRACT.read_text()

    items, in_table = [], False
    for line in text.split("\n"):
        if line.startswith("| Paper item"):
            in_table = True
            continue
        if in_table and not line.startswith("|"):
            in_table = False
        if not in_table or line.startswith("|---") or not line.startswith("| **"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 4:
            continue
        item = re.sub(r"\*\*", "", cells[0]).strip()
        scripts = CODE.findall(cells[1])
        inputs = CODE.findall(cells[2])
        outputs = CODE.findall(cells[3])

        missing_scripts = []
        for sc in scripts:
            for cand in (sc, f"scripts/{sc}", f"scripts/{sc}.py"):
                if Path(cand).exists() or list(Path("scripts").glob(f"{sc.split(',')[0].strip()}*")):
                    break
            else:
                missing_scripts.append(sc)
        missing_inputs = [t for t in inputs if not resolve(t)[0]]
        missing_outputs = [t for t in outputs if not resolve(t)[0]]
        items.append(dict(item=item, scripts=scripts, missing_scripts=missing_scripts,
                          inputs=inputs, missing_inputs=missing_inputs,
                          outputs=outputs, missing_outputs=missing_outputs,
                          runnable=not missing_scripts and not missing_inputs))

    if a.json:
        print(json.dumps(items, indent=2))
        sys.exit(0 if all(i["runnable"] for i in items) else 1)

    ok = [i for i in items if i["runnable"]]
    bad = [i for i in items if not i["runnable"]]
    print(f"contract items: {len(items)}   runnable now: {len(ok)}   blocked: {len(bad)}\n")
    for i in bad:
        print(f"  BLOCKED  {i['item']}")
        for s in i["missing_scripts"]:
            print(f"             missing script: {s}")
        for t in i["missing_inputs"]:
            print(f"             missing input : {t}")
    stale = [i for i in ok if i["missing_outputs"]]
    if stale:
        print(f"\n  runnable but output not yet present ({len(stale)}):")
        for i in stale:
            print(f"    {i['item']}: {', '.join(i['missing_outputs'])}")
    sys.exit(0 if not bad else 1)


if __name__ == "__main__":
    main()
