import ast
import re
from pathlib import Path

SPEC_PATTERN = re.compile(r"(SPEC-\d{3}[A-Z]?(?:\.\d+[a-z]?)?)")


def analyze_specs_dir(specs_dir: Path) -> set[str]:
    defined_specs = set()
    for filepath in specs_dir.rglob("*"):
        if filepath.is_file():
            text = filepath.read_text(encoding="utf-8", errors="ignore")
            defined_specs.update(SPEC_PATTERN.findall(text))
    return defined_specs


def _node_has_spec(node: ast.AST, lines: list[str]) -> bool:
    docstring = ast.get_docstring(node)
    if docstring and SPEC_PATTERN.search(docstring):
        return True

    decorator_lines = [getattr(d, "lineno", None) for d in getattr(node, "decorator_list", [])]
    decorator_lines = [ln for ln in decorator_lines if ln is not None]
    header_start = min(decorator_lines + [node.lineno])

    first_body_line = node.body[0].lineno if getattr(node, "body", None) else node.lineno
    header_block = "\n".join(lines[header_start - 1:first_body_line - 1])
    if SPEC_PATTERN.search(header_block):
        return True

    i = header_start - 2
    comment_block = []
    while i >= 0:
        s = lines[i].strip()
        if not s:
            if comment_block:
                break
            i -= 1
            continue
        if s.startswith("#"):
            comment_block.append(lines[i])
            i -= 1
            continue
        break

    if comment_block:
        comment_text = "\n".join(reversed(comment_block))
        if SPEC_PATTERN.search(comment_text):
            return True

    return False


def analyze_codebase(src_dir: Path):
    claimed_specs = set()
    rogue_nodes = []

    for filepath in src_dir.rglob("*.py"):
        text = filepath.read_text(encoding="utf-8", errors="ignore")
        lines = text.splitlines()
        claimed_specs.update(SPEC_PATTERN.findall(text))

        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue

        for parent in ast.walk(tree):
            for child in ast.iter_child_nodes(parent):
                child.parent = parent

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                name = node.name
                ntype = "Class" if isinstance(node, ast.ClassDef) else "Function"
                has_spec = _node_has_spec(node, lines)

                if (
                    not has_spec
                    and isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and isinstance(getattr(node, "parent", None), ast.ClassDef)
                ):
                    has_spec = _node_has_spec(node.parent, lines)

                if not has_spec:
                    rogue_nodes.append((str(filepath), node.lineno, ntype, name))

    return claimed_specs, rogue_nodes

def main():
    root = Path(__file__).resolve().parents[1]
    src_dir = root / "src"
    specs_dir = root / "specs"

    defined_specs = analyze_specs_dir(specs_dir)
    claimed_specs, rogue_nodes = analyze_codebase(src_dir)
    rogue_specs = claimed_specs - defined_specs

    if rogue_nodes:
        print("Nodes missing SPEC-ID:")
        for fp, line, ntype, name in rogue_nodes:
            print(f"  -> {fp}:{line} | {ntype} '{name}' lacks a SPEC-ID.")

    if rogue_specs:
        print("\nClaimed SPEC-IDs not found in specs/:")
        for spec in sorted(rogue_specs):
            print(f"  -> {spec}")

    if rogue_nodes or rogue_specs:
        raise SystemExit(1)

    print("OK: no rogue nodes and no orphaned SPEC claims.")


if __name__ == "__main__":
    main()
