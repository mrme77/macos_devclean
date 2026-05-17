---
name: devclean-macos
description: Use this skill when the user wants to inspect, preview, or clean macOS developer clutter such as AI tool caches, package manager caches, Python/Jupyter artifacts, Xcode derived data, oversized logs, browser web storage, Trash, or rebuildable project artifacts. The skill wraps a bundled deterministic cleanup script and should be used for Devclean-like maintenance workflows.
---

# Devclean macOS

## Overview

This skill helps run a Devclean-style macOS maintenance workflow with conservative defaults. It uses `scripts/devclean.py` to preview or clean rebuildable caches, logs, and artifacts while avoiding source code, credentials, settings, and active project content.

## Safety Rules

- Always start with a dry run. The script is dry-run by default; do not add `--execute` until the user has reviewed the planned actions and explicitly approved cleanup.
- Prefer `safe` mode unless the user asks for broader cleanup.
- Treat `aggressive` and `deep` as destructive maintenance modes. Explain what extra categories they include before running them with `--execute`.
- Never invent cleanup commands outside the bundled script for this workflow unless the user explicitly asks for custom behavior.
- Do not run with `sudo`.
- Do not run while Time Machine is active unless the user explicitly accepts the slowdown risk.
- If the user asks to change project roots, create or edit a config file rather than editing the script.

## Modes

- `safe`: AI tool caches, Homebrew cleanup, pip/uv/npm cache maintenance, shallow Python/Jupyter artifacts, Xcode DerivedData, and oversized user logs.
- `aggressive`: everything in `safe`, plus deeper Python artifacts, Homebrew download cache, forced npm clean, pnpm/yarn caches, Xcode archives/simulator caches, old rotated logs, and Chrome web storage if confirmed.
- `deep`: everything in `aggressive`, plus `.tox`, `.nox`, `htmlcov`, stale project logs, and rebuildable project artifacts in configured dev roots such as `.next`, `.turbo`, `.vite`, `dist`, `build`, and `target`.

## Quick Start

From this skill directory:

```bash
python3 scripts/devclean.py --mode safe
python3 scripts/devclean.py --mode deep
python3 scripts/devclean.py --mode deep --json
```

After the user approves the preview:

```bash
python3 scripts/devclean.py --mode safe --execute
```

## Configuration

Use `--config /path/to/devclean.json` for custom dev roots. Example:

```json
{
  "dev_roots": [
    "~/DevProjects",
    "~/Projects",
    "~/Developer",
    "~/src"
  ]
}
```

Only `deep` mode uses `dev_roots` for project logs and build artifacts. If no config is provided, the script checks common directories and skips missing paths.

## Reporting

Summarize dry-run output by category and call out any high-impact action, especially Chrome storage, Xcode archives, Trash, or project build artifact removal. If execution is requested, report what ran and any warnings from external tools.
