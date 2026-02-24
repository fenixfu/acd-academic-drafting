# utf-8
#!/usr/bin/env python3
"""
字数统计程序 - 用于核验中文学术文本字数

计数规则：
  - 中文字符（含标点）: 每个计 1 字
  - 英文单词（连续字母/数字序列）: 每个计 2 字（等效换算）
  - 其他符号（括号、破折号等非上述字符）: 每个计 1 字
  - 空格不计入

分区逻辑：
  - 正文：从第一个非元数据行起，到参考文献节前
  - 参考文献：以 "参考文献"、"References"、"Bibliography" 标题行或
    连续编号列表（"[1]" / "1."）开头的区段
  - 分别统计后给出合计总和
"""

import re
import sys
from pathlib import Path

# ── 计数配置 ─────────────────────────────────────────
ENGLISH_WORD_EQUIV = 2   # 1 英文单词等效 N 字
WORD_LIMIT = 800         # 默认字数上限（正文）


def strip_markdown(text: str) -> str:
    """移除 markdown 格式标记，保留纯文本内容。"""
    # 标题标记 (# ## ### 等行首井号)
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    # 粗体/斜体标记 (** * __ _)
    text = re.sub(r"\*{1,3}|_{1,3}", "", text)
    # 删除线 ~~
    text = re.sub(r"~~", "", text)
    # 行内代码 `
    text = re.sub(r"`", "", text)
    # 引用标记 >
    text = re.sub(r"^>\s*", "", text, flags=re.MULTILINE)
    # 无序列表标记 (- * + 行首)
    text = re.sub(r"^[\-\*\+]\s+", "", text, flags=re.MULTILINE)
    # 链接 [text](url) → text
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    # 图片 ![alt](url) → 移除
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", "", text)
    # 水平线 --- ***
    text = re.sub(r"^[-*_]{3,}\s*$", "", text, flags=re.MULTILINE)
    return text


def count_text(text: str) -> dict:
    """
    统计一段文本的等效字数。
    自动剥离 markdown 格式标记后再计数。

    Returns dict with keys:
        chinese_chars, english_words, english_equiv,
        other_symbols, total
    """
    text = strip_markdown(text)

    chinese_chars = len(re.findall(
        r"[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]", text
    ))
    english_words = len(re.findall(r"[a-zA-Z0-9]+", text))
    other_symbols = len(re.findall(
        r"[^\u4e00-\u9fff\u3000-\u303f\uff00-\uffef\sa-zA-Z0-9]", text
    ))

    english_equiv = english_words * ENGLISH_WORD_EQUIV
    total = chinese_chars + english_equiv + other_symbols

    return {
        "chinese_chars": chinese_chars,
        "english_words": english_words,
        "english_equiv": english_equiv,
        "other_symbols": other_symbols,
        "total": total,
    }


# ── Markdown 分区提取 ─────────────────────────────────
_REF_HEADING_RE = re.compile(
    r"^#{1,6}\s*(参考文献|References|Bibliography)\s*$",
    re.IGNORECASE,
)
_REF_INLINE_RE = re.compile(
    r"^[\*\[\【\(\（\{\<]*?(参考文献|References|Bibliography)\S*?\s*$",
    re.IGNORECASE,
)
# 连续编号列表首行：[1] 或 1.
_REF_NUMBERED_RE = re.compile(r"^\[1\]|^1\.\s")

# 元数据行（标题行、blockquote、yaml fence 等，排除正文起始点之后的标题）
_META_RE = re.compile(r"^(#|>|---|```|<!--)")


