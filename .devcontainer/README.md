# Devcontainer

Unprivileged development container for pypiano.

## What "unprivileged" means here

- Runs as user `dev` (uid 1000), **no sudo** in the image.
- `--cap-drop=ALL` and `--security-opt=no-new-privileges` on the container.
- No Docker socket, no `privileged` flag, no devcontainer features that need root at runtime.

To add a system package, edit `Dockerfile` and rebuild (`Dev Containers: Rebuild Container`).

## Toolchain

- **uv** is preinstalled and manages the interpreters and the venv (no system Python).
- The maintained CPython versions (3.11, 3.12, 3.13, 3.14) are preinstalled, so a
  multi-version test matrix (`uv run --python 3.13 ...`) works offline.
- `post-create.sh` runs `uv sync`, which installs the project and the `dev` group into `/home/dev/.venv`
  (`UV_PROJECT_ENVIRONMENT`). It lives outside the bind-mounted repo, so a `.venv` that uv creates there on the host,
  for another OS and Python, doesn't replace the container's, or the other way around.
- `.python-version` (3.14) makes uv use the same Python on the host as in the container.
- **fluidsynth** / `libfluidsynth3` are installed so `mingus.midi.pyfluidsynth` can load the library.
- **sf2-cutter** builds the bundled piano sound font (`make soundfont`).

## Hooks and linters

**prek** (a fast `pre-commit` drop-in), **hadolint**, **dprint** and **sf2-cutter** are downloaded from
their GitHub releases in the `Dockerfile`, pinned by version and verified against a
sha256 per architecture (amd64/arm64). To bump one, change its `*_VERSION` and both
`*_SHA256_*` args.

`post-create.sh` runs `prek install`, so `.pre-commit-config.yaml` runs on every commit:

- the standard `pre-commit-hooks` (whitespace, EOF, YAML/TOML/JSON syntax, large files, ...)
- `ruff check --fix` and `ruff format` for Python (config: `pyproject.toml`)
- `ty check` for type checking, run from the project environment (config: `pyproject.toml`)
- `hadolint` lints Dockerfiles (config: `.hadolint.yaml`)
- `dprint fmt` formats Dockerfiles (config: `dprint.json`)

Run everything manually with `prek run --all-files`.

## Claude Code

The `claude` CLI is installed in the image (native installer, user-local, no root).
Its config directory `/home/dev/.claude` is a named volume, so `claude login`
and settings survive container rebuilds. The VS Code extension is installed too.

## GitHub CLI

`gh` is installed from GitHub's apt repository. Its config directory
`/home/dev/.config/gh` is a named volume, so `gh auth login` persists across rebuilds.
Alternatively set `GH_TOKEN` in your environment and forward it via `remoteEnv`.

## Audio

There is no sound device inside the container. Recording to `.wav` works
(`Piano.record(...)`); live playback via `p.play(...)` will not produce sound.
On a Linux host you can pass through `--device=/dev/snd` in `runArgs` if needed.
