import os
import shutil

repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
workflows_dir = os.path.join(repo_root, ".github", "workflows")

def main():
    if not os.path.exists(workflows_dir):
        return

    # Delete redundant workflows
    for wf in ["dslv_zpdi_ci.yml", "test.yml", "lint.yml"]:
        wf_path = os.path.join(workflows_dir, wf)
        if os.path.exists(wf_path):
            os.remove(wf_path)

    # Modify ci.yml
    ci_path = os.path.join(workflows_dir, "ci.yml")
    if os.path.exists(ci_path):
        with open(ci_path, "r") as f:
            ci_content = f.read()

        if "python-version" in ci_content:
            import re
            ci_content = re.sub(r'python-version: \[.*?\]', 'python-version: ["3.10", "3.11", "3.12", "3.13", "3.14"]', ci_content)

        if "gitleaks" not in ci_content:
            gitleaks_job = """
  gitleaks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0
      - name: Gitleaks
        uses: zricethezav/gitleaks-action@master
"""
            ci_content += gitleaks_job
        
        with open(ci_path, "w") as f:
            f.write(ci_content)

    # Modify release.yml
    release_path = os.path.join(workflows_dir, "release.yml")
    if os.path.exists(release_path):
        with open(release_path, "r") as f:
            release_content = f.read()
            
        if "# Tags are immutable." not in release_content:
            release_content = "# Tags are immutable. Never re-tag. Cut a patch release instead.\n" + release_content
            with open(release_path, "w") as f:
                f.write(release_content)

if __name__ == "__main__":
    main()
