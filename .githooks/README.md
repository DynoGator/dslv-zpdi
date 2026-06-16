# Local git hooks

`core.hooksPath` is set to `.githooks` so hooks committed here are active
for this checkout without per-clone `chmod` ceremony.

## Installed hooks

### `pre-commit`
Blocks staging of secrets, credentials, and data artifacts:
- `.env`, `.env.*` — PAT / secrets file
- `*.pat`, `*.token` — raw credential files
- `data/*.h5`, `data/*.hdf5` — HDF5 stream artifacts (can be very large)
- `*.pid` — runtime PID files

### `pre-push`
Before any push to origin:
1. Verifies `GITHUB_PAT` is present in the environment (sources `.env` if available).
2. Rejects any remote URL that embeds credentials in the URL string.

Run `./configure_git_auth.sh` to satisfy pre-push requirements.
