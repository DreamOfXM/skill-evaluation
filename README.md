# Agent Skill Quality Review

![License](https://img.shields.io/badge/License-Apache_2.0-blue?style=flat-square&logo=open-source-initiative) 
![Frameworks](https://img.shields.io/badge/Frameworks-Claude_Qoder_LangChain_AutoGen-teal?style=flat-square&logo=langchain)

> ✅ **Multi-Agent Framework Compatible**: Claude Code Skills, Qoder Skills, LangChain Tools, AutoGen Agents and other LLM applications  
> ❌ Not specific to any single agent platform (e.g., not limited to Claude Code)  
> 🔁 **v6.0.0 (2026-11-10) criteria realigned with worldwide best practice** — description scored on trigger coverage (not length), type-tiered actionability, body-size budget, and a with/without value-delta check. Origin & regression data: `references/failure-log.md` #13.

[English](README.md) | [中文](README.zh-CN.md)

---

## What It Evaluates

Evaluation = checking a skill against a **layered failure model** — knowing where skills break is what qualifies an evaluator:

| Layer | Failure Shape | Detection Action | Quick | Deep |
|-------|--------------|------------------|-------|------|
| **Trigger quality** | misfires / never triggers | LLM routing: description trigger-coverage; keyword routing: bad-word rules + `test_triggers.py` | ✓ | +live |
| **Actionability** | vague/contradictory instructions, or rigidity mismatched to task type | type-tiered detection (engine) + contradiction rules | ✓ | ✓ |
| **Identity** | self-description contradicts the body | read positioning vs workflow side by side | ✓ | ✓ |
| **Consistency** | numbers/claims differ across docs | targeted grep + recomputation | ✓ | ✓ |
| **Promise** | referenced files/commands don't exist | precheck existence; `--help` + source audit + dependency health | precheck | ✓ |
| **Methodology** | workflow steps with no owner | assign an owner per step; cross-artifact term comparison | ✗ | ✓ |
| **Execution** | declared commands fail or exit codes mismatch the contract | live runs + boundary probes + good/bad-sample completeness gate | ✗ | ✓ |
| **Evidence discipline** | the evaluator's own failures: sourceless numbers, unevidenced claims | `check_report.py` mechanical check | ✓ | ✓ |

Mechanical items (file existence, coverage markers, body-size budget, metadata sync) live in the **precheck** — pass/fail only, no score weight. Padding a file can no longer buy score (since 5.0.4 a precheck failure may still **cap** the layer it actually breaks, labelled 降档依据＝前置 X). Every layer binds a detection action; the report is a layer-by-layer clearance list with evidence — never a bare "no problems". Incidents feed back: every real failure becomes a check (`references/failure-log.md`). **Who owns a criterion (5.0.5)**: changing one is the authority of someone outside the party being graded (origin: failure-log #12). **External calibration (6.0.0, 2026-11-10)**: criteria realigned with worldwide best practice — description scored on *trigger coverage* (what + when-to-use + negative boundary), never on length; actionability tiered by skill type; `_meta.json` demoted to environment-adaptive; new body-size budget and with/without value-delta comparison; evidence discipline became a report-validity gate (origin: failure-log #13).

---

## What It Doesn't Evaluate

**Quick mode is static analysis. Deep mode additionally runs the skill's declared commands (sampled verification).** What this framework never does:

| Not Evaluated | Reason |
|---------------|-------|
| Exhaustive functional testing | Deep mode samples the skill's own declared commands; it doesn't enumerate test cases |
| Security audit | That's `skill-vetter`'s job |
| Script/code quality | Whether the Python/JS is well-written is out of scope |
| "Is this skill appropriate for my scenario?" | This is a judgment call based on use case |

**Why this distinction matters:**

A well-written skill doesn't guarantee good execution. These can diverge:

- **Well-written, bad results** → Clear description, good triggers, but agent misinterprets or wrong scenario
- **Poorly written, works anyway** → Relies on agent guessing, breaks in different scenarios

Quick mode covers the first half (is it well-written?); deep mode samples the second half by actually running the skill.

---

## Two Evaluation Modes

**Quick mode (v6)** = a precheck list + two quality scores: mechanical items (existence / coverage markers / body size) are pass-or-fail only and **carry no score weight** (a precheck failure may still **cap** the layer it actually breaks, labelled 降档依据＝前置 X); the scored items are trigger quality (LLM routing reads description coverage) and type-tiered actionability (0-5 each, no composite). The engine's four dimensions are diagnostic data.

**Deep mode (v6, tiered weights; not comparable with v5 and earlier)**:

| Tier | Layers | Weight |
|------|--------|--------|
| High | Methodology / Execution (incl. with/without value-delta) | 25% each |
| Mid | Trigger quality / Actionability | 15% each |
| Mid | Identity / Consistency recomputation | 10% each |

The evidence-discipline layer (since v6) is a **report-validity gate**: `check_report.py` failing means the report is void and must be redone — it never subtracts from the evaluated skill's score. Deep reports pin the rubric hash in a config section (`shasum -a 256 references/skill-rubric.md | cut -c1-8`).

Deep mode additionally includes:

- **Trigger testing** — keyword-routing environments run `scripts/test_triggers.py` for measured hit / false-positive / miss rates; LLM-routing environments (no trigger_words) are judged on description trigger coverage instead
- **Methodology audit** — every workflow step must have an owner: a command, a delegated doc, or the AI itself; delegation via an arbitration table counts, ownerless steps don't
- **Real-run verification** — run the skill's declared commands (tool-type) or walk its instructions on a real case (advisory-type), pasting command + exit code + output excerpt as evidence
- **Value-delta comparison (new in v6)** — run the same task twice, with and without the skill, in two clean contexts; report the assertions that pass *only with* the skill. Commands running ≠ the skill being useful
- **Evidence-discipline gate (since v6)** — `scripts/check_report.py` mechanically verifies the report itself (anchor numbers / layer verdicts / evidence blocks / composite arithmetic); failing it voids the report — it never subtracts from the evaluated skill's score. Promise/consistency verdict cells use a two-segment form — mechanical segment verbatim from the engine ｜ human recomputation segment, which still owes evidence blocks

Deep mode actually runs the skill's commands, so it may take considerably longer — the time promise is qualitative only, no fixed minutes.

### Why These Dimensions?

1. **Trigger Accuracy** - Skills fail most often at the *entry point*. Too broad = misfires. Too narrow = never activates.

2. **Trigger Coverage (description)** - The model reads only the description when choosing a skill. If "when to use" isn't written, it doesn't exist — length is a non-issue (official exemplars run hundreds of chars); coverage is everything.

3. **Structure Reference Items** - Gotchas sections are the highest-value body content in worldwide practice; boundaries and examples save the model detours.

4. **Actionability** - Instructions must match the task type: tool-type needs executable anchors and verification loops; advisory-type needs branch structure and explained *why*. Unfalsifiable hedges ("适当 / when appropriate") are the real problem.

---

## Benchmark Results

Evaluated popular skills (**legacy 4.x scale**: static four-dimension score, engine-measured and reproducible; since v6 the criteria changed — description scored on coverage, actionability tiered by type — **the table below is not comparable with v6**, kept as a v4-era archive):

| Skill | Score | Trigger | Description | Structure | Actionability |
|-------|-------|---------|-------------|-----------|---------------|
| skill-evaluation (self-scored) | 4.8 ⚠️ | 4.0 | 5.0 | 5.0 | 5.0 |
| brainstorming | 2.7 | 1.0 ⚠️ | 2.5 ⚠️ | 4.2 | 3.0 |
| hallmark | 2.2 | 1.0 ⚠️ | 1.5 ⚠️ | 3.3 | 3.0 |
| marketing-ideas | 2.2 | 1.0 ⚠️ | 1.5 ⚠️ | 3.3 | 3.0 |
| ui-ux-pro-max | 2.4 | 1.0 ⚠️ | 1.5 ⚠️ | 4.2 | 3.0 |
| project-skills | 2.2 | 1.0 ⚠️ | 1.5 ⚠️ | 2.5 | 3.8 |

⚠️ The low "Description 1.5–2.5" scores below came from the **old length-based criterion** (those skills had no `_meta.json` and longer descriptions — under v6's coverage criterion most would score markedly higher). That old finding was exactly the starting point of failure-log #13: the criterion pointed the opposite way from official exemplars.

> **v6 recalibration readings**: acceptance-testing (official-recommended style) description 3.0 + length warning → **5.0**; karpathy-guidelines (no `_meta.json`) "high-priority: no trigger mechanism" false positive → **not applicable** + a real suggestion (add negative boundary).

---

## Quick Start

### Installation

One command. It installs into Claude Code, Cursor, Codex and other agents:

```bash
npx skills add DreamOfXM/skill-evaluation
```

[![skills.sh](https://skills.sh/b/DreamOfXM/skill-evaluation)](https://skills.sh/DreamOfXM/skill-evaluation)

This installs into the current project. Add `-g` to install for your user instead. Use `-a` to name the agent explicitly — running the command from inside an agent session otherwise lands the files in `.agents/skills/`, which Claude Code does not read:

```bash
npx skills add DreamOfXM/skill-evaluation -a claude-code
```

To check what a repository contains before installing anything:

```bash
npx skills add DreamOfXM/skill-evaluation --list
```

**Manual install** — copy the folder into your agent's skills directory:

```bash
git clone https://github.com/DreamOfXM/skill-evaluation.git
cp -r skill-evaluation ~/.agents/skills/
```

### Usage Examples

**In any agent conversation:**

```text
Evaluate a Claude Code skill:  skill review for the brainstorming skill
Evaluate a Qoder skill:        run skill evaluation on the product-design skill
Evaluate a LangChain tool:     give my LangChain tool a skill quality report
```

**Engine (precheck + static diagnostics, `--mode` required):**

```bash
python3 scripts/evaluate_skill.py ~/.agents/skills/your-skill --mode quick
```

---

## Evaluation Report Example (v6 shape)

```markdown
# Skill Quality Report: my-awesome-skill @ <date>

## Config section
- rubric: <shasum -a 256 references/skill-rubric.md | cut -c1-8>
- engine: evaluate_skill.py @ <version>

## Precheck (unscored)

| Item | Result | Detail |
|------|--------|--------|
| description trigger coverage / body size | fail/warn | 127 chars ✗when-to-use; 612 lines over budget |
| _meta trigger_words (env-adaptive) / file existence / metadata sync | pass/n-a/doubt | … |
| Structure reference items | reference | has: boundary, examples; missing: gotchas, related |

## Layer clearance (excerpt)

| Layer | Detection action | Result | Evidence |
|-------|-----------------|--------|----------|
| Trigger quality | coverage (LLM routing) / lexicon + live test | ⚠ | ✗when-to-use, engine scores.description=2.0 |
| Actionability | type-tiered (mechanical ｜ human, take lower) | ⚠ | no verification loop, engine scores.actionability=… |
| Promise | precheck existence | ✓ pass (mechanical) ｜ human ✗ fail: README references config/xx.json which doesn't exist | see evidence appendix |
| Execution | live runs + probes + value delta | ⚠ | 2 assertions pass only with skill; 1 with no difference |

## Quality scores: trigger 2.0 + actionability 3.0 (quick mode has no composite)

## Issues
1. [high·trigger] description has no when-to-use context — add "Use when" + user phrasings
2. [high·promise·human] referenced file missing — fix README or add the file

## Evidence appendix (deep mode required)
<command + exit code + output excerpt; value-delta comparison attached>
```

---

## Theory

### The Problem

Skills are instructions for LLMs. Unlike traditional code:
- **Output is non-deterministic**
- **"Correct" has multiple definitions**
- **Testing requires judgment, not assertions**

### Approach

1. **Multi-dimensional scoring** - No single metric captures quality
2. **Anchor-based rubrics** - Scores have specific, measurable criteria
3. **Actionable feedback** - Problems point to solutions
4. **Iterative improvement** - Track progress over time

---

## Comparison

| Feature | Skill Evaluation | Manual Review |
|---------|------------------|---------------|
| Objective scoring | ✅ | ❌ |
| Trigger analysis | ✅ | ⚠️ |
| Actionability check | ✅ | ⚠️ |
| Real-run verification (deep mode) | ✅ | ❌ |
| Honesty check on the report itself | ✅ | ❌ |
| Improvement suggestions | ✅ | ✅ |

---

## Architecture

```
skill-evaluation/
├── SKILL.md                          # Main entry point
├── scripts/
│   ├── evaluate_skill.py             # Core evaluation engine
│   ├── test_triggers.py              # Trigger word testing
│   ├── compare_runs.py               # Before/after comparison
│   ├── flaky_report.py               # Variance detection
│   ├── check_selfconsistency.py      # Rename/move self-check
│   ├── check_report.py               # Evidence-discipline mechanical check
│   └── _common.py                    # Shared validation layer
├── references/
│   ├── skill-rubric.md               # Scoring criteria
│   ├── trigger-testing.md            # Trigger analysis method
│   ├── meta-template.md              # _meta.json template
│   ├── failure-log.md                # Incident intake (failures become checks)
│   ├── rubric-design.md              # Rubric calibration (kappa)
│   ├── statistics.md                 # Sample size / MDE reference
│   ├── harness.md                    # Run harness contract
│   └── ablation.md                   # Ablation method
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## License

Apache License 2.0 - see [LICENSE](LICENSE).
