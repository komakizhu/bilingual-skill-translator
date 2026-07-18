#!/usr/bin/env python3
"""Create and restore content-addressed-ish local backups of Agent Skills."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path


def codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser().resolve()


def backup_root() -> Path:
    return codex_home() / "bilingual-skill-translator" / "backups"


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def manifest(root: Path, source: Path, kind: str) -> dict:
    files = []
    for path in sorted(root.rglob("*")):
        if path.is_file():
            files.append({"path": str(path.relative_to(root)), "sha256": digest(path)})
    return {
        "kind": kind,
        "source": str(source),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "files": files,
    }


def write_manifest(root: Path, value: dict) -> None:
    (root / "manifest.json").write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def create(source: Path, label: str | None, kind: str = "backup") -> Path:
    source = source.expanduser().resolve()
    if not source.is_dir() or not (source / "SKILL.md").is_file():
        raise SystemExit(f"不是有效的技能目录（需要目录和 SKILL.md）：{source}")
    root = backup_root()
    root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    safe_label = "".join(c if c.isalnum() or c in "-_" else "-" for c in (label or source.name))
    destination = root / f"{stamp}-{safe_label}"
    shutil.copytree(source, destination)
    write_manifest(destination, manifest(destination, source, kind))
    return destination


def resolve_backup(value: str) -> Path:
    candidate = Path(value).expanduser()
    if not candidate.is_absolute():
        candidate = backup_root() / candidate
    candidate = candidate.resolve()
    if not (candidate / "manifest.json").is_file():
        raise SystemExit(f"找不到备份或 manifest.json：{candidate}")
    return candidate


def verify(root: Path) -> list[str]:
    data = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    errors = []
    for item in data.get("files", []):
        path = root / item["path"]
        if not path.is_file():
            errors.append(f"缺少文件：{item['path']}")
        elif digest(path) != item["sha256"]:
            errors.append(f"哈希不匹配：{item['path']}")
    return errors


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    create_parser = sub.add_parser("create", help="创建技能备份")
    create_parser.add_argument("path")
    create_parser.add_argument("--label")
    list_parser = sub.add_parser("list", help="列出备份")
    list_parser.add_argument("--verify", action="store_true")
    restore_parser = sub.add_parser("restore", help="从备份恢复技能")
    restore_parser.add_argument("backup")
    restore_parser.add_argument("target")
    restore_parser.add_argument("--replace", action="store_true", help="先备份并替换已有目标")
    return p


def main() -> int:
    args = parser().parse_args()
    if args.command == "create":
        destination = create(Path(args.path), args.label)
        print(destination)
        return 0
    if args.command == "list":
        root = backup_root()
        for item in sorted(root.glob("*/manifest.json")) if root.is_dir() else []:
            data = json.loads(item.read_text(encoding="utf-8"))
            status = ""
            if args.verify:
                status = " OK" if not verify(item.parent) else " INVALID"
            print(f"{item.parent.name}\t{data.get('kind', 'backup')}\t{data.get('source', '')}{status}")
        return 0

    source = resolve_backup(args.backup)
    target = Path(args.target).expanduser().resolve()
    if target.is_symlink():
        raise SystemExit("目标是软链接；请对软链接指向的真实技能目录执行恢复")
    if target.exists():
        if not args.replace:
            raise SystemExit("目标已存在；如确认替换，请显式添加 --replace")
        create(target, f"pre-restore-{target.name}", kind="pre-restore")
        shutil.rmtree(target)
    shutil.copytree(source, target, ignore=shutil.ignore_patterns("manifest.json"))
    print(f"restored={target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
