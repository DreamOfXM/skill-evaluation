#!/usr/bin/env python3
"""从单次运行的 results.jsonl 产出 flaky 清单（报告模板的 Flaky 节由它负责）。

分类（见 references/statistics.md）：
- p_i = 1.0   稳定过
- p_i = 0.0   稳定挂（能力问题）
- 0 < p_i < 1 高方差题 → flaky 清单主体，单独跟踪

用法:
  python3 flaky_report.py evals/runs/<run_id>/results.jsonl

输入每行必须含（schema 校验，不合格退出码 2，stderr 报 文件:行号:原因）:
  case_id（不含 '|'）/ category（非空字符串，不含 '|'）/ rep（整数）/ passed（布尔）；
  按 (case_id, rep) 去重，重复行与 rep 跳号告警（与 compare_runs 共用 _common.py 同一实现）；
  flaky 清单超过 20 条只列前 20（通过率最低在前）并报总数
rep=1 的运行数学上无法定义 flaky，会直接说明并退出（报告中标"不适用"）。
退出码：0 正常（含 rep=1 不适用）/ 1 空文件 / 2 输入错误——schema 或 IO。
输出流约定：stdout = 报告全文；stderr = 致命错误（配 rc=2）。
"""
import argparse

import _common


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("results", help="一次运行的 results.jsonl")
    args = ap.parse_args()

    cases, (dup_n, dup_ex), (gap_n, gap_ex), errs = _common.load_results(args.results)
    _common.emit_schema_errors(errs)
    msgs = []
    if dup_n:
        msgs.append(f"{dup_n} 行重复 (case_id, rep)（如 {', '.join(dup_ex)}），重复行已忽略")
    if gap_n:
        msgs.append(f"{gap_n} 题 rep 序号不连续（如 {', '.join(gap_ex)}）")
    if msgs:
        print("⚠️ 数据卫生：" + "；".join(msgs) + "。")
        print()

    if not cases:
        raise SystemExit("没有读到任何用例行，检查文件路径与格式。")
    max_reps = max(c["runs"] for c in cases.values())
    if max_reps < 2:
        # rep=1 是合法状态（冒烟/线上监控）：只说明不适用并正常退出，别打断 set -e 的 runner
        print("rep=1 的运行无法定义 flaky（单次结果无方差可言）——报告的 Flaky 节标'不适用'即可。")
        return

    stable_pass = stable_fail = flaky = 0
    flaky_rows = []
    for cid, c in sorted(cases.items()):
        p = c["passes"] / c["runs"]
        if p == 1.0:
            stable_pass += 1
        elif p == 0.0:
            stable_fail += 1
        else:
            flaky += 1
            flaky_rows.append((p, cid, c["category"], c["runs"]))

    print(f"共 {len(cases)} 题：稳定过 {stable_pass} / 稳定挂 {stable_fail} / 高方差（flaky）{flaky}")
    print()
    if flaky_rows:
        flaky_rows.sort()
        cap = 20
        print("## Flaky 清单（多次运行结果不一致的题）")
        if len(flaky_rows) > cap:
            print(f"（共 {len(flaky_rows)} 条，仅列前 {cap} 条、通过率最低在前——过多通常意味着题集方差整体偏高）")
        print("| 题目 | 类目 | 通过率 | n |")
        print("|---|---|---|---|")
        for p, cid, cat, n in flaky_rows[:cap]:
            print(f"| {cid} | {cat} | {p:.0%} | {n} |")
        print()
        print("判读：flaky 题通过率的变化（如 0.33 → 0.67）通常比总分 2pt 的变化更有信息量；不要让它静默平均进总分。")


if __name__ == "__main__":
    main()
