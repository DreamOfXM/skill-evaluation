#!/usr/bin/env python3
"""
评估一个 skill 的静态质量（快速模式的机械部分）。

覆盖失效层（完整模型见 SKILL.md）：
- 前置检查（不进分）：description 触发覆盖度、正文体量与 token 估算、
  trigger_words（仅关键词路由环境）、承诺层存在性、口径层机械项
- 触发层（静态）：关键词路由环境查 trigger_words 误触词质量；
  无 _meta.json/trigger_words（LLM 路由环境）返回 None，触发判定由 description 覆盖度承担
- 写作质量层：description 触发覆盖度、结构参考项（含常见坑加分项）、
  指令可操作性（按 工具型/咨询型/混合型 分档）
- 身份层：定位段矛盾信号初筛（最终判定需人工对读）

四维分数自 v5 起为「静态诊断四维」（诊断数据，不进评分口径）。
身份层对读、方法论层审计、执行层实跑由评审者完成，引擎不替代。
v6 校准（2026-11-10 用户指名，依据全网 skill 写作最佳实践调研，见 CHANGELOG 6.0.0 与 failure-log #13）：
description 评「何时用覆盖度」不评长度；刚性指令词不再加分；可操作性按类型分档。

用法:
  python3 evaluate_skill.py <skill_path> --mode quick|deep [--output markdown|json]

示例:
  python3 evaluate_skill.py ~/.agents/skills/brainstorming --mode quick
  python3 evaluate_skill.py ~/.agents/skills/brainstorming --mode deep --output json
"""
import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path


# ============================================================
# 评分标准（与 SKILL.md 完全同步）
# ============================================================

# 不可证伪的对冲词——只有这四个词还在扣（工具型/混合型的指令行）；咨询型的启发式
# 措辞（考虑/建议/可以）是合法文风，v6 起不再扣分；"必须/禁止"等刚性词不再加分
# （官方指引：满篇刚性指令是黄旗，解释原因比吼有效）
VAGUE_UNFALSIFIABLE = [r'适当', r'适时', r'酌情', r'视情况']

# description 触发覆盖度标记（v6：长度不再进判据——开放标准与官方范例都是数百字符，
# 「做什么 + 何时用 + 负边界」的覆盖度才是触发率的杠杆；上限只有 1024 字符硬杠）
WHEN_MARKERS = (
    'use when', 'whenever', 'use this skill', 'use before', 'use after', 'use for',
    'when the user', 'asks for', 'mentions', 'triggers include',
    '何时', '什么时候', '时使用', '时用', '当用户', '用户说', '你说', '用户提到', '提到',
    '用户问', '触发', '适用于', '想要', '想测', '想评', '要做',
)
NEG_MARKERS = (
    '不触发', '不用', '不要用', '别用', '不适用', '不是用来', '除外',
    "don't use", 'do not use', "don't trigger", 'do not trigger', 'not for',
)


def _has_boundary(content):
    """「边界情况」参考项的唯一判据（v6 起维度三与前置检查共用本函数——
    此前两处各持一套词表（7 token vs 3 token），failure-log #12 同型，2026-11-10 一并收拢）"""
    c = content.lower()
    return ('边界' in content or '红线' in content or '不适用' in content
            or '禁止' in content or '注意事项' in content or 'anti-pattern' in c)


def _has_examples(content):
    """「示例」参考项的唯一判据（同上收拢，旧两处 4 token vs 2 token）"""
    c = content.lower()
    return '示例' in content or 'example' in c or '```' in content


def _has_related(content):
    """「相关 skill」参考项的唯一判据（同上收拢，旧两处 5 token vs 2 token）"""
    c = content.lower()
    return '相关' in content or 'related' in c or 'see also' in c


def _has_gotchas(content):
    """「常见坑（gotchas）」加分项判据——全网实践公认性价比最高的正文内容，
    v6 起从结构参考项中单列（Anthropic 内部实测：带坑清单的 skill 准确率可测量地更高）"""
    c = content.lower()
    return ('常见坑' in content or '踩坑' in content or '踩过的坑' in content
            or '血泪' in content or 'gotcha' in c or 'footgun' in c)


