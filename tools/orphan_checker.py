#!/usr/bin/env python3
import os
import re
import ast
import sys
from pathlib import Path
from typing import Set, Tuple, List

SPEC_PATTERN = re.compile(r'(SPEC-\d{3}[A-Z]?(?:\.\d+[a-z]?)?)')
EXEMPT_METHODS = re.compile(r'^__.*__$')

def extract_specs_from_markdown(md_path: Path) -> Set[str]:
    if not md_path.exists():
        print(f"CRITICAL: Master Spec not found at {md_path}")
        sys.exit(1)
    with open(md_path, 'r', encoding='utf-8') as f:
        return set(SPEC_PATTERN.findall(f.read()))

def analyze_codebase(src_dir: Path) -> Tuple[Set[str], List[Tuple[str, int, str, str]]]:
    claimed_specs = set()
    rogue_nodes = []
    for root, _, files in os.walk(src_dir):
        for file in files:
            if not file.endswith('.py'): continue
            filepath = Path(root) / file
            with open(filepath, 'r', encoding='utf-8') as f:
                try: tree = ast.parse(f.read())
                except: continue
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    name = node.name
                    ntype = "Class" if isinstance(node, ast.ClassDef) else "Function"
                    if EXEMPT_METHODS.match(name): continue
                    docstring = ast.get_docstring(node)
                    if docstring:
                        matches = SPEC_PATTERN.findall(docstring)
                        if matches: claimed_specs.update(matches)
                        else: rogue_nodes.append((str(filepath), node.lineno, ntype, name))
                    else:
                        rogue_nodes.append((str(filepath), node.lineno, ntype, name))
    return claimed_specs, rogue_nodes

def main():
    repo_root = Path(__file__).parent.parent
    master_spec_path = repo_root / "MASTER_SPEC.md"
    src_dir = repo_root / "src"

    defined_specs = extract_specs_from_markdown(master_spec_path)
    claimed_specs, rogue_nodes = analyze_codebase(src_dir)
    rogue_specs = claimed_specs - defined_specs

    fatal_errors = 0
    if rogue_nodes:
        print("\n[FAIL] ROGUE CODE DETECTED:")
        for fp, line, ntype, name in rogue_nodes:
            print(f"  -> {fp}:{line} | {ntype} '{name}' lacks a SPEC-ID.")
        fatal_errors += 1
    if rogue_specs:
        print("\n[FAIL] ROGUE SPECS DETECTED (Code claims it, Master Spec is missing it):")
        for spec in sorted(rogue_specs):
            print(f"  -> {spec}")
        fatal_errors += 1

    if fatal_errors > 0: sys.exit(1)
    print("[PASS] Orphan Checker: All intents aligned.")
    sys.exit(0)

if __name__ == "__main__":
    main()
