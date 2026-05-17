#!/usr/bin/env python3
"""Devclean-style macOS developer maintenance helper.

Dry-run is the default. Pass --execute to modify files.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable


MODE_ORDER = {"safe": 0, "aggressive": 1, "deep": 2}


@dataclass
class Action:
    category: str
    kind: str
    target: str
    detail: str = ""
    size: str = ""
    status: str = "planned"


def expand(path: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(path))).resolve()


def is_mode_at_least(mode: str, minimum: str) -> bool:
    return MODE_ORDER[mode] >= MODE_ORDER[minimum]


def human_size(path: Path) -> str:
    try:
        if path.is_file() or path.is_symlink():
            total = path.lstat().st_size
        else:
            total = sum(p.lstat().st_size for p in path.rglob("*") if not p.is_symlink())
    except OSError:
        return ""

    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(total)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f}{unit}" if unit != "B" else f"{int(size)}B"
        size /= 1024
    return ""


def protected_paths(home: Path) -> set[Path]:
    return {
        Path("/").resolve(),
        home,
        expand("~/.ssh"),
        expand("~/.gnupg"),
        expand("~/.aws"),
        expand("~/.config"),
        expand("~/Library"),
        expand("~/Library/Application Support"),
    }


def is_protected(path: Path, home: Path) -> bool:
    try:
        resolved = path.resolve()
    except OSError:
        resolved = path
    return resolved in protected_paths(home)


def add_existing(actions: list[Action], category: str, kind: str, path: Path, detail: str = "") -> None:
    if path.exists() or path.is_symlink():
        actions.append(Action(category, kind, str(path), detail, human_size(path)))


def command_exists(command: str) -> bool:
    return shutil.which(command) is not None


def add_command(actions: list[Action], category: str, command: list[str], detail: str = "") -> None:
    if command_exists(command[0]):
        actions.append(Action(category, "command", " ".join(command), detail))


def iter_depth(root: Path, max_depth: int) -> Iterable[Path]:
    root = root.resolve()
    if not root.exists():
        return
    root_depth = len(root.parts)
    for current, dirs, files in os.walk(root):
        current_path = Path(current)
        depth = len(current_path.parts) - root_depth
        if depth >= max_depth:
            dirs[:] = []
        yield current_path
        for name in files:
            yield current_path / name


def find_named_dirs(root: Path, max_depth: int, names: set[str]) -> list[Path]:
    matches: list[Path] = []
    root = root.resolve()
    if not root.exists():
        return matches

    root_depth = len(root.parts)
    for current, dirs, _files in os.walk(root):
        current_path = Path(current)
        depth = len(current_path.parts) - root_depth
        if depth >= max_depth:
            dirs[:] = []
            continue

        kept = []
        for dirname in dirs:
            child = current_path / dirname
            if dirname in names:
                matches.append(child)
            else:
                kept.append(dirname)
        dirs[:] = kept
    return matches


def find_named_files(root: Path, max_depth: int, names: set[str]) -> list[Path]:
    matches: list[Path] = []
    for candidate in iter_depth(root, max_depth):
        if candidate.is_file() and candidate.name in names:
            matches.append(candidate)
    return matches


def find_large_logs(root: Path, threshold_bytes: int) -> list[Path]:
    matches: list[Path] = []
    if not root.exists():
        return matches
    for candidate in root.rglob("*"):
        if not candidate.is_file() or candidate.suffix not in {".log", ".txt"}:
            continue
        try:
            if candidate.stat().st_size > threshold_bytes:
                matches.append(candidate)
        except OSError:
            continue
    return matches


def load_dev_roots(config_path: str | None, home: Path) -> list[Path]:
    roots = [
        home / "DevProjects",
        home / "Projects",
        home / "Developer",
        home / "src",
        home / "Dev",
    ]
    if not config_path:
        return [root for root in roots if root.exists()]

    with open(expand(config_path), "r", encoding="utf-8") as handle:
        config = json.load(handle)
    configured = config.get("dev_roots", [])
    if not isinstance(configured, list):
        raise ValueError("config key 'dev_roots' must be a list")
    return [expand(str(root)) for root in configured if expand(str(root)).exists()]


def build_plan(mode: str, config_path: str | None) -> list[Action]:
    home = Path.home().resolve()
    actions: list[Action] = []

    for path in [
        "~/.cache/claude-cli-nodejs",
        "~/.claude/cache",
        "~/.claude/tmp",
        "~/.claude/logs",
        "~/.claude/statsig",
        "~/Library/Caches/opencode",
        "~/Library/Application Support/OpenCode/GPUCache",
        "~/Library/Application Support/OpenCode/Code Cache",
        "~/.cache/opencode/node_modules",
        "~/.local/share/opencode/tmp",
        "~/.gemini/tmp",
        "~/.gemini/cache",
        "~/.config/gemini/tmp",
        "~/.config/gemini/cache",
        "~/.codex/tmp",
        "~/.codex/cache",
        "~/.config/codex/tmp",
        "~/.config/codex/cache",
        "~/Library/Application Support/Antigravity/Cache",
        "~/Library/Application Support/Antigravity/GPUCache",
        "~/Library/Application Support/Antigravity/Code Cache",
        "~/Library/Application Support/Antigravity/DawnGraphiteCache",
        "~/Library/Application Support/Antigravity/DawnWebGPUCache",
        "~/Library/Application Support/Antigravity/tmp",
        "~/Library/Caches/com.google.antigravity",
    ]:
        add_existing(actions, "AI tool caches", "delete", expand(path))

    if is_mode_at_least(mode, "aggressive"):
        add_existing(actions, "AI tool caches", "delete", expand("~/Library/Application Support/Antigravity/exthost"))

    add_command(actions, "Homebrew", ["brew", "cleanup", "--prune=all"], "safe cleanup")
    if is_mode_at_least(mode, "aggressive"):
        add_existing(actions, "Homebrew", "delete", expand("~/Library/Caches/Homebrew"))

    add_command(actions, "Python package caches", ["pip3", "cache", "purge"])
    add_command(actions, "Python package caches", ["pip", "cache", "purge"])
    add_command(actions, "uv caches", ["uv", "cache", "clean"])
    add_command(actions, "npm caches", ["npm", "cache", "verify"])
    if is_mode_at_least(mode, "aggressive"):
        add_command(actions, "npm caches", ["npm", "cache", "clean", "--force"])
        add_command(actions, "JS package caches", ["pnpm", "store", "prune"])
        add_command(actions, "JS package caches", ["yarn", "cache", "clean"])

    python_dirs = {"__pycache__", ".ipynb_checkpoints"}
    depth = 4
    if is_mode_at_least(mode, "aggressive"):
        python_dirs.update({".pytest_cache", ".mypy_cache", ".ruff_cache"})
        depth = 6
    if mode == "deep":
        python_dirs.update({".tox", ".nox", "htmlcov"})
        depth = 7
    for path in find_named_dirs(home, depth, python_dirs):
        add_existing(actions, "Python/Jupyter artifacts", "delete", path)
    if is_mode_at_least(mode, "aggressive"):
        for path in find_named_files(home, depth, {".coverage"}):
            add_existing(actions, "Python/Jupyter artifacts", "delete", path)

    for path in [
        "~/Library/Developer/Xcode/DerivedData",
        "~/Library/Caches/com.apple.dt.Xcode",
    ]:
        add_existing(actions, "Xcode caches", "delete", expand(path))
    if is_mode_at_least(mode, "aggressive"):
        for path in [
            "~/Library/Developer/Xcode/Archives",
            "~/Library/Developer/CoreSimulator/Caches",
        ]:
            add_existing(actions, "Xcode caches", "delete", expand(path))

    for log_root, threshold in [
        ("~/Library/Logs", 50 * 1024 * 1024),
        ("~/.claude/logs", 20 * 1024 * 1024),
        ("~/.gemini/logs", 20 * 1024 * 1024),
        ("~/.codex/logs", 20 * 1024 * 1024),
        ("~/.config/opencode/logs", 20 * 1024 * 1024),
        ("~/Library/Application Support/OpenCode/logs", 20 * 1024 * 1024),
        ("~/Library/Application Support/Antigravity/logs", 20 * 1024 * 1024),
    ]:
        for path in find_large_logs(expand(log_root), threshold):
            add_existing(actions, "Logs", "truncate", path, f">{threshold // 1024 // 1024}MB")

    if is_mode_at_least(mode, "aggressive"):
        for chrome_path in [
            "~/Library/Application Support/Google/Chrome/Default/IndexedDB",
            "~/Library/Application Support/Google/Chrome/Default/Service Worker",
            "~/Library/Application Support/Google/Chrome/Default/Cache",
        ]:
            add_existing(actions, "Chrome storage", "delete", expand(chrome_path), "requires confirmation")

    if mode == "deep":
        dev_roots = load_dev_roots(config_path, home)
        for root in dev_roots:
            for path in find_named_dirs(root, 5, {".next", ".turbo", ".vite", "dist", "build", "target"}):
                add_existing(actions, "Project build artifacts", "delete", path)
            for path in root.glob("**/*.log"):
                try:
                    if path.is_file() and path.stat().st_size > 5 * 1024 * 1024:
                        add_existing(actions, "Project logs", "delete", path, ">5MB")
                except OSError:
                    continue

    trash = home / ".Trash"
    if trash.exists() and any(trash.iterdir()):
        actions.append(Action("Trash", "delete_contents", str(trash), "requires confirmation", human_size(trash)))

    return actions


def confirm(prompt: str, assume_yes: bool) -> bool:
    if assume_yes:
        return True
    response = input(f"{prompt} [y/N] ").strip().lower()
    return response in {"y", "yes"}


def run_action(action: Action, home: Path, assume_yes: bool) -> Action:
    target = Path(action.target) if action.kind != "command" else None
    if target and is_protected(target, home):
        action.status = "skipped: protected path"
        return action

    try:
        if action.kind == "delete":
            assert target is not None
            if action.category == "Chrome storage" and not confirm(f"Clear {target}?", assume_yes):
                action.status = "skipped: user declined"
            elif target.is_dir() and not target.is_symlink():
                shutil.rmtree(target)
                action.status = "done"
            elif target.exists() or target.is_symlink():
                target.unlink()
                action.status = "done"
        elif action.kind == "truncate":
            assert target is not None
            with open(target, "w", encoding="utf-8"):
                pass
            action.status = "done"
        elif action.kind == "delete_contents":
            assert target is not None
            if not confirm(f"Empty {target}?", assume_yes):
                action.status = "skipped: user declined"
            else:
                for child in target.iterdir():
                    if child.is_dir() and not child.is_symlink():
                        shutil.rmtree(child)
                    else:
                        child.unlink(missing_ok=True)
                action.status = "done"
        elif action.kind == "command":
            completed = subprocess.run(action.target.split(), check=False, text=True, capture_output=True)
            action.status = "done" if completed.returncode == 0 else f"warning: exit {completed.returncode}"
            if completed.stderr.strip():
                action.detail = (action.detail + " " + completed.stderr.strip()).strip()
    except Exception as exc:  # noqa: BLE001 - surface operational failures in report.
        action.status = f"error: {exc}"
    return action


def time_machine_running() -> bool:
    if platform.system() != "Darwin" or not command_exists("tmutil"):
        return False
    completed = subprocess.run(["tmutil", "status"], check=False, text=True, capture_output=True)
    return '"Running" = 1' in completed.stdout


def print_text(actions: list[Action], execute: bool) -> None:
    if not actions:
        print("No matching cleanup targets found.")
        return

    by_category: dict[str, list[Action]] = {}
    for action in actions:
        by_category.setdefault(action.category, []).append(action)

    print("Execution report:" if execute else "Dry-run cleanup plan:")
    for category, items in by_category.items():
        print(f"\n[{category}]")
        for item in items:
            size = f" ({item.size})" if item.size else ""
            detail = f" - {item.detail}" if item.detail else ""
            status = f" [{item.status}]" if execute else ""
            print(f"- {item.kind}: {item.target}{size}{detail}{status}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Preview or run Devclean-style macOS developer cleanup.")
    parser.add_argument("--mode", choices=sorted(MODE_ORDER), default="safe")
    parser.add_argument("--execute", action="store_true", help="Modify files. Without this flag, only previews actions.")
    parser.add_argument("--yes", action="store_true", help="Assume yes for category confirmations during --execute.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of text.")
    parser.add_argument("--config", help="Path to JSON config with dev_roots for deep mode.")
    args = parser.parse_args()

    if platform.system() != "Darwin":
        print("Warning: this cleanup profile is designed for macOS.", file=sys.stderr)

    if args.execute and time_machine_running() and not confirm("Time Machine is running. Continue?", args.yes):
        print("Aborted.", file=sys.stderr)
        return 2

    actions = build_plan(args.mode, args.config)
    if args.execute:
        home = Path.home().resolve()
        actions = [run_action(action, home, args.yes) for action in actions]

    if args.json:
        print(json.dumps([asdict(action) for action in actions], indent=2))
    else:
        print_text(actions, args.execute)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
