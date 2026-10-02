# Devcontainer

Unprivileged development container for pypiano.

## What "unprivileged" means here

- Runs as user `dev` (uid 1000), **no sudo** in the image.
- `--cap-drop=ALL` and `--security-opt=no-new-privileges` on the container.
- No Docker socket, no `privileged` flag, no devcontainer features that need root at runtime.

To add a system package, edit `Dockerfile` and rebuild (`Dev Containers: Rebuild Container`).

## Toolchain

- **uv** is preinstalled and manages the interpreters and `.venv` (no system Python).
- The maintained CPython versions (3.11, 3.12, 3.13, 3.14) are preinstalled, so a
  multi-version test matrix (`uv run --python 3.13 ...`, tox with `tox-uv`, nox) works offline.
- `post-create.sh` detects the layout: with a `pyproject.toml` it runs `uv sync`;
  with the legacy `setup.py` + `requirements.txt` it creates `.venv` with `uv pip`
  on a best-effort basis (the old pins do not install on maintained Pythons).
- **fluidsynth** / `libfluidsynth3` are installed so `mingus.midi.pyfluidsynth` can load the library.
- **git-lfs** is installed; the post-create script pulls the sound font if the clone has pointers.

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
(`Piano.play(..., recording_file=...)`); live playback via `p.play(...)` will not produce sound.
On a Linux host you can pass through `--device=/dev/snd` in `runArgs` if needed.
