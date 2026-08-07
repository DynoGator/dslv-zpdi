#!/usr/bin/env python3
import os
import shutil

repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
source_file = os.path.join(repo_root, "AGENTS.md")

targets = [
    "CLAUDE.md",
    ".claude/rules/doctrine.md",
    ".codex/instructions.md",
    ".gemini/instructions.md",
    ".kimi/instructions.md"
]

def main():
    if not os.path.exists(source_file):
        print("AGENTS.md not found!")
        return

    for target in targets:
        target_path = os.path.join(repo_root, target)
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        shutil.copy2(source_file, target_path)
        print(f"Synced to {target}")

if __name__ == "__main__":
    main()
