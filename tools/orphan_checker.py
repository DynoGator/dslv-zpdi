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
        content = f.read()
    return set(SPEC_PATTERN.findall(content))

def analyze_codebase(src_dir: Path) -> Tuple[Set[str], List[Tuple[str, int, str, str]]]:
    claimed_specs = set()
    rogue_nodes = []
    for root, _, files in os.walk(src_dir):
        for file in files:
            if not file.endswith('.py'):
                continue
            filepath = Path(root) / file
            with open(filepath, 'r', encoding='utf-8') as f:
                try:
                    source = f.read()
                    tree = ast.parse(source)
                except Exception as e:
                    continue
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    name = node.name
                    node_type = "Class" if isinstance(node, ast.ClassDef) else "Function"
                    if EXEMPT_METHODS.match(name):
                        continue
                    docstring = ast.get_docstring(node)
                    if docstring:
                        matches = SPEC_PATTERN.findall(docstring)
                        if matches:
                            claimed_specs.update(matches)
                        else:
                            rogue_nodes.append((str(filepath), node.lineno, node_type, name))
                    else:
                        rogue_nodes.append((str(filepath), node.lineno, node_type, name))
    return claimed_specs, rogue_nodes

def main():
    repo_root = Path(__file__).parent.parent
    master_spec_path = repo_root / "MASTER_SPEC.md"
    src_dir = repo_root / "src"

    if not src_dir.exists():
        sys.exit(1)

    defined_specs = extract_specs_from_markdown(master_spec_path)
    claimed_specs, rogue_nodes = analyze_codebase(src_dir)
    rogue_specs = claimed_specs - defined_specs

    fatal_errors = 0
    if rogue_nodes:
        print("\n[FAIL] ROGUE CODE DETECTED:")
        fatal_errors += 1
    if rogue_specs:
        print("\n[FAIL] ROGUE SPECS DETECTED:")
        fatal_errors += 1

    if fatal_errors > 0:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
