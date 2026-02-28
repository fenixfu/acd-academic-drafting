#!/usr/bin/env python3
"""
中英文混排标点检测与修正工具
Bilingual Punctuation Checker for Chinese-English Mixed Text
"""

import io
import re
import sys
import argparse
from dataclasses import dataclass, field
from typing import Optional

# ── UTF-8 输出保障（主要针对 Windows）────────────────────────────────────────
# Windows 终端默认编码为 GBK/CP936，print 含中文标点或 emoji 时会抛出
# UnicodeEncodeError。此处将 stdout/stderr 统一重新包装为 UTF-8。
# errors='replace'：即使终端不支持某字符，输出替换符而非崩溃。
# hasattr 检查：在某些特殊环境（如 pytest capsys）中 buffer 属性不存在，跳过包装。
def _force_utf8(stream):
    if hasattr(stream, 'buffer'):
        enc = getattr(stream, 'encoding', '') or ''
        if enc.lower().replace('-', '') != 'utf8':
            return io.TextIOWrapper(
                stream.buffer, encoding='utf-8', errors='replace', line_buffering=True
            )
    return stream

sys.stdout = _force_utf8(sys.stdout)
sys.stderr = _force_utf8(sys.stderr)


# ─── 标点映射表 ────────────────────────────────────────────────────────────────

ZH_TO_EN = {
    '，': ',', '。': '.', '：': ':', '；': ';',
    '？': '?', '！': '!', '（': '(', '）': ')',
    '"': '"', '"': '"', ''': "'", ''': "'",
}
EN_TO_ZH = {v: k for k, v in ZH_TO_EN.items()}
# 引号单独处理
EN_TO_ZH_QUOTES = {'"': '\u201c', '"': '\u201d'}  # straight to curly handled separately

# 全角/半角括号
FULL_BRACKETS = ('（', '）')
HALF_BRACKETS = ('(', ')')

# 中文字符范围
CJK_PATTERN = re.compile(r'[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]')
# 英文字符
EN_PATTERN = re.compile(r'[a-zA-Z]')

# 所有需要检测的标点（全角+半角）
PUNCTUATION_MAP = {
    # 逗号
    '，': ('zh', ','),
    ',':  ('en', '，'),
    # 句号
    '。': ('zh', '.'),
    # 半角句点：英文句末 or 缩写，不能无脑改为 。，需要上下文判断
    # 冒号
    '：': ('zh', ':'),
    ':':  ('en', '：'),
    # 分号
    '；': ('zh', ';'),
    ';':  ('en', '；'),
    # 问号
    '？': ('zh', '?'),
    '?':  ('en', '？'),
    # 叹号
    '！': ('zh', '!'),
    '!':  ('en', '！'),
    # 括号 —— 单独处理
}


# ─── 数据结构 ──────────────────────────────────────────────────────────────────

@dataclass
class Issue:
    line_no: int
    col_no: int
    char: str
    suggestion: str
    context: str
    reason: str
    section: str = 'body'  # 'body' | 'refs'
    is_warning: bool = False  # True = 需要人工确认


@dataclass
class Config:
    refs_keyword: str = '参考文献'
    quote_strategy: str = 'A'   # A=中文行文统一中文引号; B=跟随内容语言
    output_mode: str = 'both'   # 'report' | 'fixed' | 'both'
    report_output: str = ''     # 若非空，将 Markdown 报告写入此路径


# ─── 语言判断工具 ──────────────────────────────────────────────────────────────

def zh_ratio(text: str) -> float:
    """返回文本中中文字符占（中文+英文）的比例"""
    zh = len(CJK_PATTERN.findall(text))
    en = len(EN_PATTERN.findall(text))
    total = zh + en
    return zh / total if total > 0 else 0.0


def dominant_lang(text: str) -> str:
    """返回 'zh' 或 'en'"""
    return 'zh' if zh_ratio(text) >= 0.5 else 'en'


def context_window(line: str, pos: int, window: int = 20) -> str:
    """提取标点附近的上下文"""
    start = max(0, pos - window)
    end = min(len(line), pos + window + 1)
    prefix = '…' if start > 0 else ''
    suffix = '…' if end < len(line) else ''
    marked = line[start:pos] + f'【{line[pos]}】' + line[pos+1:end]
    return prefix + marked + suffix


# ─── 参考文献处理 ──────────────────────────────────────────────────────────────

def detect_ref_author_lang(entry: str) -> Optional[str]:
    """
    检测参考文献条目的作者名语种。
    返回 'zh'、'en'，或 None（无法判断）。
    简单规则：
    - 条目开头若有汉字 → zh
    - 条目开头若是拉丁字母+逗号/句点格式 → en
    """
    stripped = entry.strip()
    if not stripped:
        return None
    first_char = stripped[0]
    if CJK_PATTERN.match(first_char):
        return 'zh'
    if EN_PATTERN.match(first_char):
        return 'en'
    return None


