---
name: bilingual-skill-creator
description: 独立处理 Codex 技能的中文翻译、双语名称与简介、三种本地化版本、中文 slash 入口、审批和最终验证。适用于用户要求翻译技能、创建双语版本、保留中英检索或增加 /bilingual 入口时使用。 Independently translate and localize Codex skills with bilingual names, descriptions, three localization variants, slash aliases, approval, and verification. Use for bilingual skill work as the standalone bilingual-skill-creator, separate from skill-creator.
---

# 双语技能（Bilingual）

将“创建技能”和“本地化技能”视为同一条可复用流程。输出必须保持原技能能力不变，同时增加中文可发现性；除非用户明确要求，否则不要修改原技能的英文主名或破坏原有入口。任何实际写入、重命名、删除或创建软链接的操作，都必须遵循下方四步审批流程。

## 工作流程（Workflow）

### 第一步：澄清目标（Clarify）

如果用户只选择了一个技能、只提供了技能路径，或说“帮我改这个 skill”但没有说明改什么，不得直接修改。先读取可安全读取的元数据，然后询问用户要做哪类操作，并提供具体选择，例如：

- 只翻译正文为中文。
- 生成中英双语 `description` 和 UI 简介。
- 增加中文 slash 调用入口。
- 同时完成翻译、双语元数据和中文入口。
- 只检查并提出优化建议，不执行修改。

处理路径时使用 `scripts/bilingual_paths.py show`：默认技能目录是 `$CODEX_HOME/skills`；若未设置 `CODEX_HOME`，则使用 `~/.codex/skills`。读取状态文件中记忆的 `last_path`，但不得未经用户确认自动使用它。若用户没有提供目标路径，先展示默认路径、上次路径和候选路径，再让用户选择；需要查找新位置时使用 `scripts/bilingual_paths.py discover --root <path>`，不得静默扫描并自行选定目录。成功执行后，只有在用户已确认该路径的情况下，才使用 `scripts/bilingual_paths.py remember <path>` 记住路径。

### 第二步：提出方案并选择版本（Propose & Choose）

明确目标后，在同一条对话消息中展示拟执行方案和以下三个版本，供用户直接选择：

1. **纯中文版本（Chinese-only UI）**：`display_name`、`short_description` 和用户可见标题全部使用中文；保留内部合法的英文 `name`。触发用的 frontmatter `description` 仍默认保留中英双语，以免失去英文检索能力。
2. **中文标题 + 英文原名（Chinese title + English original）**：`display_name` 使用中文标题，并在括号中逐字保留英文原名；`short_description` 使用中文，必要时保留关键英文术语。触发用的 frontmatter `description` 仍默认双语。
3. **中文标题 + 英文简介（Chinese title + English description）**：`display_name` 使用中文标题，`short_description` 直接使用英文简介原文；触发用的 frontmatter `description` 仍默认双语。适合需要英文说明或英文检索的场景。

同一条助手回复中还必须列出：目标技能、创建位置或安装位置、将修改的文件、三种版本分别对应的 `display_name`、`short_description` 和 frontmatter `description`、slash 入口、是否创建软链接、空格与大小写处理，以及关键差异示例。此阶段只读，不得写入文件。等待用户明确选择版本并批准当前完整方案；只有“选择版本 2，并批准按上面方案执行”这类明确绑定方案的回复才算批准。“看一下”“怎么样”“先给我方案”以及只说“版本 2”都不算批准。

### 第三步：执行（Apply）

只有用户选择版本并明确批准当前完整方案后，才进行写入或创建操作。删除旧技能、覆盖已有文件、替换已有软链接、改动原英文入口等破坏性操作，必须在方案中单独标注，并获得明确授权；不能从普通的“批准方案”中推断出删除授权。执行删除、覆盖或替换前，先运行 `python3 scripts/skill_backup.py create <真实技能目录> --label <说明>`，记录备份路径并检查备份清单。若需要回滚，先向用户说明恢复目标，再运行 `python3 scripts/skill_backup.py restore <备份目录或 ID> <目标目录> --replace`；恢复前脚本会再次创建 `pre-restore` 备份。若用户要求改动方案，必须回到第二步重新展示三个版本并请求批准。

### 第四步：验证（Verify）

执行完成后，必须独立验证实际结果，不得只依据写入命令成功来判断完成。至少检查：

