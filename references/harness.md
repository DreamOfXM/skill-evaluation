# Harness：目录、Schema、报告、对比

## 一次评测的目录布局

```
evals/
├── cases.jsonl            # 测试集（版本化，进 git）
├── rubrics/               # judge rubric 文件
│   └── reply-quality.md
├── checks/                # executable 判定用的脚本
├── runs/
│   ├── 2026-09-21T10-30-v0.3.0/
│   │   ├── results.jsonl  # 逐题逐次结果
│   │   └── report.md      # 本次报告（按 SKILL.md 模板）
│   └── 2026-09-25T09-12-v0.4.0/
└── bin/run.sh             # 一条命令跑全部：拉起被测系统 → 逐题执行 → 判定 → 落盘 → 出报告
```

原则：

- **一条命令**：`bin/run.sh` 让任何人不看文档也能重跑。手工步骤（手动贴 prompt、手动抄结果）是评测腐败的开始——一旦有人为凑结果重跑挑分，数字就再不可信。
- **改名/搬目录/动软链后自检**：`python3 ~/.agents/skills/skill-evaluation/scripts/check_selfconsistency.py`（name=目录名、_meta slug、内部引用路径含旧名残留、外部软链四项机器检查，rc=1 逐条列出问题）。2026-09-21 改名窗口这三处曾同时暗断，人眼一个都没看出来。
- **修 bug 先扫同类**：修任何缺陷前必须先问「这个缺陷类还住在哪」，逐脚本逐文档扫完再报完成——只修被点名的那一个实例，下轮评测还会抓出它的姊妹（2026-09-21 七评实证：截断只修了 compare 没扫 flaky、rc 契约漏了编码错误分支、当天新写的自检脚本自己违反当天定的契约）。
- runs/ 目录名含被测版本；报告里 pin 模型/温度/prompt 版本/commit/依赖版本。
- **失败样本全文落盘**（题目、完整输出、错误信息）。两周后没人记得当时为什么挂，落盘了才查得动。

`bin/run.sh` 的接口契约（每个项目自己实现，签名固定）：

```text
bin/run.sh --tier <smoke|regression|deep> [--reps N] [--system "<启动被测系统的命令>"] --out runs/<run_id>/
```

职责：按 tier 选出 cases.jsonl 的题 → 每题 × N 次：调用被测系统 → 按 grading 判定 → 写 results.jsonl 一行 → 失败输出存 outputs/ → 跑 `scripts/flaky_report.py` 生成 flaky 清单（rep=1 时该节标"不适用"）→ 生成 report.md。

## cases.jsonl：每行一题

```json
{
  "id": "reg-triple-quote-014",
  "category": "edge-cases",
  "tier": "regression",
  "source": "2026-09 工单 #382，用户贴三引号导致解析挂",
  "input": {"task": "...", "context": "..."},
  "grading": {"type": "executable", "cmd": ["bash", "checks/014.sh"], "expect_rc": 0}
}
```

grading 三型：

- `executable`：`{"type": "executable", "cmd": [...], "expect_rc": 0}`，可加 `expect_stdout_contains`
- `extraction`：`{"type": "extraction", "field": "answer.status", "op": "eq", "value": "refunded"}`，op ∈ eq / contains / gte / regex
- `judge`：`{"type": "judge", "rubric": "rubrics/reply-quality.md", "pass_total": 4}`，必须先完成 `references/rubric-design.md` 的校准流程

tier ∈ smoke / regression / deep，`bin/run.sh` 按 tier 选集。场景（SKILL.md 第一节）与 tier 的对应——runner 入参是 tier，别按场景名猜次数：

| 场景 | 用哪个 tier | 每题次数 |
|---|---|---|
| A 开发中快速迭代 | smoke | 1–2 |
| B 发版前深评（合入前） | regression | 3 |
| B 发版前深评（发版/换模型） | deep | 5 |
| C 线上监控 | 不走三档：线上持续抽样，rep=1，flaky 节标"不适用" | 1 |
| D 一次性能力对比 | 定制集或公开 benchmark，按其口径 | ≥3 |

写 `run.sh` 时注意：cases.jsonl 的 `id` 拷入 results.jsonl 时更名为 `case_id`。

## results.jsonl：每行一题的一次运行

```json
{
  "run_id": "2026-09-21T10-30-v0.3.0",
  "case_id": "reg-triple-quote-014",
  "category": "edge-cases",
  "rep": 2,
  "passed": false,
  "score": null,
  "latency_ms": 4210,
  "tokens_out": 812,
  "error": "JudgeCannotDecide",
  "output_path": "runs/2026-09-21T10-30-v0.3.0/outputs/reg-triple-quote-014.rep2.txt"
}
```

字段约定：`score` 仅 judge 判定时填写，= rubric 各维度得分之和；`passed` 由 rubric 里写死的及格线导出（不是从 score 反推）。executable / extraction 判定下 `score` 恒为 `null`。

## 对比两次运行

```bash
python3 ~/.agents/skills/skill-evaluation/scripts/compare_runs.py \
  evals/runs/2026-09-21T10-30-v0.3.0/results.jsonl \
  evals/runs/2026-09-25T09-12-v0.4.0/results.jsonl
```

（skill 迁移/分享到别的机器时，把上面的路径前缀替换成实际安装目录。）

输出：分类目通过率（带 Wilson CI）、双比例 z 检验显著性、翻转题清单（回归/改善）。所有差异都在噪声内时，结论行会明说"不可下结论"。通过率与显著性均按**题数口径**（每题一票，见 `references/statistics.md`）；按运行次数口径产出的历史报告与新口径不可直接对比。显著性默认对 k 个检验做 **BH 校正**（`--correct bonferroni|none` 可换/关）；总体与类目检验、题数列都只计两次运行的共同题（全量题数在注行），仅单侧有题的类目标"不检验"，类目改名会告警。results.jsonl 按 `(case_id, rep)` 去重，重复行与 rep 跳号会告警（flaky_report 同样去重并告警；公共实现在 `scripts/_common.py`，两个脚本单一真源）。翻转清单默认阈值 0.5，用 `--flip-threshold` 调低；阈值要**低于**最小一步（1/每题次数）才能覆盖它——rep=3 用 `--flip-threshold 0.33`、rep=5 用 `--flip-threshold 0.19`（不能正好卡在 1/n 上，浮点误差会吃掉边界值）。清单为空但总体显著退步、或 ≥2 题同向一步变化且零反向时，脚本会自动给出带确切值的具体命令。输入 schema 严格校验：缺必填字段、passed 非布尔（字符串 'false' 是真值、会被判成通过）、rep 非整数、category/case_id 含 '|' 都以退出码 2 拒绝，stderr 报 文件:行号:原因。翻转清单超过 20 条只列前 20（回归在前）并给总数。输出流约定：stdout = 报告全文（含卫生告警，直接粘贴）；stderr 只放致命错误（schema/IO，配 rc=2）。

## 闭环：失败回流

每次评测后：新失败题（尤其线上翻车）补进 cases.jsonl（tier=regression，source 写清来源）→ 提交。测试集只删过时题（对应功能已下线），**不删挂掉的题**。
