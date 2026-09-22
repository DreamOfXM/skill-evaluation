#!/usr/bin/env python3
"""skill 自检：改名/搬目录/动软链之后跑一遍，把机器可查的一致性全部查掉。

检查项（每一项都对应 2026-09-21 改名断链窗口里真实断过的东西）：
  1. SKILL.md frontmatter name == 目录名（不等 → 加载列表丢 description、触发词全废）
  2. _meta.json slug == 目录名
  3. 文内引用的 skills/<名字>/<路径> 若指向本库自有文件却不存在 → 疑似旧名/搬家残留
  4. ~/.zcode/skills/ 与 ~/.openclaw/workspace/skills/ 下的同名软链（若存在）解析回本目录

读不了的文件（缺失/编码错误）记为问题而不是崩溃——本脚本 rc=1 的含义是"发现一致性问题"，
崩溃混进 rc=1 等于让测量仪器说谎。
用法: python3 check_selfconsistency.py    # rc=0 全过 / rc=1 逐条列出问题（stderr）
"""
import argparse
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAME = os.path.basename(ROOT)
HOME = os.path.expanduser("~")


def read_text(path, problems, label):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError as e:
        problems.append(f"{label} 读不了：{e}")
    except UnicodeDecodeError as e:
        problems.append(f"{label} 不是 UTF-8：{e}")
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.parse_args()  # 不接收位置参数：让 --help 正常、未知参数报错，不再吞参数回 OK
    problems = []
    own_files = set()
    for sub in ("references", "scripts"):
        d = os.path.join(ROOT, sub)
        if os.path.isdir(d):
            own_files.update(os.listdir(d))

    head = read_text(os.path.join(ROOT, "SKILL.md"), problems, "SKILL.md")
    if head is not None:
        m = re.search(r"^name:\s*(\S+)", head[:2048], re.M)
        if not m:
            problems.append("SKILL.md 缺 name 字段")
        elif m.group(1) != NAME:
            problems.append(f"SKILL.md name={m.group(1)} != 目录名 {NAME}（加载列表会丢 description，触发词全废）")

    meta_raw = read_text(os.path.join(ROOT, "_meta.json"), problems, "_meta.json")
    if meta_raw is not None:
        try:
            meta = json.loads(meta_raw)
            if meta.get("slug") != NAME:
                problems.append(f"_meta.json slug={meta.get('slug')!r} != 目录名 {NAME}")
        except json.JSONDecodeError as e:
            problems.append(f"_meta.json 不是合法 JSON：{e}")

    pat = re.compile(r"[\w./~-]*skills/([\w.-]+)/([\w./-]+)")
    for sub in ("references", "scripts"):
        d = os.path.join(ROOT, sub)
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            path = os.path.join(d, fn)
            if not fn.endswith((".md", ".py")) or not os.path.isfile(path):
                continue
            text = read_text(path, problems, f"{sub}/{fn}")
            if text is None:
                continue
            for hit in sorted({m.group(0) for m in pat.finditer(text)}):
                if os.path.exists(os.path.expanduser(hit)):
                    continue
                base = hit.rsplit("/", 1)[-1]
                if base in own_files:
                    problems.append(f"{sub}/{fn} 引用的路径不存在且指向本库自有文件 {base}"
                                    f"（疑似旧名/搬家残留）：{hit}")

    for partner in (f"{HOME}/.zcode/skills/{NAME}", f"{HOME}/.openclaw/workspace/skills/{NAME}"):
        if os.path.islink(partner):
            target = os.path.realpath(partner)
            if target != os.path.realpath(ROOT):
                problems.append(f"软链 {partner} -> {target}，未指回本目录")

    if problems:
        for p in problems:
            print(f"✗ {p}", file=sys.stderr)
        raise SystemExit(1)
    print(f"OK：name/slug={NAME}；内部引用路径、外部软链全部一致")


if __name__ == "__main__":
    main()
