# 学术写作 Skill 套件

## 三个 Skill 的关系

原始的八步提示词系统按**关注点**拆分为三个独立但协同的 skill：

```
academic-writer-persona   ←── 人格底座（始终激活）
        ↓
cfp-analyzer              ←── 写前准备（步骤1-3）
        ↓
academic-drafter          ←── 写作执行（步骤4-8）
```

---

## 拆分逻辑

| Skill | 原始步骤 | 关注层 | 可独立调用？ |
|-------|---------|--------|------------|
| `academic-writer-persona` | 人格说明（前置） | 风格价值观 | ✓ 可作为润色/修改的底座 |
| `cfp-analyzer` | 步骤1 + 2 + 3 | 写前智识准备 | ✓ 单独用于分析征稿/整理讨论 |
| `academic-drafter` | 步骤4 + 5 + 6 + 7 + 8 | 写作执行 | ✓ 有提纲时可直接进入 |

---

## 典型调用场景

**场景A：从零开始投稿**
```
加载 academic-writer-persona
→ cfp-analyzer（粘贴征稿启事 + 讨论记录）
→ academic-drafter（分节写作直到定稿）
```

**场景B：已有提纲，直接写作**
```
加载 academic-writer-persona
→ 跳过 cfp-analyzer，直接进入 academic-drafter 步骤五
```

**场景C：润色已有初稿**
```
加载 academic-writer-persona
→ academic-drafter 步骤六（批判性回读）
→ academic-drafter 步骤七（形式校对）
→ academic-drafter 步骤八（AI痕迹扫描）
```

**场景D：只分析征稿启事，暂不写作**
```
cfp-analyzer 步骤一（单独使用，输出技术规格书）
```

---

## 文件结构

```
skills/
├── academic-writer-persona/
│   └── SKILL.md                       ← 执笔者五重人格定义
│	└── README.md                      ← 本文件
├── cfp-analyzer/
│   └── SKILL.md                       ← 征稿解析 + 讨论整理 + 结构设计
└── academic-drafter/
    └── SKILL.md                       ← 语言校准 + 写作 + 校对 + 定稿
	└── README.md
    └── scripts/
    	└── word_count.py              ← 字数统计脚本
```