def detect_work_title_lang(entry: str) -> Optional[str]:
    """
    检测参考文献条目中著作名的语种。
    简单启发：寻找《》（中文书名号）或斜体标记，或连续英文单词串。
    """
    # 中文书名号
    if '《' in entry or '》' in entry:
        return 'zh'
    # 找到年份后的内容作为书名候选区域（常见格式：年份后跟书名）
    m = re.search(r'\(?\d{4}\)?\.\s*(.+)', entry)
    if m:
        title_region = m.group(1)
        lang = dominant_lang(title_region)
        return lang
    return None


def check_ref_entry(entry: str, line_no: int) -> list[Issue]:
    """检测单条参考文献条目的标点"""
    issues = []
    author_lang = detect_ref_author_lang(entry)
    title_lang = detect_work_title_lang(entry)

    # 语种不一致 → 报警
    if author_lang and title_lang and author_lang != title_lang:
        issues.append(Issue(
            line_no=line_no, col_no=0,
            char='?', suggestion='?',
            context=entry[:60],
            reason=f'作者名语种（{author_lang}）与著作名语种（{title_lang}）不一致，请人工确认',
            section='refs',
            is_warning=True
        ))
        return issues  # 不继续自动检测

    expected_lang = author_lang or 'en'

    SKIP_IN_CHAR_SCAN = set('()（）\'""\u201c\u201d\u2018\u2019')
    for i, ch in enumerate(entry):
        if ch in SKIP_IN_CHAR_SCAN:
            continue
        issue = check_single_punct_for_lang(ch, i, line_no, entry, expected_lang, section='refs')
        if issue:
            issues.append(issue)

    return issues


# ─── 单字符标点检测 ────────────────────────────────────────────────────────────

def check_single_punct_for_lang(
    ch: str, pos: int, line_no: int, line: str,
    expected_lang: str, section: str = 'body'
) -> Optional[Issue]:
    """
    给定预期语言，检测单个字符是否使用了错误标点。
    返回 Issue 或 None。
    """
    ctx = context_window(line, pos)

    if expected_lang == 'zh':
        # 期望中文标点，发现英文标点
        if ch in EN_TO_ZH:
            # 半角句点特殊处理：可能是英文缩写/数字小数点，不在此处理
            if ch == '.':
                return _check_period(ch, pos, line_no, line, 'zh', section)
            suggestion = EN_TO_ZH[ch]
            return Issue(line_no, pos, ch, suggestion, ctx,
                         f'中文语境中使用了英文标点 "{ch}"，建议改为 "{suggestion}"',
                         section)
    else:
        # 期望英文标点，发现中文标点
        if ch in ZH_TO_EN:
            suggestion = ZH_TO_EN[ch]
            return Issue(line_no, pos, ch, suggestion, ctx,
                         f'英文语境中使用了中文标点 "{ch}"，建议改为 "{suggestion}"',
                         section)
    return None


def _check_period(ch: str, pos: int, line_no: int, line: str,
                  expected_lang: str, section: str) -> Optional[Issue]:
    """
    句点（.）的专项处理：
    - 在中文语境中，句末的 . 应改为 。
    - 如果紧跟在数字后（小数点）或英文字母后（缩写），则保留
    """
    if expected_lang != 'zh':
        return None
    # 前一个字符
    prev = line[pos - 1] if pos > 0 else ''
    next_ = line[pos + 1] if pos + 1 < len(line) else ''
    # 数字编号或小数点：只要点号前面是数字即排除（匹配规则 (?<=\d)\.）
    # 覆盖 "1. "（列表编号）、"3.14"（小数点）、"1.1."（多级编号）等情况
    if prev.isdigit():
        return None
    # 英文缩写：前面是英文字母
    if EN_PATTERN.match(prev):
        return None
    # 其余情况：中文语境的句末句点 → 改为 。
    ctx = context_window(line, pos)
    return Issue(line_no, pos, '.', '。', ctx,
                 '中文语境句末使用了英文句点 "."，建议改为 "。"',
                 section)


# ─── 括号检测 ──────────────────────────────────────────────────────────────────

def find_bracket_pairs(line: str) -> list[tuple[int, int, str]]:
    """
    找到行内所有括号对，返回 [(open_pos, close_pos, content), ...]
    支持全角和半角括号。
    """
    pairs = []
    stack = []
    open_chars = {'(': ')', '（': '）'}
    close_to_open = {')': '(', '）': '（'}

    for i, ch in enumerate(line):
        if ch in open_chars:
            stack.append((i, ch))
        elif ch in close_to_open:
            if stack:
                open_pos, open_ch = stack.pop()
                content = line[open_pos + 1:i]
                pairs.append((open_pos, i, content, open_ch, ch))
    return pairs


