# bilingual-skill-translator

独立的 Codex 双语技能处理器。它负责把现有 Skill 翻译、本地化为中文，并保留中英文检索能力；它与 `skill-creator` 分开，不改变普通技能创建器的职责。

## 调用

以下说法都可以触发本技能：

- `/bilingual`
- `$bilingual-skill-translator`
- “翻译”
- “翻译 skill”
- “翻译这个 skill”
- “汉化 skill”
- “本地化 skill”
- “创建双语 skill”

目录关系：

```text
~/.codex/skills/bilingual-skill-translator/  # 真实技能目录
~/.codex/skills/bilingual                 # /bilingual 软链接
~/.codex/skills/skill-creator              # 普通技能创建器
```

## 工作方式

双语处理必须经过四步：

1. 澄清目标：确认要翻译正文、生成双语元数据、增加中文入口，还是只做审查。
2. 提出方案：在同一条助手回复中展示四个版本，供用户选择；未指定时默认使用版本 2；每个版本都要根据目标 skill 的实际能力提供至少一个具体示例。
3. 执行：用户明确选择版本并批准完整方案后，才写入文件或创建软链接。
4. 验证：检查名称、简介、空格、版本内容、入口和软链接目标。

## 路径记忆与发现

默认技能目录为 `$CODEX_HOME/skills`；如果未设置 `CODEX_HOME`，则为 `~/.codex/skills`。上次确认过的目标路径记录在：

```text
$CODEX_HOME/bilingual-skill-translator/state.json
```

未设置 `CODEX_HOME` 时，实际路径为 `~/.codex/bilingual-skill-translator/state.json`。记忆路径只作为候选，不能替代用户确认。

```bash
python3 scripts/bilingual_paths.py show
python3 scripts/bilingual_paths.py discover --root ~/项目/skills
python3 scripts/bilingual_paths.py remember ~/项目/skills/my-skill
```

## 备份与回滚

破坏性操作前先备份真实技能目录。备份默认保存到：

```text
$CODEX_HOME/bilingual-skill-translator/backups/
```

```bash
python3 scripts/skill_backup.py create /path/to/skill --label before-localization
python3 scripts/skill_backup.py list --verify
python3 scripts/skill_backup.py restore <backup-id> /path/to/skill --replace
```

恢复已有目录时必须显式使用 `--replace`；脚本会先创建 `pre-restore` 备份。不要对软链接本身执行递归删除或恢复，应操作它指向的真实目录。

## 方案示例要求

确认前的方案不能只列抽象字段。每个版本都要结合目标 skill 展示真实的标题、简介、触发说法或 slash 调用示例。例如 ATS 简历 skill 可以展示：

```text
用户说：“帮我检查这份简历的 ATS 关键词匹配度。”
```

示例必须来自目标 skill 的实际能力，不得使用“示例同上”等占位文字。

## 四个版本

| 版本 | UI 名称 | UI 简介 | 触发描述 |
| --- | --- | --- | --- |
| 1. 纯中文 | 中文 | 中文 | 默认中英双语 |
| 2. 中文标题 + 英文原名 | 中文（English original） | 中文 | 默认中英双语 |
| 3. 中文标题 + 英文简介 | 中文 | English | 默认中英双语 |
| 4. 英文标题 + 中文简介 | English | 中文 | 默认中英双语 |

这里的“触发描述”指 `SKILL.md` frontmatter 的 `description`；它负责技能检索，不等同于 UI 中的 `short_description`。除非用户明确关闭英文检索，否则触发描述保留中英双语。

## 名称规则

- 内部 `name` 使用合法的英文 kebab-case：`bilingual-skill-translator`。
- `/bilingual` 是调用别名，不替代内部 `name`。
- 用户指定的名称必须逐字保留：空格、大小写、标点、连字符、下划线和中英文字符都不能擅自改变。
- 任何删除、覆盖、重命名或替换软链接的操作，都要在方案中单独说明并获得明确授权。

## Codex UI 元数据格式

`agents/openai.yaml` 的 UI 字段必须位于 `interface:` 下；顶层直接写 `display_name` 不会被 Codex 读取：

```yaml
interface:
  display_name: "中文标题 (english-name)"
  short_description: "中文简介，长度为 25–64 个字符"
  default_prompt: "Use $skill-name to ..."
```

可使用内置验证器检查结构、版本规则、简介长度、`$skill-name` 和中文软链接：

```bash
python3 scripts/validate_bilingual_skill.py /path/to/skill \
  --version 2 --alias /path/to/中文入口 --require-translation
```

## 验证

优先使用目标技能或技能包提供的验证脚本。目标目录不一定自带 `quick_validate.py`；找不到脚本时，执行结构化手动检查，并报告验证限制。备份清单可用 `python3 scripts/skill_backup.py list --verify` 检查。至少检查：

- frontmatter `name` 和 `description`；
- `agents/openai.yaml` 的显示名称和简介；
- 四个版本与用户选择是否一致；
- 用户指定入口是否逐字符一致；
- 软链接是否指向唯一真实目录；
- 是否残留旧名称或旧路径。
