# Academic Drafting - 学术写作辅助环境

基于 [opencode](https://opencode.ai) 框架构建的学术写作辅助环境，服务于批判理论导向的游戏研究（Game Studies）学术写作。项目通过模块化的 Skills 工作流，实现从征稿启事解析到论文定稿的全流程辅助。

## 项目简介

本项目的核心是一套针对中文学术写作设计的 AI 辅助工作流，主要特点：

- **征稿导向**：从征稿启事（CFP）中提取形式要求与隐含偏好，确保投稿合规
- **素材结构化**：将非结构化的讨论记录转化为可直接用于写作的素材库
- **去AI化写作**：内置「禁用表达库」与「替代方案库」，避免 AI 典型痕迹
- **多轮迭代**：批判性回读 → 形式校对 → AI痕迹扫描，循环优化直到达标

## 功能特性

### Skills 工作流

| Skill | 功能 | 输出 |
|-------|------|------|
| `cfp-analyzer` | 征稿启事解析、素材结构化、文章结构设计 | 技术规格书、结构化素材库、写作方案 |
| `academic-writer-persona` | 执笔者人格底座（批判理论/游戏研究风格） | — |
| `academic-drafter` | 正文写作、去AI化、形式校对、定稿 | 论文初稿、修改稿、最终稿 |
| `rewrite-summarize` | 文本总结与重写 | 摘要、总结 |

### 典型工作流

```
备份产出 → ./backup_output.sh (或 .\backup_output.ps1)
    ↓
用户上传文件 → 检查 ./references/
    ↓
cfp-analyzer → 技术规格书 → 结构化素材库 → 写作方案
    ↓
academic-drafter → 语言风格校准 → 分节写作
    ↓
批判性回读 → 形式规范校对 → AI痕迹扫描 → 定稿
    ↓
进一步迭代（可选）
```

### 辅助工具

- **word_count.py** - 中文学术文本字数统计
- **backup_output.sh / .ps1** - 产出备份脚本 (含 Windows PowerShell 版本)
- **setup-windows-antigravity.ps1** - Windows 环境 Antigravity 的初始化脚本
- **setup-linux-gemini.sh** - Linux 环境 Gemini CLI 的初始化脚本

## 快速开始

### 前置要求

- [opencode](https://opencode.ai) CLI
- Python 3.13+
- Ruff（可选，用于代码检查）

### 使用步骤

1. **克隆仓库**
   ```bash
   git clone https://github.com/fenixfu/acd-academic-drafting.git
   cd acd-academic-drafting
   ```
   > **Windows 下使用 Antigravity 的用户注意**：首次克隆后需执行初始化脚本建立软链接（*需要打开“开发人员模式”*）：
   > ```powershell
   > .\setup-windows-antigravity.ps1
   > ```
   > **Linux 下使用 Gemini CLI 的用户注意**：首次克隆后需执行初始化脚本建立软链接：
   > ```bash
   > chmod +x setup-linux-gemini.sh
   > ./setup-linux-gemini.sh
   > ```

2. **准备输入文件**
   - 将征稿启事放入 `./references/` 目录（文件名含 `cfp` 关键词）
   - 将讨论记录放入 `./references/` 目录（文件名含 `notes` 关键词）

3. **启动 opencode 并加载 skill**
   ```bash
   opencode
   ```
   在对话中请求学术论文写作，AI 将自动按顺序加载所需 skills。

4. **按阶段确认**
   每个步骤完成后，AI 会暂停等待确认，确保输出符合预期。

5. **获取产出**
   所有生成文件写入 `./output/` 目录。

## 目录结构

```
./
├── .opencode/                      # opencode 核心配置
│   ├── skills/                     # 学术写作技能集
│   │   ├── cfp-analyzer/           # 征稿启事解析
│   │   │   └── SKILL.md            # skill 定义文件
│   │   ├── academic-writer-persona/# 执笔者人格
│   │   │   └── SKILL.md
│   │   ├── academic-drafter/       # 写作执行器
│   │   │   ├── SKILL.md
│   │   │   └── scripts/
│   │   │       └── word_count.py   # 字数统计脚本
│   │   └── rewrite-summarize/      # 文本总结
│   │       └── SKILL.md
│   ├── plans/                      # 写作计划（运行时生成）
│   └── .gitignore
├── references/                     # 参考资料
│   ├── cfp_example.md              # 示例：征稿启事
│   └── notes_example.md            # 示例：讨论记录
├── output/                         # 产出目录（论文、摘要等）
├── former_results/                 # 备份存储目录
├── .gitignore                      # Git 忽略配置
├── LICENSE                         # CC BY-SA 4.0
├── README.md                       # 本文件
├── AGENTS.md                       # 详细技术规范与工作流指引
├── backup_output.sh                # output 备份脚本 (Linux/macOS)
├── backup_output.ps1               # output 备份脚本 (Windows)
├── setup-windows-antigravity.ps1   # Windows Antigravity 环境初始化脚本
└── setup-windows.ps1               # 废弃/通用 Windows 初始化（按需保留）
```

## 脚本使用

### 字数统计

```bash
# 统计指定文件
python .opencode/skills/academic-drafter/scripts/word_count.py output/摘要_定稿.md

# 不带参数：自动检测默认路径
python .opencode/skills/academic-drafter/scripts/word_count.py
```

### 备份产出

**macOS / Linux / WSL**：
```bash
# 执行备份（交互式确认）
./backup_output.sh

# 预览模式
./backup_output.sh --dry-run
```

**Windows (PowerShell)**：
```powershell
# 执行备份（交互式确认）
.\backup_output.ps1

# 预览模式
.\backup_output.ps1 -DryRun
```

## 注意事项

- 所有生成文件写入 `./output/` 目录，不会污染项目根目录
- 每个写作阶段完成后 AI 会暂停，需确认后再继续
- 如 `./output/` 已有文件，建议先执行备份脚本

## 许可证

本作品采用 [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) 许可证发布。

您可以自由地：
- **分享** — 以任何媒介或格式复制、发行本作品
- **演绎** — 混合、转换或基于本作品进行创作

惟须遵守：
- **署名** — 注明出处（包括本项目及原始提示词作者）
- **相同方式共享** — 若改变或演绎本作品，须以相同许可证发布
