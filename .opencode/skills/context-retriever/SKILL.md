---
name: context-retriever
description: >
  【Subagent 专用】接受主 agent 的条目检索请求：根据条目名称，在指定 markdown 文件的标题层级中定位并提取完整内容块，同时根据项目整体结构推断并附加最相关的关联条目标题列表，返回给主 agent 使用。
  适用场景：主 agent 需要按需读取项目流程文档、参考材料、规范手册中某一具体章节时，调用本 subagent 而非自行全文扫描。
---

# Context Retriever — Subagent 操作手册

> 本 skill 仅供 subagent 使用。收到主 agent 的调用后，严格按照以下流程执行，**不与用户交互**，将结果结构化返回给主 agent。

---

## 输入规格

主 agent 调用时须提供：

| 字段 | 必填 | 说明 |
|------|------|------|
| `target_entry` | ✅ | 要检索的条目名称（可以是标题全文或关键词） |
| `file_paths` | ✅ | 一个或多个待检索的 markdown 文件路径列表 |
| `context_hint` | ❌ | 可选。主 agent 当前任务的简要描述，用于辅助相关性判断 |

---

## 执行流程

### Step 1 · 读取文件结构

对 `file_paths` 中的条目：

1. 使用 `view` （或 `read_file`）工具读取文件全文
2. 提取所有 markdown 标题行（`#` / `##` / `###` 等），记录：
   - 标题层级（H1/H2/H3…）
   - 标题文本
   - 对应的行号

构建出该文件的**标题目录树**（outline），用于后续定位和相关性判断。
如果读取结果并非markdown格式，直接跳至 Step 4，在输出的 `retrieval_notes` 中注明：[该文档不在上下文寻回范围内]。

### Step 2 · 定位目标条目

在**标题目录树**中用以下策略匹配 `target_entry`：

1. **精确匹配**：标题文本完全等于 `target_entry`（忽略前后空白和大小写）
2. **包含匹配**：标题文本包含 `target_entry` 的全部关键词
3. **模糊匹配**：关键词部分重叠（取得分最高者）

若多个文件均有匹配，优先返回匹配度最高的那个；若平局，全部返回。

若**无任何匹配**，直接跳至 Step 4，在输出的 `retrieval_notes` 中注明：[条目未在文件中找到]。

### Step 3 · 提取完整内容块

定位到目标标题的行号后：

- **内容起点**：目标标题行（含）
- **内容终点**：下一个**同级或更高级**标题行的前一行（不含），或文件末尾

用 `view` （或 `read_file`）工具的 `view_range` 参数精确读取该范围的文本，作为 `entry_content`。

> ⚠️ 不要截断，不要摘要，原文完整提取。

### Step 4 · 推断关联条目标题

根据主agent对当前任务的简报，筛选与主agent请求**最直接相关**的其他条目。可以考虑的维度包括：

| 维度 | 逻辑 |
|------|------|
| **语义关联** | 标题中出现与 `target_entry` 或 `context_hint` 相同/近义的关键词 |
| **流程顺序** | 搜索定位并查看项目中记录流程的文档（尤其是包含"步骤1→步骤2"这样流程顺序的文档），提取目标条目上下游的流程步骤名称 |

**判断维度优先级的原则**：
- 如果主agent正在执行流程中的某一步骤，优先考虑流程顺序维度
    - 最优先为其提供本步骤的注意事项和执行红线
    - 其次为其提供同层级的下一步骤的名称
- 如果主agent正在调取某一skill中的内容，优先考虑语义关联维度

筛选上限：**最多 3 个**关联条目标题，按相关性从高到低排序。

每条包含：
- 标题文本
- 所在文件路径
- 简短说明（≤15字）：说明在什么意义上相关

---



## 输出格式

以如下 JSON 结构返回，**不附加任何额外解释文字**：

```json
{
  "status": "found | not_found | partial",
  "target_entry": "<主 agent 请求的条目名>",
  "matched_heading": "<实际匹配到的标题全文>",
  "source_file": "<文件路径>",
  "entry_content": "<完整原文内容块，保留 markdown 格式>",
  "related_headings": [
    {
      "heading": "<关联条目标题>",
      "source_file": "<所在文件>",
      "relevance_note": "<相关原因，≤15字>"
    }
  ],
  "retrieval_notes": "<可选：匹配过程中的异常、歧义或降级说明>"
}
```

**status 说明：**
- `found`：精确或高置信度匹配，内容完整提取
- `partial`：模糊匹配成功但置信度较低，或内容块边界有歧义
- `not_found`：无任何匹配，`entry_content` 为空字符串，`related_headings` 仍可提供

---

## 边界处理

| 情况 | 处理方式 |
|------|----------|
| 目标条目内容极长（>300行） | 完整提取，在 `retrieval_notes` 中注明行数 |
| 同名标题出现在多处 | 全部提取，以数组形式放入 `entry_content`（结构调整：改为列表） |
| 文件无法读取 | `status: not_found`，在 `retrieval_notes` 中说明原因 |
| `file_paths` 为空 | 立即返回错误，提示主 agent 补充文件路径 |
| 标题嵌套超过4层 | 按实际层级处理，不做特殊限制 |

---

## 典型调用示例

**主 agent 请求：**

```
target_entry: "错误码处理"
file_paths: ["/project/docs/api-reference.md", "/project/docs/workflow.md"]
context_hint: "正在实现支付模块的异常分支"
```

**本 subagent 返回（示意）：**

```json
{
  "status": "found",
  "target_entry": "错误码处理",
  "matched_heading": "## 错误码处理",
  "source_file": "/project/docs/api-reference.md",
  "entry_content": "## 错误码处理\n\n...(原文)...",
  "related_headings": [
    {
      "heading": "### 支付接口错误码列表",
      "source_file": "/project/docs/api-reference.md",
      "relevance_note": "支付场景专属错误码定义"
    },
    {
      "heading": "## 异常分支流程图",
      "source_file": "/project/docs/workflow.md",
      "relevance_note": "与错误处理直接关联的流程节点"
    }
  ],
  "retrieval_notes": ""
}
```