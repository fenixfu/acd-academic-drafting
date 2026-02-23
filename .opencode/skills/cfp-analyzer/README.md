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

## 文件结构

```
skills/
├── academic-writer-persona/
│   └── SKILL.md                       ← 执笔者五重人格定义
│	└── README.md                      
├── cfp-analyzer/
│   └── SKILL.md                       ← 征稿解析 + 讨论整理 + 结构设计
│	└── README.md                      ← 本文件
└── academic-drafter/
    └── SKILL.md                       ← 语言校准 + 写作 + 校对 + 定稿
	└── README.md                      
    └── scripts/
    	└── word_count.py              ← 字数统计脚本
```
