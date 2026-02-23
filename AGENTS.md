# AGENTS.md

本文档为在此代码库中工作的AI代理提供技术规范和工作流程指引。

---

## 1. 项目概述

这是一个**学术写作辅助环境**，基于opencode框架构建，服务于批判理论导向的游戏研究（Game Studies）学术写作。项目不包含传统软件代码，主要产出为中文学术论文、征稿摘要等。

**项目结构：**
```
./
├── .opencode/              # opencode核心配置
│   ├── skills/            # 学术写作技能集
│   │   ├── cfp-analyzer/  # 征稿启事解析
│   │   ├── academic-writer-persona/  # 执笔者人格
│   │   ├── academic-drafter/ # 写作执行器
│   │   │   └── scripts/word_count.py  # 字数统计脚本
│   │   └── rewrite-summarize/ # 文本总结
│   └── plans/             # 写作计划
├── references/            # 参考资料（征稿启事、讨论记录）
├── output/                # 产出目录（论文、摘要等）
├── former_results/        # 备份存储目录
└── backup_output.sh       # output备份脚本
```

---

## 2. 构建与测试命令

### 2.1 Python脚本

此项目包含一个Python脚本用于字数统计，无传统构建流程。

```bash
# 字数统计（中文学术摘要）
python .opencode/skills/academic-drafter/scripts/word_count.py <文件路径>

# 示例：统计output目录下的摘要
python .opencode/skills/academic-drafter/scripts/word_count.py output/摘要_定稿.md

# 不带参数运行：自动检测默认路径下的摘要文件
python .opencode/skills/academic-drafter/scripts/word_count.py
```

**字数统计规则：**
- 中文字符（含标点）：每个算1字
- 英文字母/数字连续序列：算1字（如"Vanguard"算1字）
- 空格：不计入

### 2.2 Lint与格式化

项目使用Ruff进行Python代码检查与格式化。

```bash
# 检查Python文件
ruff check .opencode/skills/academic-drafter/scripts/word_count.py

# 自动修复问题
ruff check --fix .opencode/skills/academic-drafter/scripts/word_count.py

# 格式化代码
ruff format .opencode/skills/academic-drafter/scripts/word_count.py
```

### 2.3 Bash脚本

项目包含一个备份脚本用于将output目录内容备份到former_results。

```bash
# 执行备份（交互式确认是否清空output）
./backup_output.sh

# 预览模式（不实际执行，仅显示将进行的操作）
./backup_output.sh --dry-run
```

**备份逻辑：**
- 命名规则：`YYYYMMDD_NNN`（如 `20260223_001`）
- 相似度检测：通过文件hash比对，若≥80%相同则追加到最新备份
- 追加策略：只复制新增文件，跳过已存在文件
- 清空确认：执行后询问是否清空output目录

### 2.4 运行单个测试

本项目**没有单元测试**。如需验证脚本功能，直接运行脚本并检查输出：

```bash
# 测试字数统计
echo "这是一个测试摘要。" > /tmp/test_abstract.txt
python .opencode/skills/academic-drafter/scripts/word_count.py /tmp/test_abstract.txt

# 测试备份脚本
./backup_output.sh --dry-run
```

---

## 3. 代码风格指南

### 3.1 Python脚本规范

适用于 `word_count.py`。如需修改或扩展，请遵循以下规范。

#### 3.1.1 通用规范

- **Python版本**：3.13
- **编码**：UTF-8
- **行长度**：默认Ruff配置（通常88字符）
- **行尾风格**：LF

#### 3.1.2 导入规范

```python
# 标准库 → 第三方库 → 本地模块
import re
import sys
from pathlib import Path

# 不允许：通配符导入 (from xxx import *)
```

#### 3.1.3 类型注解

- **必须**为所有函数参数和返回值提供类型注解
- 使用`typing`模块中的类型（如`Optional`、`List`、`Dict`）

```python
# 正确示例
def count_chinese_text(text: str) -> dict[str, int]:
    ...

def check_abstract_file(filepath: str) -> int | None:
    ...

# 不允许：无类型注解的函数
def count_chinese_text(text):  # 错误
    ...
```

#### 3.1.4 命名约定

- **函数/变量**：snake_case（如`count_chinese_text`、`abstract_stats`）
- **常量**：UPPER_SNAKE_CASE（如`LIMIT = 800`）
- **类名**（如有）：PascalCase
- **私有函数**：单下划线前缀（如`_internal_helper`）

#### 3.1.5 文档字符串

使用Google风格的docstring：

```python
def count_chinese_text(text: str) -> dict[str, int]:
    """
    统计中文学术文本的字数。

    规则：
    1. 中文字符（含标点）每个算1字
    2. 英文字母/数字连续序列算1字
    3. 空格不计入

    Args:
        text: 待统计的文本字符串

    Returns:
        包含各项统计数据的字典
    """
```

