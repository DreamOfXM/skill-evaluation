# 技能评估框架

![License](https://img.shields.io/badge/License-Apache_2.0-blue?style=flat-square&logo=open-source-initiative)  
![Supported Frameworks](https://img.shields.io/badge/Frameworks-Claude_Qoder_LangChain_AutoGen-teal?style=flat-square&logo=langchain)

> 评估 agent skill 写作质量的框架 — 它评什么，不评什么。
>
> **v6.0.0（2026-11-10）判据已与全网最佳实践对齐**：description 评"何时用覆盖度"不评长度、可操作性按类型分档、新增正文体量预算与 with/without 价值增量对比。起因与回归数据见 `references/failure-log.md` #13。

[English](README.md) | [中文](README.zh-CN.md)

---

## 它评什么

评价 = 按失效分层模型检查——知道 skill 会在哪些层出问题，评价者才算称职：

| 层 | 失效形状 | 检测动作 | 快速 | 深度 |
|----|---------|---------|------|------|
| **触发质量** | 误触 / 漏触 | LLM 路由：description 触发覆盖度；关键词路由：词表规则＋test_triggers.py 实测 | ✓ | +实测 |
| **可操作性** | 指令含糊或矛盾、与任务类型不匹配 | 类型分档检测（引擎）＋矛盾检测 | ✓ | ✓ |
| **身份层** | 定位段自声明与正文矛盾 | 定位段 vs 工作流对读 | ✓ | ✓ |
| **口径层** | 多文档数字与说法不一 | 定向 grep + 复算 | ✓ | ✓ |
| **承诺层** | 引用的文件/命令不存在 | 前置存在性；--help＋真源审计＋依赖健康 | 前置 | ✓ |
| **方法论层** | 工作流步骤无主 | 每步找主＋跨工件术语比对 | ✗ | ✓ |
| **执行层** | 命令跑不通、退出码与承诺不符 | 实跑＋边界探针＋完备性检验 | ✗ | ✓ |
| **证据纪律层** | 评估者自己的失效：无源数字、无证据指控 | check_report.py 机械核 | ✓ | ✓ |

机械项（存在性/章节/元数据同步）全部在**前置检查**里——只做过/不过判定、不参与加权："补个文件就涨分"的路已关闭（5.0.4 补：不过项**不是涨分来源，但本身构成某层缺陷时就是降档依据**，须在层行标「降档依据＝前置 X」）。每层绑定检测动作；报告主体是带证据的层清检表，永远不是一句"没问题"。事故回流：每条真实失效固化成一条检查点（`references/failure-log.md`）。**判据归属（5.0.5）**：判据的修改权在被评方之外——评审者检出检的不合理，只能改自己的产物或摊出来讨论（起因见 failure-log #12）。**外部校准（6.0.0，2026-11-10）**：判据与全网最佳实践对齐——description 评"何时用覆盖度"不评长度、可操作性按类型分档、`_meta.json` 为环境适配项、新增正文体量检查与 with/without 价值增量对比、证据纪律改为报告合格门（起因见 failure-log #13）。

---

## 它不评什么

**快速模式是纯静态分析；深度模式会实跑 skill 自声明的命令做抽验。** 本框架永远不会做的是：

| 不评估 | 原因 |
|--------|------|
| 穷举式功能测试 | 深度模式只抽验 skill 自声明的命令，不枚举测试用例 |
| 安全审计 | 那是 `skill-vetter` 的职责 |
| 脚本代码质量 | Python/JS 写得好不好不在范围内 |
| "这个技能适合我的场景吗？" | 需要根据使用场景判断 |

**为什么这个区分很重要：**

Skill 写得好不好，最终看 agent 执行效果。但这两件事可能脱节：

- **写得好，用起来烂** → description 清楚、trigger 准确，但 agent 理解偏了或场景不匹配
- **写得烂，用起来行** → 全靠 agent 猜，换个场景就崩

快速模式只管前半段（写得怎么样）；深度模式通过实跑抽验后半段。

---

## 双模式评分

**快速模式（v6）**＝ 前置检查清单 ＋ 两个质量分：机械项（存在性/覆盖度标记/体量）只做过/不过判定、**不进分**；评分只剩触发质量（LLM 路由取 description 覆盖度）与可操作性（按类型分档），各 0-5，无综合分。引擎四维为静态诊断数据。

**深度模式（v6，定档权重；与 v5 及更早不可比）**：

| 档 | 层 | 权重 |
|----|----|------|
| 高 | 方法论 / 执行（含价值增量 with/without 对比） | 各 25% |
| 中 | 触发质量 / 可操作性 | 各 15% |
| 中 | 身份 / 口径复算 | 各 10% |

证据纪律层（v6 起）为**报告合格门**：`check_report.py` 机械核报红＝报告作废重做，不进被测 skill 的分。深度报告的综合分表须**逐层一行、权重写数值**，`check_report.py` 会复算 Σ(权重×得分) 与权重加总。深度报告在配置段 pin rubric hash（`shasum -a 256 references/skill-rubric.md | cut -c1-8`）。

---

## 两种评估模式

选择评估方式：

```markdown
你想怎么评估？

A) **快速评估** - 前置检查清单（机械项过/不过，不进分）+ 触发质量与可操作性两个质量分 + Top 3 问题  
B) **深度评估** - 快速评估 + 方法论层与执行层实跑验证（含价值增量 with/without 对比）+ 证据纪律层机械核（八层全检）；要实跑被测 skill 的命令，耗时可能较长

(选 A 或 B)
```

### 快速评估（默认）

- ✅ **内容包括**：前置检查清单（过/不过，不进分）、触发质量与可操作性两个质量分、静态诊断四维（引擎实测，仅诊断数据）、Top 3 问题
- ✅ **适用场景**：初步了解技能质量

### 深度评估

- ✅ **内容包括**：快速评估 + 触发词测试 + 方法论审计 + 执行层实跑（含价值增量对比）+ 证据纪律层机械核（`scripts/check_report.py`）
- ✅ **触发词测试**：关键词路由环境运行 `scripts/test_triggers.py` 实测命中率/误触率/漏触率；LLM 路由环境（无 trigger_words）改查 description 触发覆盖度
- ✅ **方法论审计**：工作流每步找主——命令、被委派文档或 AI 自身；仲裁表裁过的委派有效，无主步骤才算断链
- ✅ **执行层实跑**：每条自声明命令跑正常路径 + 边界探针（非法参数/文件不存在），退出码与文档契约逐项核对
- ✅ **价值增量对比（v6 新增）**：同一任务"带 / 不带 skill"两个干净上下文各跑一遍，报告"带 skill 才过"的差异点——命令能跑 ≠ skill 有用
- ✅ **证据标准**：每个检查点粘贴实际命令 + 退出码 + 输出摘录，"能跑"这类话术不算证据
- ✅ **结论列两段式（承诺/口径层）**：机械段逐字对引擎｜「人工」起头的复算段不受机械核，但 ⚠/✗ 仍要交证据块
- ✅ **证据纪律层 = 报告合格门（v6）**：机械核报红＝报告作废重做，不进被测 skill 的分
- ✅ **适用场景**：需要深入验证技能实际表现

**注意：** 必须通过选择题确认，禁止跳过此步直接开始评估。时间只做定性说明：深度评估要实跑被测 skill 的命令，耗时可能较长，不写具体分钟数。

### 为什么要这四个维度？

1. **触发准确性** - 技能最容易在*入口*失败。太宽泛=频繁误触，太狭窄=永不触发。

2. **触发覆盖度（description）** - 模型只读 description 决定选不选这个 skill。"何时用"没写就是没写——长度不是问题（官方范例数百字符），覆盖度才是。

3. **结构参考项** - 常见坑（gotchas）是全网公认性价比最高的正文内容；边界与示例帮模型少走弯路。

4. **指令可操作性** - 指令要与任务类型匹配：工具型要可执行锚点与验证闭环，咨询型要分支结构与解释 why；不可证伪的对冲词（"适当/酌情"）才是真问题。

---

## 评测数据

评测了热门技能（**4.x 历史口径**：静态四维分，可复现；v6 起判据已改——description 评覆盖度、可操作性分档，**下表读数与 v6 不可比**，仅作 v4 口径的历史存档）：

| 技能 | 评分 | 触发 | 描述 | 结构 | 可操作性 |
|------|------|------|------|------|---------|
| 技能评估框架（自评） | 4.8 ⚠️ | 4.0 | 5.0 | 5.0 | 5.0 |
| brainstorming | 2.7 | 1.0 ⚠️ | 2.5 ⚠️ | 4.2 | 3.0 |
| hallmark | 2.2 | 1.0 ⚠️ | 1.5 ⚠️ | 3.3 | 3.0 |
| marketing-ideas | 2.2 | 1.0 ⚠️ | 1.5 ⚠️ | 3.3 | 3.0 |
| ui-ux-pro-max | 2.4 | 1.0 ⚠️ | 1.5 ⚠️ | 4.2 | 3.0 |
| project-skills | 2.2 | 1.0 ⚠️ | 1.5 ⚠️ | 2.5 | 3.8 |

⚠️ 4.8 是当时快速模式的口径上限，不是高分；表内"描述 1.5-2.5"的低分是**旧字数判据**所致（这些 skill 无 `_meta.json`、description 偏长——按 v6 覆盖度判据多数应显著回升）。旧表的"发现：大多数技能在描述清晰度上得分低于 3.0"正是 failure-log #13 的起点：判据与官方范例方向相反。

> **v6 校准后的读数示例**：官方推荐写法的 acceptance-testing description 由 3.0＋字数警告 → **5.0**；无 `_meta.json` 的 karpathy-guidelines 由"高优先级：没有触发机制"误报 → **不适用**＋真建议（补负边界）。

---

## 快速开始

### 安装

一条命令，装好后 Claude Code、Cursor、Codex 等 agent 都能用：

```bash
npx skills add DreamOfXM/skill-evaluation
```

[![skills.sh](https://skills.sh/b/DreamOfXM/skill-evaluation)](https://skills.sh/DreamOfXM/skill-evaluation)

默认装进当前项目；加 `-g` 改成装进用户目录。用 `-a` 指定 agent——在 agent 会话里直接跑这条命令，文件会落到 `.agents/skills/`，而 Claude Code 不读这个目录：

```bash
npx skills add DreamOfXM/skill-evaluation -a claude-code
```

安装前想先看仓库里有什么：

```bash
npx skills add DreamOfXM/skill-evaluation --list
```

**手动安装** —— 把文件夹拷进你 agent 的 skills 目录：

```bash
git clone https://github.com/DreamOfXM/skill-evaluation.git
cp -r skill-evaluation ~/.agents/skills/
```

### 使用

```bash
# 评估任何技能（--mode 必填：quick=前置清单+两个质量分；deep=八层全检）
python3 ~/.agents/skills/skill-evaluation/scripts/evaluate_skill.py ~/.agents/skills/your-skill --mode quick

# JSON 输出用于自动化
python3 ~/.agents/skills/skill-evaluation/scripts/evaluate_skill.py ~/.agents/skills/your-skill --mode quick --output json
```

### Claude Code 集成

在任何 agent 对话中：

```text
评测 Claude Code 技能：  帮我评测一下 brainstorming skill
评测 Qoder 技能：         帮我评估一下 product-design skill
评测 LangChain 工具：     看看我的 LangChain 工具写得怎么样
```

---

## 评估报告示例（v6 形状）

```markdown
# 技能质量报告：my-awesome-skill @ <date>

## 配置段
- rubric: <shasum -a 256 references/skill-rubric.md | cut -c1-8>
- engine: evaluate_skill.py @ <版本>

## 前置检查（不进分）

| 前置项 | 结果 | 明细 |
|--------|------|------|
| description 触发覆盖度 / 正文体量 | 不过/警告 | 127 字 ✗何时用；612 行 超500行 |
| _meta trigger_words（环境适配）/ 引用存在性 / 元数据同步 | 过/不适用/存疑 | … |
| 结构参考项 | 参考 | 有：边界、示例；缺：常见坑、相关 |

## 层清检表（节选）

| 层 | 检测动作 | 结果 | 证据 |
|----|---------|------|------|
| 触发质量 | 覆盖度（LLM 路由）/ 词表＋实测 | ⚠ | ✗何时用，引擎 scores.description=2.0 |
| 可操作性 | 类型分档（机械段｜人工段取较低档） | ⚠ | 缺验证闭环，引擎 scores.actionability=… |
| 承诺层 | 前置存在性 | ✓ 通过（机械项）｜人工 ✗ 失效：README 引用 config/xx.json 不存在 | 见证据附录 |
| 执行层 | 实跑＋探针＋价值增量 | ⚠ | 带 skill 才过的断言 2 条；两侧无差异 1 条 |

## 质量分：触发质量 2.0 + 可操作性 3.0（快速模式无综合分）

## 问题列表
1. [高·触发] description 无触发语境——补 Use when + 用户原话
2. [高·承诺·人工] 引用文件不存在——修 README 或补文件

## 证据附录（深度模式必附）
<命令 + 退出码 + 输出摘录；价值增量附两侧对比>
```

---

## 理论背景

### 问题

技能是给LLM的指令。与传统代码不同：
- **输出是非确定性的**
- **"正确"有多种定义**
- **测试需要判断而非断言**

### 方法

1. **多维度评分** - 单看一项说明不了问题
2. **锚点标准** - 每项分数有明确定义，不靠感觉
3. **指出具体问题** - 哪里不对，为什么不对，怎么改
4. **持续追踪** - 改完再测，看分数有没有涨

---

## 与其他方案对比

| 功能 | 技能评估框架 | 人工审查 |
|------|-------------|---------|
| 客观评分 | ✅ | ❌ |
| 触发分析 | ✅ | ⚠️ |
| 可操作性检查 | ✅ | ⚠️ |
| 实跑验证（深度模式） | ✅ | ❌ |
| 报告诚实性核对 | ✅ | ❌ |
| 改进建议 | ✅ | ✅ |

---

## 项目结构

```
skill-evaluation/
├── SKILL.md                          # 主入口
├── scripts/
│   ├── evaluate_skill.py             # 核心评估引擎
│   ├── test_triggers.py              # 触发词测试
│   ├── compare_runs.py               # 改进前后对比
│   ├── flaky_report.py               # 差异检测
│   ├── check_selfconsistency.py      # 改名/搬动自检
│   ├── check_report.py               # 证据纪律层机械核
│   └── _common.py                    # 公共校验层
├── references/
│   ├── skill-rubric.md               # 评分标准
│   ├── trigger-testing.md            # 触发词分析方法
│   ├── meta-template.md              # _meta.json 模板
│   ├── failure-log.md                # 事故回流入口（失效→检查点）
│   ├── rubric-design.md              # rubric 校准（kappa）
│   ├── statistics.md                 # 样本量 / 最小可检差异
│   ├── harness.md                    # 运行 harness 契约
│   └── ablation.md                   # 消融方法
```

---

## 贡献

详见 [CONTRIBUTING.md](CONTRIBUTING.md)。

---

## 许可证

Apache License 2.0 - 详见 [LICENSE](LICENSE)。
