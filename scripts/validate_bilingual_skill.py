#!/usr/bin/env python3
"""Validate the machine-readable and localization invariants of a Codex skill."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
LATIN_RE = re.compile(r"[A-Za-z]")


def extract_frontmatter(text: str) -> tuple[dict[str, str], list[str]]:
    errors: list[str] = []
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, ["SKILL.md 缺少 YAML frontmatter 开始标记"]
    try:
        end = next(i for i, line in enumerate(lines[1:], start=1) if line.strip() == "---")
    except StopIteration:
        return {}, ["SKILL.md 缺少 YAML frontmatter 结束标记"]
    values: dict[str, str] = {}
    for line in lines[1:end]:
        match = re.match(r"^([A-Za-z][A-Za-z0-9_-]*):\s*(.*)$", line)
        if not match:
            continue
        key, value = match.groups()
        values[key] = value.strip().strip('"\'')
    for key in ("name", "description"):
        if not values.get(key):
            errors.append(f"frontmatter 缺少 {key}")
    return values, errors


def quoted_value(lines: list[str], key: str) -> str | None:
    pattern = re.compile(rf'^  {re.escape(key)}:\s*"(.*)"\s*$')
    for line in lines:
        match = pattern.match(line)
        if match:
            raw = match.group(1)
            try:
                return json.loads('"' + raw + '"')
            except json.JSONDecodeError:
                return raw
    return None


def validate_openai_yaml(path: Path, name: str, version: str | None) -> list[str]:
    errors: list[str] = []
    if not path.is_file():
        return ["缺少 agents/openai.yaml"]
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "interface:":
        errors.append("agents/openai.yaml 必须使用顶层 interface:")
    for key in ("display_name", "short_description", "default_prompt"):
        if any(re.match(rf'^{key}:', line) for line in lines):
            errors.append(f"{key} 不得位于 YAML 顶层，必须写成 interface.{key}")
    values = {key: quoted_value(lines, key) for key in ("display_name", "short_description", "default_prompt")}
    for key, value in values.items():
        if value is None or not value.strip():
            errors.append(f"缺少或未正确引用 interface.{key}")
    short = values["short_description"]
    if short is not None and not 25 <= len(short) <= 64:
        errors.append(f"interface.short_description 长度为 {len(short)}，必须为 25–64 个字符")
    prompt = values["default_prompt"]
    if prompt is not None and f"${name}" not in prompt:
        errors.append(f"interface.default_prompt 必须包含 ${name}")
    display = values["display_name"]
    if display is not None and version != "4" and not CJK_RE.search(display):
        errors.append("interface.display_name 必须包含中文标题")
    if version == "1" and display is not None and f"({name})" in display:
        errors.append("版本 1 的 display_name 不应包含英文原名")
    if version == "2" and display is not None and f"({name})" not in display:
        errors.append(f"版本 2 的 display_name 必须逐字保留 ({name})")
    if version == "3" and short is not None and CJK_RE.search(short):
        errors.append("版本 3 的 short_description 应使用英文简介")
    if version == "4":
        if display is not None and CJK_RE.search(display):
            errors.append("版本 4 必须使用英文标题")
        if display is not None and not LATIN_RE.search(display):
            errors.append("版本 4 的 display_name 必须包含英文标题")
        if short is not None and not CJK_RE.search(short):
            errors.append("版本 4 的 short_description 必须使用中文简介")
    return errors


def validate_translation(path: Path) -> list[str]:
    errors: list[str] = []
    in_fence = False
    headings = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence and re.match(r"^#{1,6}\s+", line):
            heading = re.sub(r"^#{1,6}\s+", "", line).strip()
            headings.append((line_no, heading))
            if LATIN_RE.search(heading) and not CJK_RE.search(heading):
                errors.append(f"第 {line_no} 行标题未汉化：{heading}")
    if not any(CJK_RE.search(heading) for _, heading in headings):
        errors.append("SKILL.md 没有中文标题")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("skill_dir")
    parser.add_argument("--version", choices=("1", "2", "3", "4"))
    parser.add_argument("--alias", action="append", default=[])
    parser.add_argument("--require-translation", action="store_true")
    args = parser.parse_args()

    skill = Path(args.skill_dir).expanduser().resolve()
    errors: list[str] = []
    skill_md = skill / "SKILL.md"
    if not skill.is_dir() or not skill_md.is_file():
        errors.append("目标不是包含 SKILL.md 的技能目录")
    else:
        frontmatter, frontmatter_errors = extract_frontmatter(skill_md.read_text(encoding="utf-8"))
        errors.extend(frontmatter_errors)
        name = frontmatter.get("name", "")
        if name and not NAME_RE.fullmatch(name):
            errors.append(f"frontmatter.name 不是合法 kebab-case：{name}")
        description = frontmatter.get("description", "")
        if description and (not CJK_RE.search(description) or not LATIN_RE.search(description)):
            errors.append("frontmatter.description 必须同时包含中文和英文")
        errors.extend(validate_openai_yaml(skill / "agents" / "openai.yaml", name, args.version))
        if args.require_translation:
            errors.extend(validate_translation(skill_md))
        for alias_value in args.alias:
            alias = Path(alias_value).expanduser()
            if not alias.is_symlink():
                errors.append(f"中文入口不是软链接：{alias}")
            elif alias.resolve() != skill:
                errors.append(f"中文入口指向错误目录：{alias} -> {alias.resolve()}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"OK: {skill}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
