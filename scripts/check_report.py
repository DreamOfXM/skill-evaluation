#!/usr/bin/env python3
"""
证据纪律层机械核——检查一份评估报告是否诚实。

只做三件可机械核的事，其余证据项由评审者自查（报告中如实标"证据层未核"）：
1. 锚核对：报告声称的静态四维分 vs 引擎实测（逐字比对）
2. 层结论核对：报告层清检表中 承诺层/口径层 的结论 vs 引擎 layers 输出
3. 证据块核对：每个 ⚠/✗ 判定的层，报告须有含命令痕迹的代码块（$ / exit / rc= / ←）

本脚本核的是"报告自己"，不评被测 skill——证据纪律层的分数由评审者按
SKILL.md 分档表给：机械核全过=5；轻微不符=3；机械核报红=1（报告作废重做）。

用法:
  python3 check_report.py <report.md> --skill <skill-path>

退出码：0 全过 / 1 有不符 / 2 参数或文件错误
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ENGINE = Path(__file__).resolve().parent / 'evaluate_skill.py'


def run_engine(skill_path):
    """跑引擎拿实测锚数字与层结论"""
    proc = subprocess.run(
        [sys.executable, str(ENGINE), skill_path, '--mode', 'quick', '--output', 'json'],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        print(f'引擎执行失败（rc={proc.returncode}）: {proc.stderr.strip()[:200]}', file=sys.stderr)
        sys.exit(2)
    return json.loads(proc.stdout)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', help='评估报告 markdown 路径')
    parser.add_argument('--skill', required=True, help='被评 skill 目录路径')
    args = parser.parse_args()

    report_path = Path(args.report).expanduser()
    if not report_path.is_file():
        print(f'错误: 报告不存在 {report_path}', file=sys.stderr)
        sys.exit(2)
    report = report_path.read_text(encoding='utf-8')

    data = run_engine(args.skill)
    problems = []

    # 1. 锚核对：静态诊断四维（v5 名称；旧报告写"静态四维分"）
    m = re.search(r'静态(?:诊断四维|四维分)[：:]\s*\**\s*([\d.]+)', report)
    if not m:
        problems.append(f'锚数字：报告中找不到"静态诊断四维/静态四维分"声称（模板要求逐字引用引擎输出）')
    else:
        claimed = float(m.group(1))
        actual = round(data['weighted_score'], 1)
        if abs(claimed - actual) > 1e-9:
            problems.append(f'锚数字：报告声称 {claimed}，引擎实测 {actual}——无源数字，证据纪律层判 1，报告作废重做')

    # 2. 层结论核对：承诺/口径（引擎代查的两层）
    for layer in ('承诺层', '口径层'):
        engine_row = next((l for l in data['layers'] if l['layer'] == layer), None)
        if engine_row is None:
            continue
        row = re.search(rf'\|\s*{layer}\s*\|[^|]*\|([^|]*)\|', report)
        if row is None:
            problems.append(f'{layer}：报告层清检表缺行')
            continue
        claimed_status = row.group(1)
        # 取结论主干（✓ 通过 / ⚠ 存疑 / ✗ 失效）
        for token, verdict in (('✗', '失效'), ('⚠', '存疑'), ('✓', '通过')):
            if token in claimed_status:
                if token not in engine_row['status']:
                    problems.append(f'{layer}：报告判 [{token} {verdict}]，引擎实测 [{engine_row["status"]}]——结论与机械事实不符')
                break
        else:
            problems.append(f'{layer}：报告结论列无可识别判定（✓/⚠/✗）')

    # 3. 证据块核对：⚠/✗ 行数 vs 含命令痕迹的代码块数
    flagged = [l for l in re.findall(r'^\|[^|]+\|[^|]+\|[^|]*[⚠✗][^|]*\|', report, re.M)
               if not l.startswith('| 层 ')]
    blocks = re.findall(r'```(.*?)```', report, re.S)
    evidence_blocks = [b for b in blocks
                       if any(k in b for k in ('exit', 'rc=', '$ ', '→', '退出码'))]
    if len(flagged) > len(evidence_blocks):
        problems.append(f'证据块：{len(flagged)} 个 ⚠/✗ 判定只有 {len(evidence_blocks)} 个含命令+退出码的代码块——无证据指控')

    # 输出
    if problems:
        print(f'证据纪律层机械核：未过（{len(problems)} 项不符）')
        for p in problems:
            print(f'  ✗ {p}')
        print('证据纪律层判 1：报告作废重做（SKILL.md 分档表）')
        sys.exit(1)
    print(f'证据纪律层机械核：全过（锚数字 {data["weighted_score"]} 一致；承诺/口径结论一致；'
          f'{len(flagged)} 个 ⚠/✗ 均有证据块）')
    print('机械核之外的自查项（分数可溯、无小数编造）由评审者完成；机械核未覆盖处如实标注')
    sys.exit(0)


if __name__ == '__main__':
    main()