#### 3.1.6 错误处理

- 使用`Path.exists()`预检查文件是否存在
- 错误信息输出到`stderr`（使用`print(f"...", file=sys.stderr)`）
- 不使用裸`except:`，捕获具体异常类型

#### 3.1.7 格式化偏好

- 使用f-string进行字符串格式化
- 逗号后空格：`[1, 2, 3]`而非`[1,2,3]`
- 等号周围空格：`LIMIT = 800`而非`LIMIT=800`

### 3.2 Bash脚本规范

适用于 `backup_output.sh`。如需修改或扩展，请遵循以下规范。

#### 3.2.1 通用规范

- **Shell**：Bash (#!/bin/bash)
- **编码**：UTF-8
- **错误处理**：使用`set -e`在错误时退出

#### 3.2.2 检查工具

```bash
# 使用shellcheck检查脚本
shellcheck backup_output.sh
```

#### 3.2.3 语法偏好

- 使用`[[ ]]`而非`[ ]`进行条件测试
- 变量引用始终使用双引号：`"$VAR"`而非`$VAR`
- 使用`$()`而非反引号进行命令替换
- 使用`read -r`避免反斜杠转义

```bash
# 正确示例
if [[ -f "$filepath" ]]; then
    content=$(cat "$filepath")
fi

# 不推荐
if [ -f $filepath ]; then
    content=`cat $filepath`
fi
```

#### 3.2.4 命名约定

- **变量**：UPPER_SNAKE_CASE（如`OUTPUT_DIR`、`BACKUP_DIR`）
- **函数**：snake_case（如`calculate_similarity`）
- **局部变量**：使用`local`声明

#### 3.2.5 输出规范

- 错误信息输出到stderr：`echo "错误信息" >&2`
- 用户交互使用`read -p "提示: "`
- 状态信息使用统一前缀（如`===`分隔章节）

#### 3.2.6 安全规范

- 使用`${VAR:?}`防止空变量导致的危险操作
- 使用`rm -rf "${DIR:?}"/*`而非`rm -rf $DIR/*`
- 敏感操作前进行确认

---

## 4. 学术写作工作流

本项目的核心功能通过opencode skills实现，而非传统代码。

### 4.1 Skills加载顺序

当用户请求学术论文写作时，按以下顺序加载skills：

1. **cfp-analyzer** - 解析征稿启事，提取形式要求与主题偏好
2. **academic-writer-persona** - 激活执笔者人格底座
3. **academic-drafter** - 执行正文写作与校对
4. **rewrite-summarize** - 文本总结与重写（可选）

### 4.2 典型工作流程

```
备份产出 → ./backup_output.sh
    ↓
用户上传文件 → 检查 ./references/ → 确认文件对应关系
    ↓
cfp-analyzer执行 → 01_技术规格书.md（步骤一）
    ↓
素材结构化 → 02_结构化素材库.md（步骤二）
    ↓
文章结构设计 → 03_写作方案.md（步骤三）
    ↓
academic-drafter执行 → 04_语言风格校准书.md（步骤四）
    ↓
分节写作 → 05_初稿.md（步骤五）
    ↓
批判性回读与理论深化（委托subagent） → 06_问题清单.md, 06_修改稿.md（步骤六）
    ↓
形式规范校对（委托subagent） → 07_格式检查报告.md, 07_修改稿.md（步骤七）
    ↓
最终扫描与定稿（委托subagent） → 08_最终稿.md（步骤八）
    ↓
进一步迭代（可选） → 09_迭代稿.md（步骤九）
```

### 4.3 文件输入规范

- **征稿启事**：放在`./references/`目录，文件名含`cfp`、`call`、`征稿`关键词
- **讨论记录**：放在`./references/`目录，文件名含`notes`、`discussion`、`记录`、`讨论`关键词
- **输出文件**：写入`./output/`目录
- **备份文件**：存储于`./former_results/`目录

### 4.4 禁用AI表达清单

在学术写作中，**禁止使用**以下AI典型表达：

- 过渡套话：「本文……」「研究表明」「不是……而是……」「值得注意的是」「需要指出的是」
- 空洞概念：「随着时代的发展」「这一问题具有重要意义」「引发了广泛的讨论」
- 机械结构：「首先……其次……最后……」不得超过一次

**替代策略**：用具体学术案例和文本细读代替抽象概括；保留语言停顿和思考痕迹。

---

## 5. 注意事项

- **不要创建新的编程代码**：本项目不是软件工程环境
- **不要修改skills**：除非用户明确要求，否则不要修改skill定义文件
- **尊重用户隐私**：不要将用户的论文内容、讨论记录上传或分享
- **输出目录**：所有生成文件写入`./output/`而非项目根目录
- **询问备份**：计划阶段，如果`./output/`目录已有文件，询问用户是否执行`./backup_output.sh`备份到`./former_results/`
