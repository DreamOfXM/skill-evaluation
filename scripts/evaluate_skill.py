#!/usr/bin/env python3
"""
评估一个 skill 的静态质量（快速模式的机械部分）。

覆盖失效层（完整模型见 SKILL.md）：
- 触发层（静态）：trigger_words 数量与质量
- 写作质量层：描述清晰度、结构完整性、指令可操作性
- 承诺层（存在性）：SKILL.md/README 引用的本库文件是否存在
- 口径层（机械项）：_meta.json 与 frontmatter 同步、版本与 CHANGELOG 对齐
- 身份层：定位段矛盾信号初筛（最终判定需人工对读）

身份层对读、方法论层审计、执行层实跑由评审者完成，引擎不替代。

用法:
  python3 evaluate_skill.py <skill_path> [--output markdown|json]

示例:
  python3 evaluate_skill.py ~/.agents/skills/brainstorming
  python3 evaluate_skill.py ~/.agents/skills/brainstorming --output json
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

# 模糊词汇及影响分值
VAGUE_PATTERNS = {
    'high': [r'适当', r'适时', r'必要时', r'酌情', r'视情况'],  # -0.5
    'low': [r'考虑', r'建议', r'可以', r'或许'],  # -0.3
}

# 清晰词汇及影响分值
CLEAR_PATTERNS = {
    'medium': [r'必须', r'执行', r'运行', r'调用'],  # +0.2
    'high': [r'禁止', r'不得', r'绝不'],  # +0.3
}


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

    # 数量评估
    if num_triggers == 0:
        score = 1.0
        issues.append({
            'level': 'high',
            'desc': '没有 trigger_words 定义',
            'suggestion': '在 _meta.json 中添加 trigger_words 字段'
        })
    elif num_triggers > 15:
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


def score_description_clarity(frontmatter):
    """评估描述清晰度（0-5 分）"""
    issues = []
    description = frontmatter.get('description', '')

    # 字数评分
    desc_len = len(description)

    if desc_len == 0:
        score = 0
        issues.append({
            'level': 'high',
            'desc': 'description 为空',
            'suggestion': '添加一句话描述 skill 的功能'
        })
    elif desc_len <= 50:
        score = 5.0
    elif desc_len <= 100:
        score = 4.0
    elif desc_len <= 200:
        score = 3.0
    else:
        score = 2.0
        issues.append({
            'level': 'medium',
            'desc': f'description 过长（{desc_len} 字）',
            'suggestion': '精简到 100 字以内'
        })

    # 扣分项
    if '当用户' in description and '的时候' in description:
        score -= 0.3
        issues.append({
            'level': 'low',
            'desc': "description 包含'当用户...的时候'句式",
            'suggestion': '直接描述 skill 做什么，不要用条件句'
        })

    if '等' in description:
        score -= 0.5
        issues.append({
            'level': 'low',
            'desc': "description 包含'等'字",
            'suggestion': '精确列举或用更通用的描述'
        })

    comma_count = description.count('，') + description.count(',')
    if comma_count > 3:
        score -= 0.5
        issues.append({
            'level': 'low',
            'desc': f"description 包含过多标点符号（{comma_count} 处）",
            'suggestion': '尝试用更简洁的句式'
        })

    score = max(0, min(5, score))
    return round(score, 1), issues


def score_structure_completeness(content, frontmatter):
    """评估结构完整性（0-5 分）"""
    checks = {
        'name': bool(frontmatter.get('name')),
        'description': bool(frontmatter.get('description')),
        '前置条件': (
            '何时使用' in content or 'When to Use' in content or 'when to use' in content.lower()
            or '使用条件' in content or '前提' in content
        ),
        '边界情况': (
            '边界' in content or '红线' in content or '不适用' in content or '禁止' in content
            or 'Anti-Pattern' in content or 'anti-pattern' in content.lower()
            or '注意事项' in content
        ),
        '示例': (
            '示例' in content or 'example' in content.lower() or 'Example' in content
            or '```' in content  # 代码块通常表示示例
        ),
        '相关skill': (
            '相关' in content or 'Related' in content or 'related' in content.lower()
            or 'see also' in content.lower() or 'Related Skills' in content
        ),
    }

    issues = []
    for name, passed in checks.items():
        if not passed:
            issues.append({
                'level': 'medium',
                'desc': f'缺少 {name} 相关内容',
                'suggestion': f'添加 {name} 章节'
            })

    passed_count = sum(1 for v in checks.values() if v)
    score = round((passed_count / 6) * 5, 1)

    return round(score, 1), issues, checks


def score_actionability(content):
    """评估指令可操作性（0-5 分）"""
    issues = []

    # 只在指令相关区域检测模糊词汇（排除大段描述性文本）
    # 分割成行，检测非描述性行
    lines = content.split('\n')
    instruction_lines = []
    in_code_block = False

    for line in lines:
        # 跳过代码块
        if '```' in line:
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        # 跳过标题和空行
        stripped = line.strip()
        if not stripped or stripped.startswith('#') or stripped.startswith('-'):
            continue
        # 跳过过长的行（通常是描述性段落）
        if len(stripped) > 150:
            continue
        # 收集可能是指令的行
        if any(word in stripped for word in ['必须', '禁止', '执行', '运行', '调用', '使用']):
            instruction_lines.append(stripped)

    # 统计指令行中的模糊词汇
    instruction_text = ' '.join(instruction_lines)
    vague_deduct = 0
    for pattern in VAGUE_PATTERNS['high']:
        count = len(re.findall(pattern, instruction_text))
        vague_deduct += count * 0.5
    for pattern in VAGUE_PATTERNS['low']:
        count = len(re.findall(pattern, instruction_text))
        vague_deduct += count * 0.3

    # 统计清晰词汇
    clear_add = 0
    for pattern in CLEAR_PATTERNS['medium']:
        clear_add += len(re.findall(pattern, content)) * 0.2
    for pattern in CLEAR_PATTERNS['high']:
        clear_add += len(re.findall(pattern, content)) * 0.3

    # 基础分 + 加减分
    score = 3.0 + clear_add - vague_deduct

    # 矛盾检测（优化版，减少误报）
    lines = content.split('\n')
    contradictions = []

    # 找出所有包含关键词的行及其上下文
    must_lines = []  # 包含"必须"或"禁止"的行
    suggest_lines = []  # 包含"可以"或"建议"的行

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        if '必须' in stripped or '禁止' in stripped or '不得' in stripped:
            must_lines.append((i+1, stripped[:100]))
        if '可以' in stripped and '但不' not in stripped and '除非' not in stripped:
            suggest_lines.append((i+1, stripped[:100]))

    # 只有在同一段落内（5行内）出现才可能是矛盾
    for m_line, m_text in must_lines:
        for s_line, s_text in suggest_lines:
            if 0 < s_line - m_line <= 5:
                # 进一步检查：是否是真正的矛盾
                # "禁止 X" 和 "可以 X" 才是矛盾
                # "必须 X" 和 "可以 Y" 不是矛盾
                must_words = set(re.findall(r'[\w]+', m_text))
                suggest_words = set(re.findall(r'[\w]+', s_text))
                overlap = must_words & suggest_words
                if len(overlap) >= 1:  # 有共同词汇才可能是矛盾
                    contradictions.append((m_line, s_line, list(overlap)[:3]))

    if contradictions:
        score = min(score, 2.5)
        for line1, line2, overlap in contradictions[:3]:
            issues.append({
                'level': 'high',
                'desc': f'行 {line1} 和 {line2} 可能存在矛盾（共同词：{", ".join(overlap)}）',
                'suggestion': '检查并修正矛盾的指令'
            })

    if vague_deduct > 0:
        issues.append({
            'level': 'low',
            'desc': f'发现 {int(vague_deduct * 2)} 处模糊表述',
            'suggestion': '将"适当"、"考虑"等词替换为更明确的指令'
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


def generate_report(skill_path, scores, mode='quick'):
    """生成评估报告"""
    skill_name = Path(skill_path).name
    date = datetime.now().strftime('%Y-%m-%d')

    trigger_score, trigger_issues = scores['trigger']
    desc_score, desc_issues = scores['description']
    struct_score, struct_issues, checks = scores['structure']
    action_score, action_issues = scores['actionability']
    skill_type = scores.get('type', '混合型')

    # 静态四维分（触发静态 + 写作质量层；身份/口径/承诺在层清检表）
    weighted_score = (
        trigger_score * 0.25 +
        desc_score * 0.25 +
        struct_score * 0.25 +
        action_score * 0.25
    )

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
    layer_table += "| 方法论层 | 工作流逐步找主 | ⏸ 未检 | 快速模式不检，深度模式审计 |\n"
    layer_table += "| 执行层 | 实跑 + 边界探针 | ⏸ 未检 | 快速模式不检，深度模式实跑 |\n"

    # 生成报告
    report = f"""# Skill 质量评估报告：{skill_name}