def read_skill(path):
    """读取 skill 目录"""
    path = Path(path).expanduser()

    # 读取 SKILL.md
    skill_md = path / 'SKILL.md'
    if not skill_md.exists():
        return None, None, None, f"SKILL.md not found at {path}"

    with open(skill_md, encoding='utf-8') as f:
        content = f.read()

    # 解析 frontmatter
    frontmatter = {}
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            for line in parts[1].strip().split('\n'):
                if ':' in line:
                    key, val = line.split(':', 1)
                    frontmatter[key.strip()] = val.strip().strip('"\'')

    # 读取 _meta.json
    meta_path = path / '_meta.json'
    meta_data = {}
    if meta_path.exists():
        with open(meta_path, encoding='utf-8') as f:
            meta_data = json.load(f)

    return content, frontmatter, meta_data, None


def score_trigger_accuracy(meta_data):
    """评估触发准确性（0-5 分）"""
    score = 3.0  # 默认中等
    issues = []

    trigger_words = meta_data.get('trigger_words', [])
    num_triggers = len(trigger_words)

    # v6 环境适配：无 _meta.json/trigger_words = LLM 路由环境（Claude/ZCode/Codex 标准
    # 形态，开放标准里没有这个文件）——触发判定由 description 覆盖度承担，本维返回
    # None 而不是 1.0。旧判据把标准形态的 skill 判成"高优先级问题：没有触发机制"，
    # 属系统性误判（2026-11-10 校准，failure-log #13）
    if num_triggers == 0:
        return None, issues

    # 数量评估（仅关键词路由环境）
    if num_triggers > 15:
        score = 3.0
        issues.append({
            'level': 'medium',
            'desc': f'trigger_words 过多（{num_triggers} 个）',
            'suggestion': '建议精简到 10 个以内'
        })
    elif num_triggers > 10:
        score = 3.5
        issues.append({
            'level': 'low',
            'desc': f'trigger_words 偏多（{num_triggers} 个）',
            'suggestion': '可以考虑精简'
        })
    else:
        score = 4.0

    # 质量评估
    bad_words = {'帮我', '试试', 'test', 'help', 'make', 'do', '请'}
    short_words = set()

    for tw in trigger_words:
        tw_lower = tw.lower()
        if tw_lower in bad_words:
            score -= 0.5
            issues.append({
                'level': 'medium',
                'desc': f"'{tw}' 过于通用，容易误触",
                'suggestion': f"移除 '{tw}' 或用更精确的词替换"
            })
        if len(tw) <= 2 and tw not in {'AI', 'ML', 'UI', 'API', 'CEO', 'CFO', 'CTO', 'SaaS', 'PaaS', 'IaaS', 'CEO'}:
            short_words.add(tw)

    if short_words:
        score -= 0.3
        issues.append({
            'level': 'low',
            'desc': f"这些词太短（{', '.join(short_words)}），精确度不足",
            'suggestion': '除非是公认的专业缩写，否则用更长的词'
        })

    # 最终分数
    score = max(0, min(5, score))
    return round(score, 1), issues


