#!/usr/bin/env python3
"""对比两次评测运行：分类目通过率（Wilson 95% CI）、多重比较校正的 z 检验、翻转题清单。

口径：
- 每题一票（该题通过率），样本量按题数、不按运行次数（references/statistics.md）。
- 通过率、显著性检验、题数列都只计两次运行的共同题；全量题数只作描述（注行）。
- 类目在两次运行间改名会告警（按旧侧类目归类检验）。
- 多重比较默认 BH 校正（--correct bonferroni|none 可换/关）；单类目数据不把同一检验重复计 k。
- 数据卫生：按 (case_id, rep) 去重，重复行告警并忽略；rep 序号跳号告警。
  schema 校验、容错读取、去重与跳号检查的单一实现在 scripts/_common.py（flaky_report 共享同一份）。
- 翻转清单默认阈值 0.5，超过 20 条只列前 20（回归在前）并给出总数；清单为空但总体显著退步、
  或 ≥2 题同向一步变化且零反向时，会给出随 rep 自适应的调阈值命令（最小一步 1/n 向下取整两位）。

用法:
  python3 compare_runs.py runs/<old>/results.jsonl runs/<new>/results.jsonl
  python3 compare_runs.py old.jsonl new.jsonl --flip-threshold 0.33 --correct none

输入每行必须含（schema 校验，不合格退出码 2，stderr 报 文件:行号:原因）:
  case_id（不含 '|'）/ category（非空字符串，不含 '|'）/ rep（整数）/ passed（布尔——字符串 'false' 是真值，会被判成通过）
输出 markdown 到 stdout；差异均在噪声内时会在结论行明说。
退出码：0 正常对比 / 1 没有共同题 / 2 输入错误——schema 或 IO（根本没跑成）。
输出流约定：stdout = 报告全文（含卫生告警，可直接粘贴）；stderr = 致命错误（配 rc=2）。
"""
import argparse
import math

import _common

Z95 = 1.96


def wilson(p, n, z=Z95):
    if n == 0:
        return 0.0, 1.0
    d = 1 + z * z / n
    center = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, center - half), min(1.0, center + half)


def two_sided_p(z):
    return math.erfc(abs(z) / math.sqrt(2))


def bonferroni_adjust(pvals):
    return [min(p * len(pvals), 1.0) for p in pvals]


def bh_adjust(pvals):
    """BH step-up 校正 p 值（控 FDR；全零假设下等价于控族错误率）。"""
    k = len(pvals)
    order = sorted(range(k), key=lambda i: pvals[i])
    adj = [1.0] * k
    prev = 1.0
    for rank in range(k, 0, -1):
        i = order[rank - 1]
        prev = min(prev, pvals[i] * k / rank)
        adj[i] = min(prev, 1.0)
    return adj


def load(path):
    """读 results.jsonl（schema 校验/去重/rep 跳号检查的实现在 _common，与 flaky_report 共享）。"""
    cases, dups, gaps, errs = _common.load_results(path)
    _common.emit_schema_errors(errs)
    return cases, dups, gaps


def rates(cases, category=None):
    """每题一票：返回该类目下各题的通过率列表。样本量 = 题数。"""
    out = []
    for c in cases.values():
        if category is not None and c["category"] != category:
            continue
        if c["runs"]:
            out.append(c["passes"] / c["runs"])
    return out


def mean(xs):
    return sum(xs) / len(xs) if xs else 0.0