def split_sections(content: str):
    """
    将 markdown 内容拆分为 (正文文本, 参考文献文本)。

    逻辑：
    1. 跳过文件开头的元数据行（#、>、--- 等）
    2. 遇到参考文献节标识时切换到参考文献区
    3. 返回两段纯文本
    """
    lines = content.splitlines()

    body_lines = []
    ref_lines = []
    in_ref = False
    body_started = False

    for line in lines:
        stripped = line.strip()

        # 检测参考文献节开始
        if not in_ref and (
            _REF_HEADING_RE.match(stripped)
            or _REF_INLINE_RE.match(stripped)
        ):
            in_ref = True
            ref_lines.append(line)
            continue

        if in_ref:
            ref_lines.append(line)
            continue

        # 正文尚未开始时跳过元数据行
        if not body_started:
            if stripped and not _META_RE.match(stripped):
                body_started = True
            else:
                continue  # 跳过元数据

        # 正文中出现编号列表首行，且已有足够正文，视为参考文献开始
        if body_started and _REF_NUMBERED_RE.match(stripped):
            # 只有在正文已有内容时才切换（避免误判正文内编号）
            if len(body_lines) > 5:
                in_ref = True
                ref_lines.append(line)
                continue

        body_lines.append(line)

    return "\n".join(body_lines), "\n".join(ref_lines)


# ── 显示辅助 ─────────────────────────────────────────
def fmt_stats(stats: dict, label: str, limit: int | None = None) -> None:
    print(f"\n  【{label}】")
    print(f"    中文字符  : {stats['chinese_chars']} 字")
    print(f"    英文单词  : {stats['english_words']} 词 × {ENGLISH_WORD_EQUIV} = {stats['english_equiv']} 字（等效）")
    print(f"    其他符号  : {stats['other_symbols']} 个")
    print( "    ─────────────────────────────")
    print(f"    小计      : {stats['total']} 字")
    if limit is not None:
        remaining = limit - stats["total"]
        if remaining >= 0:
            print(f"    ✅ 符合上限 {limit} 字，剩余 {remaining} 字")
        else:
            print(f"    ❌ 超出上限 {limit} 字，超出 {-remaining} 字")


def check_file(filepath: str, limit: int = WORD_LIMIT) -> int:
    """检查文件，分别统计正文与参考文献，返回合计字数。"""
    path = Path(filepath)
    if not path.exists():
        print(f"❌ 文件不存在: {filepath}")
        return 0

    content = path.read_text(encoding="utf-8")
    body_text, ref_text = split_sections(content)

    body_stats = count_text(body_text)
    ref_stats = count_text(ref_text)
    combined_total = body_stats["total"] + ref_stats["total"]

    print(f"\n{'=' * 60}")
    print(f"📄 文件: {filepath}")
    print(f"{'=' * 60}")

    fmt_stats(body_stats, "正文（不含参考文献）", limit=limit)
    fmt_stats(ref_stats,  "参考文献")

    print(f"\n  合计（正文 + 参考文献）: {combined_total} 字")
    print(f"{'=' * 60}")

    return combined_total


# ── 入口 ─────────────────────────────────────────────
def main():
    print("📝 学术文本字数统计工具")
    print("=" * 60)
    print(f"计数规则：英文单词 × {ENGLISH_WORD_EQUIV}，中文字符 × 1，符号 × 1")
    print(f"默认正文上限：{WORD_LIMIT} 字")
    print("=" * 60)

    if len(sys.argv) > 1:
        # [修复] 改用 range 索引遍历，避免静态类型检查器对 list 切片(sys.argv[1:])报错
        for i in range(1, len(sys.argv)):
            check_file(sys.argv[i])
    else:
        # 默认查找输出目录下的摘要文件
        # 注意：这里假设脚本位于项目深层目录，如果层级不足 parents[4] 可能会越界
        try:
            project_root = Path(__file__).resolve().parents[4]  # 4 级向上到项目根
            candidates = list(project_root.glob("output/*.md"))
            
            if not candidates:
                print("\n⚠️ 未找到文件，请指定路径:")
                print("  python word_count.py <文件路径>")
                return
            
            # 取最新修改的文件
            target = max(candidates, key=lambda p: p.stat().st_mtime)
            print(f"\n自动选取最新文件: {target}")
            check_file(str(target))
        except IndexError:
            print("\n⚠️ 无法自动定位项目根目录 (parents[4] 越界)。")
            print("请直接提供文件路径: python word_count.py <文件路径>")


if __name__ == "__main__":
    main()