def score_description_coverage(frontmatter):
    """评估 description 触发覆盖度（0-5 分，v6 判据）。

    长度不再进判据（旧判据 ≤50 字满分/>200 字 2 分——开放标准的官方范例 docx/pdf/xlsx
    全在 437-948 字符，全球 693 个 skill 中位 357；长 description 是官方要求的写法：
    pushy、含用户原话与负边界）。改查三样覆盖：
      ①做什么（非空且 ≥10 字符，存在性代理检）
      ②何时用（含触发语境标记：Use when/你说/当用户/提到…——LLM 路由下唯一杠杆）
      ③负边界（不触发/不适用/Don't use…——防近邻误触）
    硬杠只剩一条：>1024 字符 = 违反开放标准。
    """
    issues = []
    description = frontmatter.get('description', '')
    desc_len = len(description)
    desc_lower = description.lower()

    if not description:
        return 0.0, [{
            'level': 'high',
            'desc': 'description 为空',
            'suggestion': '补写：做什么 + 何时用（用户会怎么说）+ 什么时候不用'
        }]

    what = desc_len >= 10
    when_hit = any(m in desc_lower for m in WHEN_MARKERS)
    neg_hit = any(m in description for m in NEG_MARKERS) or any(m in desc_lower for m in NEG_MARKERS)

    if not what:
        score = 1.0
        issues.append({
            'level': 'high',
            'desc': f'description 过短（{desc_len} 字符），说不清做什么',
            'suggestion': '写清 skill 做什么 + 何时用'
        })
    elif not when_hit:
        score = 3.0 if neg_hit else 2.0
        issues.append({
            'level': 'high',
            'desc': 'description 无触发语境（缺"何时用/用户会怎么说"）',
            'suggestion': '补 Use when 段：用户会说的原话、文件类型、交付物——LLM 路由下这是唯一杠杆，不写最可能漏触发'
        })
    elif not neg_hit:
        score = 4.0
        issues.append({
            'level': 'low',
            'desc': 'description 缺负边界（"不触发/不适用于…"）',
            'suggestion': '补一句 Don\'t use for <相邻场景>，防近邻任务误触'
        })
    else:
        score = 5.0

    if desc_len > 1024:
        score = min(score, 2.0)
        issues.append({
            'level': 'high',
            'desc': f'description 超 1024 字符（{desc_len}）——违反 Agent Skills 开放标准',
            'suggestion': '压缩到 1024 以内'
        })

    score = max(0, min(5, score))
    return round(score, 1), issues


def score_structure_completeness(content, frontmatter):
    """评估结构参考项（0-5 分，v6：参考项不再判缺项扣档）。

    v6 变化：①「前置条件/何时使用」正文小节不再计入——触发判据在 description，
    正文在触发之后才加载，写在正文里的 when-to-use 模型根本看不到（OpenAI 官方
    明示该写法无效）；保留为参考信息不进判据。②「常见坑（gotchas）」顶替其位置
    成为第六项——全网实践公认性价比最高的正文内容。③共用谓词（_has_boundary 等），
    消灭两套词表。缺项只出低优先级建议（参考项），不构成缺陷指控。
    """
    checks = {
        'name': bool(frontmatter.get('name')),
        'description': bool(frontmatter.get('description')),
        '边界情况': _has_boundary(content),
        '示例': _has_examples(content),
        '常见坑(gotchas)': _has_gotchas(content),
        '相关skill': _has_related(content),
    }

    issues = []
    for name, passed in checks.items():
        if not passed:
            issues.append({
                'level': 'low',
                'desc': f'结构参考项缺：{name}（参考项，不扣档）',
                'suggestion': f'可补 {name} 相关内容（name/description 两项除外——那是硬项）'
            })

    passed_count = sum(1 for v in checks.values() if v)
    score = round((passed_count / 6) * 5, 1)

    return round(score, 1), issues, checks