def check_brackets(line: str, line_no: int, section: str = 'body') -> list[Issue]:
    """
    检测括号使用是否正确：
    - 括号内内容以英文字母开头且以英文字母/.结尾 → 半角
    - 否则 → 全角
    """
    issues = []
    pairs = find_bracket_pairs(line)

    for open_pos, close_pos, content, open_ch, close_ch in pairs:
        content_stripped = content.strip()
        # 判断括号内内容期望的括号类型
        should_be_half = (
            bool(EN_PATTERN.match(content_stripped[:1])) and
            bool(re.search(r'[a-zA-Z.\d]$', content_stripped))
        ) if content_stripped else False

        # 特殊：纯年份数字（如 1999, 2011）
        # 年份括号的全/半角取决于所在行的主导语言
        if re.match(r'^\d{4}$', content_stripped):
            # 需要行上下文来判断，此处传入 line 做语言判断
            line_lang = dominant_lang(line)
            should_be_half = (line_lang == 'en')

        expected_open = '(' if should_be_half else '（'
        expected_close = ')' if should_be_half else '）'

        if open_ch != expected_open:
            ctx = context_window(line, open_pos)
            issues.append(Issue(
                line_no, open_pos, open_ch, expected_open, ctx,
                f'括号内容{"为英文" if should_be_half else "为中文/年份"}，开括号应使用 "{expected_open}"',
                section
            ))
        if close_ch != expected_close:
            ctx = context_window(line, close_pos)
            issues.append(Issue(
                line_no, close_pos, close_ch, expected_close, ctx,
                f'括号内容{"为英文" if should_be_half else "为中文/年份"}，闭括号应使用 "{expected_close}"',
                section
            ))
    return issues


# ─── 引号检测：断句 + 栈配对 ──────────────────────────────────────────────────

# 所有引号字符（直引号 + 弯引号）
QUOTE_CHARS = set('"\'"\u201c\u201d\u2018\u2019')
STRAIGHT_DOUBLE = '"'
STRAIGHT_SINGLE = "'"
# 中文弯引号
ZH_DQUOTE_OPEN  = '\u201c'  # "
ZH_DQUOTE_CLOSE = '\u201d'  # "
ZH_SQUOTE_OPEN  = '\u2018'  # '
ZH_SQUOTE_CLOSE = '\u2019'  # '
# 英文弯引号（与中文相同字符，语义上按语境区分）




@dataclass
class QuotePair:
    """一对配对好的引号"""
    open_pos: int    # 在拼接字符串中的位置
    close_pos: int
    open_char: str
    close_char: str
    content: str     # 引号内的文字
    sentence_lang: str   # 所在句子的主导语言
    in_brackets: bool    # 是否位于括号内


@dataclass
class UnpairedQuote:
    """未配对的引号"""
    pos: int
    char: str
    is_open: bool   # True=多余开引号, False=多余闭引号
    line_no: int
    context: str


def _bracket_depth_at(text: str, pos: int) -> int:
    """计算 pos 处在当前段落中的括号嵌套深度（包括半角和全角括号）"""
    depth = 0
    # 找到 pos 所在段落的开头，避免跨段落的未闭合括号污染后续段落
    start = text.rfind('\n', 0, pos) + 1
    for i in range(start, pos):
        if text[i] in ('(', '（'):
            depth += 1
        elif text[i] in (')', '）'):
            depth = max(0, depth - 1)
    return depth


