#!/usr/bin/env python3
"""
测试 skill 的触发词准确性。

用法:
  python3 test_triggers.py <skill_path> [--query-file <file>]

功能：
1. 构建 query 测试集（应该触发的 / 不应该触发的 / 边界 case）
2. 模拟触发判断（基于 trigger_words 匹配）
3. 报告命中率 / 误触率 / 漏触率
4. 给出触发词优化建议
"""
import argparse
import json
import re
import sys
from pathlib import Path


def load_trigger_words(skill_path):
    """加载 skill 的 trigger_words"""
    meta_path = Path(skill_path) / '_meta.json'
    if not meta_path.exists():
        return []

    with open(meta_path, encoding='utf-8') as f:
        meta = json.load(f)

    return meta.get('trigger_words', [])


def should_trigger(query, trigger_words):
    """判断 query 是否应该触发 skill"""
    query_lower = query.lower()

    for tw in trigger_words:
        tw_lower = tw.lower()
        # 精确匹配
        if tw_lower in query_lower:
            return True
        # 模糊匹配（query 包含 trigger word）
        if tw_lower.strip() in query_lower:
            return True

    return False


def load_default_queries():
    """加载默认测试 query 集（通用版）"""
    return [
        # 通用场景（应该触发）
        {"query": "帮我做一下", "should": False, "reason": "过于通用，不应该触发任何 skill"},
        {"query": "test", "should": False, "reason": "test 过于通用"},
        {"query": "帮我测试", "should": False, "reason": "测试请求"},
        {"query": "帮我写代码", "should": False, "reason": "通用实现请求"},
        {"query": "hello", "should": False, "reason": "普通问候"},
        {"query": "what is this", "should": False, "reason": "普通询问"},
    ]


def load_skill_specific_queries(skill_path):
    """根据 skill 类型加载特定测试 query"""
    skill_name = Path(skill_path).name.lower()
    queries = []

    # brainstorming skill
    if 'brainstorm' in skill_name:
        queries.extend([
            {"query": "帮我头脑风暴一下这个功能设计", "should": True, "reason": "常规头脑风暴请求"},
            {"query": "我想做头脑风暴", "should": True, "reason": "明确表达头脑风暴意图"},
            {"query": "brainstorm", "should": True, "reason": "包含关键词"},
            {"query": "帮我测试这个功能", "should": False, "reason": "测试请求，不是头脑风暴"},
            {"query": "帮我写代码实现", "should": False, "reason": "实现请求"},
        ])
    # marketing skill
    elif 'market' in skill_name:
        queries.extend([
            {"query": "给我一些营销 ideas", "should": True, "reason": "营销建议请求"},
            {"query": "怎么推广我的产品", "should": True, "reason": "推广策略请求"},
            {"query": "marketing ideas", "should": True, "reason": "包含关键词"},
            {"query": "帮我头脑风暴", "should": False, "reason": "头脑风暴请求，不是营销"},
        ])
    # hallmark skill
    elif 'hallmark' in skill_name:
        queries.extend([
            {"query": "帮我设计一个页面", "should": True, "reason": "设计请求"},
            {"query": "build a landing page", "should": True, "reason": "设计请求（英文）"},
            {"query": "hallmark audit", "should": True, "reason": "明确调用 hallmark"},
            {"query": "帮我写代码", "should": False, "reason": "纯实现请求，不是设计"},
        ])
    # 其他 skill
    else:
        queries.extend([
            {"query": "帮我", "should": False, "reason": "过于通用"},
            {"query": "试试", "should": False, "reason": "过于通用"},
        ])

    return queries


def load_custom_queries(query_file):
    """从文件加载自定义 query"""
    queries = []
    with open(query_file, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                try:
                    queries.append(json.loads(line))
                except:
                    pass
    return queries


def test_triggers(skill_path, query_file=None):
    """测试触发词准确性"""
    trigger_words = load_trigger_words(skill_path)

    if not trigger_words:
        print("警告: 没有找到 trigger_words", file=sys.stderr)
        return None

    print(f"触发词列表 ({len(trigger_words)} 个):")
    for tw in trigger_words:
        print(f"  - {tw}")
    print()

    # 加载测试 query
    if query_file:
        queries = load_custom_queries(query_file)
    else:
        # 混合默认和 skill 特定的
        queries = load_default_queries() + load_skill_specific_queries(skill_path)

    # 统计
    hit = 0
    miss = 0
    false_positive = 0
    correct_reject = 0

    results = []

    for q in queries:
        triggered = should_trigger(q['query'], trigger_words)
        expected = q['should']

        if expected and triggered:
            hit += 1
            status = "命中"
        elif expected and not triggered:
            miss += 1
            status = "漏触"
        elif not expected and triggered:
            false_positive += 1
            status = "误触"
        else:
            correct_reject += 1
            status = "正确拒绝"

        results.append({
            'query': q['query'],
            'status': status,
            'expected': '触发' if expected else '不触发',
            'reason': q.get('reason', ''),
            'triggered': triggered,
        })

    # 计算指标
    should_trigger_total = hit + miss
    should_not_total = false_positive + correct_reject

    hit_rate = hit / should_trigger_total if should_trigger_total > 0 else 0
    miss_rate = miss / should_trigger_total if should_trigger_total > 0 else 0
    false_positive_rate = false_positive / should_not_total if should_not_total > 0 else 0

    # 输出结果
    print("## 测试结果")
    print()

    print("| Query | 预期 | 结果 | 原因 |")
    print("|-------|------|------|------|")
    for r in results:
        status_icon = "✓" if r['status'] == "命中" or r['status'] == "正确拒绝" else "✗" if r['status'] == "漏触" else "⚠"
        print(f"| {r['query'][:30]:<30} | {r['expected']} | {status_icon} {r['status']} | {r['reason']} |")

    print()
    print("## 统计")
    print()
    print(f"- 命中率: {hit_rate:.0%} ({hit}/{should_trigger_total})")
    print(f"- 漏触率: {miss_rate:.0%} ({miss}/{should_trigger_total})")
    print(f"- 误触率: {false_positive_rate:.0%} ({false_positive}/{should_not_total})")
    print(f"- 正确拒绝率: {1 - false_positive_rate:.0%}")

    # 建议
    suggestions = []

    if miss > 0:
        suggestions.append("建议补充变体词（如近义词、英文对应词）")

    if false_positive > 0:
        suggestions.append("建议移除过于通用的词（如 '帮我'、'test'）")

    if len(trigger_words) > 15:
        suggestions.append("触发词偏多，建议精简到 10 个以内")

    if suggestions:
        print()
        print("## 优化建议")
        for s in suggestions:
            print(f"- {s}")

    return {
        'hit_rate': hit_rate,
        'miss_rate': miss_rate,
        'false_positive_rate': false_positive_rate,
        'suggestions': suggestions,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('skill_path', help='Skill 目录路径')
    parser.add_argument('--query-file', help='自定义测试 query 文件（JSONL 格式）')
    args = parser.parse_args()

    result = test_triggers(args.skill_path, args.query_file)

    if result is None:
        sys.exit(1)


if __name__ == '__main__':
    main()