def score_actionability(content, skill_type='混合型'):
    """评估指令可操作性（0-5 分，v6 按类型分档）。

    v6 判据（外部校准，2026-11-10）：
    - 删掉"刚性词加分/柔性词扣分"的通用词频——官方指引明确说满篇 必须/禁止 是黄旗，
      解释原因比吼有效；咨询型 skill 的启发式措辞（考虑/建议/可以）是合法文风。
    - 改查"自由度与任务类型匹配"：工具型查可执行锚点（命令/代码块）与验证闭环，
      咨询型查结构锚点（分支表/决策树）与示例；两类共用的加分项是"解释 why"。
    - 仅剩四个不可证伪的对冲词（适当/适时/酌情/视情况）在工具型/混合型指令行中扣分。
    - 矛盾检测原样保留（禁令+许可同段共词）。
    """
    issues = []
    c_lower = content.lower()

    has_commands = ('```' in content
                    or bool(re.search(r'\b(?:python3?|bash|zsh|npm|npx|uv|git|curl)\b', content)))
    has_verification = any(k in content for k in ('退出码', '什么算', '复算', '--help', '校验', '验证'))
    has_why = any(k in content for k in ('因为', '原因是', '避免', '防止', '否则会', '否则就', '教训'))
    has_structure = ('|---' in content
                     or any(k in content for k in ('决策树', '分支', '场景表', '流程图')))
    has_examples = _has_examples(content)

    # 只在指令相关区域检测对冲词（排除大段描述性文本与代码块）
    lines = content.split('\n')
    instruction_lines = []
    in_code_block = False
    for line in lines:
        if '```' in line:
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        stripped = line.strip()
        if not stripped or stripped.startswith(('#', '-')):
            continue
        if len(stripped) > 150:
            continue
        if any(word in stripped for word in ('必须', '禁止', '执行', '运行', '调用', '使用', '做', '写')):
            instruction_lines.append(stripped)
    instruction_text = ' '.join(instruction_lines)

    vague_count = sum(len(re.findall(p, instruction_text)) for p in VAGUE_UNFALSIFIABLE)

    def tool_adjust():
        adj = (1.0 if has_commands else 0.0) + (0.5 if has_verification else 0.0) + (0.5 if has_why else 0.0)
        pen = min(1.2, vague_count * 0.3)
        return adj - pen

    def consult_adjust():
        return ((1.0 if has_structure else 0.0) + (0.5 if has_examples else 0.0)
                + (0.5 if has_why else 0.0))

    if skill_type == '工具型':
        score = 3.0 + tool_adjust()
    elif skill_type == '咨询型':
        score = 3.0 + consult_adjust()
    else:
        score = 3.0 + (tool_adjust() + consult_adjust()) / 2

    if skill_type in ('工具型', '混合型') and vague_count:
        issues.append({
            'level': 'low',
            'desc': f'发现 {vague_count} 处不可证伪的对冲词（适当/适时/酌情/视情况）',
            'suggestion': '换成可判定的写法：什么条件下做什么，怎么算完成'
        })
    if skill_type in ('工具型', '混合型') and not has_commands:
        issues.append({
            'level': 'medium',
            'desc': '工具型 skill 未见可执行锚点（命令/代码块）',
            'suggestion': '关键步骤给出可直接运行的命令或脚本调用'
        })
    if not has_why:
        issues.append({
            'level': 'low',
            'desc': '未见解释原因（"因为/避免/否则会…"）',
            'suggestion': '非显然规则解释 why——官方指引：解释原因比刚性 MUST 更有效'
        })

    # 矛盾检测（保留 v5 逻辑：禁令与许可同段共词才可能是矛盾）
    lines = content.split('\n')
    contradictions = []
    must_lines, suggest_lines = [], []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        if '必须' in stripped or '禁止' in stripped or '不得' in stripped:
            must_lines.append((i + 1, stripped[:100]))
        if '可以' in stripped and '但不' not in stripped and '除非' not in stripped:
            suggest_lines.append((i + 1, stripped[:100]))

    for m_line, m_text in must_lines:
        for s_line, s_text in suggest_lines:
            if 0 < s_line - m_line <= 5:
                must_words = set(re.findall(r'[\w]+', m_text))
                suggest_words = set(re.findall(r'[\w]+', s_text))
                overlap = must_words & suggest_words
                if len(overlap) >= 1:
                    contradictions.append((m_line, s_line, list(overlap)[:3]))

    if contradictions:
        score = min(score, 2.5)
        for line1, line2, overlap in contradictions[:3]:
            issues.append({
                'level': 'high',
                'desc': f'行 {line1} 和 {line2} 可能存在矛盾（共同词：{", ".join(overlap)}）',
                'suggestion': '检查并修正矛盾的指令'
            })

    score = max(0, min(5, score))
    return round(score, 1), issues


def determine_skill_type(content, frontmatter):
    """判断 skill 类型"""
    content_lower = content.lower()

    # 工具型特征
    tool_features = ['执行', '运行', '调用', 'invoke', 'execute', 'run', 'tool']
    # 咨询型特征
    consult_features = ['问', '建议', '帮助', 'guide', 'help', 'ask', 'advice', 'strateg']

    tool_score = sum(1 for f in tool_features if f in content_lower)
    consult_score = sum(1 for f in consult_features if f in content_lower)

    if tool_score > consult_score:
        return '工具型'
    elif consult_score > tool_score:
        return '咨询型'
    else:
        return '混合型'