def z_test(p1, n1, p2, n2):
    pooled = (p1 * n1 + p2 * n2) / (n1 + n2)
    se = math.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    z = abs(p1 - p2) / se if se > 0 else 0.0
    return two_sided_p(z)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("old", help="旧运行 results.jsonl")
    ap.add_argument("new", help="新运行 results.jsonl")
    ap.add_argument("--flip-threshold", type=float, default=0.5,
                    help="单题通过率变化超过该值才列入翻转清单（默认 0.5）")
    ap.add_argument("--correct", choices=["bh", "bonferroni", "none"], default="bh",
                    help="多重比较校正：bh 控 FDR（默认）/ bonferroni 控族错误率 / none 关闭")
    args = ap.parse_args()

    old, odup, ogap = load(args.old)
    new, ndup, ngap = load(args.new)

    for label, (dn, dex), (gn, gex) in (("旧", odup, ogap), ("新", ndup, ngap)):
        msgs = []
        if dn:
            msgs.append(f"{dn} 行重复 (case_id, rep)（如 {', '.join(dex)}），重复行已忽略")
        if gn:
            msgs.append(f"{gn} 题 rep 序号不连续（如 {', '.join(gex)}）")
        if msgs:
            print(f"⚠️ 数据卫生（{label}运行）：" + "；".join(msgs) + "。")
            print()

    only_old = sorted(set(old) - set(new))
    only_new = sorted(set(new) - set(old))
    shared = sorted(set(old) & set(new))
    if not shared:
        raise SystemExit("两次运行没有共同 case_id，无法对比（检查 results.jsonl 的 case_id）")
    renamed = [cid for cid in shared if old[cid]["category"] != new[cid]["category"]]

    # ---- 逐类目行 + 总体行（检验都只计共同题）----
    cats = sorted({c["category"] for c in old.values()} | {c["category"] for c in new.values()})
    rows = []
    for cat in cats:
        n1_all, n2_all = len(rates(old, cat)), len(rates(new, cat))
        cids_cat = [cid for cid in shared if old[cid]["category"] == cat]
        if not cids_cat:
            a1, a2 = rates(old, cat), rates(new, cat)
            rows.append(dict(cat=cat, one_sided=True, n1=n1_all, n2=n2_all,
                             p1=mean(a1) if a1 else None, p2=mean(a2) if a2 else None))
            continue
        r1 = [old[cid]["passes"] / old[cid]["runs"] for cid in cids_cat]
        r2 = [new[cid]["passes"] / new[cid]["runs"] for cid in cids_cat]
        p1, p2 = mean(r1), mean(r2)
        rows.append(dict(cat=cat, one_sided=False, disp_n=f"{len(r1)}→{len(r2)}",
                         n1=len(r1), n2=len(r2), p1=p1, p2=p2,
                         pv=z_test(p1, len(r1), p2, len(r2))))
    r1 = [old[cid]["passes"] / old[cid]["runs"] for cid in shared]
    r2 = [new[cid]["passes"] / new[cid]["runs"] for cid in shared]
    p1, p2 = mean(r1), mean(r2)
    overall = dict(cat=None, one_sided=False, disp_n=f"{len(r1)}→{len(r2)}",
                   n1=len(r1), n2=len(r2), p1=p1, p2=p2,
                   pv=z_test(p1, len(r1), p2, len(r2)))

    # ---- 多重比较校正：对实际做了的检验族校正；单类目与总体同题时不重复计 k ----
    performed = [r for r in rows if not r["one_sided"]] + [overall]
    fam_idx = list(range(len(performed)))
    if len(performed) == 2 and math.isclose(performed[0]["pv"], performed[1]["pv"]):
        fam_idx = [0]
    fam_pv = [performed[i]["pv"] for i in fam_idx]
    if args.correct == "bonferroni":
        fam_adj = bonferroni_adjust(fam_pv)
    elif args.correct == "bh":
        fam_adj = bh_adjust(fam_pv)
    else:
        fam_adj = fam_pv
    for r in performed:
        r["adj"] = r["pv"]
    for i, a in zip(fam_idx, fam_adj):
        performed[i]["adj"] = a
    if len(fam_idx) < len(performed):
        performed[-1]["adj"] = fam_adj[0]

    print("| 类目 | 题数 | 旧通过率 | 新通过率 | Δ | 显著(α=0.05) |")
    print("|---|---|---|---|---|---|")
    any_sig = False
    for r in rows + [overall]:
        name = "**总体（共同题）**" if r["cat"] is None else str(r["cat"])
        if r["one_sided"]:
            c1 = "—" if r["p1"] is None else f"{r['p1']:.0%}"
            c2 = "—" if r["p2"] is None else f"{r['p2']:.0%}"
            d = "—" if (r["p1"] is None or r["p2"] is None) else f"{r['p2'] - r['p1']:+.0%}"
            print(f"| {name} | {r['n1']}→{r['n2']} | {c1} | {c2} | {d} | 不检验（仅单侧有题） |")
            continue
        lo1, hi1 = wilson(r["p1"], r["n1"])
        lo2, hi2 = wilson(r["p2"], r["n2"])
        sig = r["adj"] < 0.05
        any_sig = any_sig or sig
        if math.isclose(r["adj"], r["pv"], rel_tol=1e-9):
            sig_txt = f"**是** (p={r['pv']:.3f})" if sig else f"否 (p={r['pv']:.2f})"
        else:
            sig_txt = (f"**是** (p={r['pv']:.3f}→{r['adj']:.3f})" if sig
                       else f"否 (p={r['pv']:.2f}→{r['adj']:.2f})")
        print(f"| {name} | {r['disp_n']} | {r['p1']:.0%} [{lo1:.0%},{hi1:.0%}] "
              f"| {r['p2']:.0%} [{lo2:.0%},{hi2:.0%}] | {r['p2'] - r['p1']:+.0%} | {sig_txt} |")

    if args.correct != "none" and len(fam_pv) >= 2:
        print()
        print(f"（多重比较：{args.correct.upper()} 校正，k={len(fam_pv)}；显著列为 原始p→校正p）")

    if renamed:
        ex = ", ".join(f"{cid}: {old[cid]['category']}→{new[cid]['category']}" for cid in renamed[:3])
        print()
        print(f"⚠️ {len(renamed)} 题的类目在两次运行间改名（如 {ex}），"
              "类目表按旧侧类目归类检验。")
    if only_old or only_new:
        all1, all2 = rates(old), rates(new)
        print()
        print(f"注：通过率与检验只计共同题。全量通过率（描述性，不进检验）："
              f"旧 {mean(all1):.0%}（{len(all1)} 题）→ 新 {mean(all2):.0%}（{len(all2)} 题）。")
    for r in rows:
        if not (r["one_sided"] and r["n1"] == 0 and r["p2"] is not None and r["p2"] < 0.5):
            continue
        # 这些题在旧运行里搜得到 = 改名而非新增，交给上面的改名告警解释
        cat_cids_new = [cid for cid, c in new.items() if c["category"] == r["cat"]]
        if any(cid in old for cid in cat_cids_new):
            continue
        print(f"⚠️ 类目 {r['cat']} 仅新运行存在且通过率 {r['p2']:.0%}（{r['n2']} 题）"
              "——疑似新增类目整体翻车，需人工确认。")

    print()
    flips = []
    for cid in shared:
        p1 = old[cid]["passes"] / old[cid]["runs"]
        p2 = new[cid]["passes"] / new[cid]["runs"]
        if abs(p2 - p1) >= args.flip_threshold:
            flips.append((p2 - p1, cid, p1, p2))
    rep_mismatch = [cid for cid in shared if old[cid]["runs"] != new[cid]["runs"]]
    single_run = max(max(c["runs"] for c in old.values()),
                     max(c["runs"] for c in new.values())) <= 1
    if single_run:
        print("⚠️ 当前为单次运行（rep=1），翻转只是 0↔1 翻转、噪声大，建议 rep≥3 后再作为回归依据。")
        print()
    if rep_mismatch:
        head = rep_mismatch[0]
        print(f"⚠️ {len(rep_mismatch)} 题两次运行重复次数不一致"
              f"（如 {head}：旧 {old[head]['runs']} 次 vs 新 {new[head]['runs']} 次），"
              "通过率口径不对等，翻转与显著性判读需谨慎。")
        print()
    if flips:
        flips.sort(key=lambda x: x[0])
        cap = 20
        head = f"共 {len(flips)} 条"
        if len(flips) > cap:
            head += f"，仅列前 {cap} 条（回归在前）——过多通常意味着 rep 偏低或阈值过低"
        print(f"## 翻转题（单题通过率变化 ≥ {args.flip_threshold:.0%}，{head}）")
        for d, cid, p1, p2 in flips[:cap]:
            tag = "回归" if d < 0 else "改善"
            print(f"- [{tag}] {cid}: {p1:.0%} → {p2:.0%} ({d:+.0%})")
    else:
        print(f"无单题通过率变化 ≥ {args.flip_threshold:.0%} 的翻转题。")
        max_reps = max(max(c["runs"] for c in old.values()),
                       max(c["runs"] for c in new.values()))
        # 推荐阈值 = 最小一步 1/n 向下取整两位：正好卡在 1/n 会被浮点误差吃掉边界（rep=5 的 0.2 吃不到 4/5）
        step = math.floor((1 / max_reps) * 100 - 1e-6) / 100 if max_reps >= 2 else 0.49
        ds = [new[cid]["passes"] / new[cid]["runs"] - old[cid]["passes"] / old[cid]["runs"]
              for cid in shared]
        up = sum(1 for d in ds if d >= step)
        down = sum(1 for d in ds if d <= -step)
        if any_sig and overall["p2"] < overall["p1"]:
            print(f"⚠️ 翻转清单为空但总体显著退步（{overall['p1']:.0%} → {overall['p2']:.0%}）——"
                  f"整批小幅回归低于默认阈值，用 --flip-threshold {step} 查看逐题变化。")
        elif (down >= 2 and up == 0) or (up >= 2 and down == 0):
            n, tag = (down, "退步") if down else (up, "改善")
            leak = "；整批同向改善要警惕泄漏或过拟合（SKILL.md 第 6 节）" if tag == "改善" else ""
            print(f"⚠️ 翻转清单为空但有 {n} 题同向一步{tag}且无反向变化——"
                  f"整批小幅变化低于默认阈值{leak}，用 --flip-threshold {step} 查看逐题。")

    notes = []
    if only_old:
        notes.append(f"{len(only_old)} 题仅存在于旧运行（如 {', '.join(only_old[:5])}）")
    if only_new:
        notes.append(f"{len(only_new)} 题仅存在于新运行（如 {', '.join(only_new[:5])}）")
    if notes:
        print()
        print("注意：" + "；".join(notes) + "。")

    print()
    sig_cats = [r for r in rows if not r["one_sided"] and r["adj"] < 0.05]
    if overall["adj"] < 0.05:
        print(f"结论：总体存在统计显著差异（共同题 {overall['p1']:.0%} → {overall['p2']:.0%}）。"
              "显著项见上表；翻转题需逐个看输出，确认是真实回归而不是判定器抖动。")
    elif sig_cats:
        names = "、".join(str(r["cat"]) for r in sig_cats)
        print(f"结论：仅类目级显著（{names}），总体（共同题 {overall['p1']:.0%} → {overall['p2']:.0%}）"
              "不显著——括号里的总体数不显著，别当整体退步/提升读；类目级结论先按多重比较残留对待，"
              "复跑确认后再采信，翻转题逐个看输出。")
    else:
        print(f"结论：所有类目的差异均在噪声范围内（共同题 {overall['p1']:.0%} → {overall['p2']:.0%}），"
              "不可据此下结论。要么差异真不存在，要么题量不足以检出"
              "（见 references/statistics.md 的最小可检差异表）。")


if __name__ == "__main__":
    main()