def pair_quotes_by_paragraph(
    full_text: str,
) -> tuple[list[QuotePair], list[UnpairedQuote]]:
    """
    以段落（换行符）为边界进行引号配对。

    每段流程：
    1. 扫描全段，将所有引号 (abs_pos, char) 依次收入 queue
    2. 段落结束后对 queue 执行 stack_b 配对流程
    3. 清空，进入下一段

    stack_b[n] 结构：
      zh_slot : (pos, char) | '^' | None
          None  = 尚未初始化
          '^'   = 段落首引号为英文，无中文开引号的占位符
          tuple = 真实中文开引号 (pos, char)
      en_stack: list of (pos, char)，至多暂存 2 个英文引号

    "满"状态：zh_slot 非 None 且 en_stack 已有 2 个元素。

    meta_stack: 嵌套栈，每个元素是一个 stack_b dict（已"暂停"等待恢复）。
    """
    pairs: list[QuotePair] = []
    unpaired: list[UnpairedQuote] = []

    display = full_text.replace('\n', '↵')

    def _warn(pos: int, ch: str, is_open: bool, reason: str = ''):
        ln = _pos_to_lineno_from_text(full_text, pos)
        ctx = context_window(display, pos)
        kind = ('未闭合的开引号' if is_open else '多余的闭引号')
        msg = f'{kind} "{ch}"' + (f'，{reason}' if reason else '') + '，请人工检查'
        unpaired.append(UnpairedQuote(pos=pos, char=ch, is_open=is_open,
                                      line_no=ln, context=ctx))

    def _new_stackb():
        return {'zh_slot': None, 'en_stack': []}

    def _process_queue(queue: list):
        """对一段的 queue 执行 stack_b / meta_stack 配对。"""
        meta_stack: list[dict] = []   # 已暂停的 stack_b
        cur: dict = _new_stackb()     # 当前活跃 stack_b

        def _push_meta():
            """将 cur 推入 meta_stack，重建一个新的 cur。"""
            nonlocal cur
            meta_stack.append(cur)
            cur = _new_stackb()

        def _pop_meta() -> dict | None:
            """从 meta_stack 弹出，恢复为 cur。"""
            nonlocal cur
            if meta_stack:
                cur = meta_stack.pop()
            else:
                cur = _new_stackb()
            return cur

        def _try_pair_en(new_pos: int, new_ch: str):
            """
            将新英文引号加入 cur['en_stack']，尝试配对。
            en_stack 达到 2 个时：
              - 若两者单双一致（均为 " 或均为 '）→ 配对，清空
              - 否则保持满状态；再来一个英文引号时强制弹出前两个再压入新的
            """
            en = cur['en_stack']
            if len(en) == 2:
                # 已满且未配对（单双不一致的情况）：强制弹出，压入新引号
                old0, old1 = en[0], en[1]
                cur['en_stack'] = [new_pos, new_ch] if False else []
                # 弹出旧的两个作为一对（不管单双，记录并报内容供 decide 处理）
                content = full_text[old0[0] + 1: old1[0]]
                in_brk = _bracket_depth_at(full_text, old0[0]) > 0
                pairs.append(QuotePair(
                    open_pos=old0[0], close_pos=old1[0],
                    open_char=old0[1], close_char=old1[1],
                    content=content,
                    sentence_lang=dominant_lang(content) if content.strip() else 'zh',
                    in_brackets=in_brk,
                ))
                cur['en_stack'] = [(new_pos, new_ch)]
            else:
                en.append((new_pos, new_ch))
                if len(en) == 2:
                    # 检查单双是否一致
                    c0, c1 = en[0][1], en[1][1]
                    same_type = (
                        (c0 in (STRAIGHT_DOUBLE,) and c1 in (STRAIGHT_DOUBLE,)) or
                        (c0 in (STRAIGHT_SINGLE,) and c1 in (STRAIGHT_SINGLE,))
                    )
                    if same_type:
                        # 配对成功，清空
                        p0, p1 = en[0], en[1]
                        content = full_text[p0[0] + 1: p1[0]]
                        in_brk = _bracket_depth_at(full_text, p0[0]) > 0
                        pairs.append(QuotePair(
                            open_pos=p0[0], close_pos=p1[0],
                            open_char=p0[1], close_char=p1[1],
                            content=content,
                            sentence_lang=dominant_lang(content) if content.strip() else 'en',
                            in_brackets=in_brk,
                        ))
                        cur['en_stack'] = []
                    # else: 保持满状态，等待下一个英文引号

        for abs_pos, ch in queue:
            in_brk = _bracket_depth_at(full_text, abs_pos) > 0
            is_known_open  = ch in (ZH_DQUOTE_OPEN,  ZH_SQUOTE_OPEN)
            is_known_close = ch in (ZH_DQUOTE_CLOSE, ZH_SQUOTE_CLOSE)
            is_straight    = ch in (STRAIGHT_DOUBLE, STRAIGHT_SINGLE)

            zh_slot = cur['zh_slot']
            en_stack = cur['en_stack']

            # ── 无活跃 stack_b（zh_slot 为 None）────────────────────────────
            if zh_slot is None:
                if is_known_open:
                    cur['zh_slot'] = (abs_pos, ch)
                elif is_straight:
                    cur['zh_slot'] = '^'
                    _try_pair_en(abs_pos, ch)
                elif is_known_close:
                    _warn(abs_pos, ch, is_open=False, reason='段落内无匹配的中文开引号')
                continue

            # ── zh_slot 已设，en_stack 非空时读到中文引号 → 报警 ────────────
            if en_stack:
                if is_known_open or is_known_close:
                    # en_stack 中有未配对英文引号
                    for ep, ec in en_stack:
                        _warn(ep, ec, is_open=True, reason='中文引号出现时英文引号尚未闭合')
                    cur['en_stack'] = []
                    # 继续处理当前中文引号（fall through）
                    en_stack = cur['en_stack']

            # ── zh_slot 已设，en_stack 为空 ──────────────────────────────────
            if not cur['en_stack']:
                if is_straight:
                    _try_pair_en(abs_pos, ch)
                elif is_known_open:
                    # 嵌套：将当前层推入 meta_stack，新建层
                    _push_meta()
                    cur['zh_slot'] = (abs_pos, ch)
                elif is_known_close:
                    # 弹栈配对
                    zh = cur['zh_slot']
                    if zh == '^':
                        _warn(abs_pos, ch, is_open=False,
                              reason='该层由英文引号开始，中文闭引号无对应中文开引号')
                    else:
                        # 检查单双匹配
                        zh_pos, zh_ch = zh
                        expected_close = ZH_DQUOTE_CLOSE if zh_ch == ZH_DQUOTE_OPEN else ZH_SQUOTE_CLOSE
                        if ch != expected_close:
                            _warn(abs_pos, ch, is_open=False,
                                  reason=f'中文引号不匹配：开引号为 "{zh_ch}"，闭引号为 "{ch}"')
                            _warn(zh_pos, zh_ch, is_open=True,
                                  reason=f'中文引号不匹配：开引号为 "{zh_ch}"，闭引号为 "{ch}"')
                        else:
                            content = full_text[zh_pos + 1: abs_pos]
                            pairs.append(QuotePair(
                                open_pos=zh_pos, close_pos=abs_pos,
                                open_char=zh_ch, close_char=ch,
                                content=content,
                                sentence_lang=dominant_lang(content) if content.strip() else 'zh',
                                in_brackets=in_brk,
                            ))
                    # 恢复上一层（若有）
                    _pop_meta()
            else:
                # en_stack 满（2个且未配对），已在上面 en_stack 非空+中文引号处理，
                # 此处只可能是直引号（中文引号已在上方处理）
                if is_straight:
                    _try_pair_en(abs_pos, ch)

        # ── 段落结束，清理剩余 ────────────────────────────────────────────────
        # 当前层剩余
        if cur['en_stack']:
            for ep, ec in cur['en_stack']:
                _warn(ep, ec, is_open=True, reason='段落结束时英文引号未闭合')
        if cur['zh_slot'] and cur['zh_slot'] != '^':
            zh_pos, zh_ch = cur['zh_slot']
            _warn(zh_pos, zh_ch, is_open=True, reason='段落结束时中文开引号未闭合')

        # meta_stack 剩余层
        for layer in reversed(meta_stack):
            if layer['en_stack']:
                for ep, ec in layer['en_stack']:
                    _warn(ep, ec, is_open=True, reason='段落结束时英文引号未闭合')
            if layer['zh_slot'] and layer['zh_slot'] != '^':
                zh_pos, zh_ch = layer['zh_slot']
                _warn(zh_pos, zh_ch, is_open=True, reason='段落结束时中文开引号未闭合')

    # ── 主循环：按段落切分 ────────────────────────────────────────────────────
    paragraphs = full_text.split('\n')
    abs_offset = 0
    for para in paragraphs:
        queue: list[tuple[int, str]] = []
        for rel_pos, ch in enumerate(para):
            if ch in QUOTE_CHARS:
                queue.append((abs_offset + rel_pos, ch))
        if queue:
            _process_queue(queue)
        abs_offset += len(para) + 1  # +1 for the '\n'

    return pairs, unpaired