def check_static_layers(skill_path, content, frontmatter, meta_data):
    """静态可机械检查的失效层：承诺层（引用存在性）、口径层（元数据复算）、身份层（矛盾信号初筛）"""
    root = Path(skill_path).expanduser().resolve()
    layers = []

    # 承诺层：正文与 README 引用的本库相对路径是否存在（外部绝对路径不算本库承诺）
    ref_re = re.compile(r'(?:scripts|references)/[\w\-]+(?:/[\w\-]+)*\.(?:py|md|mjs|sh|js|ts)')
    referenced = {}
    docs = [('SKILL.md', content)]
    for readme in sorted(root.glob('README*.md')):
        try:
            docs.append((readme.name, readme.read_text(encoding='utf-8')))
        except OSError:
            pass
    for doc_name, doc in docs:
        for line_no, line in enumerate(doc.split('\n'), 1):
            # 含外部绝对路径的行，行内相对引用视为锚定外部根（如"真源在 ~/x/（…+ scripts/y.py）"），不算本库承诺
            if '~/' in line or '/Users/' in line:
                continue
            for m in ref_re.finditer(line):
                prev = line[m.start() - 1] if m.start() > 0 else ''
                if prev in '~/.' or prev.isalnum() or prev == '-':
                    continue  # 更长路径的一部分（外部引用），不是本库承诺
                referenced.setdefault(m.group(0), f'{doc_name}:{line_no}')
    missing = [r for r in sorted(referenced) if not (root / r).exists()]
    layers.append({
        'layer': '承诺层',
        'action': f'引用文件存在性（{len(referenced)} 处本库引用）',
        'status': '✗ 失效' if missing else '✓ 通过',
        'detail': '缺失：' + '、'.join(missing) if missing else '本库引用全部存在',
    })

    # 口径层：_meta 与 frontmatter 同步、name 与目录名一致、版本出现在 CHANGELOG
    findings = []
    meta_desc = meta_data.get('description')
    if meta_desc is not None and meta_desc != frontmatter.get('description', ''):
        findings.append('_meta.json 与 frontmatter 的 description 不一致')
    meta_name = meta_data.get('name') or meta_data.get('slug')
    if meta_name and frontmatter.get('name') and meta_name != frontmatter['name']:
        findings.append('_meta.json 与 frontmatter 的 name 不一致')
    if frontmatter.get('name') and frontmatter['name'] != root.name:
        findings.append(f'frontmatter name（{frontmatter["name"]}）≠ 目录名（{root.name}）')
    version = meta_data.get('version') or frontmatter.get('version')
    changelog = root / 'CHANGELOG.md'
    if version and changelog.exists():
        try:
            if version not in changelog.read_text(encoding='utf-8'):
                findings.append(f'版本 {version} 未出现在 CHANGELOG.md')
        except OSError:
            pass
    layers.append({
        'layer': '口径层',
        'action': '元数据同步与版本对齐复算',
        'status': '⚠ 存疑' if findings else '✓ 通过',
        'detail': '；'.join(findings) if findings else '元数据与版本口径一致',
    })

    # 身份层：定位段"不做 X"声明 vs 正文实跑表述（机械初筛，最终需人工对读）
    head = content[:3000]
    neg_markers = [m for m in ('不是功能测试', '纯文档层面', '只做静态分析') if m in head]
    pos_markers = [m for m in ('实跑', '实际跑') if m in content]
    if neg_markers and pos_markers:
        layers.append({
            'layer': '身份层',
            'action': '定位段矛盾信号初筛',
            'status': '⚠ 存疑',
            'detail': f'定位段含 {neg_markers}、正文含 {pos_markers}——需人工对读定位段与工作流',
        })
    else:
        layers.append({
            'layer': '身份层',
            'action': '定位段矛盾信号初筛',
            'status': '⏠ 需人工对读',
            'detail': '未检出机械矛盾信号；本层最终判定需对读定位段与工作流',
        })

    return layers