**评估日期：** {date}
**评估模式：** {'快速' if mode == 'quick' else '深度'}
**Skill 类型：** {skill_type}

---

## 静态四维分：{weighted_score:.1f}/5

（触发层静态 + 写作质量层；身份/口径/承诺见层清检表）

| 维度 | 分数 | 状态 |
|------|------|------|
| 触发准确性 | {trigger_score} | {'✓ 良好' if trigger_score >= 4 else '⚠ 需改进'} |
| 描述清晰度 | {desc_score} | {'✓ 良好' if desc_score >= 4 else '⚠ 需改进'} |
| 结构完整性 | {struct_score} | {'✓ 良好' if struct_score >= 4 else '⚠ 需改进'} |
| 指令可操作性 | {action_score} | {'✓ 良好' if action_score >= 4 else '⚠ 需改进'} |

---

## 结构扫描

| 检查项 | 状态 |
|--------|------|
| name 字段 | {'✓' if checks.get('name') else '✗'} |
| description 字段 | {'✓' if checks.get('description') else '✗'} |
| 前置条件说明 | {'✓' if checks.get('前置条件') else '✗'} |
| 边界情况处理 | {'✓' if checks.get('边界情况') else '✗'} |
| 示例 | {'✓' if checks.get('示例') else '✗'} |
| 相关 skill 引用 | {'✓' if checks.get('相关skill') else '✗'} |
{layer_table}
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
        'score_kind': 'static_four',
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
    parser.add_argument('--output', choices=['markdown', 'json'], default='markdown',
                        help='输出格式（默认 markdown）')
    args = parser.parse_args()

    # 读取 skill
    content, frontmatter, meta_data, error = read_skill(args.skill_path)
    if error:
        print(f"错误: {error}", file=sys.stderr)
        sys.exit(1)

    # 评分
    scores = {
        'trigger': score_trigger_accuracy(meta_data),
        'description': score_description_clarity(frontmatter),
        'structure': score_structure_completeness(content, frontmatter),
        'actionability': score_actionability(content),
        'type': determine_skill_type(content, frontmatter),
        'layers': check_static_layers(args.skill_path, content, frontmatter, meta_data),
    }

    # 生成报告
    report, data = generate_report(args.skill_path, scores, 'quick')

    if args.output == 'json':
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(report)


if __name__ == '__main__':
    main()