def _pos_to_lineno_from_text(text: str, pos: int) -> int:
    """在文本中将绝对偏移转换为行号（1-indexed）"""
    return text[:pos].count('\n') + 1


def decide_correct_quote_form(
    pair: QuotePair, strategy: str
) -> tuple[str, str]:
    """
    根据配对信息和策略，返回该对引号应使用的 (open_char, close_char)。
    策略 A：看句子语言 + 是否在括号内
    策略 B：看引号内容语言
    """
    if strategy == 'A':
        if pair.in_brackets:
            # 括号内引文：英文引号
            return (STRAIGHT_DOUBLE, STRAIGHT_DOUBLE)
        if pair.sentence_lang == 'zh':
            return (ZH_DQUOTE_OPEN, ZH_DQUOTE_CLOSE)
        else:
            return (STRAIGHT_DOUBLE, STRAIGHT_DOUBLE)
    else:  # strategy B
        content_lang = dominant_lang(pair.content) if pair.content.strip() else pair.sentence_lang
        if content_lang == 'zh':
            return (ZH_DQUOTE_OPEN, ZH_DQUOTE_CLOSE)
        else:
            return (STRAIGHT_DOUBLE, STRAIGHT_DOUBLE)


def check_quotes(
    full_text: str,
    strategy: str,
    section: str = 'body'
) -> tuple[list[Issue], list[tuple[int, str, int, str]]]:
    """
    引号检测主函数。
    返回 (issues, replacements)
    replacements 格式：[(abs_pos, correct_char, line_no, original_char), ...]
    用于后续 apply_fixes_with_quote_replacements。
    """
    issues: list[Issue] = []
    replacements: list[tuple[int, str, int, str]] = []

    pairs, unpaired = pair_quotes_by_paragraph(full_text)

    # 处理配对引号：检测是否使用了正确形式
    for pair in pairs:
        expected_open, expected_close = decide_correct_quote_form(pair, strategy)

        if pair.open_char != expected_open:
            line_no = _pos_to_lineno_from_text(full_text, pair.open_pos)
            ctx = context_window(full_text.replace('\n', '↵'), pair.open_pos)
            reason = (
                f'{"括号内引文" if pair.in_brackets else "该语境"}应使用 '
                f'{"英文" if expected_open == STRAIGHT_DOUBLE else "中文"}引号，'
                f'开引号 "{pair.open_char}" 建议改为 "{expected_open}"'
            )
            issues.append(Issue(line_no, pair.open_pos, pair.open_char,
                                expected_open, ctx, reason, section))
            replacements.append((pair.open_pos, expected_open, line_no, pair.open_char))

        if pair.close_char != expected_close:
            line_no = _pos_to_lineno_from_text(full_text, pair.close_pos)
            ctx = context_window(full_text.replace('\n', '↵'), pair.close_pos)
            reason = (
                f'{"括号内引文" if pair.in_brackets else "该语境"}应使用 '
                f'{"英文" if expected_close == STRAIGHT_DOUBLE else "中文"}引号，'
                f'闭引号 "{pair.close_char}" 建议改为 "{expected_close}"'
            )
            issues.append(Issue(line_no, pair.close_pos, pair.close_char,
                                expected_close, ctx, reason, section))
            replacements.append((pair.close_pos, expected_close, line_no, pair.close_char))

    # 处理未配对引号：报警
    for uq in unpaired:
        kind = '未闭合的开引号' if uq.is_open else '多余的闭引号'
        issues.append(Issue(
            uq.line_no, uq.pos, uq.char, '?',
            uq.context,
            f'{kind} "{uq.char}"，请人工检查',
            section,
            is_warning=True
        ))

    return issues, replacements