def build_precheck(frontmatter, meta_data, content, layers):
    """前置检查（v6：机械项不进分，只做过/不过判定；新增正文体量与环境适配分流）"""
    precheck = []

    fm_name = bool(frontmatter.get('name'))
    fm_desc = frontmatter.get('description', '')
    precheck.append({
        'item': 'frontmatter name/description 存在',
        'result': '过' if (fm_name and fm_desc) else '不过',
        'detail': '' if (fm_name and fm_desc) else 'name 或 description 缺失',
    })

    # 环境适配项（v6）：trigger_words 只在关键词路由环境是必查项；
    # LLM 路由环境（Claude/ZCode/Codex 标准）没有这个文件，触发判定由下一行覆盖度承担
    trigger_words = meta_data.get('trigger_words', [])
    n = len(trigger_words)
    if n == 0:
        result, detail = '不适用', '无 trigger_words——LLM 路由环境，触发看 description 覆盖度（下一行）'
    elif n > 15:
        result, detail = '不过', f'{n} 个（>15 过多，关键词路由环境）'
    elif n > 10:
        result, detail = '警告', f'{n} 个（11-15 偏多，关键词路由环境）'
    else:
        result, detail = '过', f'{n} 个（关键词路由环境）'
    precheck.append({'item': '_meta.json trigger_words（环境适配）', 'result': result, 'detail': detail})

    # v6 核心：description 触发覆盖度（做什么 + 何时用 + 负边界；>1024 违反开放标准）
    desc_len = len(fm_desc)
    desc_lower = fm_desc.lower()
    what = desc_len >= 10
    when_hit = any(m in desc_lower for m in WHEN_MARKERS)
    neg_hit = any(m in fm_desc for m in NEG_MARKERS) or any(m in desc_lower for m in NEG_MARKERS)
    marks = f"{'✓' if what else '✗'}做什么 {'✓' if when_hit else '✗'}何时用 {'✓' if neg_hit else '✗'}负边界"
    if not fm_desc or not when_hit or desc_len > 1024:
        result = '不过'
    elif not neg_hit:
        result = '警告'
    else:
        result = '过'
    precheck.append({'item': 'description 触发覆盖度', 'result': result,
                     'detail': f'{desc_len} 字；{marks}'})

    # v6 新增：正文体量与 token 估算（上下文是公共品——官方建议 <500 行/<5000 token，
    # 压缩重挂截断线 20000 字节；不评油耗等于没评）
    body = content.split('---', 2)[2] if content.startswith('---') and len(content.split('---', 2)) >= 3 else content
    body_lines = len(body.split('\n'))
    est_tokens = round((len(body) + desc_len) / 4)
    body_bytes = len(content.encode('utf-8'))
    if body_lines > 800 or est_tokens > 8000:
        result = '不过'
    elif body_lines > 500 or est_tokens > 5000 or body_bytes > 20000:
        result = '警告'
    else:
        result = '过'
    precheck.append({'item': '正文体量与 token 估算', 'result': result,
                     'detail': f'{body_lines} 行；正文+description 约 {est_tokens} token；全文 {body_bytes} 字节'})

    # 结构参考项（v6：不判缺项——报告缺什么供参考，name/description 硬项在前置第一行）
    ref_items = {
        '边界': _has_boundary(content), '示例': _has_examples(content),
        '常见坑': _has_gotchas(content), '相关': _has_related(content),
    }
    present = [k for k, v in ref_items.items() if v]
    absent = [k for k, v in ref_items.items() if not v]
    precheck.append({'item': '结构参考项（不判不过）', 'result': '参考',
                     'detail': '有：' + ('、'.join(present) if present else '无') + '；缺：'
                               + ('、'.join(absent) if absent else '无') + '（常见坑为高价值加分项）'})

    for key, item_name in (('承诺层', '引用文件存在性'), ('口径层', '元数据同步')):
        row = next((l for l in layers if l['layer'] == key), None)
        if row:
            result = '过' if '✓' in row['status'] else ('警告' if '⚠' in row['status'] else '不过')
            precheck.append({'item': item_name, 'result': result, 'detail': row['detail']})
    return precheck


