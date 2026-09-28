# Agent Skill Quality Review

![License](https://img.shields.io/badge/License-Apache_2.0-blue?style=flat-square&logo=open-source-initiative) 
![Frameworks](https://img.shields.io/badge/Frameworks-Claude_Qoder_LangChain_AutoGen-teal?style=flat-square&logo=langchain)

> ✅ **Multi-Agent Framework Compatible**: Claude Code Skills, Qoder Skills, LangChain Tools, AutoGen Agents and other LLM applications  
> ❌ Not specific to any single agent platform (e.g., not limited to Claude Code)

[English](README.md) | [中文](README.zh-CN.md)

---

## What It Evaluates

Evaluation = checking a skill against a **layered failure model** — knowing where skills break is what qualifies an evaluator:

| Layer | Failure Shape | Detection Action | Quick | Deep |
|-------|--------------|------------------|-------|------|
| **Trigger quality** | misfire-prone word choices | bad-word rules; `test_triggers.py` | ✓ | +live |
| **Actionability** | vague or contradictory instructions | vague-word / contradiction rules (engine) | ✓ | ✓ |
| **Identity** | self-description contradicts the body | read positioning vs workflow side by side | ✓ | ✓ |
| **Consistency** | numbers/claims differ across docs | targeted grep + recomputation | ✓ | ✓ |
| **Promise** | referenced files/commands don't exist | precheck existence; `--help` + source audit + dependency health | precheck | ✓ |
| **Methodology** | workflow steps with no owner | assign an owner per step; cross-artifact term comparison | ✗ | ✓ |
| **Execution** | declared commands fail or exit codes mismatch the contract | live runs + boundary probes + good/bad-sample completeness gate | ✗ | ✓ |
| **Evidence discipline** | the evaluator's own failures: sourceless numbers, unevidenced claims | `check_report.py` mechanical check | ✓ | ✓ |

Mechanical items (file existence, word counts, required sections, metadata sync) live in the **precheck** — pass/fail only, no score weight. Padding a file can no longer buy score; the deep composite is earned through behavioral and judgment-based criteria (tiered weights below). Every layer binds a detection action; the report is a layer-by-layer clearance list with evidence — never a bare "no problems". Incidents feed back: every real failure becomes a check (`references/failure-log.md`).

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

**Quick mode (v5)** = a precheck list + two quality scores: mechanical items (existence / word count / required sections) are pass-or-fail only and **carry no score weight**; the scored items are trigger quality and actionability (0-5 each, no composite). The engine's four dimensions are downgraded to diagnostic data.

**Deep mode (v5, tiered weights)**:

| Tier | Layers | Weight |
|------|--------|--------|
| High | Evidence discipline / Methodology / Execution | 20% each |
| Mid | Identity / Consistency recomputation / Trigger quality / Actionability | 10% each |

Tiering rationale: an incident distribution of n=9 supports exactly one ordering claim (evidence discipline on top), not decimal-level tuning. Mechanical items all moved into the precheck — **the deep composite can only be earned through behavioral and judgment-based criteria**. Deep reports pin the rubric hash in a config section (`shasum -a 256 references/skill-rubric.md | cut -c1-8`).

Deep mode additionally includes:

- **Trigger testing** — run `scripts/test_triggers.py` for measured hit / false-positive / miss rates
- **Methodology audit** — every workflow step must have an owner: a command, a delegated doc, or the AI itself; delegation via an arbitration table counts, ownerless steps don't
- **Real-run verification** — run the skill's declared commands (tool-type) or walk its instructions on a real case (advisory-type), pasting command + exit code + output excerpt as evidence
- **Evidence-discipline check** — `scripts/check_report.py` mechanically verifies the report itself (anchor numbers / layer verdicts / evidence blocks); promise/consistency verdict cells use a two-segment form — mechanical segment verbatim from the engine ｜ human recomputation segment, which still owes evidence blocks

Deep mode actually runs the skill's commands, so it may take considerably longer — the time promise is qualitative only, no fixed minutes.

### Why These Dimensions?

1. **Trigger Accuracy** - Skills fail most often at the *entry point*. Too broad = misfires. Too narrow = never activates.

2. **Description Clarity** - Users decide in 3 seconds based on description. Vague = abandoned.

3. **Structure Completeness** - Skills with clear boundaries (what it does + doesn't do) have higher user satisfaction.

4. **Actionability** - Vague instructions ("consider", "when appropriate") cause LLM confusion. Precise instructions = reliable behavior.

---

## Benchmark Results

Evaluated popular skills (**legacy 4.x scale**: static four-dimension score, engine-measured and reproducible; since v5 the engine's four dims are diagnostic data, not comparable with v5 scoring):

| Skill | Score | Trigger | Description | Structure | Actionability |
|-------|-------|---------|-------------|-----------|---------------|
| skill-evaluation (self-scored) | 4.8 ⚠️ | 4.0 | 5.0 | 5.0 | 5.0 |
| brainstorming | 2.7 | 1.0 ⚠️ | 2.5 ⚠️ | 4.2 | 3.0 |
| hallmark | 2.2 | 1.0 ⚠️ | 1.5 ⚠️ | 3.3 | 3.0 |
| marketing-ideas | 2.2 | 1.0 ⚠️ | 1.5 ⚠️ | 3.3 | 3.0 |
| ui-ux-pro-max | 2.4 | 1.0 ⚠️ | 1.5 ⚠️ | 4.2 | 3.0 |
| project-skills | 2.2 | 1.0 ⚠️ | 1.5 ⚠️ | 2.5 | 3.8 |

⚠️ 4.8 is the maximum quick mode can produce, not a high score: the trigger dimension is capped at 4.0 in the engine (`evaluate_skill.py:109`) and the four dimensions weigh 0.25 each, so `0.25×4.0 + 0.25×5.0×3 = 4.75 → 4.8`. The first row is this tool grading its own homework — read the other five.

> **Finding:** Most evaluated skills scored below 3.0 on trigger accuracy and description clarity. Common issues: missing `_meta.json`, overly long descriptions, no trigger word optimization.

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

## Evaluation Report Example (v5 shape)

```markdown
# Skill Quality Report: my-awesome-skill @ <date>

## Config section
- rubric: <shasum -a 256 references/skill-rubric.md | cut -c1-8>
- engine: evaluate_skill.py @ <version>

## Precheck (unscored)

| Item | Result | Detail |
|------|--------|--------|
| _meta.json + trigger_words | fail | no trigger_words |
| description length/patterns | warn | 127 chars |
| Six required sections | missing | boundary, examples |

## Layer clearance (excerpt)

| Layer | Detection action | Result | Evidence |
|-------|-----------------|--------|----------|
| Trigger quality | bad-word rules | ⚠ | contains "帮我", engine scores.trigger=… |
| Actionability | vague-word rules | ⚠ | "适当" ×2, engine scores.actionability=… |
| Promise | precheck existence | ✓ pass (mechanical) ｜ human ✗ fail: README references config/xx.json which doesn't exist | see evidence appendix |

## Quality scores: trigger 2.5 + actionability 3.0 (quick mode has no composite)

## Issues
1. [high·precheck] no trigger_words — add _meta.json
2. [high·promise·human] referenced file missing — fix README or add the file

## Evidence appendix (deep mode required)
<command + exit code + output excerpt>
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