# ─── 正文检测 ──────────────────────────────────────────────────────────────────

def check_body_line(line: str, line_no: int, config: Config) -> list[Issue]:
    """检测正文中的单行（不含引号，引号在 process() 中全文统一处理）"""
    issues = []

    # 确定行的主导语言
    lang = dominant_lang(line)

    # 括号和引号由专项检测器处理，逐字符扫描时跳过
    SKIP_IN_CHAR_SCAN = set('()（）\'""\u201c\u201d\u2018\u2019')

    # 1. 逐字符检测常规标点（跳过括号和引号）
    for i, ch in enumerate(line):
        if ch in SKIP_IN_CHAR_SCAN:
            continue
        issue = check_single_punct_for_lang(ch, i, line_no, line, lang, section='body')
        if issue:
            issues.append(issue)

    # 2. 括号专项检测
    issues.extend(check_brackets(line, line_no, section='body'))

    # 引号在 process() 中对正文全文统一做断句+配对检测，不在此处处理

    return issues


# ─── 文本分割：正文 vs 参考文献 ────────────────────────────────────────────────

def split_body_refs(lines: list[str], refs_keyword: str) -> tuple[list, list, int]:
    """
    返回 (body_lines, ref_lines, ref_start_line_no)
    ref_start_line_no 是参考文献起始的行号（1-indexed）
    """
    for i, line in enumerate(lines):
        if refs_keyword in line:
            return lines[:i+1], lines[i+1:], i + 2  # +2 因为1-indexed且跳过标题行
    return lines, [], -1


# ─── 修正应用 ──────────────────────────────────────────────────────────────────