def generate_report(skill_path, scores, mode='quick'):
    """生成评估报告"""
    skill_name = Path(skill_path).name
    date = datetime.now().strftime('%Y-%m-%d')

    trigger_score, trigger_issues = scores['trigger']
    desc_score, desc_issues = scores['description']
    struct_score, struct_issues, checks = scores['structure']
    action_score, action_issues = scores['actionability']
    skill_type = scores.get('type', '混合型')

    # 静态诊断四维（触发静态 + 写作质量层；v5 起为诊断数据，不进评分口径）
    # v6：触发静态在 LLM 路由环境为 None（trigger_words 不适用），加权 = 其余三维均值
    dims = [d for d in (trigger_score, desc_score, struct_score, action_score) if d is not None]
    weighted_score = sum(dims) / len(dims) if dims else 0.0
    trigger_disp = '—' if trigger_score is None else str(trigger_score)
    trigger_status = ('⏠ 不适用（LLM 路由环境，看描述覆盖度）' if trigger_score is None
                      else ('✓ 良好' if trigger_score >= 4 else '⚠ 需改进'))

    # 收集所有问题
    all_issues = []
    for issue in trigger_issues + desc_issues + struct_issues + action_issues:
        all_issues.append(issue)

    # 按优先级排序
    priority_order = {'high': 0, 'medium': 1, 'low': 2}
    all_issues.sort(key=lambda x: priority_order.get(x['level'], 3))

    # 层清检表（静态部分）
    layers = scores.get('layers', [])
    layer_table = "\n---\n\n## 层清检表（静态部分）\n\n| 层 | 检测动作 | 结果 | 说明 |\n|----|---------|------|------|\n"
    for lay in layers:
        layer_table += f"| {lay['layer']} | {lay['action']} | {lay['status']} | {lay['detail']} |\n"
    layer_table += "| 方法论层 | 工作流逐步找主 | ⏸ 不在引擎职责内 | 深度模式由评审者审计 |\n"
    layer_table += "| 执行层 | 实跑 + 边界探针 + 价值增量(with/without) | ⏸ 不在引擎职责内 | 深度模式由评审者实跑 |\n"
    layer_table += "| 证据纪律层 | check_report.py 机械核（v6 起为报告合格门，不进被测分） | ⏠ 不在引擎职责内 | 对报告本身核对，非被评 skill |\n"

    # 前置检查（不进分）
    precheck = scores.get('precheck', [])
    precheck_table = "\n---\n\n## 前置检查（不进分）\n\n| 前置项 | 结果 | 明细 |\n|--------|------|------|\n"
    for p in precheck:
        precheck_table += f"| {p['item']} | {p['result']} | {p['detail']} |\n"

    # 生成报告
    report = f"""# Skill 质量评估报告：{skill_name}

**评估日期：** {date}
**评估模式：** {'快速' if mode == 'quick' else '深度'}
**Skill 类型：** {skill_type}

---

## 静态诊断四维：{weighted_score:.1f}/5

（诊断数据，v5 起不进评分口径；前置检查见层清检表之后）

| 维度 | 分数 | 状态 |
|------|------|------|
| 触发准确性 | {trigger_disp} | {trigger_status} |
| 触发覆盖度（description） | {desc_score} | {'✓ 良好' if desc_score >= 4 else '⚠ 需改进'} |
| 结构参考项 | {struct_score} | {'✓ 良好' if struct_score >= 4 else '⚠ 需改进'} |
| 指令可操作性（按{skill_type}分档） | {action_score} | {'✓ 良好' if action_score >= 4 else '⚠ 需改进'} |

---

## 结构扫描

| 检查项 | 状态 |
|--------|------|
| name 字段 | {'✓' if checks.get('name') else '✗'} |
| description 字段 | {'✓' if checks.get('description') else '✗'} |
| 常见坑(gotchas，加分项) | {'✓' if checks.get('常见坑(gotchas)') else '✗'} |
| 边界情况处理 | {'✓' if checks.get('边界情况') else '✗'} |
| 示例 | {'✓' if checks.get('示例') else '✗'} |
| 相关 skill 引用 | {'✓' if checks.get('相关skill') else '✗'} |
{layer_table}{precheck_table}
---

## 问题列表

"""

    if not all_issues:
        report += "**未发现明显问题。**\n\n"
    else:
        # 按优先级分组
        high_issues = [i for i in all_issues if i['level'] == 'high']
        medium_issues = [i for i in all_issues if i['level'] == 'medium']
        low_issues = [i for i in all_issues if i['level'] == 'low']

        if high_issues:
            report += "### 高优先级（必须修复）\n\n"
            for i, issue in enumerate(high_issues, 1):
                report += f"**{i}. {issue['desc']}**\n"
                report += f"   - 现状：{issue['desc']}\n"
                report += f"   - 建议：{issue['suggestion']}\n\n"

        if medium_issues:
            report += "### 中优先级（建议修复）\n\n"
            for i, issue in enumerate(medium_issues, 1):
                report += f"**{i}. {issue['desc']}**\n"
                report += f"   - 建议：{issue['suggestion']}\n\n"

        if low_issues:
            report += "### 低优先级（可选优化）\n\n"
            for i, issue in enumerate(low_issues, 1):
                report += f"**{i}. {issue['desc']}**\n"
                report += f"   - 建议：{issue['suggestion']}\n\n"

    # 改进清单
    high_todos = [i for i in all_issues if i['level'] == 'high']
    medium_todos = [i for i in all_issues if i['level'] == 'medium']

    report += "---\n\n## 改进清单\n\n"
    report += "### 必须修复\n\n"
    if high_todos:
        for issue in high_todos:
            report += f"- [ ] {issue['suggestion']}\n"
    else:
        report += "- 暂无\n"

    report += "\n### 建议优化\n\n"
    if medium_todos:
        for issue in medium_todos:
            report += f"- [ ] {issue['suggestion']}\n"
    else:
        report += "- 暂无\n"

    return report, {
        'skill': skill_name,
        'date': date,
        'mode': mode,
        'type': skill_type,
        'score_kind': 'static_diagnostic',
        'note': 'v6：description=触发覆盖度；可操作性按类型分档；正文体量入前置检查；_meta 为环境适配项。四维为静态诊断数据，不进评分；评分口径见 SKILL.md Step 4',
        'precheck': precheck,
        'scores': {
            'trigger': trigger_score,
            'description': desc_score,
            'structure': struct_score,
            'actionability': action_score,
        },
        'weighted_score': round(weighted_score, 1),
        'layers': layers,
        'issues': all_issues,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('skill_path', help='Skill 目录路径')
    parser.add_argument('--mode', choices=['quick', 'deep'],
                        help='评估模式（必填）：quick=前置清单+两个质量分；deep=八层全检（方法论/执行/证据纪律由评审者完成）')
    parser.add_argument('--output', choices=['markdown', 'json'], default='markdown',
                        help='输出格式（默认 markdown）')
    args = parser.parse_args()

    # --mode 必填闸门：缺失时把选择题打到 stderr 并退 2（参数错=2，与其他脚本契约一致）
    if args.mode is None:
        print("""[!] 未指定 --mode。评估模式必须由用户选择，不得代答：

你想怎么评估？

A) 快速评估 - 前置检查清单（机械项过/不过，不进分）+ 触发质量与可操作性两个质量分 + Top 3 问题
B) 深度评估 - 快速评估 + 方法论层与执行层实跑验证（含价值增量 with/without 对比）+ 证据纪律层机械核（八层全检）；要实跑被测 skill 的命令，耗时可能较长

(选 A 或 B；用户消息已明示"快速/深度"时按其选择传 --mode)""", file=sys.stderr)
        sys.exit(2)

    # 读取 skill
    content, frontmatter, meta_data, error = read_skill(args.skill_path)
    if error:
        print(f"错误: {error}", file=sys.stderr)
        sys.exit(1)

    # 评分
    skill_type = determine_skill_type(content, frontmatter)
    scores = {
        'trigger': score_trigger_accuracy(meta_data),
        'description': score_description_coverage(frontmatter),
        'structure': score_structure_completeness(content, frontmatter),
        'actionability': score_actionability(content, skill_type),
        'type': skill_type,
        'layers': check_static_layers(args.skill_path, content, frontmatter, meta_data),
    }
    scores['precheck'] = build_precheck(frontmatter, meta_data, content, scores['layers'])

    # 生成报告
    report, data = generate_report(args.skill_path, scores, args.mode)

    if args.output == 'json':
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(report)


if __name__ == '__main__':
    main()
