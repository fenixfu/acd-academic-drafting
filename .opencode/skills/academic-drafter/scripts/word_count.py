# utf-8
#!/usr/bin/env python3
"""
字数统计程序 - 用于核验中文学术文本字数

计数规则：
  - 中文字符（含标点）: 每个计 1 字
  - 英文单词（连续字母序列）: 每个计 2 字（等效换算）
  - 数字字符: 每位计 1 字
  - 标点符号等其他字符: 不计入
  - 空格不计入

分区逻辑：
  - 正文：从第一个非元数据行起，到参考文献节前
  - 参考文献：以 "参考文献"、"References"、"Bibliography" 标题行或
    连续编号列表（"[1]" / "1."）开头的区段
  - 分别统计后给出合计总和

用法示例：
  python word_count.py [文件路径 ...]          # 统计一个或多个文件
  python word_count.py --text "文本内容"        # 直接统计文本串（不分区，整体计数）
  python word_count.py --limit 1500 论文.md     # 指定字数上限（默认 800）
  python word_count.py 摘要.md 正文.md               # 同时统计多个文件
  python word_count.py --limit 500 --text "$(cat 摘要.md)"  # 管道传入文本
"""

import argparse
import re
import sys
from pathlib import Path

# ── 计数配置 ─────────────────────────────────────────
ENGLISH_WORD_EQUIV = 2   # 1 英文单词等效 N 字
DEFAULT_WORD_LIMIT = 800 # 默认字数上限


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
        digit_chars, total
    """
    text = strip_markdown(text)

    chinese_chars = len(re.findall(
        r"[\u4e00-\u9fff]", text
    ))
    # 英文单词：仅匹配连续字母序列（不含数字）
    english_words = len(re.findall(r"[a-zA-Z]+", text))
    # 数字字符：每位单独计 1 字
    digit_chars = len(re.findall(r"[0-9]", text))
    # 标点符号等其他字符不计入

    english_equiv = english_words * ENGLISH_WORD_EQUIV
    total = chinese_chars + english_equiv + digit_chars

    return {
        "chinese_chars": chinese_chars,
        "english_words": english_words,
        "english_equiv": english_equiv,
        "digit_chars": digit_chars,
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
def fmt_stats(stats: dict, label: str, limit: int | None = None, tolerance: float = 5.0, boundary: str = "hard") -> None:
    print(f"\n  【{label}】")
    print(f"    中文字符  : {stats['chinese_chars']} 字")
    print(f"    英文单词  : {stats['english_words']} 词 × {ENGLISH_WORD_EQUIV} = {stats['english_equiv']} 字（等效）")
    print(f"    数字字符  : {stats['digit_chars']} 位 × 1 = {stats['digit_chars']} 字")
    print( "    ─────────────────────────────")
    print(f"    小计      : {stats['total']} 字")
    if limit is not None:
        if boundary == "hard":
            min_limit = limit * (100 - 2 * tolerance) / 100.0
            max_limit = float(limit)
        else: # soft boundary
            min_limit = limit * (100 - tolerance) / 100.0
            max_limit = limit * (100 + tolerance) / 100.0
            
        if stats["total"] < min_limit:
            missing = min_limit - stats["total"]
            print(f"    ❌ 字数不足（严重浪费），要求下限 {min_limit:.1f} 字，当前缺少 {missing:.1f} 字")
        elif stats["total"] > max_limit:
            excess = stats["total"] - max_limit
            print(f"    ❌ 超出字数上限 {max_limit:.1f} 字，超出 {excess:.1f} 字")
        else:
            print(f"    ✅ 符合字数限制（范围 [{min_limit:.1f}, {max_limit:.1f}] 字）")
            


def check_file(filepath: str, limit: int = DEFAULT_WORD_LIMIT, tolerance: float = 5.0, boundary: str = "hard") -> int:
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

    fmt_stats(body_stats, "正文")
    fmt_stats(ref_stats,  "参考文献")
    print(f"\n  【正文+参考文献】")
    print(f"    总计      : {combined_total} 字")
    
    if boundary == "hard":
        min_limit = limit * (100 - 2 * tolerance) / 100.0
        max_limit = float(limit)
    else: # soft boundary
        min_limit = limit * (100 - tolerance) / 100.0
        max_limit = limit * (100 + tolerance) / 100.0

    if combined_total < min_limit:
        missing = min_limit - combined_total
        print(f"    ❌ 字数不足（严重浪费），要求下限 {min_limit:.1f} 字，当前总计缺少 {missing:.1f} 字")
    elif combined_total > max_limit:
        excess = combined_total - max_limit
        print(f"    ❌ 超出字数上限 {max_limit:.1f} 字，当前总计超出 {excess:.1f} 字")
    else:
        print(f"    ✅ 符合字数限制（范围 [{min_limit:.1f}, {max_limit:.1f}] 字）")

    print(f"{'=' * 60}")

    return combined_total


def check_text(text: str, limit: int = DEFAULT_WORD_LIMIT, tolerance: float = 5.0, boundary: str = "hard") -> int:
    """直接统计文本串（不分区），返回字数。"""
    stats = count_text(text)

    print(f"\n{'=' * 60}")
    print(f"📝 文本串统计（不分正文/参考文献区）")
    print(f"{'=' * 60}")
    fmt_stats(stats, "全文", limit, tolerance, boundary)
    print(f"{'=' * 60}")

    return stats["total"]


# ── 入口 ─────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="学术文本字数统计工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python word_count.py 论文.md                      # 统计文件，默认上限 800
  python word_count.py --limit 1500 论文.md          # 指定上限 1500
  python word_count.py 摘要.md 正文.md               # 同时统计多个文件
  python word_count.py --text "这是一段需要统计的文本"  # 直接统计文本串
  python word_count.py --limit 500 --text "$(cat 摘要.md)"  # 管道传入文本
        """,
    )
    parser.add_argument(
        "files",
        nargs="*",
        metavar="文件路径",
        help="要统计的文件（可多个）",
    )
    parser.add_argument(
        "--text", "-t",
        metavar="文本内容",
        help="直接传入文本串进行统计（不分正文/参考文献区）",
    )
    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=DEFAULT_WORD_LIMIT,
        metavar="字数上限",
        help=f"字数上限（默认 {DEFAULT_WORD_LIMIT}）",
    )
    parser.add_argument(
        "--tolerance", "-x",
        type=float,
        default=5.0,
        metavar="宽容区间",
        help="宽容区间百分比 (默认 5.0)",
    )
    parser.add_argument(
        "--boundary", "-b",
        choices=["hard", "soft"],
        default="hard",
        metavar="边界类型",
        help="边界计算方式 (hard/soft，默认 hard)",
    )

    args = parser.parse_args()

    print("📝 学术文本字数统计工具")
    print("=" * 60)
    print(f"计数规则：英文单词 × {ENGLISH_WORD_EQUIV}，中文字符 × 1，数字字符 × 1，标点等符号不计")
    
    if args.boundary == 'hard':
        print(f"字数限制：{args.limit} 字 (边界类型: 硬边界，宽容度 {args.tolerance}%)")
    else:
        print(f"字数限制：{args.limit} 字 (边界类型: 软边界，宽容度 {args.tolerance}%)")
    print("=" * 60)

    # --text 模式：直接统计文本串
    if args.text is not None:
        if args.files:
            print("⚠️  同时指定了 --text 和文件路径，仅统计 --text 内容，忽略文件路径。")
        check_text(args.text, limit=args.limit, tolerance=args.tolerance, boundary=args.boundary)
        return

    # 文件模式
    if args.files:
        for filepath in args.files:
            check_file(filepath, limit=args.limit, tolerance=args.tolerance, boundary=args.boundary)
        return

    # 无参数：尝试自动定位最新文件
    try:
        project_root = Path(__file__).resolve().parents[4]
        candidates = list(project_root.glob("output/*.md"))

        if not candidates:
            print("\n⚠️ 未找到文件，请指定路径:")
            print("  python word_count.py <文件路径>")
            print("  python word_count.py --text '文本内容'")
            return

        target = max(candidates, key=lambda p: p.stat().st_mtime)
        print(f"\n自动选取最新文件: {target}")
        check_file(str(target), limit=args.limit, tolerance=args.tolerance, boundary=args.boundary)
    except IndexError:
        print("\n⚠️ 无法自动定位项目根目录 (parents[4] 越界)。")
        print("请直接提供文件路径: python word_count.py <文件路径>")


if __name__ == "__main__":
    main()