def apply_fixes(
    text: str,
    issues: list[Issue],
    quote_replacements: list[tuple[int, str, int, str]] | None = None,
) -> str:
    """
    将所有非警告类 Issue 应用到文本上。
    quote_replacements: [(abs_pos, correct_char, line_no, original_char), ...]
    引号修正通过绝对偏移直接替换，避免与逐行 col_no 替换的坐标体系混淆。
    """
    # ── 先处理引号（绝对偏移替换，倒序避免位移）──────────────────────────────
    text_list = list(text)
    if quote_replacements:
        for abs_pos, correct_char, _, orig_char in sorted(quote_replacements,
                                                           key=lambda x: x[0],
                                                           reverse=True):
            if 0 <= abs_pos < len(text_list) and text_list[abs_pos] == orig_char:
                text_list[abs_pos] = correct_char
    text = ''.join(text_list)

    # ── 再处理非引号 Issue（逐行 col_no 替换）────────────────────────────────
    lines = text.split('\n')
    from collections import defaultdict
    line_issues = defaultdict(list)
    for issue in issues:
        # 跳过：警告、无法自动修正的模糊建议、引号（已在上面处理）
        if issue.is_warning:
            continue
        if issue.suggestion in ('?',):
            continue
        if issue.char in QUOTE_CHARS and issue.suggestion in QUOTE_CHARS:
            continue  # 引号已由 quote_replacements 处理
        line_issues[issue.line_no].append(issue)

    for line_no, line_issue_list in line_issues.items():
        line_idx = line_no - 1
        if line_idx >= len(lines):
            continue
        line = lines[line_idx]
        sorted_issues = sorted(line_issue_list, key=lambda x: x.col_no, reverse=True)
        line_list = list(line)
        for issue in sorted_issues:
            if 0 <= issue.col_no < len(line_list):
                if line_list[issue.col_no] == issue.char:
                    line_list[issue.col_no] = issue.suggestion
        lines[line_idx] = ''.join(line_list)

    return '\n'.join(lines)


# ─── 报告输出 ──────────────────────────────────────────────────────────────────

def build_report_md(issues: list[Issue], total_lines: int) -> str:
    """生成 Markdown 格式的检测报告字符串"""
    lines = []

    if not issues:
        lines.append('# 标点检测报告')
        lines.append('')
        lines.append('✅ 未发现标点问题。')
        return '\n'.join(lines)

    warnings = [i for i in issues if i.is_warning]
    errors   = [i for i in issues if not i.is_warning]

    lines.append('# 标点检测报告')
    lines.append('')
    lines.append(f'共 **{total_lines}** 行，发现 **{len(errors)}** 处问题，**{len(warnings)}** 处警告。')
    lines.append('')

    if warnings:
        lines.append(f'## ⚠️ 警告（需人工确认，共 {len(warnings)} 处）')
        lines.append('')
        for w in warnings:
            lines.append(f'- **第 {w.line_no} 行** `[{w.section}]`')
            lines.append(f'  - 原因：{w.reason}')
            lines.append(f'  - 上下文：`{w.context}`')
        lines.append('')

    if errors:
        lines.append(f'## 🔴 问题（可自动修正，共 {len(errors)} 处）')
        lines.append('')
        for e in errors:
            lines.append(f'- **第 {e.line_no} 行 第 {e.col_no+1} 列** `[{e.section}]`')
            lines.append(f'  - 当前：`{e.char}` → 建议：`{e.suggestion}`')
            lines.append(f'  - 原因：{e.reason}')
            lines.append(f'  - 上下文：`{e.context}`')
        lines.append('')

    return '\n'.join(lines)


def print_report(issues: list[Issue], total_lines: int) -> None:
    """将报告打印到终端（从 Markdown 源转换，去掉标记符）"""
    import re as _re
    md = build_report_md(issues, total_lines)
    plain = _re.sub(r'^#{1,3} ', '', md, flags=_re.MULTILINE)
    plain = _re.sub(r'\*\*(.*?)\*\*', r'\1', plain)
    plain = plain.replace('`', '')
    plain = _re.sub(r'^- ', '  ', plain, flags=_re.MULTILINE)
    print(plain)


# ─── 交互式配置 ────────────────────────────────────────────────────────────────

def interactive_config() -> Config:
    config = Config()

    print('\n【标点检测工具】中英文混排标点检测与修正\n')

    # 1. 参考文献标题关键词
    print('请选择参考文献区块的标题关键词：')
    print('  1. 参考文献')
    print('  2. References')
    print('  3. 手动输入')
    choice = input('请输入选项编号（默认 1）：').strip() or '1'
    if choice == '1':
        config.refs_keyword = '参考文献'
    elif choice == '2':
        config.refs_keyword = 'References'
    elif choice == '3':
        config.refs_keyword = input('请输入参考文献标题关键词：').strip()

    # 2. 引号策略
    print('\n请选择中文行文中的引号策略：')
    print('  A. 中文行文统一使用中文引号（括号内引文除外）')
    print('  B. 引号跟随引号内容的语言（中文内容用中文引号，英文内容用英文引号）')
    q_choice = input('请输入选项（A/B，默认 A）：').strip().upper() or 'A'
    config.quote_strategy = q_choice if q_choice in ('A', 'B') else 'A'

    # 3. 输出模式
    print('\n请选择输出模式：')
    print('  1. 仅输出检测报告')
    print('  2. 仅输出修正后文本')
    print('  3. 两者都要（默认）')
    o_choice = input('请输入选项编号（默认 3）：').strip() or '3'
    mode_map = {'1': 'report', '2': 'fixed', '3': 'both'}
    config.output_mode = mode_map.get(o_choice, 'both')

    return config


