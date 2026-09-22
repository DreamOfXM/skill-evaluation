#!/usr/bin/env python3
"""compare_runs / flaky_report 的公共层：schema 校验、容错读取、(case_id, rep) 去重、kappa。

为什么抽公共块（2026-09-21 八评教训）：两脚本曾各持一份逐字拷贝——去重告警只在一侧存在、
编码 wrapper 又复制了一份。拷贝分叉是缺陷类反复复发的结构机制：同一缺陷修三次，
每次都在另一份拷贝里再被抓一次。单一真源让两个脚本同时生效。
本模块除致命错误（IO/编码 → stderr + rc=2；schema 错误由 emit_schema_errors 统一输出）外不打印，
告警信息返回给调用方按各自口径输出。
"""
import json
import sys
from collections import defaultdict


def schema_error(r):
    """一行数据的 schema 问题（None = 合格）。passed 必须严格布尔：字符串 'false' 是真值，会被判成通过。"""
    if not isinstance(r, dict):
        return "不是 JSON 对象"
    for k in ("case_id", "category", "rep", "passed"):
        if k not in r:
            return f"缺必填字段 {k}"
    if not isinstance(r["passed"], bool):
        return f"passed 必须是布尔值（现在是 {type(r['passed']).__name__}）"
    if isinstance(r["rep"], bool) or not isinstance(r["rep"], int):
        return f"rep 必须是整数（现在是 {type(r['rep']).__name__}）"
    cat = r["category"]
    if not isinstance(cat, str) or not cat or "|" in cat:
        return "category 必须是非空字符串且不含 '|'（会撑破 markdown 表格）"
    if "|" in str(r["case_id"]):
        return "case_id 不含 '|'（会撑破 markdown 表格）"
    return None


def read_lines(path):
    """容错读取：IO/编码错误 → stderr 一行 + rc=2（"根本没跑成"）。"""
    try:
        with open(path, encoding="utf-8") as f:
            return f.read().splitlines()
    except OSError as e:
        print(f"IO 错误（根本没跑成）：{path}: {e}", file=sys.stderr)
        raise SystemExit(2)
    except UnicodeDecodeError as e:
        print(f"编码错误（根本没跑成）：{path}: {e}", file=sys.stderr)
        raise SystemExit(2)


def load_results(path):
    """读 results.jsonl → (cases, (重复行数, 示例), (跳号题数, 示例), schema 错误列表)。

    cases: {case_id: {"passes", "runs", "category", "reps"}}；按 (case_id, rep) 去重，
    重复行与 rep 序号不连续都收集成告警信息——打印由调用方负责（两个脚本口径不同）。
    """
    cases = defaultdict(lambda: {"passes": 0, "runs": 0, "category": "?", "reps": []})
    seen = set()
    dup_n, dup_ex = 0, []
    gap_n, gap_ex = 0, []
    errs = []
    for lineno, line in enumerate(read_lines(path), 1):
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError as e:
            errs.append(f"{path}:{lineno}: 不是合法 JSON（{e.msg}）")
            continue
        bad = schema_error(r)
        if bad:
            errs.append(f"{path}:{lineno}: {bad}")
            continue
        cid = str(r["case_id"])
        rep = r["rep"]
        if (cid, rep) in seen:
            dup_n += 1
            if len(dup_ex) < 3:
                dup_ex.append(f"{cid} rep={rep}")
            continue
        seen.add((cid, rep))
        c = cases[cid]
        c["passes"] += 1 if r["passed"] else 0
        c["runs"] += 1
        c["reps"].append(rep)
        c["category"] = r["category"]
    for cid, c in cases.items():
        rs = sorted(c["reps"])
        if rs != list(range(1, len(rs) + 1)):
            gap_n += 1
            if len(gap_ex) < 3:
                gap_ex.append(f"{cid} {rs}")
    return dict(cases), (dup_n, dup_ex), (gap_n, gap_ex), errs


def emit_schema_errors(errs):
    """有 schema 错误就打印（前 10 条 + 总数）并以 rc=2 退出；无错原样返回。"""
    if not errs:
        return
    for e in errs[:10]:
        print(f"schema 错误：{e}", file=sys.stderr)
    if len(errs) > 10:
        print(f"schema 错误：… 共 {len(errs)} 处", file=sys.stderr)
    raise SystemExit(2)


def kappa(a, b):
    """Cohen's kappa（rubric-design.md 校准节的同一实现：人/judge 对同一批题的 0/1 判定）。

    上两轮验证中"过线/被拒"方向曾两次写反（一次标签、一次条件），单一副本消灭各自写反的机会。
    """
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    pa, pb = sum(a) / n, sum(b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    if pe == 1:  # 同质批次（全过/全挂）：kappa 数学上无定义
        return 1.0 if po == 1 else 0.0
    return (po - pe) / (1 - pe)
