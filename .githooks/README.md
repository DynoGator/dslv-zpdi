# Local git hooks

`core.hooksPath` is set to `.githooks` so any hook script committed here is
active for this checkout without per-clone `chmod` ceremony.

Reserved slots for when the Secure Storage Token / GitHub PAT arrives:

- `pre-push` — verify `GITHUB_PAT` is present in env and the remote URL uses
  the credential helper (never the bare token in the URL).
- `pre-commit` — block accidental commits of `.env`, `*.pat`, or any file
  matching `data/*.h5`.

No hooks are installed yet; the directory exists so the path resolves.