# ─── 主流程 ────────────────────────────────────────────────────────────────────

def process(text: str, config: Config) -> tuple[list[Issue], str]:
    """处理文本，返回 (issues, fixed_text)"""
    lines = text.split('\n')
    body_lines, ref_lines, ref_start = split_body_refs(lines, config.refs_keyword)

    all_issues: list[Issue] = []
    all_quote_replacements: list[tuple[int, str, int, str]] = []

    # ── 处理正文（逐行：常规标点 + 括号）────────────────────────────────────
    for i, line in enumerate(body_lines, start=1):
        issues = check_body_line(line, i, config)
        all_issues.extend(issues)

    # ── 处理正文引号（全文段落级配对）────────────────────────────────────────
    body_text = '\n'.join(body_lines)
    quote_issues, quote_replacements = check_quotes(
        body_text, config.quote_strategy, section='body'
    )
    all_issues.extend(quote_issues)
    all_quote_replacements.extend(quote_replacements)

    # ── 处理参考文献────────────────────────────────────────────────────────
    if ref_lines:
        for j, line in enumerate(ref_lines, start=ref_start):
            if line.strip():
                issues = check_ref_entry(line, j)
                all_issues.extend(issues)

    fixed_text = apply_fixes(text, all_issues, all_quote_replacements)
    return all_issues, fixed_text


def main():
    parser = argparse.ArgumentParser(
        description='中英文混排标点检测与修正工具'
    )
    parser.add_argument('input', nargs='?', help='输入文件路径（不指定则从 stdin 读取）')
    parser.add_argument('-o', '--output', help='输出修正文件路径')
    parser.add_argument('--refs', help='参考文献标题关键词（跳过交互）')
    parser.add_argument('--quote', choices=['A', 'B'], help='引号策略（跳过交互）')
    parser.add_argument('--mode', choices=['report', 'fixed', 'both'],
                        help='输出模式（跳过交互）')
    parser.add_argument('--report-output', metavar='FILE',
                        help='将检测报告以 Markdown 格式写入指定 .md 文件')
    parser.add_argument('--non-interactive', action='store_true',
                        help='非交互模式（需同时提供 --refs、--quote、--mode）')
    args = parser.parse_args()

    # 读取输入
    if args.input:
        with open(args.input, 'r', encoding='utf-8') as f:
            text = f.read()
    else:
        text = sys.stdin.read()

    # 配置
    if args.non_interactive:
        config = Config(
            refs_keyword=args.refs or '参考文献',
            quote_strategy=args.quote or 'A',
            output_mode=args.mode or 'both',
            report_output=args.report_output or '',
        )
    else:
        config = interactive_config()
        # 命令行参数覆盖交互结果
        if args.refs:
            config.refs_keyword = args.refs
        if args.quote:
            config.quote_strategy = args.quote
        if args.mode:
            config.output_mode = args.mode
        if args.report_output:
            config.report_output = args.report_output

    # 处理
    issues, fixed_text = process(text, config)
    total_lines = len(text.split('\n'))

    # 输出
    if config.output_mode in ('report', 'both'):
        print_report(issues, total_lines)

    # 写 Markdown 报告文件
    if config.report_output:
        md_text = build_report_md(issues, total_lines)
        with open(config.report_output, 'w', encoding='utf-8') as f:
            f.write(md_text)
        print(f'\n📄 检测报告已写入：{config.report_output}')

    if config.output_mode in ('fixed', 'both'):
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(fixed_text)
            print(f'\n✅ 修正后的文本已写入：{args.output}')
        else:
            if config.output_mode == 'fixed':
                print(fixed_text)
            else:
                # both 模式且无输出文件：打印修正文本到 stdout
                out_path = (args.input.rsplit('.', 1)[0] + '_fixed.' + args.input.rsplit('.', 1)[1]
                            if args.input and '.' in args.input
                            else 'output_fixed.txt')
                with open(out_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_text)
                print(f'\n✅ 修正后的文本已写入：{out_path}')


if __name__ == '__main__':
    main()
