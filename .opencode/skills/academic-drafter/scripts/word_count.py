#!/usr/bin/env python3
"""
字数统计程序 - 用于核验中文学术摘要字数
目标：博雅2026CFP投稿摘要（800字上限）
"""

import re
import sys
from pathlib import Path


def count_chinese_text(text):
    """
    统计中文学术文本的字数

    规则：
    1. 中文字符（含标点）每个算1字
    2. 英文字母/数字连续序列算1字（如"Vanguard"算1字，"2026"算1字）
    3. 空格不计入
    4. 参考文献按实际字符数计算

    返回：总字数
    """
    # 移除多余空格
    text = text.strip()

    # 统计中文字符（含标点）
    chinese_chars = len(re.findall(r"[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]", text))

    # 统计英文单词（连续字母/数字序列算作1个单位）
    english_words = len(re.findall(r"[a-zA-Z0-9]+", text))

    # 统计其他符号（如括号、破折号等）
    other_symbols = len(
        re.findall(r"[^\u4e00-\u9fff\u3000-\u303f\uff00-\uffef\sa-zA-Z0-9]", text)
    )

    total = chinese_chars + english_words + other_symbols

    return {
        "total": total,
        "chinese_chars": chinese_chars,
        "english_words": english_words,
        "other_symbols": other_symbols,
    }


def check_abstract_file(filepath):
    """检查摘要文件的字数"""
    path = Path(filepath)
    if not path.exists():
        print(f"❌ 文件不存在: {filepath}")
        return

    content = path.read_text(encoding="utf-8")

    # 移除markdown标题等元数据，只统计正文
    lines = content.split("\n")

    # 查找摘要正文开始位置（通常是第一个非空行且不包含"#"）
    abstract_start = 0
    for i, line in enumerate(lines):
        if (
            line.strip()
            and not line.startswith("#")
            and not line.startswith(">")
            and not line.startswith("-")
        ):
            abstract_start = i
            break

    # 查找参考文献开始位置
    ref_start = len(lines)
    for i, line in enumerate(lines):
        if (
            "参考文献" in line
            or "References" in line
            or line.strip().startswith("1. ")
            or line.strip().startswith("1.")
        ):
            if i > abstract_start + 5:  # 确保不是正文中的编号
                ref_start = i
                break

    # 提取正文（不含参考文献）
    abstract_lines = lines[abstract_start:ref_start]
    abstract_text = "\n".join(abstract_lines)

    # 统计
    abstract_stats = count_chinese_text(abstract_text)
    full_stats = count_chinese_text(content)

    print(f"\n{'=' * 60}")
    print(f"📄 文件: {filepath}")
    print(f"{'=' * 60}")
    print("\n摘要正文统计（不含参考文献）:")
    print(f"  中文字符: {abstract_stats['chinese_chars']} 字")
    print(f"  英文单词: {abstract_stats['english_words']} 个")
    print(f"  其他符号: {abstract_stats['other_symbols']} 个")
    print("  ─────────────────")
    print(f"  总计: {abstract_stats['total']} 字")

    # 检查是否超标
    LIMIT = 800
    if abstract_stats["total"] <= LIMIT:
        print(f"  ✅ 符合要求（上限 {LIMIT} 字）")
        print(f"     剩余额度: {LIMIT - abstract_stats['total']} 字")
    else:
        print(f"  ❌ 超出限制（上限 {LIMIT} 字）")
        print(f"     超出: {abstract_stats['total'] - LIMIT} 字")

    print("\n完整文件统计（含标题、参考文献）:")
    print(f"  总计: {full_stats['total']} 字")

    return abstract_stats["total"]


def main():
    """主函数"""
    print("📝 中文学术摘要字数统计工具")
    print("=" * 60)
    print("目标上限: 800 字（博雅2026CFP要求）")
    print("Token 预算: 600 tokens（保守估计）")
    print("=" * 60)

    if len(sys.argv) > 1:
        # 检查指定文件
        for filepath in sys.argv[1:]:
            check_abstract_file(filepath)
    else:
        # 检查默认位置
        default_files = [
            "/home/fenix/projects/drafting1/output/博雅2026_摘要_定稿.md",
            "/home/fenix/projects/drafting1/output/05_摘要_初稿.md",
            "/home/fenix/projects/drafting1/output/05_摘要.md",
        ]

        found = False
        for filepath in default_files:
            if Path(filepath).exists():
                check_abstract_file(filepath)
                found = True
                break

        if not found:
            print("\n⚠️ 未找到摘要文件")
            print("请提供文件路径: python3 word_count.py <文件路径>")


if __name__ == "__main__":
    main()
