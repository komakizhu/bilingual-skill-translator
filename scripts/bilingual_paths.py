#!/usr/bin/env python3
"""Manage default, remembered, and discoverable Agent Skill paths."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Iterable


def codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser().resolve()


def state_file() -> Path:
    return codex_home() / "bilingual-skill-translator" / "state.json"


def default_skill_root() -> Path:
    return codex_home() / "skills"


def load_state() -> dict:
    path = state_file()
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"无法读取路径记忆文件 {path}: {exc}")
    return value if isinstance(value, dict) else {}


def save_state(value: dict) -> None:
    path = state_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def discover(roots: Iterable[Path], max_depth: int) -> list[Path]:
    results: set[Path] = set()
    for root in roots:
        root = root.expanduser().resolve()
        if not root.is_dir():
            continue
        for current, dirs, files in os.walk(root, followlinks=False):
            current_path = Path(current)
            depth = len(current_path.relative_to(root).parts)
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            if depth >= max_depth:
                dirs[:] = []
            if "SKILL.md" in files:
                results.add(current_path)
    return sorted(results)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("show", help="显示默认路径、记忆路径和状态文件")

    discover_parser = sub.add_parser("discover", help="查找包含 SKILL.md 的目录")
    discover_parser.add_argument("--root", action="append", help="要扫描的根目录，可重复")
    discover_parser.add_argument("--max-depth", type=int, default=5)

    remember_parser = sub.add_parser("remember", help="记住一个已确认的技能目录")
    remember_parser.add_argument("path")
    return p


def main() -> int:
    args = parser().parse_args()
    state = load_state()

    if args.command == "show":
        print(f"default_path={default_skill_root()}")
        print(f"last_path={state.get('last_path', '')}")
        print(f"state_file={state_file()}")
        return 0

    if args.command == "discover":
        roots = [Path(item) for item in args.root] if args.root else [
            default_skill_root(),
            Path.cwd() / ".codex" / "skills",
            Path.home() / ".claude" / "skills",
            Path.home() / ".agents" / "skills",
        ]
        for path in discover(roots, max(0, args.max_depth)):
            print(path)
        return 0

    path = Path(args.path).expanduser().resolve()
    if not path.is_dir() or not (path / "SKILL.md").is_file():
        raise SystemExit(f"不是有效的技能目录（需要目录和 SKILL.md）：{path}")
    state["last_path"] = str(path)
    save_state(state)
    print(f"remembered={path}")
    print(f"state_file={state_file()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