- frontmatter 的 `name` 合法且未被意外改名。
- `agents/openai.yaml` 的显示名称和简介与用户选择的版本一致；`short_description` 满足界面约束（通常为 25–64 个字符）。
- 用户指定的 slash 入口逐字一致，空格数量、大小写、连字符、下划线和中英文字符均正确。
- 第 2 版本确实在 UI `display_name` 中保留英文原名；第 3 版本确实在 UI `short_description` 中使用英文简介；第 1 版本没有不必要的英文用户可见文本。
- 软链接存在且指向唯一真实技能目录，原有英文入口仍按方案保留。
- 优先运行技能自身或技能包提供的验证脚本；如果目标技能没有验证脚本，再定位可用的 `quick_validate.py` 或使用结构化手动检查。使用 `python3 scripts/skill_backup.py list --verify` 检查本次备份清单。不要假设目标技能目录内存在验证脚本；若验证脚本或依赖不可用，必须明确报告限制。

若验证发现任何名称、空格、版本内容或入口不一致，不得直接默默修复；应报告差异，回到第二步提出新方案并重新请求批准。

### 方案实施细节（Implementation）

1. **确定目标**：确认是新建技能，还是翻译/改造现有技能；读取目标 `SKILL.md`、`agents/openai.yaml` 和相关资源。新建技能时先询问或确认创建位置；若用户未指定，使用 `$CODEX_HOME/skills`，未设置时使用 `~/.codex/skills`，并说明该位置。若目标可能在其他位置，展示 `bilingual_paths.py discover` 的候选结果，让用户选择。
2. **初始化新技能**：新建技能时优先运行可用的 `init_skill.py`，生成合法目录、frontmatter 和 `agents/openai.yaml`；已有技能不重复初始化。
3. **提炼能力**：保留原技能的触发场景、工作流、工具约束和资源引用，不把翻译变成摘要。
4. **编写双语元数据**：
   - `name` 保持合法的英文 kebab-case，除非用户明确要求改名。
   - frontmatter `description` 是触发和检索描述，默认先写自然中文，再保留准确英文；两种语言都要包含“做什么”和“何时触发”。它不随 UI 三版本任意删掉英文，除非用户明确批准关闭英文检索。
   - `agents/openai.yaml` 的 `display_name` 与 `short_description` 按第二步选定的版本生成；不要把 UI 文案误写进 frontmatter `name`。
   - 保留原有图标、依赖和默认提示；如生成 `default_prompt`，同时包含 `$skill-name`。
5. **翻译正文**：准确翻译标题、说明、步骤、代码注释和用户可见文字；代码、路径、命令、字段名、API 名称和品牌名保持原样。必要时采用“中文（English）”术语，确保中英检索仍能命中。
6. **设置入口**：为中文调用名创建指向真实技能目录的软链接（symlink），例如 `/skill创建器` 对应 `skill-creator`。不要复制整份技能目录，避免双份版本漂移。若别名已存在，先确认它是否为目标软链接，再安全替换；替换前备份真实技能目录，不要把软链接本身当作普通目录递归删除。
7. **校验**：按第四步验证实际结果，并检查 YAML frontmatter、名称规则、软链接目标、双语触发词和原有资源路径。

## 翻译质量要求（Translation Quality）

- 不改变语义、步骤顺序、权限边界或安全要求。
- 保留原文中的关键英文术语，以支持英文用户请求和中英混合请求。
- 中文简介要简洁、可检索；避免只写“翻译版”这类无法说明能力的描述。
- 新增的中文入口应与用户指定的 slash 名称逐字一致。逐字一致包括空格数量、大小写、连字符、下划线、中文字符和英文字符；用户说“不要空格”时，必须显式检查并确保没有空格。
- 显示名、文件夹名、frontmatter `name`、软链接名和 slash 入口是不同字段，不得擅自混用或替换；任何名称变化都必须在第二步方案中列出并经用户批准。
- 方案中展示的字符串必须与最终写入的字符串一致；执行前后逐字符比对，防止自动格式化或 UI 元数据残留旧名称。
- 同一条助手回复必须同时包含三个版本，不要拆成多轮分别展示，以免用户在不同版本之间批准了不一致的方案。
- 三个版本只改变用户可见的 UI 字段；内部 `name`、触发用 `description` 和技术路径默认保持稳定，除非用户明确批准改变。
- 不额外创建 README、安装指南、变更日志等非必要文件。

## 交付检查（Handoff Checklist）

- 如果原技能已有英文入口，原技能仍可通过原英文名称调用；新建技能则只验证方案中约定的入口。
- 中文软链接存在且指向唯一真实目录。
- 触发用的 frontmatter `description` 同时覆盖中文和英文能力、触发场景；UI 文案则符合用户选择的版本。
- `agents/openai.yaml` 与 `SKILL.md` 的名称和简介一致。
- 校验结果或依赖缺失情况已报告。
