# Agent Skill Quality Review

<p align="center">
  <img src="https://img.shields.io/badge/Skill%20Score-4.8%2F5-brightgreen?style=for-the-badge" alt="Skill Score">
  <img src="https://img.shields.io/badge/License-Apache%202.0-blue?style=for-the-badge" alt="License">
  <img src="https://img.shields.io/badge/Supported%20Frameworks-Claude%20|%20Qoder%20|%20LangChain%20|%20AutoGen-green?style=for-the-badge" alt="Frameworks">
</p>

> ✅ **Multi-Agent Framework Compatible**：Claude Code Skills、Qoder Skills、LangChain Tools、AutoGen Agents 以及其他 LLM 应用<br>
> ❌ Not specific to any single agent platform (e.g., not limited to Claude Code)

[English](README.md) | [中文](README.zh-CN.md)

---

## What It Evaluates

Evaluation = checking a skill against a **layered failure model** — knowing where skills break is what qualifies an evaluator:

| Layer | Failure Shape | Detection Action | Quick | Deep |
|-------|--------------|------------------|-------|------|
| **Trigger** | misfires / misses | trigger_words static rules; `test_triggers.py` | static | +live |
| **Writing quality** | vague description, missing sections, ambiguous instructions | rubric rules (engine) | ✓ | ✓ |
| **Identity** | self-description contradicts the body | read positioning vs workflow side by side | ✓ | ✓ |
| **Consistency** | numbers/claims differ across docs | targeted grep + recomputation | ✓ | ✓ |
| **Promise** | referenced files/commands don't exist | existence check; `--help` | existence | +live |
| **Methodology** | workflow steps with no owner | assign an owner per step (command / delegated doc / the AI itself) | ✗ | ✓ |
| **Execution** | declared commands fail or exit codes mismatch the contract | live runs + boundary probes | ✗ | ✓ |

Every layer binds a detection action; the report is a layer-by-layer clearance list with evidence — never a bare "no problems". Incidents feed back: every real failure becomes a check (`references/failure-log.md`).

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

**Quick mode** outputs a static four-dimension score (trigger / description / structure / actionability, 25% each — engine-measured), plus a layer clearance table for identity / consistency / promises (pass / suspect / fail, not rolled into the number).

**Deep mode** adds a methodology audit and live runs of declared commands, producing a seven-layer weighted composite:

| Layer | Weight |
|-------|--------|
| Trigger | 15% |
| Writing quality | 15% |
| Identity | 10% |
| Consistency | 10% |
| Promise | 10% |
| Methodology | 20% |
| Execution | 20% |

Deep mode additionally includes:

- **Trigger testing** — run `scripts/test_triggers.py` for measured hit / false-positive / miss rates
- **Methodology audit** — every workflow step must have an owner: a command, a delegated doc, or the AI itself; delegation via an arbitration table counts, ownerless steps don't
- **Real-run verification** — run the skill's declared commands (tool-type) or walk its instructions on a real case (advisory-type), pasting command + exit code + output excerpt as evidence

Deep mode actually runs the skill's commands, so it may take considerably longer — the time promise is qualitative only, no fixed minutes.

### Why These Dimensions?

1. **Trigger Accuracy** - Skills fail most often at the *entry point*. Too broad = misfires. Too narrow = never activates.

2. **Description Clarity** - Users decide in 3 seconds based on description. Vague = abandoned.

3. **Structure Completeness** - Skills with clear boundaries (what it does + doesn't do) have higher user satisfaction.

4. **Actionability** - Vague instructions ("consider", "when appropriate") cause LLM confusion. Precise instructions = reliable behavior.

---

## Benchmark Results

Evaluated popular skills (static four-dimension scores, quick mode, engine-measured and reproducible):

| Skill | Score | Trigger | Description | Structure | Actionability |
|-------|-------|---------|-------------|-----------|---------------|
| **skill-evaluation** | **4.8** | 4.0 | 5.0 | 5.0 | 5.0 |
| brainstorming | 2.7 | 1.0 ⚠️ | 2.5 ⚠️ | 4.2 | 3.0 |
| hallmark | 2.2 | 1.0 ⚠️ | 1.5 ⚠️ | 3.3 | 3.0 |
| marketing-ideas | 2.2 | 1.0 ⚠️ | 1.5 ⚠️ | 3.3 | 3.0 |
| ui-ux-pro-max | 2.4 | 1.0 ⚠️ | 1.5 ⚠️ | 4.2 | 3.0 |
| project-skills | 2.2 | 1.0 ⚠️ | 1.5 ⚠️ | 2.5 | 3.8 |

> **Finding:** Most evaluated skills scored below 3.0 on trigger accuracy and description clarity. Common issues: missing `_meta.json`, overly long descriptions, no trigger word optimization.

---

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/DreamOfXM/skill-evaluation.git

# Add as an agent skill (any platform)
cp -r skill-evaluation ~/.agents/skills/
```

### Usage Examples

**In any agent conversation:**

```bash
# Evaluate a Claude Code skill
帮我评测一下 brainstorming skill

# Evaluate a Qoder skill
评估一下 product-design skill

# Evaluate a LangChain tool
看看我的 LangChain 工具写得好不好
```

---

## Evaluation Report Example

```markdown
# Skill Quality Report: my-awesome-skill

**Overall Score: 3.8/5**

| Dimension | Score | Status |
|-----------|-------|--------|
| Trigger Accuracy | 4.0 | ✓ Good |
| Description Clarity | 3.5 | ⚠ Needs Work |
| Structure Completeness | 4.0 | ✓ Good |
| Actionability | 3.5 | ⚠ Needs Work |

## Issues Found

### High Priority (Must Fix)
1. Missing `trigger_words` in `_meta.json`
2. Description is 247 characters (recommend <100)

### Medium Priority (Recommended)
1. Add "When NOT to Use" section
2. Clarify vague phrase "when appropriate"
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
