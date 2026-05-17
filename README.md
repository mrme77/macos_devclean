# Devclean macOS Skill

[![skills.sh](https://skills.sh/b/mrme77/macos_devclean)](https://skills.sh/mrme77/macos_devclean)

Devclean macOS is an agent skill for previewing and cleaning macOS developer clutter: AI tool caches, package manager caches, Python and Jupyter artifacts, Xcode derived data, oversized logs, Chrome web storage, Trash, and rebuildable project artifacts.

The skill is inspired by the Devclean maintenance workflow, but is packaged for agent use with stricter safety defaults. It bundles a deterministic Python cleanup helper so agents do not improvise filesystem deletion commands.

## What This Repository Contains

```text
skills/
  devclean-macos/
    SKILL.md
    agents/
      openai.yaml
    scripts/
      devclean.py
```

- `SKILL.md`: agent-facing workflow, safety rules, mode guidance, and usage instructions.
- `scripts/devclean.py`: dry-run-first cleanup CLI used by the skill.
- `agents/openai.yaml`: Codex UI metadata for display name, short description, and default prompt.

## Safety Model

This skill is designed around preview-before-cleanup.

- Dry run is the default.
- File changes require `--execute`.
- The skill instructs the agent to ask for user approval before execution.
- It refuses protected broad paths such as the home directory, `~/.ssh`, `~/.gnupg`, `~/.aws`, `~/.config`, and top-level `~/Library`.
- It does not use `sudo`.
- It checks whether Time Machine is running before execution.
- Browser storage, Trash, and other high-impact categories are called out in reports.

This is still a cleanup tool. Review dry-run output before executing it.

## Cleanup Modes

### Safe

The default mode. Targets obvious rebuildable clutter:

- Claude, Gemini, Codex, OpenCode, and Antigravity caches
- Homebrew cleanup
- pip, uv, and npm cache maintenance
- shallow Python and Jupyter artifacts
- Xcode `DerivedData`
- oversized user-space logs
- Trash prompt when contents exist

### Aggressive

Includes `safe`, plus broader caches and artifacts:

- Homebrew download cache
- forced npm cache clean
- pnpm and yarn cache cleanup
- `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, and `.coverage`
- Xcode archives and simulator caches
- Chrome IndexedDB, Service Worker, and Cache directories

### Deep

Includes `aggressive`, plus project-root cleanup:

- `.tox`, `.nox`, and `htmlcov`
- stale large project logs
- rebuildable project artifacts such as `.next`, `.turbo`, `.vite`, `dist`, `build`, and `target`

Deep mode only scans configured or common development roots. It is not intended to sweep the entire filesystem.

## Install

From GitHub:

```bash
npx skills add mrme77/macos_devclean --skill devclean-macos -g
```

From a local checkout:

```bash
npx skills add . --skill devclean-macos -g
```

You can also install the skill manually by copying `skills/devclean-macos` into your agent's skills directory, such as:

```bash
~/.codex/skills/devclean-macos
```

Restart the agent after manual installation if it does not discover new skills dynamically.

## Usage

Ask your agent:

```text
Use $devclean-macos to preview safe developer cache cleanup on this Mac.
```

The skill should first run a dry-run command similar to:

```bash
python3 scripts/devclean.py --mode safe
```

For structured output:

```bash
python3 scripts/devclean.py --mode safe --json
```

Only after reviewing the preview should cleanup be executed:

```bash
python3 scripts/devclean.py --mode safe --execute
```

## Configuration

Deep mode can use a JSON config file for project roots:

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

Run with:

```bash
python3 scripts/devclean.py --mode deep --config ./devclean.json
```

## Direct CLI Reference

```bash
python3 scripts/devclean.py --mode safe
python3 scripts/devclean.py --mode aggressive
python3 scripts/devclean.py --mode deep
python3 scripts/devclean.py --mode deep --json
python3 scripts/devclean.py --mode safe --execute
python3 scripts/devclean.py --mode aggressive --execute --yes
```

Options:

- `--mode safe|aggressive|deep`: choose cleanup scope.
- `--execute`: modify files. Without this, the command only previews.
- `--yes`: assume yes for prompts during execution.
- `--json`: print machine-readable output.
- `--config PATH`: load `dev_roots` for deep mode.

## What It Does Not Clean

The skill is not intended to delete source code, credentials, settings, active virtual environments, databases, documents, or arbitrary user files.

It only targets known cache, log, and rebuildable artifact patterns.

## Discoverability

This skill is discoverable through the open skills ecosystem because it is hosted in a public GitHub repository with a valid `skills/devclean-macos/SKILL.md` file. Users can install it directly with:

```bash
npx skills add mrme77/macos_devclean --skill devclean-macos -g
```

The skills.sh leaderboard and install badge are driven by anonymous install telemetry from the `skills` CLI. The project page is:

```text
https://skills.sh/mrme77/macos_devclean
```

## License

MIT
